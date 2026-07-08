import json
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================
# 0. ESQUEMAS DE DATOS - alineados con Medallion (Silver + Gold)
# =============================================================


class ExperienciaDetalle(BaseModel):
    company: str = Field(description="Empresa o negocio mencionado en el CV")
    position: str = Field(description="Cargo desempenado")
    start: Optional[str] = Field(None, description="Fecha de inicio como texto libre")
    end: Optional[str] = Field(None, description="Fecha de fin como texto libre")
    description: str = Field(description="Descripcion breve de funciones y logros")


class EducacionDetalle(BaseModel):
    institution: str
    career: str
    start: Optional[str] = None
    end: Optional[str] = None


# Silver - candidates_structured
class CVSchema(BaseModel):
    dni: str = Field(
        pattern=r"^\d{8}$",
        description="DNI peruano del candidato, obligatorio, exactamente 8 digitos",
    )
    candidate_name: Optional[str] = Field(None, description="Nombre y apellidos completos")
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary_profile: Optional[str] = None
    commercial_experience_years: Optional[float] = Field(
        None,
        ge=0,
        description="Anos de experiencia comercial estimados desde el CV",
    )
    last_position: Optional[str] = None
    last_company: Optional[str] = None
    education_level: Optional[str] = None
    education_career: Optional[str] = None
    education_institution: Optional[str] = None
    field_sales_experience: Optional[str] = Field(
        None,
        description="Evidencia de ventas de campo o trabajo comercial presencial",
    )
    traditional_channel_experience: Optional[str] = Field(
        None,
        description="Evidencia de experiencia en bodegas, minimarkets o canal tradicional",
    )
    route_management_experience: Optional[str] = None
    new_account_opening_experience: Optional[str] = None
    client_retention_experience: Optional[str] = None
    portfolio_management_experience: Optional[str] = None
    collection_experience: Optional[str] = None
    daily_visits_experience: Optional[str] = None
    sales_quota_experience: Optional[str] = None
    point_of_sale_execution_experience: Optional[str] = None
    commercial_tools: List[str] = Field(default_factory=list)
    sales_kpis_mentioned: List[str] = Field(default_factory=list)
    experience_detail: List[ExperienciaDetalle] = Field(default_factory=list)
    education_detail: List[EducacionDetalle] = Field(default_factory=list)
    commercial_evidence: List[str] = Field(
        default_factory=list,
        description="Frases o senales concretas extraidas del CV que sustentan el perfil comercial",
    )


# Gold - candidates_final
class EvaluacionSchema(BaseModel):
    score_commercial_experience: float = Field(ge=0, le=100)
    score_traditional_channel: float = Field(ge=0, le=100)
    score_prospecting: float = Field(ge=0, le=100)
    score_retention: float = Field(ge=0, le=100)
    score_route_coverage: float = Field(ge=0, le=100)
    score_discipline_communication: float = Field(ge=0, le=100)
    score_fit_preventista: float = Field(ge=0, le=100)
    score_total: float = Field(ge=0, le=100)
    assignment_readiness: Literal[
        "requiere_revision",
        "requiere_acompanamiento",
        "apto_operativo",
        "apto_cartera_critica",
    ]
    salesperson_type: Literal["Hunter", "Farmer", "Ejecutor"]
    salesperson_type_confidence: float = Field(ge=0, le=1)
    commercial_seniority: Optional[str] = Field(
        None,
        description="Nivel comercial estimado: junior, semi_senior, senior u otro texto justificado",
    )
    rotation_risk_level: Literal["bajo", "medio", "alto"]
    recommended_assignment: Literal["Diamante/Oro", "Plata", "Bronce/Nuevo", "Revisión humana"]
    requires_human_review: bool
    xai_explanation: str = Field(min_length=1)
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    raw_llm_evaluation: Optional[str] = Field(
        None,
        description="Resumen opcional de la evaluacion original del LLM para trazabilidad",
    )


# Schemas JSON para inyectar en los prompts.
json_schema_cv = json.dumps(CVSchema.model_json_schema(), ensure_ascii=False, indent=2)
json_schema_evaluacion = json.dumps(
    EvaluacionSchema.model_json_schema(),
    ensure_ascii=False,
    indent=2,
)


# =============================================================
# 1. PROMPTS DEL SISTEMA (System Prompts)
# =============================================================

