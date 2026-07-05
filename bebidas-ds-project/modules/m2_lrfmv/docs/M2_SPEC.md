# M2_SPEC_CANONICO_v2 — Scoring, Clusterización y Churn de Clientes B2B

**Proyecto:** Sistema de Data Science para distribución B2B de bebidas  
**Módulo:** Módulo 2 — Scoring, Clusterización y Churn de Clientes  
**Versión:** Canónica v3 — revisión final con guardrails de datos, categorías, churn dormido y umbral dinámico  
**Fecha:** 2026-07-05  
**Estado:** Spec único de trabajo para notebook, scripts y posterior integración con FastAPI/Supabase.

---

## 1. Problema de negocio

La empresa distribuidora de bebidas no cuenta con una visión estructurada del comportamiento de sus clientes del canal tradicional —bodegas, minimarkets, restaurantes y comercios similares—. No sabe con claridad qué clientes están en riesgo de abandono, cuáles tienen mayor valor comercial, cuáles tienen potencial de crecimiento ni cómo priorizar la cartera para asignar mejor el esfuerzo de los preventistas.

Esta falta de segmentación provoca pérdida de clientes de alto valor, visitas comerciales poco priorizadas y dificultad para conectar el diagnóstico comercial del cliente con el perfil más adecuado de preventista en el Módulo 3.

---

## 2. Objetivos del Módulo 2

El Módulo 2 transforma el historial transaccional de clientes B2B en una segmentación comercial accionable.

Debe producir tres salidas principales:

1. **Score LRFMV 0-100:** indicador continuo de prioridad comercial del cliente.
2. **Cluster comercial:** etiqueta de segmento: `Diamante`, `Oro`, `Plata`, `Bronce` o `Nuevo`.
3. **Riesgo de churn:** indicador de posible pérdida o deterioro del cliente, sujeto a elegibilidad histórica.

Objetivos específicos:

1. Segmentar clientes maduros en grupos homogéneos usando LRFMV y K-Means.
2. Identificar clientes nuevos mediante regla de negocio, no mediante K-Means.
3. Identificar clientes en riesgo de abandono usando `delta_frequency` y un umbral dinámico de `recency_days` por cluster.
4. Identificar clientes de alto valor (`Diamante` y `Oro`) para proteger cartera y orientar asignación de preventistas `Farmer`.
5. Identificar clientes `Bronce` y `Nuevo` que pueden ser abordados por perfiles `Hunter`.
6. Entregar a M3 la tabla `gold.clients_clustered` como insumo del motor de matching preventista-cliente.
7. Garantizar reproducibilidad mediante persistencia de parámetros de escalado, modelo K-Means y reglas de negocio.

---

## 3. Principio arquitectónico

**Supabase no computa, persiste. FastAPI es el motor.**

Supabase se usa como base PostgreSQL para persistir capas `bronze`, `silver` y `gold`, además de almacenar artefactos del modelo cuando el pipeline se lleve a producción.

FastAPI orquesta el pipeline completo:

```text
lectura de datos → validación → feature engineering → escalado → clustering → scoring → churn → persistencia
```

En etapa académica/desarrollo local, el pipeline puede ejecutarse primero en notebook o scripts con CSV para validar lógica. La integración posterior con Supabase debe respetar la misma arquitectura Medallion.

---

## 4. Estado actual del dataset

El dataset sintético ya existe y ya fue revisado en EDA inicial.

Archivos disponibles:

| Archivo | Filas | Rol |
|---|---:|---|
| `clients_raw.csv` | 500 | Dimensión/catálogo de clientes |
| `transactions_raw.csv` | 68,483 | Tabla de hechos transaccionales |
| `_ground_truth.csv` | 500 | Validación sintética auxiliar |

Por tanto, el siguiente trabajo no es diseñar el dataset sintético desde cero, sino implementar el pipeline del Módulo 2 sobre estos datos ya generados y validados exploratoriamente.

---

## 5. Datasets de entrada

### 5.1 `clients_raw.csv`

Representa la dimensión/catálogo de clientes, conceptualmente `dim_clientes`.

Columnas reales esperadas:

```text
client_id
business_name
store_type
zone
latitude
longitude
registration_date
```

Uso principal:

- `client_id`: llave de unión con transacciones.
- `registration_date`: fuente oficial y única para calcular `length_days`.
- `store_type`, `zone`, `latitude`, `longitude`: variables descriptivas para análisis y visualización; no entran al K-Means LRFMV en esta versión.

### 5.2 `transactions_raw.csv`

Representa la tabla de hechos transaccionales.

Columnas reales esperadas:

```text
transaction_id
client_id
date
amount
sku_count
categories_purchased
```

Uso principal:

- `date`: fecha de transacción. En el código puede parsearse como `transaction_date`, pero Bronze debe preservar el contrato real del CSV.
- `amount`: base para calcular `monetary`.
- `categories_purchased`: base para calcular `volume`.
- `sku_count`: se conserva en Bronze por trazabilidad, pero se excluye del modelo LRFMV.

### 5.3 `_ground_truth.csv`

Archivo auxiliar de validación sintética.

Columnas esperadas:

```text
client_id
archetype_initial
trajectory_type
inflection_month
expected_cluster_tentative
expected_cluster_jun2025
```

Uso:

- No se usa para entrenar K-Means.
- No se usa para calcular score.
- No es target supervisado.
- Puede persistirse como `bronze.ground_truth` o leerse directamente desde `data/` durante validación.
- Sirve para comparar exploratoriamente si los clusters descubiertos se parecen a la distribución sintética esperada.

`expected_cluster_jun2025` está nulo en la versión actual, por lo que no debe usarse como criterio de validación.

---

## 6. Arquitectura Medallion del Módulo 2

### 6.1 Bronze — datos crudos

Tablas:

```text
bronze.clients_raw
bronze.transactions_raw
bronze.ground_truth
```

