# M1_SPEC_SIMPLE_v1 — Perfilamiento Comercial de Preventistas con IA

**Proyecto:** Sistema de Data Science para distribución B2B de bebidas  
**Módulo:** Módulo 1 — CV Screening y Perfilamiento Comercial con IA  
**Versión:** Simple v1 — versión académica enfocada en aprendizaje  
**Fecha:** 2026-07-08  
**Estado:** Spec de trabajo para adaptar el Módulo 1 heredado al proyecto actual.

---

## 1. Propósito del módulo

El Módulo 1 analiza CVs de candidatos a preventistas usando IA para identificar su perfil comercial dominante y apoyar una mejor asignación futura a carteras de clientes.

Este módulo no está pensado como un sistema puro de Recursos Humanos ni como un sistema automático de contratación. Su objetivo principal es **perfilar comercialmente al preventista** para reducir el riesgo de mala asignación, frustración temprana y rotación.

La salida principal del módulo es una tabla de candidatos con:

1. **Score de adecuación comercial al rol de preventista B2B** entre 0 y 100.
2. **Tipo de preventista dominante**: `Hunter`, `Farmer` o `Ejecutor`.
3. **Nivel de confianza de la clasificación**.
4. **Riesgo de rotación o mala asignación**.
5. **Recomendación de asignación comercial inicial**.
6. **Explicación XAI** del resultado.

El campo clave para conectar este módulo con el Módulo 3 es:

```text
salesperson_type
```

---

## 2. Problema de negocio

La empresa presenta alta rotación de preventistas, ventas desordenadas y bajo cumplimiento de protocolos comerciales.

Una causa probable es que los vendedores son evaluados de forma general, sin identificar correctamente:

```text
- qué tipo de vendedor son
- en qué tipo de cartera podrían rendir mejor
- qué riesgo existe si se les asigna una cartera inadecuada
```

Esto genera dos escenarios negativos:

```text
1. Un vendedor inexperto puede ser asignado a clientes valiosos y deteriorar la relación comercial.

2. Un vendedor con alto potencial puede ser asignado a un nicho equivocado, frustrarse y terminar rotando.
```

Por eso, el Módulo 1 no busca decidir simplemente si alguien debe ser contratado o no. Busca responder:

```text
¿Este candidato tiene perfil comercial para preventa B2B?
¿Qué tipo de preventista parece ser?
¿A qué tipo de cartera conviene asignarlo inicialmente?
¿Qué riesgo tendría una mala asignación?
```

---

## 3. Idea central del Módulo 1

El Módulo 1 transforma CVs no estructurados en información comercial estructurada.

Flujo conceptual:

```text
CV PDF
→ extracción de texto
→ estructuración del CV con LLM
→ evaluación comercial con LLM
→ clasificación del tipo de preventista
→ salida explicable para Módulo 3
```

La pregunta principal no es:

```text
¿Este candidato es bueno o malo?
```

Sino:

```text
¿Qué tipo de preventista es y dónde podría desempeñarse mejor?
```

---

## 4. Alcance de esta versión

Esta versión se enfoca únicamente en candidatos para el rol de preventista B2B en distribución de bebidas, especialmente en canal tradicional: bodegas, minimarkets y pequeños comercios.

Incluye:

```text
- lectura de CVs en PDF
- extracción de texto
- estructuración del CV
- evaluación comercial
- clasificación Hunter/Farmer/Ejecutor
- score 0-100 de adecuación comercial
- riesgo simple de rotación o mala asignación
- explicación XAI
- salida Gold para Módulo 3
```

No incluye:

```text
- decisión automática de contratación
- entrevistas automatizadas
- análisis de voz o video
- validación psicométrica
- predicción supervisada de renuncia
- agente autónomo completo
- conexión obligatoria a FastAPI
- dashboard final
```

---

## 5. Estado actual heredado

El proyecto anterior ya contiene un pipeline base de CV screening.

El flujo heredado realiza:

```text
1. Extracción de texto desde PDF usando pdfplumber.
2. Estructuración del CV usando un LLM.
3. Evaluación del candidato contra un Job Spec.
4. Guardado de resultados en arquitectura Medallion.
```

El problema es que la evaluación heredada estaba orientada a un puesto técnico, usando dimensiones como:

```text
- skills técnicos
- experiencia
- educación
- idiomas
- fit general
```

Para el proyecto actual, esas dimensiones deben reemplazarse por criterios comerciales de preventistas:

```text
- experiencia comercial de campo
- canal tradicional
- prospección
- retención de cartera
- cobertura de ruta
- disciplina comercial
- comunicación con clientes
- cumplimiento de protocolos
```

---

## 6. Enfoque simplificado

En esta versión académica se mantiene una arquitectura simple:

```text
LLM estructura el CV
LLM evalúa el perfil comercial
Pydantic valida la salida
Python orquesta el pipeline
CSV o Supabase persiste los resultados
```

Esta versión no se presenta como un agente autónomo completo.

La definición correcta es:

```text
pipeline LLM de screening y perfilamiento comercial de preventistas
```

Como trabajo futuro podría evolucionar a:

```text
agente de IA para screening, validación, perfilamiento y recomendación de asignación inicial
```

---

## 7. Arquitectura Medallion del Módulo 1

La arquitectura mantiene tres capas:

```text
Bronze → texto crudo del CV
Silver → CV estructurado y evaluación comercial intermedia
Gold   → perfil comercial final listo para matching
```

### 7.1 Bronze

Responsabilidad:

```text
- almacenar el texto extraído del CV
- conservar metadatos del archivo
- no aplicar reglas de negocio complejas
```

Tabla o archivo conceptual:

```text
bronze.cv_raw_text
```

Columnas recomendadas:

```text
raw_cv_id
candidate_id
filename
file_hash
raw_text
num_pages
file_size_bytes
extraction_status
created_at
```

### 7.2 Silver

Responsabilidad:

```text
- estructurar información del candidato
- extraer experiencia laboral, educación y señales comerciales
- generar scores comerciales intermedios
```

Tablas o archivos conceptuales:

```text
silver.candidates_structured
silver.candidates_evaluated
```

### 7.3 Gold

Responsabilidad:

```text
- generar salida final para el Módulo 3
- definir score total de adecuación comercial
- definir salesperson_type
- explicar la decisión
- marcar riesgo de rotación o mala asignación
```

Tabla o archivo conceptual:

```text
gold.candidates_final
```

---

## 8. Inputs del Módulo 1

### 8.1 CVs en PDF

Entrada principal:

```text
data/m1/raw_cvs/*.pdf
```

Cada PDF representa un candidato.

### 8.2 Job Spec comercial

El Job Spec debe describir el rol objetivo:

```text
Preventista B2B para distribución de bebidas en canal tradicional.
```

Debe incluir criterios como:

```text
- ventas de campo
- canal tradicional
- bodegas y minimarkets
- gestión de ruta
- apertura de clientes
- retención de cartera
- cobertura diaria
- cumplimiento de cuota
- cobranza
- comunicación comercial
- cumplimiento de protocolos
```

---

## 9. Tipos de preventista

El campo principal para conectar Módulo 1 con Módulo 3 es:

```text
salesperson_type
```

Valores permitidos:

```text
Hunter
Farmer
Ejecutor
```

### 9.1 Hunter

Perfil orientado a prospección, apertura y reactivación.

Señales típicas en el CV:

```text
- apertura de clientes nuevos
- prospección
- venta fría
- captación de cartera
- expansión territorial
- reactivación de clientes
- cumplimiento agresivo de cuotas
```

Asignación comercial recomendada:

```text
- clientes Nuevo
- clientes Bronce
```

Riesgo si se asigna mal:

```text
Puede ser demasiado agresivo o poco relacional para cuentas Diamante.
```

### 9.2 Farmer

Perfil orientado a retención, fidelización y desarrollo de cartera.

Señales típicas en el CV:

```text
- gestión de cartera
- seguimiento a clientes recurrentes
- fidelización
- incremento de ticket
- cross-selling
- up-selling
- desarrollo de cuentas
- relación comercial estable
```

Asignación comercial recomendada:

```text
- clientes Diamante
- clientes Oro
```

Riesgo si se asigna mal:

```text
Puede frustrarse si se le asigna una cartera débil que no aprovecha su capacidad de desarrollo comercial.
```

### 9.3 Ejecutor

Perfil orientado a cobertura, disciplina de ruta y operación comercial.

Señales típicas en el CV:

```text
- cumplimiento de rutas
- visitas diarias
- cobertura de zona
- ejecución en punto de venta
- toma de pedidos
- cumplimiento de protocolo
- orden operativo
- venta de volumen
```

Asignación comercial recomendada:

```text
- clientes Plata
```

Riesgo si se asigna mal:

```text
Puede no ser el mejor perfil para negociar cuentas grandes ni para abrir agresivamente clientes nuevos.
```

---

## 10. Variables comerciales a extraer

Además de los campos básicos del CV, el Módulo 1 debe extraer señales comerciales útiles para clasificar al candidato.

Campos básicos:

```text
candidate_name
email
phone
location
summary_profile
commercial_experience_years
last_position
last_company
education_level
education_career
education_institution
```

Campos comerciales específicos:

```text
field_sales_experience
traditional_channel_experience
route_management_experience
new_account_opening_experience
client_retention_experience
portfolio_management_experience
collection_experience
daily_visits_experience
sales_quota_experience
point_of_sale_execution_experience
commercial_tools
sales_kpis_mentioned
```

Campos de evidencia:

```text
experience_detail
education_detail
commercial_evidence
```

---

## 11. Evaluación comercial

La evaluación no debe centrarse en skills técnicos.

Dimensiones recomendadas:

```text
score_commercial_experience
score_traditional_channel
score_prospecting
score_retention
score_route_coverage
score_discipline_protocol
score_communication
score_fit_preventista
```

Cada score debe estar entre:

```text
0 y 100
```

Interpretación:

```text
0   = sin evidencia
50  = evidencia parcial
100 = evidencia fuerte y directamente relacionada
```

---

## 12. Score total de adecuación comercial

El `score_total` mide el ajuste general del candidato al rol de preventista B2B.

No representa una decisión de contratación automática. Representa una medida de adecuación comercial para orientar el perfilamiento y la asignación posterior.

Pesos recomendados para versión simple:

| Dimensión | Peso |
|---|---:|
| Experiencia comercial | 25% |
| Canal tradicional | 20% |
| Prospección | 15% |
| Retención de cartera | 15% |
| Cobertura de ruta | 15% |
| Disciplina y comunicación | 10% |

Fórmula conceptual:

```text
score_total =
    0.25 * score_commercial_experience
  + 0.20 * score_traditional_channel
  + 0.15 * score_prospecting
  + 0.15 * score_retention
  + 0.15 * score_route_coverage
  + 0.10 * score_discipline_communication
```

El score total debe expresarse en escala:

```text
0-100
```

---

## 13. Nivel de preparación para asignación

En lugar de usar una recomendación de contratación, esta versión usa un campo operativo:

```text
assignment_readiness
```

Este campo indica qué tan preparado está el candidato para recibir una cartera comercial.

Valores permitidos:

```text
requiere_revision
requiere_acompanamiento
apto_operativo
apto_cartera_critica
```

Interpretación:

```text
requiere_revision:
    información insuficiente, perfil ambiguo o score bajo.

requiere_acompanamiento:
    candidato con potencial, pero necesita supervisión inicial.

apto_operativo:
    candidato adecuado para cartera regular según su perfil.

apto_cartera_critica:
    candidato con alta adecuación comercial y confianza suficiente para cartera sensible.
```

Regla orientativa:

```text
score_total < 50:
    assignment_readiness = "requiere_revision"

50 <= score_total < 70:
    assignment_readiness = "requiere_acompanamiento"

70 <= score_total < 85:
    assignment_readiness = "apto_operativo"

score_total >= 85:
    assignment_readiness = "apto_cartera_critica"
```

