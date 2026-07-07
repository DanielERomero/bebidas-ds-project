# M2_SPEC_SIMPLE_v1 — Scoring, Segmentación y Churn de Clientes B2B

**Proyecto:** Sistema de Data Science para distribución B2B de bebidas  
**Módulo:** Módulo 2 — Scoring, Clusterización y Churn de Clientes  
**Versión:** Simple v1 — versión académica enfocada en aprendizaje  
**Fecha:** 2026-07-05  
**Estado:** Spec simplificado de trabajo para notebooks y defensa académica.

---

## 1. Propósito del módulo

El Módulo 2 transforma el historial de compras de clientes B2B —bodegas, minimarkets, restaurantes y negocios similares— en una salida comercial accionable.

La salida principal del módulo es una tabla de clientes con:

1. **Score LRFMV 0-100**: prioridad comercial del cliente.
2. **Cluster comercial**: `Diamante`, `Oro`, `Plata`, `Bronce` o `Nuevo`.
3. **Riesgo de churn**: alerta simple de posible abandono o deterioro.

Esta versión prioriza claridad, aprendizaje y explicabilidad. No busca ser una implementación productiva completa, sino una versión académica sólida y fácil de defender.

---

## 2. Enfoque simplificado

En esta versión se reduce la complejidad del diseño original.

Decisiones principales:

1. `Length` se calcula desde la **primera compra observada**, no desde `registration_date`.
2. Clientes sin transacciones se excluyen del modelamiento y se reportan aparte.
3. El churn usa una regla simple basada en `recency_days` y `delta_frequency`.
4. Se mantienen solo los campos necesarios para el análisis LRFMV.
5. Supabase y FastAPI quedan como propuesta futura, no como parte obligatoria de esta etapa.
6. La arquitectura Medallion se mantiene de forma conceptual y simple: Bronze, Silver y Gold.

Justificación general:

> Como el proyecto está en una fase de aprendizaje, se prioriza una versión entendible y ejecutable de punta a punta. Las reglas complejas de auditoría, inferencia productiva y persistencia avanzada se dejan como mejoras futuras.

---

## 3. Datasets de entrada

### 3.1 `clients_raw.csv`

Archivo de clientes.

Columnas esperadas:

```text
client_id
business_name
store_type
zone
latitude
longitude
registration_date
```

Uso en esta versión:

- `client_id`: llave para unir con transacciones.
- `business_name`, `store_type`, `zone`, `latitude`, `longitude`: variables descriptivas.
- `registration_date`: se conserva por trazabilidad, pero **no se usa para calcular Length**.

### 3.2 `transactions_raw.csv`

Archivo de transacciones.

Columnas esperadas:

```text
transaction_id
client_id
date
amount
sku_count
categories_purchased
```

Uso en esta versión:

- `date`: fecha de compra.
- `amount`: base para Monetary.
- `categories_purchased`: base para Volume.
- `sku_count`: se conserva, pero no se usa en LRFMV.

### 3.3 `_ground_truth.csv`

Archivo auxiliar del dataset sintético.

Uso:

- No se usa para entrenar modelos.
- No se usa para calcular score.
- Puede usarse solo como validación exploratoria opcional.

---

## 4. Arquitectura Medallion simplificada

La arquitectura se mantiene en tres capas, pero de forma ligera.

```text
Bronze → datos crudos
Silver → features LRFMV + score
Gold   → clusters + churn + salida comercial
```

### 4.1 Bronze

Responsabilidad:

- Cargar CSVs originales.
- Validar columnas mínimas.
- No aplicar reglas de negocio complejas.

Archivos/tablas conceptuales:

```text
bronze.clients_raw
bronze.transactions_raw
bronze.ground_truth
```

### 4.2 Silver

Responsabilidad:

- Construir variables LRFMV.
- Calcular `delta_frequency`.
- Calcular `es_nuevo`.
- Calcular `churn_eligible`.
- Calcular score LRFMV 0-100.

Salida conceptual:

```text
silver.clients_features
```

### 4.3 Gold

Responsabilidad:

- Aplicar K-Means.
- Etiquetar clusters comerciales.
- Integrar clientes nuevos.
- Calcular riesgo simple de churn.
- Exportar tabla final para negocio y para el Módulo 3.