Responsabilidad:

- preservar datos de entrada;
- validar columnas obligatorias;
- no aplicar transformaciones de negocio;
- mantener trazabilidad del dataset sintético.

Campos esperados en `bronze.clients_raw`:

```text
client_id
business_name
store_type
zone
latitude
longitude
registration_date
```

Campos esperados en `bronze.transactions_raw`:

```text
transaction_id
client_id
date
amount
sku_count
categories_purchased
```

Campos esperados en `bronze.ground_truth`:

```text
client_id
archetype_initial
trajectory_type
inflection_month
expected_cluster_tentative
expected_cluster_jun2025
```

### 6.2 Silver — feature engineering

Tabla:

```text
silver.clients_features
```

Responsabilidad:

- construir variables LRFMV crudas;
- calcular `delta_frequency`;
- calcular flags de madurez e historial;
- calcular elegibilidad para churn;
- conservar variables interpretables de negocio.

Campos recomendados:

```text
client_id
snapshot_date
registration_date
first_observed_purchase_date
last_purchase_date
has_observed_transactions
has_recent_window_transactions
transaction_before_registration_flag
length_days
recency_days
frequency
monetary
volume
n_transactions_total
frequency_last_3_months
frequency_previous_3_months
delta_frequency
es_nuevo
low_history_flag
churn_eligible
```

Reglas para clientes sin transacciones observadas:

- Si un cliente no tiene transacciones observadas, entonces `has_observed_transactions = False`.
- Para que el pipeline no genere nulos en variables de modelamiento, se asigna `frequency = 0`, `monetary = 0` y `volume = 0`.
- `first_observed_purchase_date` y `last_purchase_date` quedan en `NULL`.
- Para score y reglas operativas, `recency_days` se imputa como `length_days`, interpretado como días desde el registro sin compra observada.
- Estos clientes mantienen `low_history_flag = True` y no son elegibles para churn.

Decisión cerrada sobre `Length`:

- `length_days` se calcula desde `registration_date`, proveniente de `bronze.clients_raw`.
- `first_observed_purchase_date` se calcula desde `bronze.transactions_raw` solo como variable auxiliar de auditoría transaccional.
- `first_observed_purchase_date` no reemplaza a `registration_date` y no se usa para calcular `Length`.
- No debe aplicarse fallback silencioso del tipo `length_days = snapshot_date - first_observed_purchase_date` si falta `registration_date`; ese caso debe tratarse como problema de calidad de datos o marcarse explícitamente con un flag de imputación.

Guardrail de calidad detectado en la revisión final:

- En el dataset sintético actual existen transacciones con `date < registration_date`.
- Esto no cambia la definición metodológica de `Length`: `registration_date` sigue siendo la fuente oficial de `length_days`.
- Estos casos deben marcarse con `transaction_before_registration_flag = True` para auditoría.
- En producción, este caso debería revisarse con el negocio o bloquearse según la severidad definida.
- En la versión académica se permite continuar porque el dataset es sintético, pero el flag debe quedar documentado para no ocultar la inconsistencia temporal.

### 6.3 Silver — transformaciones y normalización

Tabla:

```text
silver.clients_normalized
```

Responsabilidad:

- guardar variables transformadas;
- guardar variables normalizadas para score;
- guardar variables estandarizadas para K-Means;
- guardar el score LRFMV calculado en escala 0-100 o dejarlo listo para Gold.

Debe incluir dos ramas de transformación.

#### Rama para score

```text
MinMaxScaler.fit() sobre toda la población de clientes.
```

Variables resultantes:

```text
L_minmax
R_log
R_minmax
R_score
F_minmax
M_log
M_minmax
V_minmax
score_lrfmv_0_100
```

#### Rama para K-Means

```text
StandardScaler.fit() solo sobre clientes maduros: es_nuevo = False.
```

Variables resultantes:

```text
L_standard
R_log_standard
F_standard
M_log_standard
V_standard
```

Solo se usan para clustering en clientes maduros.

### 6.4 Silver — parámetros

Tablas o archivos recomendados:

```text
silver.standard_scaler_params
silver.score_scaler_params
```

Responsabilidad:

- persistir medias y desviaciones estándar del `StandardScaler`;
- persistir mínimos y máximos del `MinMaxScaler`;
- permitir inferencia con `transform()` sin recalcular parámetros.

### 6.5 Gold — salida comercial

Tabla:

```text
gold.clients_clustered
```

Responsabilidad:

- guardar score final;
- guardar etiqueta comercial;
- guardar origen de la etiqueta;
- guardar umbral dinámico de churn por cluster;
- guardar resultado final de churn;
- dejar una salida lista para el Módulo 3.

Campos recomendados:

```text
client_id
snapshot_date
score_lrfmv_0_100
es_nuevo
low_history_flag
churn_eligible
cluster_id
cluster_label
cluster_source
cluster_profile
median_F_cluster
purchase_cycle_days
churn_threshold_days
is_churn_risk
```

Valores esperados:

```text
cluster_label ∈ {Diamante, Oro, Plata, Bronce, Nuevo}
cluster_source ∈ {kmeans, business_rule}
is_churn_risk ∈ {True, False, NULL}
```

---

## 7. Ventana de análisis y snapshot

El dataset sintético contiene transacciones hasta junio de 2025. La versión actual del pipeline trabaja con un `snapshot_date` al final del período disponible:

```text
snapshot_date = 2025-06-30
```

Las variables de comportamiento reciente se calculan sobre una ventana de 180 días:

```text
ANALYSIS_WINDOW_DAYS = 180
```

Justificación:

1. `delta_frequency` necesita comparar dos ventanas de 90 días.
2. La ventana de 180 días captura comportamiento reciente sin dejar que clientes antiguos acumulen ventaja mecánica en F, M y V.
3. `Length` captura antigüedad; F, M y V capturan comportamiento comercial reciente.