Esta regla puede ajustarse según criterio comercial.

---

## 14. Clasificación de salesperson_type

El LLM debe clasificar al candidato como:

```text
Hunter | Farmer | Ejecutor
```

La clasificación debe basarse en evidencia del CV.

Además, debe devolver:

```text
salesperson_type_confidence
```

Rango:

```text
0.00 a 1.00
```

Interpretación:

```text
0.00-0.59 → baja confianza
0.60-0.79 → confianza media
0.80-1.00 → confianza alta
```

Regla simple:

```text
Si salesperson_type_confidence < 0.60:
    requires_human_review = True
```

---

## 15. Riesgo de rotación o mala asignación

El Módulo 1 debe incluir una alerta simple de riesgo.

Campo:

```text
rotation_risk_level
```

Valores permitidos:

```text
bajo
medio
alto
```

Criterios orientativos:

```text
bajo:
    experiencia comercial clara
    perfil coherente
    buena confianza en la clasificación
    señales de estabilidad laboral

medio:
    experiencia parcial
    perfil comercial mixto
    poca evidencia de canal tradicional
    candidato junior

alto:
    baja experiencia
    perfil ambiguo
    cambios laborales frecuentes
    baja confianza en salesperson_type
    poca evidencia de venta de campo
```

Este campo no reemplaza evaluación humana. Sirve como alerta operativa para evitar asignaciones de alto riesgo.

---

## 16. Explicabilidad XAI

La salida debe incluir explicación en lenguaje natural.

Campo:

```text
xai_explanation
```

Debe responder:

```text
- por qué recibió ese score
- por qué fue clasificado como Hunter/Farmer/Ejecutor
- qué evidencia del CV respalda la decisión
- qué riesgos o brechas existen
- qué asignación inicial sería más razonable
```

Restricciones:

```text
No inventar experiencia.
No usar justificaciones genéricas.
Toda explicación debe basarse en evidencia del CV.
```

Ejemplo correcto:

```text
El candidato se clasifica como Farmer porque muestra experiencia en gestión de cartera, seguimiento de clientes recurrentes y desarrollo comercial. Presenta menor evidencia de apertura agresiva de cuentas nuevas, por lo que no se prioriza como Hunter.
```

Ejemplo incorrecto:

```text
El candidato tiene buen perfil comercial y puede vender bien.
```

---

## 17. Schema conceptual de salida Silver estructurada

Tabla o archivo:

```text
silver.candidates_structured
```

Columnas recomendadas:

```text
candidate_id
raw_cv_id
candidate_name
email
phone
location
summary_profile
commercial_experience_years
last_position
last_company
education_level
education_career
education_institution
field_sales_experience
traditional_channel_experience
route_management_experience
new_account_opening_experience
client_retention_experience
portfolio_management_experience
collection_experience
daily_visits_experience
sales_quota_experience
point_of_sale_execution_experience
commercial_tools
sales_kpis_mentioned
experience_detail
education_detail
commercial_evidence
```

---

## 18. Schema conceptual de evaluación Silver

Tabla o archivo:

```text
silver.candidates_evaluated
```

Columnas recomendadas:

```text
candidate_id
score_commercial_experience
score_traditional_channel
score_prospecting
score_retention
score_route_coverage
score_discipline_communication
score_fit_preventista
strengths
gaps
risks
raw_llm_evaluation
```

---

## 19. Schema conceptual de salida Gold

Tabla o archivo:

```text
gold.candidates_final
```

Columnas recomendadas:

```text
candidate_id
candidate_name
score_total
assignment_readiness
salesperson_type
salesperson_type_confidence
commercial_seniority
rotation_risk_level
recommended_assignment
requires_human_review
xai_explanation
strengths
gaps
risks
created_at
```

Valores esperados:

```text
salesperson_type ∈ {Hunter, Farmer, Ejecutor}

assignment_readiness ∈ {
    requiere_revision,
    requiere_acompanamiento,
    apto_operativo,
    apto_cartera_critica
}

rotation_risk_level ∈ {bajo, medio, alto}

recommended_assignment ∈ {
    Diamante/Oro,
    Plata,
    Bronce/Nuevo,
    Revisión humana
}
```

---

## 20. Relación con el Módulo 3

El Módulo 3 no necesita todo el CV.

Solo necesita desde Módulo 1:

```text
candidate_id
candidate_name
score_total
assignment_readiness
salesperson_type
salesperson_type_confidence
rotation_risk_level
```

El campo clave es:

```text
salesperson_type
```

El Módulo 2 entrega:

```text
client_id
cluster_label
score_lrfmv_0_100
is_churn_risk
```

Entonces el Módulo 3 cruza:

```text
salesperson_type × cluster_label
```

Ejemplos:

```text
Farmer + Diamante → óptimo
Farmer + Oro      → óptimo
Ejecutor + Plata  → óptimo
Hunter + Bronce   → óptimo
Hunter + Nuevo    → óptimo
```

---

## 21. Matriz conceptual de asignación futura

Referencia para Módulo 3:

| Cluster cliente | Preventista recomendado | Justificación |
|---|---|---|
| Diamante | Farmer | Retención y protección de cartera valiosa |
| Oro | Farmer | Desarrollo y fidelización |
| Plata | Ejecutor | Cobertura operativa y volumen |
| Bronce | Hunter | Reactivación selectiva |
| Nuevo | Hunter | Prospección y onboarding |

El Módulo 1 no ejecuta el matching. Solo entrega el perfil comercial del candidato.

---

## 22. Prompts necesarios

Esta versión requiere dos prompts principales.

### 22.1 Prompt de estructuración

Objetivo:

```text
Extraer información del CV y devolver un JSON estructurado.
```

Debe enfocarse en:

```text
- datos personales básicos
- experiencia laboral
- educación
- señales comerciales
- experiencia en ventas de campo
- canal tradicional
- rutas
- cartera
- prospección
- retención
```

Restricción:

```text
No evaluar.
No opinar.
No inventar.
Solo extraer evidencia del CV.
```

### 22.2 Prompt de evaluación comercial

Objetivo:

```text
Evaluar el ajuste del candidato al rol de preventista B2B y clasificar su perfil comercial dominante.
```

Debe devolver:

```text
- scores comerciales
- score_total
- assignment_readiness
- salesperson_type
- salesperson_type_confidence
- rotation_risk_level
- recommended_assignment
- xai_explanation
- strengths
- gaps
- risks
```

Restricción:

```text
Evaluar solo con evidencia del CV estructurado.
Si falta evidencia, penalizar o marcar incertidumbre.
```

---

## 23. Validaciones mínimas

El pipeline debe validar:

```text
1. Que el PDF tenga texto extraíble.
2. Que el JSON de estructuración cumpla el schema.
3. Que el JSON de evaluación cumpla el schema.
4. Que score_total esté entre 0 y 100.
5. Que salesperson_type sea Hunter, Farmer o Ejecutor.
6. Que assignment_readiness sea uno de los valores permitidos.
7. Que confidence esté entre 0 y 1.
8. Que exista xai_explanation.
```

Reglas simples:

```text
Si texto_extraido está vacío:
    extraction_status = failed
    no evaluar

Si JSON inválido:
    validation_status = failed

Si salesperson_type_confidence < 0.60:
    requires_human_review = True

Si score_total < 50:
    assignment_readiness = requiere_revision
```

---

## 24. Outputs esperados

Para versión local:

```text
outputs/m1/bronze/cv_raw_text.csv
outputs/m1/silver/candidates_structured.csv
outputs/m1/silver/candidates_evaluated.csv
outputs/m1/gold/candidates_final.csv
```

Para versión con Supabase:

```text
bronze.cv_raw_text
silver.candidates_structured
silver.candidates_evaluated
gold.candidates_final
```

---

## 25. Flujo final del pipeline