Salida conceptual:

```text
gold.clients_clustered
```

---

## 5. Ventana de análisis

El dataset contiene transacciones hasta junio de 2025.

Fecha de corte:

```text
snapshot_date = 2025-06-30
```

Ventana reciente:

```text
ANALYSIS_WINDOW_DAYS = 180
```

Subventanas para `delta_frequency`:

```text
últimos 90 días
90 días anteriores
```

---

## 6. Regla para clientes sin transacciones

Los clientes sin historial transaccional no entran al modelamiento LRFMV.

Regla:

```text
Si un cliente no tiene ninguna transacción observada:
    excluir del score
    excluir de K-Means
    excluir de churn
    reportar en un archivo o tabla de calidad
```

Justificación:

> LRFMV se basa en comportamiento de compra. Si un cliente no tiene transacciones, no existe evidencia suficiente para calcular Frequency, Monetary, Volume, Recency ni Length transaccional.

En el dataset actual existen 2 clientes sin transacciones:

```text
CLI-0313
CLI-0315
```

Estos clientes se reportan aparte como:

```text
clientes_sin_transacciones.csv
```

No es necesario crear reglas especiales para imputarlos dentro del modelo.

---

## 7. Variables LRFMV simplificadas

En esta versión, LRFMV se calcula solo sobre clientes con al menos una transacción observada.

### 7.1 Length

Definición:

```text
length_days = snapshot_date - first_purchase_date
```

Donde:

```text
first_purchase_date = primera fecha de compra observada del cliente
```

Interpretación:

```text
Length = antigüedad transaccional observada
```

Justificación:

> Como el modelo LRFMV se basa en comportamiento de compra, se usa la primera compra observada como inicio del historial comercial medible del cliente. Esto simplifica el pipeline y evita discutir diferencias entre fecha administrativa de registro y fecha real de primera compra.

### 7.2 Recency

Definición:

```text
recency_days = snapshot_date - last_purchase_date
```

Donde:

```text
last_purchase_date = última compra observada del cliente hasta snapshot_date
```

Interpretación:

```text
menor recency_days = cliente más activo recientemente
mayor recency_days = cliente más alejado o potencialmente dormido
```

### 7.3 Frequency

Definición:

```text
frequency = número de compras en los últimos 180 días
```

Interpretación:

```text
mayor frequency = mayor recurrencia comercial reciente
```

### 7.4 Monetary

Definición:

```text
monetary = suma de amount en los últimos 180 días
```

Interpretación:

```text
mayor monetary = mayor valor económico reciente
```

### 7.5 Volume

Definición:

```text
volume = número de categorías distintas compradas en los últimos 180 días
```

La columna base es:

```text
categories_purchased
```

Ejemplo:

```text
gaseosas|agua|jugos
```

Categorías esperadas:

```text
gaseosas
agua
jugos
energeticas
```

Interpretación:

```text
mayor volume = mayor amplitud de portafolio comprado
```

`Volume` no mide SKUs individuales. Mide categorías distintas compradas.

---

## 8. Exclusión de `sku_count`

`sku_count` se conserva en los datos crudos, pero no entra al modelo LRFMV.

Justificación:

- `sku_count` mide granularidad de productos.
- `volume` mide amplitud de portafolio por categoría.
- El objetivo del Módulo 2 es segmentar clientes, no recomendar productos específicos.

Por tanto:

```text
sku_count se conserva para trazabilidad, pero no se usa en score ni K-Means.
```

---

## 9. Delta frequency

`delta_frequency` mide si la frecuencia reciente del cliente subió, bajó o se mantuvo.

Fórmula:

```text
delta_frequency = frequency_last_3_months - frequency_previous_3_months
```

Donde:

```text
frequency_last_3_months     = compras en los últimos 90 días
frequency_previous_3_months = compras entre 91 y 180 días antes del snapshot
```

Interpretación:

```text
delta_frequency < 0  → caída de frecuencia
delta_frequency = 0  → estabilidad
delta_frequency > 0  → mejora de frecuencia
```

---

## 10. Cliente nuevo

La etiqueta `Nuevo` no sale de K-Means.

