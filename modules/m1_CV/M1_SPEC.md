# M1 - Perfil comercial de preventistas

## 1. Propósito

El Módulo 1 procesa un informe interno de desempeño preparado por RR. HH. para
identificar el perfil comercial principal de cada preventista actual.

El resultado final será utilizado por el Módulo 3 para asignar una cartera de
clientes compatible con el perfil del preventista.

M1 no evalúa postulantes, no analiza CV, no recomienda contrataciones o despidos
y no decide si un trabajador merece recibir una cartera. Todo preventista activo
debe terminar con un perfil comercial válido antes de ejecutar M3.

```text
Streamlit
→ extracción del PDF
→ Bronze: texto y metadatos
→ LLM + Pydantic
→ Silver: métricas y evidencia estructuradas
→ LLM para evidencia narrativa + reglas Python
→ LLM para explicación detallada de la decisión
→ confirmación excepcional de RR. HH.
→ Gold: perfil comercial final
→ M3: asignación de cartera
```

El PDF original no se almacena. Solo se conserva el texto extraído, su hash y
los metadatos necesarios para trazabilidad.

---

## 2. Documento de entrada

RR. HH. cargará un PDF por preventista. El documento corresponderá al periodo
enero-junio de 2025 para mantener coherencia con la fecha de corte de M2:
30 de junio de 2025.

El informe debe contener:

- DNI o identificador del preventista;
- nombre del colaborador;
- antigüedad en la empresa;
- zona actual;
- periodo evaluado;
- métricas de campo con resultado y meta;
- evaluación narrativa del supervisor;
- fortalezas reportadas;
- aspectos por mejorar.

Las métricas mínimas son:

| Métrica | Resultado requerido |
|---|---|
| Cumplimiento de cuota | Porcentaje alcanzado |
| Cobertura de ruta | Resultado y meta porcentual |
| Retención de cartera | Resultado y meta porcentual |
| Cuentas nuevas abiertas | Resultado y meta |
| Reportes entregados a tiempo | Resultado y meta porcentual |

Un número sin periodo o sin meta no se considera evidencia completa. La ausencia
de información no se interpreta como bajo desempeño ni se convierte en cero.
El informe debe corregirse antes de generar el perfil final.

---

## 3. Fuentes de evaluación

Cada dimensión combina dos fuentes:

```text
70 % métricas de campo
30 % evaluación del supervisor
```

Las métricas tienen mayor peso porque representan resultados observados. La
evaluación del supervisor aporta contexto y conductas que no pueden explicarse
solo mediante números.

La antigüedad se conserva como información administrativa. No aumenta el score,
no produce un nivel y no se utiliza para excluir al preventista del matching.

---

## 4. Responsabilidades del LLM y Python

### 4.1 LLM de estructuración

El primer llamado al LLM:

- extrae únicamente cifras explícitas del informe;
- no calcula porcentajes ni completa metas ausentes;
- organiza la evidencia narrativa por dimensión;
- devuelve `null` cuando una cifra no está presente;
- no puntúa ni propone el perfil comercial;
- produce JSON validado con Pydantic v2.

### 4.2 LLM de evaluación narrativa

El segundo llamado al LLM califica solamente las observaciones del supervisor
con el catálogo cerrado:

```text
0, 25, 50, 75, 100
```

No utiliza las métricas para calcular estos scores y no decide el perfil final.

| Score | Interpretación de la evidencia del supervisor |
|---:|---|
| 0 | No existe evidencia favorable para la dimensión |
| 25 | Evidencia débil o desempeño bajo |
| 50 | Evidencia intermedia, pero poco consistente |
| 75 | Evidencia clara con conducta o ejemplo concreto |
| 100 | Evidencia sólida, repetida y acompañada de resultados |

### 4.3 LLM de explicación final

El tercer llamado recibe únicamente resultados ya calculados por Python:

- los cuatro scores finales;
- los tres indicadores de perfil;
- el perfil propuesto y la diferencia entre los dos líderes;
- los scores por fuente, la evidencia y las inconsistencias detectadas;
- el estado técnico del procesamiento.