```text
1. Leer PDFs de candidatos.

2. Extraer texto con pdfplumber.

3. Guardar texto crudo y metadatos en Bronze.

4. Enviar texto al LLM para estructuración.

5. Validar salida con Pydantic.

6. Guardar CV estructurado en Silver.

7. Enviar CV estructurado + Job Spec comercial al LLM para evaluación.

8. Validar evaluación con Pydantic.

9. Calcular o confirmar score_total.

10. Clasificar salesperson_type.

11. Definir assignment_readiness.

12. Marcar riesgo de rotación o mala asignación.

13. Marcar revisión humana si corresponde.

14. Guardar salida final en Gold.

15. Exportar gold.candidates_final para Módulo 3.
```

---

## 26. Decisiones cerradas

| Decisión | Estado |
|---|---|
| M1 se enfoca en perfilamiento comercial de preventistas B2B | Cerrado |
| M1 no se presenta como sistema puro de Recursos Humanos | Cerrado |
| M1 no entrega recomendación automática de contratación | Cerrado |
| El campo clave para M3 es `salesperson_type` | Cerrado |
| Tipos permitidos: Hunter, Farmer, Ejecutor | Cerrado |
| Se mantiene score 0-100 de adecuación comercial | Cerrado |
| Se reemplaza `hire_cluster` por `assignment_readiness` | Cerrado |
| Se incluye explicación XAI | Cerrado |
| Se incluye riesgo simple de rotación o mala asignación | Cerrado |
| Se usa LLM para estructurar CV | Cerrado |
| Se usa LLM para evaluar perfil comercial | Cerrado |
| Pydantic valida las salidas | Cerrado |
| M1 no ejecuta matching | Cerrado |
| M1 alimenta a M3 mediante Gold | Cerrado |
| No se presenta como agente autónomo completo | Cerrado |

---

## 27. Límites de alcance

Esta versión no incluye:

```text
- agente autónomo completo
- múltiples agentes especializados
- entrevistas por voz
- análisis emocional
- predicción supervisada de renuncia
- validación con datos reales de RRHH
- decisión automática de contratación
- conexión obligatoria a FastAPI
- deployment productivo
- dashboard final
```

Estos puntos pueden mencionarse como trabajo futuro.

---

## 28. Trabajo futuro

Mejoras posibles:

```text
1. Separar extracción con LLM y scoring determinístico en Python.
2. Agregar critic interno para revisar inconsistencias.
3. Reintentar automáticamente cuando el JSON sea inválido.
4. Agregar revisión humana para perfiles ambiguos.
5. Convertir el pipeline en agente con LangGraph.
6. Usar historial real de desempeño y rotación para validar el score.
7. Incorporar entrevistas estructuradas como fuente adicional.
8. Ajustar pesos del score con expertos comerciales o AHP.
```

---

## 29. Respuesta para defensa

> El Módulo 1 aborda la alta rotación de preventistas desde una perspectiva de ajuste comercial. No se limita a rankear candidatos ni a emitir una recomendación de contratación, sino que analiza CVs con IA para identificar el perfil dominante del vendedor: Hunter, Farmer o Ejecutor. Esta clasificación permite anticipar en qué tipo de cartera podría desempeñarse mejor cada persona. Un vendedor inexperto asignado a clientes valiosos puede deteriorar la relación comercial, mientras que un vendedor de alto potencial ubicado en una cartera incorrecta puede frustrarse y rotar. Por ello, el módulo genera un score de adecuación comercial, una explicación XAI, una alerta de riesgo de mala asignación y el campo clave `salesperson_type`, que luego será usado por el Módulo 3 para asignar preventistas a clientes según compatibilidad comercial.

---

## 30. Idea central

El Módulo 1 debe demostrar que la rotación no es solo un problema de contratación.

También es un problema de asignación.

Por eso, la salida más importante no es solo:

```text
score_total
```

Sino:

```text
salesperson_type
```

Porque el objetivo final es:

```text
perfilar mejor + asignar mejor + reducir frustración + proteger clientes valiosos
```