Por tanto:

- `length_days` usa antigüedad desde `registration_date` hasta `snapshot_date`.
- `frequency`, `monetary` y `volume` usan la ventana reciente de 180 días.
- `recency_days` usa la última compra observada hasta `snapshot_date`.
- `delta_frequency` compara últimos 90 días vs. los 90 días anteriores.

Nota para defensa:

> Aunque LRFMV incluye Length para capturar antigüedad, Frequency, Monetary y Volume se calculan sobre una ventana reciente de 180 días. Esto evita que los clientes más antiguos acumulen ventaja solo por haber tenido más tiempo de compra. La antigüedad queda representada por Length, mientras que F, M y V capturan comportamiento comercial reciente.

---

## 8. Variables LRFMV

| Variable | Campo final | Definición | Interpretación comercial |
|---|---|---|---|
| Length | `length_days` | Días desde `registration_date` hasta `snapshot_date` | Antigüedad de relación comercial |
| Recency | `recency_days` | Días desde la última compra hasta `snapshot_date` | Qué tan reciente es la actividad |
| Frequency | `frequency` | Número de compras en los últimos 180 días | Intensidad de compra reciente |
| Monetary | `monetary` | Monto total comprado en los últimos 180 días | Valor económico reciente |
| Volume | `volume` | Número de categorías distintas compradas en los últimos 180 días | Penetración de portafolio |

### 8.1 Length

```text
length_days = snapshot_date - registration_date
```

`registration_date` es la fuente oficial de antigüedad comercial porque representa desde cuándo la bodega existe como cliente registrado en la distribuidora.

No se debe calcular `Length` desde la primera compra observada:

```text
NO usar: length_days = snapshot_date - first_observed_purchase_date
```

`first_observed_purchase_date` puede conservarse en Silver como campo auxiliar para auditoría y análisis de calidad, pero no forma parte de la definición de `Length`. La razón es que la primera transacción observada puede depender de la ventana disponible, de datos faltantes o de una demora inicial entre registro y primera compra. Si se usara como fuente de `Length`, un cliente registrado hace mucho tiempo pero con pocas compras observadas podría quedar artificialmente clasificado como nuevo.

Por tanto, en este proyecto:

```text
Length = antigüedad de relación comercial registrada
first_observed_purchase_date = primera compra observada en transacciones, solo auxiliar
```

### 8.2 Recency

```text
recency_days = snapshot_date - last_purchase_date
```

Recency tiene interpretación inversa:

```text
menor recency_days = mejor comportamiento reciente
mayor recency_days = mayor urgencia comercial
```

Para el score se invierte después de aplicar log y MinMaxScaler:

```text
R_score = 1 - R_minmax
```

### 8.3 Frequency

```text
frequency = count(transaction_id) en los últimos 180 días
```

No se aplica `log1p` a Frequency en esta versión porque su skew observado es moderado. Transformarla con log puede sobrecorregir la distribución y comprimir diferencias comerciales útiles.

### 8.4 Monetary

```text
monetary = sum(amount) en los últimos 180 días
```

Se conserva `monetary` crudo para interpretación de negocio, pero para score y K-Means se usa:

```text
M_log = log1p(monetary)
```

### 8.5 Volume

`categories_purchased` llega como string delimitado:

```text
gaseosas|agua|jugos
```

La variable `volume` se calcula como el número de categorías distintas compradas por cliente en la ventana de 180 días.

Categorías reales existentes en el CSV actual:

```text
gaseosas
agua
jugos
energeticas
```

Nota importante: en el CSV la categoría aparece como `energeticas` sin tilde. El pipeline debe validar contra el valor crudo sin tilde. Si en reportes se desea mostrar `energéticas`, esa conversión debe hacerse solo como etiqueta de presentación, no como valor esperado del contrato Bronze.

Ejemplo conceptual:

```text
categorías del cliente en la ventana = {gaseosas, agua, jugos, energeticas}
volume = 4
```

`Volume` no debe interpretarse como conteo de SKUs individuales. En el dataset actual, V es discreta y acotada en el rango 0-4, por lo que no se aplica `log1p`.

### 8.6 Exclusión de `sku_count`

`sku_count` se conserva en Bronze, pero no se usa como variable del modelo LRFMV.

La razón no es que esté capturada por `amount`. Son dimensiones distintas:

- `amount` mide valor económico.
- `sku_count` mide granularidad intra-categoría.
- `volume` mide amplitud estratégica del portafolio a nivel de categorías.

El Módulo 2 no busca recomendar productos específicos, sino segmentar clientes, identificar churn y alimentar matching preventista-cliente. Para este objetivo, `volume` por categorías es más interpretable y menos ruidoso que `sku_count`.

---

## 9. Delta frequency

`delta_frequency` mide cambio de frecuencia reciente:

```text
delta_frequency = frequency_last_3_months - frequency_previous_3_months
```

Donde:

```text
frequency_last_3_months     = compras entre snapshot_date - 90 días y snapshot_date
frequency_previous_3_months = compras entre snapshot_date - 180 días y snapshot_date - 91 días
```

Interpretación:

```text
delta_frequency < 0  → caída de frecuencia
delta_frequency = 0  → estabilidad
delta_frequency > 0  → mejora de frecuencia
```

La variable requiere una ventana mínima de 180 días para ser comparable.

---

## 10. Cliente nuevo y bajo historial

### 10.1 Cliente nuevo

La etiqueta `Nuevo` no se obtiene por K-Means. Se define por regla de negocio basada solo en antigüedad:

```text
NEW_CLIENT_WINDOW_DAYS = 180
es_nuevo = length_days < 180
```

Justificación:

`delta_frequency` compara dos ventanas de tres meses. Un cliente con menos de 180 días aún no posee una ventana histórica completa para evaluar deterioro de frecuencia.

### 10.2 Bajo historial transaccional

