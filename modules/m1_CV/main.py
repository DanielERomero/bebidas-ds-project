from __future__ import annotations

import hashlib
import io
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import BinaryIO

import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError
from supabase import Client, create_client

from prompts import (
    PROMPT_VERSION,
    SYS_PROMPT_ESTRUCTURACION,
    SYS_PROMPT_EVALUACION,
    SYS_PROMPT_EXPLICACION,
    EvaluacionSupervisorSchema,
    ExplicacionFinalSchema,
    PerfilPreventistaSchema,
    PeriodoEvaluacion,
    get_user_prompt_estructuracion,
    get_user_prompt_evaluacion,
    get_user_prompt_explicacion,
)
from rules import (
    construir_evaluacion_intermedia,
    construir_resultado_correccion,
    encontrar_datos_faltantes,
    seleccionar_perfil,
)


MODULE_DIR = Path(__file__).resolve().parent
load_dotenv(MODULE_DIR / ".env")


def obtener_configuracion(nombre: str, default: str | None = None) -> str | None:
    """Lee .env localmente y st.secrets cuando la app corre en Streamlit Cloud."""
    valor_entorno = os.getenv(nombre)
    if valor_entorno is not None:
        return valor_entorno

    try:
        import streamlit as st

        return st.secrets.get(nombre, default)
    except FileNotFoundError:
        return default


SUPABASE_URL = obtener_configuracion("SUPABASE_URL")
SUPABASE_KEY = obtener_configuracion(
    "SUPABASE_SERVICE_ROLE_KEY"
) or obtener_configuracion("SUPABASE_KEY")
GITHUB_TOKEN = obtener_configuracion("GITHUB_TOKEN")
MODELO_NUBE = obtener_configuracion("M1_LLM_MODEL", "gpt-4o")

PERIODO_INICIO = date(2025, 1, 1)
PERIODO_FIN = date(2025, 6, 30)
PERIODO_MESES = 6

BRONZE_TABLE = "raw_informe_preventista"
SILVER_TABLE = "perfil_preventista_estructurado"
GOLD_TABLE = "preventistas_evaluados"
GOLD_EVALUATION_FIELDS = {
    "employee_id",
    "employee_name",
    "zona_actual",
    "score_captacion",
    "score_fidelizacion",
    "score_cobertura_ruta",
    "score_disciplina_comunicacion",
    "perfil_comercial",
    "fortalezas",
    "aspectos_mejora",
    "explicacion_final",
}

supabase: Client | None = None
llm_client: OpenAI | None = None


def get_supabase_client() -> Client:
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Faltan SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY (o SUPABASE_KEY)."
            )
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


def get_llm_client() -> OpenAI:
    global llm_client
    if llm_client is None:
        if not GITHUB_TOKEN:
            raise ValueError("Falta GITHUB_TOKEN en el entorno o archivo .env.")
        llm_client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=GITHUB_TOKEN,
        )
    return llm_client


def _abrir_pdf(origen: str | Path | bytes | BinaryIO):
    if isinstance(origen, bytes):
        return pdfplumber.open(io.BytesIO(origen))
    return pdfplumber.open(origen)


def extraer_texto_pdf_detallado(
    origen: str | Path | bytes | BinaryIO,
) -> tuple[str, int, str | None]:
    texto_extraido = []
    try:
        with _abrir_pdf(origen) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_extraido.append(texto)
            return "\n".join(texto_extraido).strip(), len(pdf.pages), None
    except Exception as exc:
        return "", 0, str(exc)


def extraer_texto_pdf(origen: str | Path | bytes | BinaryIO) -> tuple[str, int]:
    """Interfaz pequeña para pruebas locales de extracción."""

    texto, paginas, _ = extraer_texto_pdf_detallado(origen)
    return texto, paginas


def detectar_dni(texto: str) -> str | None:
    coincidencia_etiquetada = re.search(
        r"(?i)\bDNI\s*(?:N[.°ºo]*\s*)?[:\-]?\s*(\d{8})\b", texto
    )
    if coincidencia_etiquetada:
        return coincidencia_etiquetada.group(1)

    candidatos = re.findall(r"(?<!\d)(\d{8})(?!\d)", texto)
    return candidatos[0] if len(set(candidatos)) == 1 else None


