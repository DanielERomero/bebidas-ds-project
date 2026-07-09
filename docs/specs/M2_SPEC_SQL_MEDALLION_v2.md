M2_SPEC_SQL_MEDALLION_v2 — LRFMV, Segmentación y Churn en Base de Datos
Proyecto: Sistema de Data Science para distribución B2B de bebidas  
Módulo: Módulo 2 — Scoring, Segmentación y Churn de Clientes  
Versión: SQL Medallion v2  
Fecha: 2026-07-09  
Estado: Spec actualizado para practicar arquitectura Medallion desde una base de datos.
---
1. Propósito del módulo
El Módulo 2 transforma el historial de compras de clientes B2B —bodegas, minimarkets y negocios similares— en una salida comercial accionable:
Score LRFMV 0-100.
Cluster comercial: `Diamante`, `Oro`, `Plata`, `Bronce` o `Nuevo`.
Riesgo de churn.
Salida Gold lista para dashboard y para el Módulo 3.
La diferencia principal de esta versión es que la arquitectura Medallion se implementa en una base de datos PostgreSQL/Supabase, no solo como archivos CSV o notebooks.
---
2. Cambio principal respecto a la versión simple
Antes:
```text
CSV → pandas/notebooks → features LRFMV → K-Means → CSV outputs
```
Ahora:
```text
CSV → bronze en Supabase → silver en SQL → Python K-Means → gold en Supabase
```
Principio de diseño:
```text
SQL/PostgreSQL calcula LRFMV.
Python ejecuta Machine Learning.
Supabase persiste las capas Bronze, Silver y Gold.
```
---
3. Stack tecnológico actualizado
Herramientas principales:
```text
Supabase / PostgreSQL  → base de datos y arquitectura Medallion
SQL                    → creación de tablas, validaciones y features LRFMV
VS Code                → desarrollo del proyecto
Python                 → conexión a Supabase y K-Means
scikit-learn           → StandardScaler y KMeans
pandas                 → lectura/escritura intermedia desde Python
supabase-py            → conexión Python ↔ Supabase
python-dotenv          → variables de entorno
uv                     → gestión del entorno Python
Git/GitHub             → control de versiones
```
No se usará MCP al inicio. Se prioriza entender manualmente la creación de tablas, queries SQL y conexión Python.
---
4. Arquitectura Medallion en base de datos
La arquitectura se implementa con tres schemas:
```sql
bronze
silver
gold
```
Flujo:
```text
bronze → datos crudos cargados desde CSV
silver → tablas limpias, dimensiones, hechos y features LRFMV
gold   → resultados comerciales finales
```
---
5. Capa Bronze
5.1 Objetivo
Bronze conserva los datos crudos casi igual a los CSV originales.
Responsabilidades:
```text
- cargar datos originales
- conservar trazabilidad
- validar columnas mínimas
- no aplicar lógica avanzada de negocio
```
5.2 Tablas Bronze
```text
bronze.clients\_raw
bronze.transactions\_raw
bronze.ground\_truth
```
5.3 `bronze.clients\_raw`
Columnas esperadas:
```text
client\_id
business\_name
store\_type
zone
latitude
longitude
registration\_date
loaded\_at
```
`registration\_date` se conserva, pero no se usa para calcular `Length`.
5.4 `bronze.transactions\_raw`
Columnas esperadas:
```text
transaction\_id
client\_id
date
amount
sku\_count
categories\_purchased
loaded\_at
```
`sku\_count` se conserva por trazabilidad, pero no entra al modelo LRFMV.
---
6. Capa Silver
6.1 Objetivo
Silver transforma los datos crudos en datos analíticos confiables.
Responsabilidades:
```text
- crear dimensiones limpias
- crear tabla de hechos de ventas
- validar calidad mínima
- calcular features LRFMV
- calcular score LRFMV
- calcular flags de negocio
```
---
7. Modelo dimensional simple
7.1 Dimensión clientes
Tabla:
```text
silver.dim\_clientes
```
Una fila por cliente.
Columnas recomendadas:
```text
client\_id
business\_name
store\_type
zone
latitude
longitude
registration\_date
created\_at
```
Uso:
```text
Catálogo principal de clientes B2B.
```
---
7.2 Fact ventas
Tabla:
```text
silver.fact\_ventas
```
Una fila por transacción.
Columnas recomendadas:
```text
transaction\_id
client\_id
transaction\_date
amount
sku\_count
categories\_purchased
created\_at
```
Uso:
```text
Tabla de hechos transaccional para calcular LRFMV.
```
---
7.3 Clientes sin transacciones
Tabla:
```text
silver.clients\_without\_transactions
```
Regla:
```text
Clientes que existen en dim\_clientes pero no tienen ventas en fact\_ventas.
```
Estos clientes se excluyen de LRFMV, K-Means y churn.
En el dataset actual existen:
```text
CLI-0313
CLI-0315
```
---
8. Tabla Silver principal: LRFMV
Tabla o vista:
```text
silver.client\_lrfmv\_features
```
Esta tabla se calcula principalmente con SQL.
Columnas recomendadas:
```text
client\_id
snapshot\_date
first\_purchase\_date
last\_purchase\_date
length\_days
recency\_days
frequency
monetary
volume
n\_transactions\_total
frequency\_last\_3\_months
frequency\_previous\_3\_months
delta\_frequency
es\_nuevo
churn\_eligible
is\_churn\_risk
score\_lrfmv\_0\_100
created\_at
```
---
9. Ventana de análisis
Fecha de corte académica:
```text
snapshot\_date = 2025-06-30
```
Ventana de análisis:
```text
ANALYSIS\_WINDOW\_DAYS = 180
```
Subventanas para delta frequency:
```text
últimos 90 días
90 días anteriores
```
---
10. Variables LRFMV en SQL
10.1 Length
```text
length\_days = snapshot\_date - first\_purchase\_date
```
Donde:
```text
first\_purchase\_date = MIN(transaction\_date)
```
Se usa la primera compra observada, no `registration\_date`.
---
10.2 Recency
```text
recency\_days = snapshot\_date - last\_purchase\_date
```
Donde:
```text
last\_purchase\_date = MAX(transaction\_date)
```
---
10.3 Frequency
```text
frequency = número de compras en los últimos 180 días
```
---
10.4 Monetary
```text
monetary = SUM(amount) en los últimos 180 días
```
---
10.5 Volume
```text
volume = número de categorías distintas compradas en los últimos 180 días
```
La columna base es:
```text
categories\_purchased
```
Ejemplo:
```text
gaseosas|agua|jugos
```
En PostgreSQL se puede separar con:
```sql
unnest(string\_to\_array(categories\_purchased, '|'))
```
`Volume` mide categorías, no SKUs.
---
11. Delta frequency en SQL
Fórmula:
```text
delta\_frequency = frequency\_last\_3\_months - frequency\_previous\_3\_months
```
Interpretación:
```text
delta\_frequency < 0  → caída de frecuencia
delta\_frequency = 0  → estabilidad
delta\_frequency > 0  → mejora de frecuencia
```
---
12. Reglas de negocio
12.1 Cliente nuevo
```text
es\_nuevo = length\_days < 180
```
La etiqueta `Nuevo` no sale de K-Means. Se asigna por regla de negocio.
---
12.2 Elegibilidad para churn
```text
churn\_eligible = length\_days >= 180 AND n\_transactions\_total >= 3
```
---
12.3 Churn simplificado
```text
is\_churn\_risk = churn\_eligible = true
                AND recency\_days > 60
                AND delta\_frequency <= 0
```
---
13. Score LRFMV en SQL
El score se calcula en Silver porque depende de agregaciones y reglas determinísticas.
Transformaciones:
```text
R\_log = ln(1 + recency\_days)
M\_log = ln(1 + monetary)
```
Normalización tipo MinMaxScaler usando SQL:
```text
x\_minmax = (x - min(x)) / (max(x) - min(x))
```
Recency se invierte:
```text
R\_score = 1 - R\_minmax
```
Pesos:
Variable	Peso
Frequency	30%
Recency	20%
Monetary	20%
Volume	20%
Length	10%
Fórmula:
```text
score\_lrfmv\_0\_100 = 100 \* (
    0.30 \* F\_minmax
  + 0.20 \* R\_score
  + 0.20 \* M\_minmax
  + 0.20 \* V\_minmax
  + 0.10 \* L\_minmax
)
```
---
14. Qué hace Python
Python no recalcula LRFMV.
Python se encarga solo de:
```text
1. Leer silver.client\_lrfmv\_features desde Supabase.
2. Filtrar clientes donde es\_nuevo = false.
3. Preparar variables para clustering.
4. Aplicar StandardScaler.
5. Entrenar KMeans con k=4.
6. Perfilar clusters.
7. Etiquetar Diamante, Oro, Plata y Bronce.
8. Integrar clientes Nuevo.
9. Escribir resultado final en gold.clients\_clustered.
```
Variables para K-Means:
```text
length\_days
R\_log
frequency
M\_log
volume
```
Parámetros:
```python
KMeans(n\_clusters=4, random\_state=42, n\_init=10)
```
---
15. Capa Gold
15.1 Objetivo
Gold contiene la salida lista para negocio, dashboards y Módulo 3.
Tabla principal:
```text
gold.clients\_clustered
```
Columnas recomendadas:
```text
client\_id
snapshot\_date
first\_purchase\_date
last\_purchase\_date
length\_days
recency\_days
frequency
monetary
volume
n\_transactions\_total
frequency\_last\_3\_months
frequency\_previous\_3\_months
delta\_frequency
es\_nuevo
churn\_eligible
is\_churn\_risk
score\_lrfmv\_0\_100
cluster\_id
cluster\_label
cluster\_source
created\_at
```
Valores esperados:
```text
cluster\_label ∈ {Diamante, Oro, Plata, Bronce, Nuevo}
cluster\_source ∈ {kmeans, business\_rule}
```
---
16. Relación con Módulo 3
El Módulo 3 consume desde Gold:
```text
client\_id
cluster\_label
score\_lrfmv\_0\_100
is\_churn\_risk
```
Uso comercial:
Cluster cliente	Preventista recomendado	Justificación
Diamante	Farmer	Retención y protección de cartera
Oro	Farmer	Desarrollo y fidelización
Plata	Ejecutor	Cobertura operativa
Bronce	Hunter	Reactivación selectiva
Nuevo	Hunter	Prospección y onboarding
---
17. Estructura recomendada del repositorio
```text
project\_bebidas/
│
├── sql/
│   ├── 01\_create\_schemas.sql
│   ├── 02\_create\_bronze\_tables.sql
│   ├── 03\_create\_silver\_dim\_fact.sql
│   ├── 04\_create\_silver\_lrfmv\_features.sql
│   ├── 05\_create\_gold\_tables.sql
│   └── 06\_quality\_checks.sql
│
├── modules/
│   └── m2\_lrfmv/
│       ├── scripts/
│       │   ├── load\_bronze.py
│       │   ├── run\_kmeans\_from\_supabase.py
│       │   └── write\_gold\_clients\_clustered.py
│       └── notebooks/
│           ├── 01\_bronze\_data\_quality.ipynb
│           ├── 02\_compare\_sql\_vs\_python\_lrfmv.ipynb
│           └── 03\_gold\_cluster\_review.ipynb
│
├── data/
│   └── raw/
│       ├── clients\_raw.csv
│       ├── transactions\_raw.csv
│       └── \_ground\_truth.csv
│
├── .env
├── pyproject.toml
└── README.md
```
---
18. Orden de implementación
```text
1. Crear schemas bronze, silver y gold en Supabase.
2. Crear tablas bronze.
3. Cargar CSVs a bronze.
4. Crear silver.dim\_clientes.
5. Crear silver.fact\_ventas.
6. Crear silver.clients\_without\_transactions.
7. Crear silver.client\_lrfmv\_features con SQL.
8. Validar que el LRFMV SQL coincide con la lógica del notebook anterior.
9. Crear gold.clients\_clustered.
10. Crear script Python para K-Means desde Supabase.
11. Escribir clusters en gold.clients\_clustered.
12. Usar Gold para dashboard o Módulo 3.
```
---
19. Decisiones cerradas
Decisión	Estado
Medallion se implementa en base de datos	Cerrado
Supabase/PostgreSQL será la base principal	Cerrado
Bronze conserva datos crudos	Cerrado
Silver calcula dimensiones, hechos, LRFMV y score	Cerrado
SQL calcula LRFMV	Cerrado
Python solo ejecuta K-Means	Cerrado
Python escribe resultados en Gold	Cerrado
`Length` usa primera compra observada	Cerrado
`registration\_date` no se usa en LRFMV	Cerrado
`Volume` mide categorías distintas compradas	Cerrado
`sku\_count` no entra al modelo	Cerrado
`Nuevo` se asigna por regla de negocio	Cerrado
K-Means usa k=4 para clientes maduros	Cerrado
Gold alimenta Módulo 3	Cerrado
MCP no se usa al inicio	Cerrado
---
20. Respuesta para defensa
> En esta versión, el Módulo 2 se implementa siguiendo arquitectura Medallion directamente en una base de datos PostgreSQL/Supabase. La capa Bronze conserva los datos crudos de clientes y transacciones; la capa Silver transforma esos datos en dimensiones, hechos y variables LRFMV mediante SQL; y la capa Gold almacena los resultados comerciales finales. SQL se usa para LRFMV porque sus cálculos son principalmente agregaciones transaccionales, como frecuencia, recencia, monto, volumen y delta de frecuencia. Python se reserva para K-Means, ya que el clustering requiere librerías especializadas como scikit-learn. Finalmente, los resultados del modelo regresan a la base de datos como `gold.clients\_clustered`, lista para dashboard y para el Módulo 3 de matching.
---
21. Idea central
La idea central de esta versión es practicar un flujo realista de datos:
```text
datos crudos en Bronze
→ transformación SQL en Silver
→ machine learning en Python
→ resultados finales en Gold
```
Esto mantiene el proyecto práctico, defendible y más cercano a cómo se trabaja con datos en empresas.