SYS_PROMPT_ESTRUCTURACION = f"""
Eres un extractor especializado de informacion de CVs para preventistas B2B.
Tu unica funcion es extraer datos y evidencia comercial. No evalues, no opines y no inventes experiencia ausente.

CONTEXTO:
Se te proporciona el texto completo de un CV de una persona candidata a preventista para una empresa de distribucion de bebidas en Peru.

TAREA:
Extrae informacion estructurada del CV, con foco en DNI, experiencia comercial de campo, canal tradicional, gestion de ruta, apertura de clientes, retencion, cobranza, visitas diarias, cuotas, ejecucion en punto de venta, herramientas comerciales y KPIs mencionados.

REGLAS:
- dni es obligatorio y debe tener exactamente 8 digitos. Si el CV no contiene DNI, devuelve null y la validacion Pydantic rechazara el registro para revision humana.
- Si un campo no esta presente, devuelve null para campos escalares o [] para listas.
- commercial_experience_years debe estimarse conservadoramente desde la experiencia laboral comercial.
- commercial_evidence debe incluir solo senales textuales o resumidas que aparezcan en el CV.
- No clasifiques al candidato como Hunter, Farmer o Ejecutor en esta fase.
- No recomiendes contratacion ni asignacion en esta fase.

RESTRICCIONES:
1. Tu respuesta debe ser SOLO un objeto JSON valido, comenzando con {{ y terminando con }}.
2. El JSON DEBE cumplir estrictamente con este schema:
{json_schema_cv}
3. Escapa correctamente las comillas dobles internas o reemplazalas por comillas simples.
4. Reemplaza saltos de linea dentro de los textos por \\n.
""".strip()


SYS_PROMPT_EVALUACION = f"""
Eres un evaluador comercial especializado en preventa B2B para distribucion de bebidas en canal tradicional.
Tu objetivo no es decidir contratacion. Tu objetivo es perfilar comercialmente al candidato para orientar una futura asignacion de cartera.

CONTEXTO:
Recibes:
1. Un CV ya estructurado y validado.
2. Un Job Spec comercial para preventista B2B.

TAREA:
Evalua el ajuste comercial del candidato al rol de preventista B2B y clasifica su perfil dominante como Hunter, Farmer o Ejecutor.

DIMENSIONES DE SCORE 0-100:
- score_commercial_experience: experiencia comercial general.
- score_traditional_channel: evidencia de canal tradicional, bodegas, minimarkets o pequenos comercios.
- score_prospecting: apertura de clientes, prospeccion, reactivacion o venta fria.
- score_retention: gestion, fidelizacion o desarrollo de cartera.
- score_route_coverage: rutas, visitas diarias, cobertura o ejecucion operativa.
- score_discipline_communication: cumplimiento de protocolos, cobranza, reportes y comunicacion comercial.
- score_fit_preventista: coherencia general con el rol de preventista B2B.

REGLAS DE NEGOCIO:
- score_total debe estar entre 0 y 100.
- assignment_readiness debe seguir esta guia:
  score_total < 50 -> requiere_revision
  50 <= score_total < 70 -> requiere_acompanamiento
  70 <= score_total < 85 -> apto_operativo
  score_total >= 85 -> apto_cartera_critica
- salesperson_type debe ser exactamente Hunter, Farmer o Ejecutor.
- salesperson_type_confidence debe estar entre 0 y 1.
- requires_human_review debe ser true si salesperson_type_confidence < 0.60.
- recommended_assignment debe ser:
  Hunter -> Bronce/Nuevo
  Farmer -> Diamante/Oro
  Ejecutor -> Plata
  Si la evidencia es insuficiente -> Revisión humana

RESTRICCIONES:
- Evalua solo con evidencia del CV estructurado. Si falta evidencia, penaliza o marca incertidumbre.
- No uses lenguaje de contratacion automatica.
- No uses hire_cluster.
- xai_explanation debe explicar el score, el salesperson_type, la evidencia usada, brechas, riesgos y asignacion inicial razonable.
- Las justificaciones deben ser especificas, no genericas.

FORMATO DE RESPUESTA:
SOLO un objeto JSON valido que cumpla este schema:
{json_schema_evaluacion}
""".strip()


# =============================================================
# 2. PROMPTS DEL USUARIO (User Prompts)
# =============================================================


def get_user_prompt_estructuracion(texto_cv: str) -> str:
    return (
        "Extrae los datos comerciales de este CV estrictamente siguiendo las reglas indicadas:\n"
        "---\n"
        f"{texto_cv}\n"
        "---\n"
    )


def get_user_prompt_evaluacion(cv_json_str: str, job_spec: str) -> str:
    return (
        "JOB SPEC COMERCIAL:\n"
        "---\n"
        f"{job_spec}\n"
        "---\n\n"
        "CANDIDATO (CV estructurado):\n"
        "---\n"
        f"{cv_json_str}\n"
        "---\n\n"
        "JSON:\n"
    )
