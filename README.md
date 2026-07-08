# bebidas-ds-project

Proyecto de ciencia de datos para segmentación y análisis de clientes de bebidas.

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

### 2. Ejecutar Modulo 1 - CV Screening y perfilamiento comercial

El Modulo 1 analiza CVs de candidatos a preventistas B2B y valida las salidas del LLM con Pydantic v2.

Entrar al modulo:

```bash
cd modules/m1_CV
```

Crear o sincronizar el entorno:

```bash
uv sync
```

Configurar credenciales en el archivo `.env` de la raiz del proyecto:

```env
GITHUB_TOKEN=tu_token_de_github_models
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
```

Ejecutar pruebas locales de validacion de schemas, sin LLM ni Supabase:

```bash
uv run python tests/test_schemas.py
```

Ejecutar prueba end-to-end local de evaluacion, con PDF y LLM, sin Supabase:

```bash
uv run python test_evaluacion.py
```

Esta prueba toma PDFs desde `tests/pdfs/` y guarda un JSON trazable en `tests/outputs/`.

Para probar el pipeline con un PDF local, coloca un CV de prueba en:

```text
modules/m1_CV/tests/pdfs/cv_prueba.pdf
```

Y ejecuta:

```bash
uv run python main.py
```

Notas:

- El archivo `.env` no debe subirse a git.
- Las pruebas de schema no requieren credenciales.
- Los PDFs de prueba se guardan localmente en `tests/pdfs/` y no deben subirse a git.
- M1 no genera carpetas locales Bronze, Silver ni Gold; Supabase persiste resultados y el computo ocurre en Python.

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

### 5. Usar el entorno en notebooks

Para abrir Jupyter desde el entorno de `uv`:

```bash
uv run jupyter notebook
```

Si trabajas en VS Code, selecciona como kernel el entorno `.venv` creado dentro de:

```text
modules/m2_lrfmv/.venv
```

### 6. Ejecutar notebooks en orden

Desde `modules/m2_lrfmv/notebooks`, ejecutar:

```text
01_eda_bronze.ipynb
02_silver_clients_features_final.ipynb
03_gold_clients_clustered.ipynb
```

## Salidas esperadas

Al ejecutar los notebooks se generan archivos en:

```text
modules/m2_lrfmv/outputs/m2/eda
modules/m2_lrfmv/outputs/m2/silver
modules/m2_lrfmv/outputs/m2/gold
modules/m2_lrfmv/outputs/m2/figures
```