Regla:

```text
NEW_CLIENT_WINDOW_DAYS = 180
es_nuevo = length_days < 180
```

Interpretación:

```text
Un cliente es Nuevo si tiene menos de 180 días de historial transaccional observado.
```

Justificación:

> `delta_frequency` compara dos ventanas de 90 días. Un cliente con menos de 180 días no tiene historial completo para comparar dos periodos equivalentes.

---

## 11. Elegibilidad para churn

El churn no se evalúa en clientes nuevos ni en clientes con muy pocas compras.

Regla simple:

```text
MIN_TRANSACTIONS_FOR_CHURN = 3

churn_eligible = (
    length_days >= 180
    AND n_transactions_total >= 3
)
```

Donde:

```text
n_transactions_total = número total de transacciones observadas del cliente hasta snapshot_date
```

Interpretación:

```text
Solo evaluamos churn si el cliente tiene suficiente antigüedad transaccional y evidencia mínima de compra.
```

---

## 12. Churn simplificado

En esta versión no se usa umbral dinámico por cluster.

Regla final:

```text
CHURN_RECENCY_THRESHOLD_DAYS = 60

is_churn_risk = (
    churn_eligible == True
    AND recency_days > 60
    AND delta_frequency <= 0
)
```

Interpretación:

Un cliente se considera en riesgo si:

1. Tiene suficiente historial para ser evaluado.
2. Lleva más de 60 días sin comprar.
3. Su frecuencia reciente no mejoró.

Justificación:

> Se usa un umbral fijo de 60 días porque representa un tercio de la ventana reciente de 180 días. En distribución de bebidas, pasar dos meses sin compra puede considerarse una señal razonable de alerta comercial en una versión académica simplificada.

Trabajo futuro:

```text
En una versión productiva, el umbral de churn podría ajustarse por cluster, zona o ciclo de compra histórico del cliente.
```

---

## 13. Transformaciones por asimetría

Antes del escalado se evalúa la asimetría de las variables LRFMV.

Decisión simple:

```text
Aplicar log1p a:
- recency_days
- monetary

No aplicar log1p a:
- length_days
- frequency
- volume
```

Variables transformadas:

```text
R_log = log1p(recency_days)
M_log = log1p(monetary)
```

Justificación:

- `monetary` suele tener cola positiva: pocos clientes concentran montos altos.
- `recency_days` puede tener cola positiva: algunos clientes llevan mucho tiempo sin comprar.
- `frequency` se mantiene cruda para no comprimir demasiado la recurrencia.
- `volume` es discreta y acotada.
- `length_days` se mantiene cruda para interpretación directa.

---

## 14. MinMaxScaler para score

El score LRFMV busca una escala interpretable de 0 a 100.

Por eso se usa:

```text
MinMaxScaler
```

Variables usadas:

```text
L = length_days
R = R_log
F = frequency
M = M_log
V = volume
```

Variables normalizadas:

```text
L_minmax
R_minmax
F_minmax
M_minmax
V_minmax
```

Como `Recency` tiene interpretación inversa:

```text
R_score = 1 - R_minmax
```

Flujo correcto para Recency:

```text
recency_days → log1p → MinMaxScaler → 1 - R_minmax
```

---

## 15. Score LRFMV 0-100

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

Justificación:

- `Frequency` recibe mayor peso porque la recurrencia de compra es la señal más importante en distribución de bebidas.
- `Recency` mide actividad reciente.
- `Monetary` mide valor económico.
- `Volume` mide amplitud del portafolio.
- `Length` aporta contexto de antigüedad transaccional, pero no debe dominar el score.

---

## 16. StandardScaler para K-Means

K-Means trabaja con distancias euclidianas.

Por eso se usa:

```text
StandardScaler
```

Variables usadas:

```text
L = length_days
R = R_log
F = frequency
M = M_log
V = volume
```

Variables estandarizadas:

```text
L_standard
R_log_standard
F_standard
M_log_standard
V_standard
```

Justificación:

> K-Means necesita que las variables estén en escalas comparables. Si no se estandarizan, variables como `monetary` o `length_days` podrían dominar la distancia y sesgar los clusters.

---

## 17. Población de clustering