La baja cantidad de transacciones se modela con un flag independiente:

```text
MIN_TRANSACTIONS_FOR_CHURN = 3
low_history_flag = n_transactions_total < 3
```

Este flag no convierte al cliente en `Nuevo`.

`n_transactions_total` se calcula sobre todo el historial observado hasta `snapshot_date`, no solo sobre la ventana de 180 días. La razón es que `low_history_flag` mide cantidad de evidencia transaccional disponible para evaluar churn, mientras que `frequency` mide comportamiento reciente para score y clustering.

### 10.3 Diferencia conceptual

| Fenómeno | Regla | Campo |
|---|---|---|
| Cliente reciente / onboarding | `length_days < 180` | `es_nuevo` |
| Cliente con poca evidencia transaccional | `n_transactions_total < 3` | `low_history_flag` |

No usar:

```text
es_nuevo = length_days < 180 OR n_transactions_total < 3
```

porque mezcla antigüedad con volumen de evidencia.

---

## 11. Elegibilidad para churn

El churn no debe evaluarse en clientes nuevos ni en clientes con bajo historial.

```text
churn_eligible = (
    es_nuevo == False
    AND low_history_flag == False
    AND delta_frequency IS NOT NULL
)
```

Si el cliente no es elegible:

```text
is_churn_risk = NULL
```

Casos esperados:

| Cliente | `length_days` | `n_transactions_total` | `es_nuevo` | `low_history_flag` | `churn_eligible` | `is_churn_risk` |
|---|---:|---:|---|---|---|---|
| A | 15 | 1 | True | True | False | NULL |
| B | 15 | 4 | True | False | False | NULL |
| C | 400 | 2 | False | True | False | NULL |
| D | 400 | 10 | False | False | True | True/False |

---

## 12. Transformaciones por skewness

Antes del escalado se evalúa la asimetría de las variables LRFMV.

Resultados actuales observados:

| Variable | Skew observado | Decisión |
|---|---:|---|
| `R` | 2.43 | Aplicar `log1p` |
| `M` | 2.34 | Aplicar `log1p` |
| `F` | 0.74 | No aplicar `log1p` |
| `V` | -0.62 | No aplicar `log1p` |
| `L` | -1.16 | No aplicar `log1p` |

Regla metodológica:

```text
Si skew > 1.0 → aplicar log1p para asimetría positiva fuerte.
Si -1.0 <= skew <= 1.0 → mantener crudo.
Si skew < -1.0 → no aplicar log1p automáticamente; revisar histograma.
```

Decisión final para esta versión:

```text
R_log = log1p(recency_days)
M_log = log1p(monetary)
```

Variables sin log:

```text
L
F
V
```

Justificaciones:

- `M` tiene cola positiva fuerte: pocos clientes concentran montos altos.
- `R` tiene cola positiva fuerte: algunos clientes llevan muchos días sin comprar.
- `F` tiene skew moderado; aplicar log puede sobrecorregir y comprimir diferencias útiles de frecuencia.
- `V` es discreta y acotada en rango 0-4; log distorsionaría una variable casi ordinal.
- `L` tiene skew negativo; `log1p` está pensado principalmente para colas positivas.

---

## 13. Orden exacto de transformación para Recency

Para el score LRFMV, el orden correcto es:

```text
1. R_log = log1p(recency_days)
2. R_minmax = MinMaxScaler(R_log)
3. R_score = 1 - R_minmax
```

Flujo correcto:

```text
recency_days → log1p → MinMaxScaler → 1 - R_minmax
```

Flujo incorrecto:

```text
recency_days → 1 - recency_days → log1p
```

Razón:

- `recency_days` aún no está en escala 0-1 antes del MinMaxScaler.
- La inversión solo tiene sentido después de normalizar.
- La inversión pertenece al score, no al cálculo de churn.

Para K-Means:

```text
recency_days → log1p → StandardScaler
```

No se aplica `1 - R_minmax` en K-Means. La interpretación del centroide debe recordar que menor `recency_days` es mejor.

Para churn:

```text
recency_days crudo
```

No se usa `R_log` ni `R_score` porque el umbral de churn debe interpretarse en días.

---

## 14. Escalamiento diferenciado

El pipeline usa dos escaladores porque responden a objetivos distintos.

| Uso | Objetivo | Escalador | Población de ajuste |
|---|---|---|---|
| Score LRFMV | Índice interpretable 0-100 | MinMaxScaler | Todos los clientes |
| K-Means | Distancia euclidiana entre clientes | StandardScaler | Solo clientes maduros (`es_nuevo = False`) |

### 14.1 MinMaxScaler para score

Se ajusta sobre toda la cartera:

```text
MinMaxScaler.fit() sobre todos los clientes
```

Incluye:

```text
es_nuevo = True
es_nuevo = False
low_history_flag = True
low_history_flag = False
```

Justificación:

El score debe ser comparable para toda la cartera. Un cliente `Nuevo` y un cliente `Diamante` pueden compararse por prioridad comercial, aunque pertenezcan a segmentos distintos.

Variables usadas para score:

```text
L
R_log
F
M_log
V
```

Variables resultantes:

```text
L_minmax
R_minmax
R_score
F_minmax
M_minmax
V_minmax
```

En inferencia, usar:

```text
MinMaxScaler.transform()
```

Nunca usar `fit_transform()` sobre datos nuevos.

Como guardrail de producción se permite:

```text
clip(0, 1)
```

para evitar valores fuera del rango entrenado.

### 14.2 StandardScaler para K-Means

Se ajusta solo sobre clientes maduros:

```text
StandardScaler.fit() sobre clientes WHERE es_nuevo = False
```

Variables usadas para clustering:

```text
L
R_log
F
M_log
V
```

Variables resultantes:

```text
L_standard
R_log_standard
F_standard
M_log_standard
V_standard
```

Justificación:

K-Means usa distancia euclidiana. StandardScaler evita que variables con mayor escala numérica dominen la distancia.

En inferencia, usar:

```text
StandardScaler.transform()
```

Nunca usar `fit_transform()` sobre datos nuevos.

---

## 15. Score LRFMV 0-100

El score se calcula para todos los clientes, incluyendo clientes nuevos.

Pesos definidos:

| Variable | Peso |
|---|---:|
| Frequency | 30% |
| Recency | 20% |
| Monetary | 20% |
| Volume | 20% |
| Length | 10% |

Fórmula:

```text
score_lrfmv =
    0.30 * F_minmax
  + 0.20 * R_score
  + 0.20 * M_minmax
  + 0.20 * V_minmax
  + 0.10 * L_minmax

score_lrfmv_0_100 = score_lrfmv * 100
```

Donde:

```text
R_score = 1 - R_minmax
```

Justificación de pesos:

- **Frequency — 30%:** señal más directa de actividad comercial recurrente; además alimenta `delta_frequency`.
- **Recency — 20%:** indica urgencia de intervención.
- **Monetary — 20%:** determina impacto económico.
- **Volume — 20%:** mide penetración del portafolio por categorías.
- **Length — 10%:** aporta contexto relacional, pero no debe dominar el score.

---

## 16. K-Means y población de clustering

K-Means no debe recibir clientes nuevos.

Población:

```text
kmeans_population = clientes WHERE es_nuevo = False
```

Número de clusters cerrado para esta versión:

```text
K-Means(k=4)
```

No se usa `k=5` ni rango `k=4-5` como decisión final. La quinta etiqueta comercial, `Nuevo`, se asigna fuera del modelo mediante regla de negocio.

Los cuatro clusters maduros se etiquetan posteriormente como:

```text
Diamante
Oro
Plata
Bronce
```

Parámetros recomendados:

```text
KMeans(
    n_clusters=4,
    random_state=42,
    n_init=10
)
```

---

## 17. Etiquetado de clusters

No se debe asumir que `cluster_id = 0` significa `Diamante`.

Los IDs de K-Means son arbitrarios:

```text
cluster_id = 0, 1, 2, 3
```

La etiqueta comercial se asigna después de perfilar centroides y métricas promedio.

Para cada cluster calcular:

```text
centroide promedio LRFMV
score promedio
frequency promedio
recency promedio
monetary promedio
volume promedio
length promedio
tamaño del cluster
proporción churn_eligible
proporción is_churn_risk
```

Perfil esperado:

| Etiqueta | Perfil esperado |
|---|---|
| Diamante | Alta frecuencia, alto monetary, alto volume, alta antigüedad, baja recency |
| Oro | Buen valor, buena frecuencia, relación estable, ligeramente inferior a Diamante |
| Plata | Comportamiento medio, útil para cobertura operativa |
| Bronce | Baja frecuencia, bajo monetary/volume o alta recency |

Regla conceptual:

```text
cluster_id no tiene significado.
cluster_profile sí tiene significado.
```

---

## 18. Integración de clientes Nuevo en Gold

Clientes con:

```text
es_nuevo = True
```

no pasan por K-Means.

En Gold reciben:

```text
cluster_id = NULL
cluster_label = "Nuevo"
cluster_source = "business_rule"
```

Clientes maduros reciben:

```text
cluster_id = 0 | 1 | 2 | 3
cluster_label = "Diamante" | "Oro" | "Plata" | "Bronce"
cluster_source = "kmeans"
```

---

## 19. Churn final dinámico por cluster

La elegibilidad para churn se calcula en Silver. El resultado final de churn se calcula en Gold porque depende de `cluster_label`, y `cluster_label` solo existe después de ejecutar K-Means y etiquetar los clusters.

### 19.1 En Silver

Silver responde:

```text
¿El cliente tiene suficiente madurez e historial para evaluar churn?
```

Regla:

```text
churn_eligible = (
    es_nuevo == False
    AND low_history_flag == False
    AND delta_frequency IS NOT NULL
)
```

Si el cliente no es elegible:

```text
is_churn_risk = NULL
```

### 19.2 Antecedente v1: umbral fijo de 14 días

En una primera versión implementable se usó:

```text
BASE_CHURN_THRESHOLD_DAYS = 14
```

Esa regla era una simplificación inicial basada en el ciclo operativo de visita del preventista: si una bodega no compraba durante aproximadamente dos semanas, se consideraba una posible señal temprana de abandono.

Esta regla fue útil para una v1 porque permitía implementar y probar el flujo completo de churn sin depender todavía de los clusters. Sin embargo, no queda como regla final activa, porque trata igual a clientes con ritmos de compra muy diferentes.

Ejemplo de negocio:

```text
Diamante: puede comprar cada 3-4 días.
Bronce: puede comprar cada 25-30 días.
```

Aplicar `14 días sin comprar = alerta` a ambos produce distorsiones:

- En `Diamante`, 14 días pueden representar varios ciclos de compra perdidos.
- En `Bronce`, 14 días pueden estar todavía dentro de su ciclo normal.

Por tanto, el umbral fijo de 14 días se considera una simplificación defendible de v1, no un error; pero se reemplaza por un umbral dinámico por cluster en la versión final.

### 19.3 Regla final: umbral dinámico por cluster

Gold responde:

```text
Dado su segmento comercial, ¿el cliente está en riesgo de churn?
```

Primero se calcula la frecuencia típica del cluster usando la mediana de `frequency` de clientes maduros y con frecuencia positiva:

```text
median_F_cluster = median(frequency)
                   WHERE cluster_label = cluster_actual
                   AND es_nuevo = False
                   AND frequency > 0
```

Este filtro evita que clientes sin compras recientes distorsionen el ciclo típico del segmento y previene divisiones por cero.

Luego se convierte esa frecuencia en ciclo esperado de compra:

```text
purchase_cycle_days = 180 / median_F_cluster
```

Interpretación:

```text
Si median_F_cluster = 6,
entonces purchase_cycle_days = 180 / 6 = 30 días.
```

Finalmente, el umbral de churn se define como el doble del ciclo esperado:

```text
CHURN_CYCLE_MULTIPLIER = 2
churn_threshold_days = purchase_cycle_days * CHURN_CYCLE_MULTIPLIER
```

Equivalente:

```text
churn_threshold_days = 2 * (180 / median_F_cluster)
```

Guardrail técnico:

```text
Si median_F_cluster IS NULL o median_F_cluster <= 0,
no se calcula purchase_cycle_days y el cluster debe revisarse como segmento inactivo o de baja evidencia.
```

Justificación del multiplicador `2`:

No conviene activar alerta apenas el cliente supera su ciclo esperado. Si un cliente compra normalmente cada 14 días, que pasen 15 o 16 días sin compra puede ser variación normal del negocio, no abandono. El multiplicador reduce falsos positivos y activa la alerta cuando la demora duplica el patrón esperado del segmento.

Regla final:

```text
is_churn_risk =
    churn_eligible == True
    AND recency_days > churn_threshold_days
    AND (
        delta_frequency < 0
        OR frequency_last_3_months == 0
    )
```



La condición adicional `frequency_last_3_months == 0` evita un falso negativo importante: clientes que ya están dormidos pueden tener `delta_frequency = 0` porque no compraron ni en los últimos 90 días ni en los 90 días anteriores. Sin esta condición, un cliente con alta `recency_days` y cero compras recientes podría quedar fuera del riesgo solo porque la caída ocurrió antes de la ventana comparativa.

Si:

```text
churn_eligible == False
```

entonces:

```text
is_churn_risk = NULL
```

### 19.4 Por qué el churn final vive en Gold y no en Silver

La fórmula dinámica necesita este dato:

```text
cluster_label
```

Pero `cluster_label` no existe en Silver. En Silver solo existen variables LRFMV, `delta_frequency`, `es_nuevo`, `low_history_flag` y `churn_eligible`.

`median_F_cluster` requiere agrupar clientes por `cluster_label`. Ese agrupamiento solo es posible después de:

```text
K-Means → perfilamiento de centroides → asignación de cluster_label
```

Por tanto, calcular `churn_threshold_days` en Silver generaría una dependencia circular. La separación correcta es:

```text
Silver: calcula elegibilidad para churn.
Gold: calcula umbral por cluster y resultado final de churn.
```

---

## 20. Flujo final del pipeline de entrenamiento

```text
1. Leer CSVs
   - clients_raw.csv
   - transactions_raw.csv
   - _ground_truth.csv solo para validación auxiliar

2. Validar contratos Bronze
   - columnas obligatorias
   - duplicados de client_id
   - duplicados de transaction_id
   - fechas válidas
   - amount > 0
   - categories_purchased válido

3. Construir silver.clients_features
   - parsear date como fecha de transacción
   - conservar registration_date desde clients_raw
   - calcular first_observed_purchase_date solo como auxiliar transaccional
   - calcular length_days desde registration_date
   - calcular recency_days
   - calcular frequency en ventana 180 días
   - calcular monetary en ventana 180 días
   - calcular volume como categorías distintas en ventana 180 días
   - calcular n_transactions_total
   - calcular has_observed_transactions
   - calcular has_recent_window_transactions
   - calcular transaction_before_registration_flag
   - calcular frequency_last_3_months
   - calcular frequency_previous_3_months
   - calcular delta_frequency
   - calcular es_nuevo
   - calcular low_history_flag
   - calcular churn_eligible

4. Evaluar skewness y documentar EDA
   - df[['L','R','F','M','V']].skew()
   - histogramas crudo vs log1p para R y M
   - matriz de correlación

5. Aplicar transformaciones
   - R_log = log1p(recency_days)
   - M_log = log1p(monetary)
   - F sin log
   - V sin log
   - L sin log

6. Calcular score LRFMV
   - MinMaxScaler.fit() sobre todos los clientes
   - R_score = 1 - R_minmax
   - aplicar pesos
   - score_lrfmv_0_100

7. Preparar clustering
   - filtrar clientes con es_nuevo = False
   - StandardScaler.fit() sobre clientes maduros
   - KMeans(k=4)

8. Etiquetar clusters
   - analizar centroides
   - asignar Diamante, Oro, Plata, Bronce

9. Integrar clientes nuevos
   - cluster_label = Nuevo
   - cluster_source = business_rule

10. Calcular churn final dinámico en Gold
    - calcular median_F_cluster por cluster_label maduro con frequency > 0
    - calcular purchase_cycle_days = 180 / median_F_cluster
    - calcular churn_threshold_days = 2 * purchase_cycle_days
    - si churn_eligible = False → is_churn_risk = NULL
    - si churn_eligible = True → aplicar recency_days + churn_threshold_days + (delta_frequency < 0 OR frequency_last_3_months = 0)

11. Persistir salida
    - gold.clients_clustered
    - scaler_params
    - kmeans_model.joblib
```

---

## 21. Modo inferencia

En inferencia no se recalculan parámetros de escalado ni se reentrena K-Means.

Flujo:

```text
1. Cargar artefactos
   - standard_scaler.joblib
   - kmeans_model.joblib
   - score_scaler_params
   - tabla/regla de churn_threshold_days por cluster, si se persiste

2. Calcular features LRFMV con la misma lógica de entrenamiento

3. Aplicar transformaciones
   - R_log = log1p(recency_days)
   - M_log = log1p(monetary)

4. Score
   - MinMaxScaler.transform()
   - clip(0, 1) si hay valores fuera de rango
   - R_score = 1 - R_minmax
   - score_lrfmv_0_100

5. Clustering
   - si es_nuevo = True → cluster_label = Nuevo
   - si es_nuevo = False → StandardScaler.transform() + kmeans.predict()

6. Churn
   - calcular churn_eligible
   - usar churn_threshold_days correspondiente al cluster_label
   - calcular is_churn_risk en Gold
```

