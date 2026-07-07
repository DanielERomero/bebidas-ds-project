# bebidas-ds-project

Proyecto de ciencia de datos para segmentación y análisis de clientes de bebidas.

## Cómo ejecutar el proyecto con uv

### 1. Clonar el repositorio

```bash
git clone https://github.com/DanielERomero/bebidas-ds-project.git
cd bebidas-ds-project
```

Si ya tienes el repositorio clonado, solo actualiza:

```bash
git pull
```

### 2. Entrar al módulo de trabajo

```bash
cd modules/m2_lrfmv
```

### 3. Crear el entorno e instalar dependencias

Como el proyecto usa `uv`, no es necesario instalar paquete por paquete manualmente. Ejecuta:

```bash
uv sync
```

Este comando crea el entorno virtual `.venv` y sincroniza las dependencias definidas en `pyproject.toml` y `uv.lock`.

### 4. Usar el entorno en notebooks

Para abrir Jupyter desde el entorno de `uv`:

```bash
uv run jupyter notebook
```

Si trabajas en VS Code, selecciona como kernel el entorno `.venv` creado dentro de:

```text
modules/m2_lrfmv/.venv
```

### 5. Ejecutar notebooks en orden

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