K-Means no se aplica a clientes nuevos.

Regla:

```text
kmeans_population = clientes donde es_nuevo == False
```

Los clientes nuevos se asignan directamente a:

```text
cluster_label = "Nuevo"
cluster_source = "business_rule"
```

---

## 18. K-Means

Número de clusters:

```text
k = 4
```

Parámetros recomendados:

```text
KMeans(
    n_clusters=4,
    random_state=42,
    n_init=10
)
```

Los cuatro clusters maduros se etiquetan como:

```text
Diamante
Oro
Plata
Bronce
```

La quinta categoría, `Nuevo`, no viene de K-Means. Se asigna por regla de negocio.

Justificación:

> Se usa k=4 porque el negocio necesita cuatro segmentos maduros accionables: clientes de alto valor, clientes buenos, clientes medios y clientes de baja actividad. La etiqueta `Nuevo` se maneja fuera del modelo porque responde a antigüedad transaccional insuficiente.

---

## 19. Etiquetado de clusters

Los IDs de K-Means son arbitrarios.

No asumir:

```text
cluster_id = 0 → Diamante
```

Primero se perfila cada cluster usando:

```text
score promedio
frequency promedio
recency promedio
monetary promedio
volume promedio
length promedio
tamaño del cluster
churn_rate
```

Luego se asignan etiquetas comerciales:

| Etiqueta | Perfil esperado |
|---|---|
| Diamante | Alta frecuencia, alto monetary, alto volume, baja recency, alto score |
| Oro | Buen valor y estabilidad, inferior a Diamante |
| Plata | Comportamiento medio, útil para cobertura operativa |
| Bronce | Baja frecuencia, bajo monetary/volume o alta recency |
| Nuevo | Menos de 180 días de historial transaccional |

---

## 20. Salida final Gold

Tabla final:

```text
gold.clients_clustered
```

Columnas recomendadas:

```text
client_id
snapshot_date
first_purchase_date
last_purchase_date
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
churn_eligible
is_churn_risk
score_lrfmv_0_100
cluster_id
cluster_label
cluster_source
```

Valores esperados:

```text
cluster_label ∈ {Diamante, Oro, Plata, Bronce, Nuevo}
cluster_source ∈ {kmeans, business_rule}
```

---

## 21. Flujo final del pipeline

```text
1. Leer CSVs
   - clients_raw.csv
   - transactions_raw.csv
   - _ground_truth.csv opcional

2. Validar datos mínimos
   - columnas obligatorias
   - duplicados
   - fechas válidas
   - amount > 0
   - categories_purchased válido

3. Separar clientes sin transacciones
   - reportarlos aparte
   - excluirlos del modelamiento

4. Construir variables LRFMV
   - first_purchase_date
   - last_purchase_date
   - length_days
   - recency_days
   - frequency
   - monetary
   - volume
   - n_transactions_total

5. Calcular delta_frequency
   - frequency_last_3_months
   - frequency_previous_3_months
   - delta_frequency

6. Calcular reglas simples
   - es_nuevo
   - churn_eligible
   - is_churn_risk

7. Transformar variables
   - R_log = log1p(recency_days)
   - M_log = log1p(monetary)

8. Calcular score LRFMV
   - MinMaxScaler
   - pesos fijos
   - score_lrfmv_0_100

9. Preparar K-Means
   - filtrar es_nuevo == False
   - StandardScaler
   - K-Means k=4

10. Etiquetar clusters
    - perfilar clusters
    - asignar Diamante, Oro, Plata, Bronce
    - integrar Nuevo por regla de negocio

11. Exportar salida Gold
    - gold.clients_clustered.csv
```

---

## 22. Outputs esperados

```text
outputs/m2/bronze/bronze_data_quality_report.csv
outputs/m2/silver/clients_features.csv
outputs/m2/silver/clients_without_transactions.csv
outputs/m2/gold/clients_clustered.csv
outputs/m2/gold/cluster_profile.csv
```

Opcionalmente:

```text
outputs/m2/figures/skewness_lrfmv.png
outputs/m2/figures/hist_recency_raw_vs_log.png
outputs/m2/figures/hist_monetary_raw_vs_log.png
outputs/m2/figures/correlation_matrix.png
outputs/m2/figures/elbow_kmeans.png
outputs/m2/figures/silhouette_kmeans.png
```