Su única salida es `explicacion_final`, validada con Pydantic v2 y limitada a
1200 caracteres. No puede devolver ni modificar scores, estados o perfiles.

En un perfil claro explica por qué ganó. En un caso cercano compara los dos
perfiles principales, explica por qué existe la cercanía e indica qué evidencia
debe revisar RR. HH. En una inconsistencia identifica las fuentes en conflicto y
explica por qué se necesita criterio humano.

### 4.4 Reglas Python

Python:

- convierte el cumplimiento de las metas en puntajes;
- combina métricas y supervisor con pesos 70/30;
- calcula las cuatro dimensiones;
- compara los indicadores de perfil;
- determina el perfil comercial cuando existe una diferencia clara;
- detecta datos faltantes, empates e inconsistencias;
- escribe en Gold únicamente un perfil final válido.

El LLM interpreta y explica el texto. Python aplica las reglas finales.

---

## 5. Contrato Silver

Silver conserva una fila estructurada por informe e incluye:

```text
dni
nombre_colaborador
antiguedad_meses_empresa
zona_actual
metricas_campo
evidencia_supervisor
processing_status
model_name
prompt_version
created_at
```

`processing_status` es un estado técnico del procesamiento y solo admite:

```text
valid
needs_correction
needs_profile_selection
```

Este estado no es un perfil comercial y no se envía a M3.

### 5.1 Métricas de campo

`metricas_campo` contiene:

```text
periodo_inicio
periodo_fin
periodo_meses
cumplimiento_cuota_pct
cobertura_ruta_pct
meta_cobertura_ruta_pct
retencion_cartera_pct
meta_retencion_cartera_pct
cuentas_nuevas_abiertas
meta_cuentas_nuevas
reportes_a_tiempo_pct
meta_reportes_a_tiempo_pct
```

### 5.2 Evidencia del supervisor

`evidencia_supervisor` separa las observaciones de:

```text
captacion
fidelizacion
cobertura_ruta
disciplina_comunicacion
fortalezas_reportadas
aspectos_mejora_reportados
```

---

## 6. Dimensiones y puntajes

Las cuatro dimensiones son:

```text
score_captacion
score_fidelizacion
score_cobertura_ruta
score_disciplina_comunicacion
```

Para cada dimensión:

```text
score_dimension =
    0.70 × score_metrica
  + 0.30 × score_supervisor
```

El cumplimiento de una meta se convierte a la escala cerrada:

| Cumplimiento | Score métrico |
|---:|---:|
| 0 % | 0 |
| Mayor que 0 % y menor que 70 % | 25 |
| Desde 70 % y menor que 90 % | 50 |
| Desde 90 % y menor que 105 % | 75 |
| 105 % o más | 100 |

La dimensión de disciplina y comunicación utiliza el cumplimiento de cuota y
los reportes entregados a tiempo. Primero se obtiene el score métrico de cada
indicador y luego se calcula su promedio.

```text
score_metrica_disciplina =
    (score_cumplimiento_cuota + score_reportes_a_tiempo) / 2
```

Si falta una métrica o una meta obligatoria, la dimensión correspondiente no se
calcula y el informe queda en `needs_correction`.

No se calcula un score total porque el objetivo de M1 es identificar la fortaleza
comercial principal, no clasificar a los trabajadores por nivel de desempeño.

---

## 7. Perfiles comerciales

M1 utiliza solamente tres perfiles finales:

| Valor interno | Nombre visible | Indicador comparado |
|---|---|---|
| `captacion` | Captación de clientes | `score_captacion` |
| `fidelizacion` | Fidelización de cartera | `score_fidelizacion` |
| `ejecucion_campo` | Ejecución en campo | Promedio de cobertura y disciplina |

El indicador de ejecución en campo se calcula así:

```text
indicador_ejecucion =
    (score_cobertura_ruta + score_disciplina_comunicacion) / 2
```

Python compara:

```text
score_captacion
score_fidelizacion
indicador_ejecucion
```

El indicador mayor determina el perfil comercial.

`perfil_comercial` solo puede contener:

```text
captacion
fidelizacion
ejecucion_campo
```

No se permiten como perfiles:

```text
pendiente
sin_asignar
ambiguo
en_desarrollo
```

---

## 8. Resolución de casos excepcionales

La intervención de RR. HH. ocurre antes de guardar el resultado en Gold.

### 8.1 Perfil claro

Si la diferencia entre los dos indicadores principales es mayor que 10 puntos,
Python asigna automáticamente el perfil y lo guarda en Gold.

### 8.2 Perfil cercano o empate

Si la diferencia entre los dos indicadores principales es menor o igual que
10 puntos, Silver registra `needs_profile_selection`.

La aplicación muestra los tres indicadores y la evidencia. RR. HH. selecciona
uno de los tres perfiles permitidos. Después de esa selección, el resultado se
guarda en Gold.

No se guarda `ambiguo`, `pendiente` ni `sin_asignar` como perfil.

### 8.3 Información incompleta

Si falta una métrica, meta, DNI válido, periodo o evidencia obligatoria, Silver
registra `needs_correction`.

RR. HH. debe corregir o volver a cargar el informe. No se escribe una evaluación
incompleta en Gold.

### 8.4 Inconsistencia entre fuentes

Si la diferencia entre el score métrico y el score del supervisor es de 50
puntos o más, la aplicación muestra una advertencia antes de finalizar.

RR. HH. revisa la evidencia y confirma uno de los tres perfiles permitidos. La
advertencia no crea un cuarto perfil ni un estado permanente en Gold.

---

## 9. Contrato Gold simplificado

Gold mantiene un perfil comercial final y vigente por preventista:

```text
employee_id
employee_name
zona_actual
score_captacion
score_fidelizacion
score_cobertura_ruta
score_disciplina_comunicacion
perfil_comercial
fortalezas
aspectos_mejora
explicacion_final
evaluated_at
```

Reglas de Gold:

- una fila vigente por `employee_id`;
- actualización mediante `upsert`;
- las cuatro dimensiones deben estar calculadas;
- `perfil_comercial` debe pertenecer al catálogo permitido;
- no se guardan perfiles pendientes o incompletos;
- no se guarda nivel de asignación;
- no se guarda elegibilidad para M3;
- no se guarda un flujo de aprobación o rechazo.
- `explicacion_final` es obligatoria y admite como máximo 1200 caracteres.

La interfaz principal mostrará:

- perfil comercial final;
- fortalezas principales;
- aspectos por mejorar;
- explicación basada en métricas y evidencia.

---

## 10. Relación simple con M3

M3 consume únicamente perfiles finales de Gold:

```text
employee_id
employee_name
zona_actual
perfil_comercial
```

La relación inicial entre M1 y M2 será:

| Cluster predominante de la cartera | Perfil preferido |
|---|---|
| Diamante y Oro | Fidelización |
| Plata | Ejecución en campo |
| Bronce y Nuevo | Captación |

Captación significa capacidad para conseguir cuentas nuevas y desarrollar
clientes recientes o poco consolidados.

M1 no bloquea preventistas ni decide qué cartera recibe cada uno. M3 realizará
la asignación final y deberá entregar una cartera a cada preventista activo.

Para el proyecto se asumirá que, antes de ejecutar M3, todos los preventistas
activos tienen un perfil comercial válido en Gold.

---

## 11. Contrato Medallion

M1 comparte los esquemas `bronze`, `silver` y `gold` de la misma instancia de
Supabase utilizada por M2, pero usa tablas propias:

```text
bronze.raw_informe_preventista
silver.perfil_preventista_estructurado
gold.preventistas_evaluados
```

Bronze conserva una fila por carga, incluso si falla la extracción o validación.
Silver conserva el historial de informes estructurados y sus estados técnicos.
Gold mantiene solamente perfiles comerciales finales.

Las tablas anteriores de CV no se reutilizarán silenciosamente. El cambio debe
implementarse mediante una migración SQL.

---

## 12. Flujo de Streamlit

La aplicación tendrá dos acciones principales:

1. **Cargar informe interno:** valida el PDF, extrae el texto, calcula el hash y
   guarda Bronze.
2. **Evaluar preventista:** estructura el informe, valida con Pydantic, aplica el
   LLM narrativo, ejecuta las reglas Python y genera la explicación detallada.
   Silver registra el estado; Gold se escribe solo cuando el perfil es final.

Después de evaluar:

```text
Perfil claro
→ guardar automáticamente en Gold

Perfil cercano o empate
→ RR. HH. selecciona uno de los tres perfiles
→ guardar en Gold

Información incompleta
→ solicitar corrección
→ no guardar en Gold
```

No existirán botones de aprobar o rechazar. La acción excepcional será
únicamente seleccionar el perfil o corregir el informe.

---

## 13. Pruebas de aceptación

Se deben validar como mínimo:

- PDF válido, vacío, dañado o sin texto extraíble;
- DNI ausente, no numérico o con longitud incorrecta;
- fechas del periodo válidas y ordenadas;
- métricas y metas dentro de rangos permitidos;
- ausencia de una métrica sin convertirla en cero;
- cálculo 70 % métricas y 30 % supervisor;
- catálogo narrativo `0, 25, 50, 75, 100`;
- límites de cumplimiento `70 %`, `90 %` y `105 %`;
- perfil de captación;
- perfil de fidelización;
- perfil de ejecución en campo;
- diferencia mayor que 10 para asignación automática;
- diferencia menor o igual que 10 para selección de RR. HH.;
- corrección obligatoria cuando falta información;
- advertencia cuando las fuentes difieren en 50 puntos o más;
- explicación final de hasta 1200 caracteres sin campos de decisión;
- comparación causal de los perfiles líderes cuando existe empate o cercanía;
- fallo técnico del tercer LLM sin escritura en Gold;
- imposibilidad de guardar un perfil fuera del catálogo;
- ausencia de valores `pendiente` o `sin_asignar` en Gold;
- persistencia Bronze → Silver → Gold;
- reejecución sin duplicar el perfil vigente en Gold.

---

## 14. Ejecución prevista

La implementación mantiene:

```text
Streamlit
pdfplumber
LLM
Pydantic v2
Python
Supabase/PostgreSQL
```

Variables de entorno:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
GITHUB_TOKEN
M1_LLM_MODEL
```

Estas variables se cargan desde `modules/m1_CV/.env`. M2 utiliza su propio
archivo `modules/m2_lrfmv/.env`; no se comparte un `.env` en la raíz.

Las credenciales no se escriben en el código, la interfaz ni los logs. La clave
de servicio solo se utiliza desde el servidor de Streamlit.

---

## 15. Fuera de alcance

- análisis de CV o selección de postulantes;
- recomendación de contratación o despido;
- clasificación por nivel de asignación;
- exclusión automática de preventistas activos;
- predicción de renuncia;
- cálculo automático de métricas desde sistemas externos;
- seguimiento completo del desempeño laboral;
- modificación automática de carteras;
- matching o Método Húngaro dentro de M1;
- almacenamiento del PDF original.

M1 termina cuando entrega a Gold uno de los tres perfiles comerciales válidos.
M3 utilizará ese perfil para asignar una cartera a cada preventista.

---

## 16. Decisiones cerradas

| Decisión | Estado |
|---|---|
| La entrada es un informe interno de RR. HH. | Cerrado |
| El CV queda fuera de M1 | Cerrado |
| Se mantienen cuatro dimensiones | Cerrado |
| Métricas 70 % y supervisor 30 % | Cerrado |
| Solo existen tres perfiles comerciales | Cerrado |
| Se elimina el nivel de asignación | Cerrado |
| Se elimina el score total | Cerrado |
| Se eliminan `m3_eligible` y estados de revisión de Gold | Cerrado |
| Los casos ambiguos se resuelven antes de Gold | Cerrado |
| Los informes incompletos se corrigen antes de Gold | Cerrado |
| Todo preventista activo tendrá un perfil final | Cerrado |
| M3 asignará una cartera a cada preventista | Cerrado |
