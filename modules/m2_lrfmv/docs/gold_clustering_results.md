# Documentación de resultados Gold - Clustering de clientes

## Objetivo

Este documento resume los resultados generados por el notebook `03_gold_clients_clustered.ipynb`.

El objetivo de la capa Gold es tomar las variables LRFMV calculadas en Silver, segmentar los clientes maduros mediante K-Means y producir una tabla final con etiquetas comerciales interpretables para uso posterior en asignación comercial y priorización.

## Entradas y salidas

Entrada principal:

- `outputs/m2/silver/clients_features.csv`

Salidas generadas:

- `outputs/m2/gold/clients_clustered.csv`
- `outputs/m2/gold/cluster_profile.csv`
- `outputs/m2/figures/kmeans_clusters_overview.png`

La tabla `clients_clustered.csv` contiene 498 clientes y 20 columnas finales. La tabla `cluster_profile.csv` contiene el perfil agregado de los 5 segmentos comerciales finales.

## Preparación del modelo

El notebook separa los clientes en dos grupos:

- Clientes maduros: clientes con historial suficiente para entrar a K-Means.
- Clientes nuevos: clientes con menos de 180 días de historial, asignados por regla de negocio al segmento `Nuevo`.

Distribución usada:

| Grupo | Clientes | Método de asignación |
| --- | ---: | --- |
| Clientes maduros | 414 | K-Means |
| Clientes nuevos | 84 | Regla de negocio |
| Total | 498 | - |

Las variables usadas para entrenar K-Means fueron:

- `length_days`
- `R_log`
- `frequency`
- `M_log`
- `volume`

Estas variables se estandarizaron con `StandardScaler` antes del entrenamiento, porque K-Means depende de distancias y las variables tienen escalas distintas.

## Evaluación de número de clusters

Se evaluaron valores de `k` entre 2 y 8 mediante inertia y silhouette score.

| k | Inertia | Silhouette score |
| ---: | ---: | ---: |
| 2 | 875.88 | 0.535 |
| 3 | 616.37 | 0.432 |
| 4 | 493.07 | 0.396 |
| 5 | 417.45 | 0.356 |
| 6 | 354.61 | 0.345 |
| 7 | 297.42 | 0.357 |
| 8 | 267.52 | 0.353 |

Aunque `k=2` obtiene el mayor silhouette score, se mantiene `k=4` para los clientes maduros porque el objetivo comercial requiere cuatro segmentos accionables: `Diamante`, `Oro`, `Plata` y `Bronce`. El segmento `Nuevo` se agrega aparte por regla de negocio.

## Asignación de etiquetas comerciales

K-Means genera IDs numéricos sin significado de negocio. Para interpretarlos, el notebook ordena los clusters maduros por `avg_score` descendente y asigna las etiquetas:

| Cluster ID K-Means | Etiqueta comercial |
| ---: | --- |
| 2 | Diamante |
| 3 | Oro |
| 0 | Plata |
| 1 | Bronce |
| -1 | Nuevo |

El cluster `-1` no proviene de K-Means; identifica clientes nuevos asignados por regla de negocio.

## Distribución final de clientes

| Segmento | Clientes | Participación |
| --- | ---: | ---: |
| Diamante | 193 | 38.8% |
| Bronce | 99 | 19.9% |
| Oro | 88 | 17.7% |
| Nuevo | 84 | 16.9% |
| Plata | 34 | 6.8% |
| Total | 498 | 100.0% |

## Perfil promedio por segmento

| Segmento | Clientes | Score prom. | Length prom. | Recency prom. | Frequency prom. | Monetary prom. | Volume prom. | Churn rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Diamante | 193 | 71.57 | 1413.02 | 5.04 | 27.10 | 4786.30 | 3.20 | 0.0% |
| Oro | 88 | 49.71 | 1370.73 | 51.75 | 9.50 | 1093.31 | 2.65 | 34.1% |
| Plata | 34 | 46.66 | 792.06 | 28.24 | 10.82 | 941.07 | 1.91 | 14.7% |
| Nuevo | 84 | 40.98 | 89.95 | 12.45 | 8.58 | 738.72 | 1.94 | 0.0% |
| Bronce | 99 | 11.88 | 1329.16 | 379.67 | 0.07 | 4.57 | 0.06 | 100.0% |