def enmascarar_dni(dni: str | None) -> str:
    return f"****{dni[-4:]}" if dni else "no disponible"


def interactuar_con_gpt(prompt: str, rol_sistema: str) -> dict:
    try:
        response = get_llm_client().chat.completions.create(
            messages=[
                {"role": "system", "content": rol_sistema},
                {"role": "user", "content": prompt},
            ],
            model=MODELO_NUBE,
            temperature=0,
            response_format={"type": "json_object"},
        )
        contenido = response.choices[0].message.content
        return json.loads(contenido or "{}")
    except Exception as exc:
        raise RuntimeError("No se pudo obtener una respuesta válida del LLM.") from exc


def estructurar_informe(
    texto_crudo: str,
    *,
    periodo_inicio: date | str,
    periodo_fin: date | str,
    periodo_meses: int,
) -> dict:
    resultado = interactuar_con_gpt(
        get_user_prompt_estructuracion(
            texto_crudo,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            periodo_meses=periodo_meses,
        ),
        SYS_PROMPT_ESTRUCTURACION,
    )
    try:
        return PerfilPreventistaSchema.model_validate(resultado).model_dump(mode="json")
    except ValidationError as exc:
        raise ValueError(
            "La estructuración del informe no cumple el contrato Silver."
        ) from exc


def evaluar_preventista(perfil_estructurado: dict) -> dict:
    evidencia_json = json.dumps(
        perfil_estructurado["evidencia_supervisor"],
        ensure_ascii=False,
    )
    resultado = interactuar_con_gpt(
        get_user_prompt_evaluacion(evidencia_json),
        SYS_PROMPT_EVALUACION,
    )
    try:
        evaluacion_supervisor = EvaluacionSupervisorSchema.model_validate(
            resultado
        ).model_dump()
    except ValidationError as exc:
        raise ValueError(
            "La evaluación narrativa no cumple el contrato Pydantic."
        ) from exc
    return construir_evaluacion_intermedia(
        perfil_estructurado, evaluacion_supervisor
    )


def construir_contexto_explicacion(
    perfil_estructurado: dict,
    evaluacion: dict,
) -> dict:
    """Expone al tercer LLM hechos calculados, no autoridad de decision."""

    campos_scores = (
        "score_captacion",
        "score_fidelizacion",
        "score_cobertura_ruta",
        "score_disciplina_comunicacion",
    )
    campos_metricas = (
        "score_metrica_captacion",
        "score_metrica_fidelizacion",
        "score_metrica_cobertura_ruta",
        "score_metrica_disciplina_comunicacion",
    )
    campos_supervisor = (
        "score_supervisor_captacion",
        "score_supervisor_fidelizacion",
        "score_supervisor_cobertura_ruta",
        "score_supervisor_disciplina_comunicacion",
    )
    return {
        "processing_status": evaluacion["processing_status"],
        "scores_finales": {
            campo: evaluacion[campo] for campo in campos_scores
        },
        "scores_metricas": {
            campo: evaluacion[campo] for campo in campos_metricas
        },
        "scores_supervisor": {
            campo: evaluacion[campo] for campo in campos_supervisor
        },
        "indicadores_perfil": evaluacion["indicadores_perfil"],
        "perfil_propuesto": evaluacion.get("perfil_propuesto"),
        "diferencia_perfiles": evaluacion["diferencia_perfiles"],
        "inconsistencias": evaluacion["inconsistencias"],
        "evidencia_supervisor": perfil_estructurado["evidencia_supervisor"],
        "fortalezas": evaluacion["fortalezas"],
        "aspectos_mejora": evaluacion["aspectos_mejora"],
    }


def generar_explicacion_final(
    perfil_estructurado: dict,
    evaluacion: dict,
) -> str:
    if evaluacion["processing_status"] == "needs_correction":
        raise ValueError("Un informe incompleto no genera explicacion final.")

    resultado = interactuar_con_gpt(
        get_user_prompt_explicacion(
            construir_contexto_explicacion(perfil_estructurado, evaluacion)
        ),
        SYS_PROMPT_EXPLICACION,
    )
    try:
        return ExplicacionFinalSchema.model_validate(
            resultado
        ).explicacion_final
    except ValidationError as exc:
        raise ValueError(
            "La explicación final no cumple el contrato Pydantic."
        ) from exc