Regla crítica:

```text
En inferencia se usa transform(), nunca fit_transform().
```

---

## 22. Artefactos producidos

### 22.1 Base de datos Medallion

| Artefacto | Schema | Tabla | Descripción |
|---|---|---|---|
| Clientes crudos | bronze | clients_raw | Dimensión de clientes |
| Transacciones crudas | bronze | transactions_raw | Historial transaccional |
| Ground truth auxiliar | bronze | ground_truth | Validación sintética |
| Features LRFMV | silver | clients_features | Variables crudas y flags |
| Features normalizadas | silver | clients_normalized | Variables para score y clustering |
| Parámetros StandardScaler | silver | standard_scaler_params | Medias y desviaciones para K-Means |
| Parámetros MinMaxScaler | silver | score_scaler_params | Mínimos y máximos para score |
| Salida comercial | gold | clients_clustered | Score, cluster y churn |

### 22.2 Supabase Storage / filesystem local

| Artefacto | Formato | Uso |
|---|---|---|
| K-Means | `.joblib` | Reutilizar centroides en inferencia |
| StandardScaler | `.joblib` | Transformar clientes maduros en inferencia |
| Score scaler params | `.json` / tabla | Normalizar score sin recalcular rangos |
| Churn thresholds por cluster | `.json` / tabla | Reutilizar umbrales dinámicos en inferencia |
| EDA outputs | `.csv`, `.json`, `.png` | Documentación y defensa |

---

## 23. Validación técnica

### 23.1 Data quality Bronze

Validaciones mínimas:

```text
clientes en maestro
clientes con transacciones
clientes sin transacciones
transacciones sin cliente maestro
duplicados en client_id
duplicados en transaction_id
fechas inválidas
amount <= 0
categories_purchased vacío o mal formado
```

Clientes sin transacciones no deben romper el pipeline. Deben conservarse en la cartera con flags adecuados y valores controlados.

### 23.2 EDA obligatorio antes de modelar

Debe documentarse:

```text
skewness de L, R, F, M, V
histogramas crudos vs log1p para R y M
matriz de correlación
boxplots de variables LRFMV
distribución de es_nuevo
distribución de low_history_flag
distribución de churn_eligible
```

### 23.3 Validación de clustering

Métricas:

```text
silhouette_score
elbow method
inertia
perfilamiento de centroides
```

Rango de evaluación para sustento:

```text
k = 2 a 8
```

Decisión cerrada para esta versión:

```text
k = 4 para clientes maduros
```

Elbow y silhouette se usan para defender que k=4 es razonable, pero la quinta etiqueta comercial `Nuevo` se asigna fuera del modelo por regla de negocio.

### 23.4 Validación con ground truth sintético

`_ground_truth.csv` se usa solo como referencia auxiliar.

Validaciones posibles:

```text
tabla cruzada cluster_label vs expected_cluster_tentative
proporción de coincidencia aproximada
revisión de trajectory_type vs delta_frequency
revisión de inflection_month vs señales de caída
```

No debe usarse como target supervisado.

---

## 24. Validación de negocio

Cada cluster debe interpretarse en unidades reales.

Para defensa, se debe mostrar una tabla de perfil:

| cluster_label | n_clientes | score_promedio | L_promedio | R_promedio | F_promedio | M_promedio | V_promedio | median_F_cluster | purchase_cycle_days | churn_threshold_days | churn_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Diamante | | | | | | | | | | | |
| Oro | | | | | | | | | | | |
| Plata | | | | | | | | | | | |
| Bronce | | | | | | | | | | | |
| Nuevo | | | | | | | | NULL | NULL | NULL | NULL |

Criterios esperados:

- `Diamante`: score alto, frecuencia alta, monetary alto, volume alto, recency baja.
- `Oro`: buen valor y estabilidad, inferior a Diamante.
- `Plata`: comportamiento medio, útil para cobertura.
- `Bronce`: baja actividad, baja penetración o alta recency.
- `Nuevo`: antigüedad menor a 180 días, no evaluable para churn.

---

## 25. Relación con Módulo 3

Módulo 3 consume:

```text
gold.candidates_final
gold.clients_clustered
```

Del Módulo 1 recibe:

```text
salesperson_type = Hunter | Farmer | Ejecutor
```

Del Módulo 2 recibe:

```text
client_id
cluster_label
score_lrfmv_0_100
is_churn_risk
```

Matriz conceptual de compatibilidad:

| Cluster cliente | Preventista recomendado | Justificación |
|---|---|---|
| Diamante | Farmer | Retención, ticket y relación |
| Oro | Farmer | Desarrollo y protección |
| Plata | Ejecutor | Cobertura operativa |
| Bronce | Hunter | Reactivación selectiva |
| Nuevo | Hunter | Prospección y onboarding |

El score se usa para priorizar clientes dentro de cada segmento.

---

## 26. Límites de alcance

### 26.1 Sin predicción de ventas

M2 no predice volumen de ventas futuro. Su objetivo es segmentar y priorizar clientes por comportamiento histórico.

### 26.2 Sin recomendación a nivel SKU

M2 no recomienda marca, sabor, presentación o botella específica. Usa `volume` como amplitud de portafolio a nivel de categorías.

### 26.3 Sin procesamiento en tiempo real

El sistema opera por lotes. No contempla webhooks ni conexión en tiempo real al sistema de ventas.

### 26.4 Sin validación con datos reales

La versión académica usa datos sintéticos con distribuciones intencionales. La validación con ventas reales queda como trabajo futuro.

---

## 27. Revisión final v3 — puntos que no deben pasarse por alto