## Interpretación de segmentos

### Diamante

Es el segmento de mayor valor comercial. Tiene el score LRFMV promedio más alto, alta frecuencia de compra, mayor monetary promedio, mayor volumen promedio y recencia muy baja.

Lectura comercial:

- Clientes activos y de alto valor.
- Compran con mucha frecuencia y recientemente.
- Deben priorizarse para retención, beneficios, cobertura comercial y oportunidades de venta cruzada.

### Oro

Es un segmento de valor medio-alto. Tiene buen score, historial largo y volumen alto, pero presenta recencia promedio mayor que Diamante y una tasa de riesgo de churn de 34.1%.

Lectura comercial:

- Clientes relevantes, pero con señales de deterioro en actividad.
- Conviene activar campañas preventivas, visitas comerciales y recuperación de frecuencia.

### Plata

Es un segmento intermedio. Tiene frecuencia y recencia razonables, pero menor monetary y menor volumen que Oro y Diamante.

Lectura comercial:

- Clientes con potencial de crecimiento.
- Pueden trabajarse con promociones, ampliación de portafolio y seguimiento de recompra.

### Nuevo

Este segmento no fue creado por K-Means. Agrupa clientes con menos de 180 días de historial transaccional.

Lectura comercial:

- Clientes recientes, todavía sin historial suficiente para compararlos justamente con clientes maduros.
- Deben monitorearse para maduración, onboarding y primeras recompras.

### Bronce

Es el segmento de menor desempeño. Tiene score promedio muy bajo, recencia extremadamente alta, frecuencia reciente casi nula, monetary casi cero y churn rate de 100%.

Lectura comercial:

- Clientes inactivos o en riesgo crítico.
- Requieren acciones de recuperación o depuración según rentabilidad y costo de atención.

## Riesgo de churn por segmento

| Segmento | Clientes en riesgo | Total segmento | Tasa |
| --- | ---: | ---: | ---: |
| Bronce | 99 | 99 | 100.0% |
| Oro | 30 | 88 | 34.1% |
| Plata | 5 | 34 | 14.7% |
| Diamante | 0 | 193 | 0.0% |
| Nuevo | 0 | 84 | 0.0% |

El riesgo se concentra principalmente en `Bronce` y, en segundo lugar, en `Oro`. Esto sugiere dos frentes de acción distintos:

- `Bronce`: recuperación selectiva o depuración comercial.
- `Oro`: prevención temprana para evitar pérdida de clientes valiosos.

## Visualización generada

El notebook genera el archivo:

- `outputs/m2/figures/kmeans_clusters_overview.png`

El gráfico incluye:

- Proyección 2D de clientes maduros usando PCA sobre las variables escaladas.
- Distribución de clientes por segmento.
- Score LRFMV promedio por segmento.
- Perfil relativo promedio de variables clave por segmento.

Esta visualización sirve para validar que la segmentación sea interpretable y que las etiquetas comerciales reflejen diferencias reales en comportamiento.

## Columnas finales de `clients_clustered.csv`

La salida Gold conserva las siguientes columnas:

- `client_id`
- `snapshot_date`
- `first_purchase_date`
- `last_purchase_date`
- `length_days`
- `recency_days`
- `frequency`
- `monetary`
- `volume`
- `n_transactions_total`
- `frequency_last_3_months`
- `frequency_previous_3_months`
- `delta_frequency`
- `es_nuevo`
- `churn_eligible`
- `is_churn_risk`
- `score_lrfmv_0_100`
- `cluster_id`
- `cluster_label`
- `cluster_source`

## Conclusión

La capa Gold produce una segmentación comercial lista para consumo analítico y operativo. Los clientes maduros son agrupados con K-Means en cuatro segmentos interpretables, mientras que los clientes nuevos se mantienen separados por regla de negocio.

El resultado más relevante es que `Diamante` concentra clientes activos de alto valor, `Oro` contiene clientes valiosos con señales de riesgo moderado, `Plata` representa clientes de potencial medio, `Nuevo` agrupa clientes en etapa temprana y `Bronce` concentra clientes en riesgo crítico.