def registrar_bronze(
    *,
    file_name: str,
    pdf_bytes: bytes,
    extracted_text: str,
    page_count: int,
    employee_id: str | None,
    periodo: dict,
    extraction_status: str,
    error_message: str | None = None,
) -> str:
    registro = {
        "employee_id": employee_id,
        "file_name": Path(file_name).name,
        "file_hash": hashlib.sha256(pdf_bytes).hexdigest(),
        "extracted_text": extracted_text or None,
        "page_count": page_count,
        **periodo,
        "extraction_status": extraction_status,
        "error_message": error_message,
    }
    response = (
        get_supabase_client()
        .schema("bronze")
        .table(BRONZE_TABLE)
        .insert(registro)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase no devolvió el identificador Bronze.")
    return response.data[0]["raw_informe_id"]


def registrar_silver(
    raw_informe_id: str,
    perfil_estructurado: dict,
    processing_status: str,
) -> str:
    registro = {
        "raw_informe_id": raw_informe_id,
        "dni": perfil_estructurado["dni"],
        "nombre_colaborador": perfil_estructurado["nombre_colaborador"],
        "antiguedad_meses_empresa": perfil_estructurado.get(
            "antiguedad_meses_empresa"
        ),
        "zona_actual": perfil_estructurado.get("zona_actual"),
        "metricas_campo": perfil_estructurado["metricas_campo"],
        "evidencia_supervisor": perfil_estructurado["evidencia_supervisor"],
        "processing_status": processing_status,
        "model_name": MODELO_NUBE,
        "prompt_version": PROMPT_VERSION,
    }
    response = (
        get_supabase_client()
        .schema("silver")
        .table(SILVER_TABLE)
        .upsert(registro, on_conflict="raw_informe_id")
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase no devolvió el identificador Silver.")
    return response.data[0]["perfil_estructurado_id"]


def actualizar_estado_silver(
    perfil_estructurado_id: str,
    processing_status: str,
) -> None:
    response = (
        get_supabase_client()
        .schema("silver")
        .table(SILVER_TABLE)
        .update({"processing_status": processing_status})
        .eq("perfil_estructurado_id", perfil_estructurado_id)
        .execute()
    )
    if not response.data:
        raise RuntimeError("No se pudo actualizar el estado Silver.")


def registrar_gold(
    *,
    raw_informe_id: str,
    perfil_estructurado_id: str,
    evaluacion: dict,
) -> dict:
    registro = {
        **{
            campo: evaluacion[campo]
            for campo in GOLD_EVALUATION_FIELDS
        },
        "raw_informe_id": raw_informe_id,
        "perfil_estructurado_id": perfil_estructurado_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    response = (
        get_supabase_client()
        .schema("gold")
        .table(GOLD_TABLE)
        .upsert(registro, on_conflict="employee_id")
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase no devolvió la evaluación Gold.")
    return response.data[0]


def cargar_informe_en_bronze(
    file_name: str,
    pdf_bytes: bytes,
    *,
    periodo_inicio: date | str,
    periodo_fin: date | str,
    periodo_meses: int,
) -> dict:
    periodo = PeriodoEvaluacion.model_validate(
        {
            "periodo_inicio": periodo_inicio,
            "periodo_fin": periodo_fin,
            "periodo_meses": periodo_meses,
        }
    ).model_dump(mode="json")

    texto, paginas, error = extraer_texto_pdf_detallado(pdf_bytes)
    employee_id = detectar_dni(texto) if texto else None

    if error:
        estado = "invalid_pdf"
        mensaje = "El archivo no es un PDF válido o está dañado."
    elif not texto:
        estado = "empty_text"
        mensaje = "El PDF no contiene texto extraíble."
    elif not employee_id:
        estado = "invalid_dni"
        mensaje = "No se encontró un DNI peruano válido y no ambiguo."
    else:
        estado = "success"
        mensaje = None

    raw_informe_id = registrar_bronze(
        file_name=file_name,
        pdf_bytes=pdf_bytes,
        extracted_text=texto,
        page_count=paginas,
        employee_id=employee_id,
        periodo=periodo,
        extraction_status=estado,
        error_message=mensaje,
    )
    return {
        "raw_informe_id": raw_informe_id,
        "employee_id": employee_id,
        "extracted_text": texto,
        "page_count": paginas,
        **periodo,
        "extraction_status": estado,
        "error_message": mensaje,
    }


def estructurar_evaluar_y_guardar(carga_bronze: dict) -> dict:
    if carga_bronze["extraction_status"] != "success":
        raise ValueError("Solo un registro Bronze exitoso puede avanzar a Silver.")

    perfil_estructurado = estructurar_informe(
        carga_bronze["extracted_text"],
        periodo_inicio=carga_bronze["periodo_inicio"],
        periodo_fin=carga_bronze["periodo_fin"],
        periodo_meses=carga_bronze["periodo_meses"],
    )
    if perfil_estructurado["dni"] != carga_bronze["employee_id"]:
        raise ValueError("El DNI estructurado no coincide con el detectado en Bronze.")

    if encontrar_datos_faltantes(perfil_estructurado):
        evaluacion = construir_resultado_correccion(perfil_estructurado)
        perfil_estructurado_id = registrar_silver(
            carga_bronze["raw_informe_id"],
            perfil_estructurado,
            evaluacion["processing_status"],
        )
        return {
            "structured_profile": perfil_estructurado,
            "evaluation": evaluacion,
            "perfil_estructurado_id": perfil_estructurado_id,
            "gold": None,
        }

    evaluacion = evaluar_preventista(perfil_estructurado)
    evaluacion["explicacion_final"] = generar_explicacion_final(
        perfil_estructurado, evaluacion
    )
    perfil_estructurado_id = registrar_silver(
        carga_bronze["raw_informe_id"],
        perfil_estructurado,
        evaluacion["processing_status"],
    )

    gold = None
    if evaluacion["processing_status"] == "valid":
        gold = registrar_gold(
            raw_informe_id=carga_bronze["raw_informe_id"],
            perfil_estructurado_id=perfil_estructurado_id,
            evaluacion=evaluacion,
        )
    return {
        "structured_profile": perfil_estructurado,
        "evaluation": evaluacion,
        "perfil_estructurado_id": perfil_estructurado_id,
        "gold": gold,
    }


def confirmar_perfil(
    *,
    raw_informe_id: str,
    perfil_estructurado_id: str,
    evaluacion: dict,
    perfil_comercial: str,
) -> dict:
    evaluacion_final = seleccionar_perfil(evaluacion, perfil_comercial)
    actualizar_estado_silver(perfil_estructurado_id, "valid")
    gold = registrar_gold(
        raw_informe_id=raw_informe_id,
        perfil_estructurado_id=perfil_estructurado_id,
        evaluacion=evaluacion_final,
    )
    return {"evaluation": evaluacion_final, "gold": gold}


def procesar_preventista(ruta_pdf: str) -> dict:
    """Pipeline completo para una prueba manual con un informe local."""

    pdf_bytes = Path(ruta_pdf).read_bytes()
    carga = cargar_informe_en_bronze(
        Path(ruta_pdf).name,
        pdf_bytes,
        periodo_inicio=PERIODO_INICIO,
        periodo_fin=PERIODO_FIN,
        periodo_meses=PERIODO_MESES,
    )
    if carga["extraction_status"] != "success":
        print(f"[-] Carga detenida: {carga['error_message']}")
        return {"bronze": carga}

    resultado = estructurar_evaluar_y_guardar(carga)
    evaluacion = resultado["evaluation"]
    print(
        "[+] Evaluación guardada para "
        f"{enmascarar_dni(carga['employee_id'])}: "
        f"{evaluacion['processing_status']} - "
        f"{evaluacion.get('perfil_comercial') or 'seleccion pendiente'}"
    )
    return {"bronze": carga, **resultado}


if __name__ == "__main__":
    print("Ejecuta la interfaz con: uv run streamlit run app.py")