---

## 23. Relación con Módulo 3

El Módulo 3 necesita recibir del Módulo 2:

```text
client_id
cluster_label
score_lrfmv_0_100
is_churn_risk
```

Uso comercial:

| Cluster cliente | Preventista recomendado | Justificación |
|---|---|---|
| Diamante | Farmer | Retención y protección de cartera |
| Oro | Farmer | Desarrollo y fidelización |
| Plata | Ejecutor | Cobertura operativa |
| Bronce | Hunter | Reactivación selectiva |
| Nuevo | Hunter | Prospección y onboarding |

---

## 24. Límites de alcance

Esta versión no incluye:

```text
Supabase obligatorio
FastAPI obligatorio
umbral dinámico de churn por cluster
AHP para pesos
inferencia productiva
reentrenamiento automático
validación con datos reales
recomendación de SKUs
predicción supervisada de ventas
```

Estos puntos pueden mencionarse como trabajo futuro.

---

## 25. Decisiones cerradas de la versión simple

| Decisión | Estado |
|---|---|
| `Length` se calcula desde `first_purchase_date` | Cerrado |
| `registration_date` se conserva pero no se usa en LRFMV | Cerrado |
| Clientes sin transacciones se excluyen del modelo | Cerrado |
| Clientes sin transacciones se reportan aparte | Cerrado |
| `Volume` mide categorías distintas compradas | Cerrado |
| `sku_count` se excluye del modelo LRFMV | Cerrado |
| `es_nuevo = length_days < 180` | Cerrado |
| `churn_eligible = length_days >= 180 AND n_transactions_total >= 3` | Cerrado |
| Churn simple: `recency_days > 60 AND delta_frequency <= 0` | Cerrado |
| Score usa MinMaxScaler | Cerrado |
| K-Means usa StandardScaler | Cerrado |
| Score usa pesos fijos | Cerrado |
| K-Means usa k=4 | Cerrado |
| `Nuevo` se asigna por regla de negocio | Cerrado |
| Supabase/FastAPI quedan como futuro | Cerrado |

---

## 26. Respuesta para defensa

> En esta versión académica simplificamos el Módulo 2 para enfocarnos en el flujo principal de Data Science: construcción de variables LRFMV, score, clustering y churn. Como LRFMV se basa en comportamiento de compra, definimos Length como la antigüedad transaccional observada, calculada desde la primera compra del cliente. Los clientes sin transacciones se excluyen del modelamiento porque no existe evidencia suficiente para calcular variables de compra. El score se construye con MinMaxScaler para obtener una escala interpretable de 0 a 100, mientras que K-Means usa StandardScaler porque trabaja con distancias euclidianas. Se usa k=4 para segmentar clientes maduros en Diamante, Oro, Plata y Bronce, y los clientes nuevos se asignan por regla de negocio cuando tienen menos de 180 días de historial. Para churn usamos una regla simple: clientes elegibles con más de 60 días sin comprar y frecuencia reciente no creciente. Esta versión prioriza claridad y explicabilidad; reglas más avanzadas como churn dinámico por cluster, Supabase y FastAPI quedan como trabajo futuro.

---

## 27. Orden recomendado de notebooks

```text
01_bronze_data_quality.ipynb
02_silver_clients_features_simple.ipynb
03_gold_clients_clustered_simple.ipynb
```

### 27.1 Notebook 01

Objetivo:

```text
cargar CSVs, validar datos mínimos y detectar clientes sin transacciones
```

### 27.2 Notebook 02

Objetivo:

```text
calcular LRFMV, delta_frequency, es_nuevo, churn_eligible, score LRFMV
```

### 27.3 Notebook 03

Objetivo:

```text
aplicar StandardScaler, entrenar K-Means, etiquetar clusters, integrar Nuevo y exportar Gold
```

---

## 28. Idea central

La versión simple del Módulo 2 debe demostrar que se entiende el proceso completo:

```text
datos crudos → variables LRFMV → score → clustering → churn → salida comercial
```

Ese flujo es más importante que agregar reglas complejas prematuramente.
