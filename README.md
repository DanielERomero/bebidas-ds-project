# bebidas-ds-project

Proyecto de ciencia de datos para segmentación y análisis de clientes de bebidas.

## Estructura mínima

```text
project_bebidas/
├── docs/              # Especificaciones compartidas
├── modules/
│   ├── m1_CV/         # Informes internos, LLM y Streamlit
│   └── m2_lrfmv/      # Pipeline SQL, LRFMV y K-Means
├── sql/               # Migraciones SQL de los módulos
├── AGENTS.md
└── README.md
```

Cada módulo administra su propio `pyproject.toml`, `uv.lock`, `.env` y `.venv`.
No se crea un entorno Python en la raíz del repositorio.

## Como ejecutar el proyecto con uv

### 1. Clonar el repositorio

```bash
git clone https://github.com/DanielERomero/bebidas-ds-project.git
cd bebidas-ds-project
```

Si ya tienes el repositorio clonado, solo actualiza:

```bash
git pull
```

### 2. Ejecutar Módulo 1 - Perfil comercial de preventistas

El Módulo 1 analiza informes internos de desempeño de preventistas activos. Usa
dos llamadas LLM para estructurar y puntuar la evidencia narrativa, Python para
aplicar las reglas 70/30 y una tercera llamada LLM para redactar una explicación
detallada. Todas las respuestas del modelo se validan con Pydantic v2.

Entrar al modulo:

```bash
cd modules/m1_CV
```

Crear o sincronizar el entorno:

```bash
uv sync
```

Crear la configuración de M1 copiando su ejemplo local:

```bash
cp .env.example .env
```

El archivo `modules/m1_CV/.env` utiliza:

```env
GITHUB_TOKEN=tu_token_de_github_models
SUPABASE_URL=tu_url_de_supabase
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
M1_LLM_MODEL=gpt-4o
```

M2 mantiene una configuración independiente en `modules/m2_lrfmv/.env`, creada
desde su propio `.env.example`. Ningún módulo carga el `.env` de la raíz.

Ejecutar todas las pruebas locales, sin LLM ni Supabase reales:

```bash
uv run python -m unittest discover -s tests -v
```

Ejecutar una prueba manual end-to-end con PDF, LLM y Supabase configurados:

```bash
uv run python test_evaluacion.py
```

Esta prueba toma informes desde `tests/pdfs/`. Los datos incompletos quedan en
Silver, los empates esperan una selección en Streamlit y solo los perfiles
finales se escriben en Gold.

Para probar el pipeline, coloca un informe interno ficticio en:

```text
modules/m1_CV/tests/pdfs/informe_preventista_prueba.pdf
```

Para usar la interfaz ejecuta:

```bash
uv run streamlit run app.py
```

Notas:

- Los archivos `.env` de cada módulo no deben subirse a git.
- Las pruebas de schema no requieren credenciales.
- Los PDFs de prueba se guardan localmente en `tests/pdfs/` y no deben subirse a git.
- No uses PDFs con datos personales reales en las pruebas del repositorio.
- M1 no genera carpetas locales Bronze, Silver ni Gold; Supabase persiste los
  datos y Python aplica el cómputo.
- Ejecuta `sql/08_create_m1_informe_medallion.sql` y luego
  `sql/09_simplify_m1_perfil_comercial.sql` en ese orden.

### 3. Ejecutar Modulo 2 - LRFMV y segmentacion

Entrar al modulo de trabajo:

```bash
cd modules/m2_lrfmv
```

### 4. Crear el entorno e instalar dependencias

Como el proyecto usa `uv`, no es necesario instalar paquete por paquete manualmente. Ejecuta:

```bash
uv sync
```

Este comando crea el entorno virtual `.venv` y sincroniza las dependencias definidas en `pyproject.toml` y `uv.lock`.

### Módulo 2 — flujo SQL Medallion

1. Crear schemas en Supabase:
   bronze, silver, gold

2. Ejecutar scripts SQL desde /sql

3. Cargar CSVs a bronze

4. SQL calcula silver.client_lrfmv_features

5. Python lee Silver, ejecuta K-Means y escribe Gold

6. Resultado final:
   gold.clients_clustered

```