La última revisión detectó cinco puntos que podían causar ambigüedad o errores de implementación:

1. **Categoría `energeticas` sin tilde:** el contrato Bronze debe validar el valor crudo `energeticas`, no `energéticas`. La tilde solo puede usarse como etiqueta de presentación.
2. **Transacciones anteriores a `registration_date`:** el dataset sintético contiene casos con `date < registration_date`. No se cambia la definición de `Length`, pero se agrega `transaction_before_registration_flag` para auditoría.
3. **Clientes sin transacciones observadas:** deben conservarse sin romper el pipeline. Se agregan flags y reglas de imputación controlada para F, M, V y R.
4. **Ambigüedad de `n_transactions`:** se reemplaza por `n_transactions_total` para dejar claro que `low_history_flag` usa historial total observado, mientras `frequency` usa la ventana reciente de 180 días.
5. **Churn en clientes ya dormidos:** la regla final incluye `frequency_last_3_months == 0` además de `delta_frequency < 0`, porque un cliente puede tener `delta_frequency = 0` si ya no compró en ninguna de las dos subventanas.

---

## 28. Decisiones cerradas

| Decisión | Estado |
|---|---|
| Dataset sintético ya existe: 68,483 transacciones y 500 clientes | Cerrado |
| Valor crudo de categoría es `energeticas` sin tilde | Cerrado |
| Transacciones anteriores a `registration_date` se marcan con `transaction_before_registration_flag` | Cerrado |
| Clientes sin transacciones se conservan con imputación controlada y flags | Cerrado |
| `Length` se calcula desde `registration_date`, no desde primera compra observada | Cerrado |
| `first_observed_purchase_date` queda solo como campo auxiliar de auditoría | Cerrado |
| `Volume` mide categorías distintas compradas, no SKUs individuales | Cerrado |
| Categorías actuales: gaseosas, agua, jugos, energeticas | Cerrado |
| `sku_count` se conserva en Bronze pero se excluye del modelo LRFMV | Cerrado |
| `Nuevo` depende solo de antigüedad | Cerrado |
| Umbral de nuevo = 180 días | Cerrado |
| `low_history_flag` separado de `es_nuevo` | Cerrado |
| Clientes nuevos no son evaluables para churn | Cerrado |
| `churn_eligible` vive en Silver | Cerrado |
| `is_churn_risk` final vive en Gold | Cerrado |
| Umbral fijo de 14 días fue simplificación v1, no regla final activa | Cerrado |
| Churn final usa umbral dinámico por cluster: `2 * (180 / median_F_cluster)` | Cerrado |
| Churn incluye `frequency_last_3_months == 0` para capturar clientes ya dormidos | Cerrado |
| Churn usa `recency_days` crudo, no `R_log` | Cerrado |
| Score LRFMV se calcula para todos los clientes | Cerrado |
| MinMaxScaler del score se ajusta sobre población completa | Cerrado |
| StandardScaler de K-Means se ajusta solo sobre clientes maduros | Cerrado |
| K-Means usa `k=4` fijo | Cerrado |
| `Nuevo` no sale de K-Means | Cerrado |
| Etiquetas de clusters se asignan por centroides, no por `cluster_id` | Cerrado |
| `M` usa `log1p` | Cerrado |
| `R` usa `log1p` | Cerrado |
| `F` no usa `log1p` porque sobrecorrige skew | Cerrado |
| `V` no usa `log1p` porque es discreta y acotada | Cerrado |
| `L` no usa `log1p` por skew negativo | Cerrado |

---

## 29. Respuesta esperada para defensa

> El Módulo 2 usa LRFMV porque en distribución B2B no basta con saber cuánto compra un cliente; también importa desde cuándo existe la relación, qué tan reciente fue la última compra, con qué frecuencia compra y qué tan amplio es el portafolio adquirido. En este proyecto, `Length` se calcula desde `registration_date`, porque representa la antigüedad comercial registrada de la bodega; la primera compra observada queda solo como variable auxiliar de auditoría. `Volume` no mide SKUs individuales, sino categorías distintas compradas, porque el objetivo del módulo es medir penetración estratégica del portafolio, no granularidad intra-categoría. La categoría `Nuevo` no se obtiene por K-Means, sino por una regla de negocio basada en antigüedad menor a 180 días, porque `delta_frequency` necesita comparar dos ventanas de tres meses. Por eso los clientes nuevos no se evalúan como churn. El score se calcula para toda la cartera usando MinMaxScaler para mantener una escala común de 0 a 100, mientras que K-Means se entrena solo sobre clientes maduros con StandardScaler porque el algoritmo depende de distancias euclidianas. Se usa `k=4` fijo para descubrir los segmentos maduros Diamante, Oro, Plata y Bronce; la quinta etiqueta, Nuevo, se asigna fuera del modelo. Finalmente, el churn final se calcula en Gold con un umbral dinámico por cluster basado en `2 * (180 / median_F_cluster)`, reemplazando el umbral fijo de 14 días usado solo como simplificación inicial de v1. Además, la regla considera tanto caída de frecuencia (`delta_frequency < 0`) como ausencia total de compras en los últimos 90 días, para no dejar fuera clientes que ya están dormidos.

---

## 30. Orden recomendado de implementación

1. Validar contratos Bronze de los tres CSV.
2. Construir `silver.clients_features`.
3. Documentar EDA: skew, histogramas, correlación y calidad de datos.
4. Aplicar `log1p` a `R` y `M`.
5. Implementar MinMaxScaler y score LRFMV.
6. Implementar StandardScaler y K-Means k=4 sobre clientes maduros.
7. Perfilar centroides y etiquetar clusters.
8. Integrar clientes `Nuevo` en Gold.
9. Calcular umbrales dinámicos de churn por cluster en Gold.
10. Calcular `is_churn_risk` final.
11. Exportar `gold.clients_clustered` para M3.
