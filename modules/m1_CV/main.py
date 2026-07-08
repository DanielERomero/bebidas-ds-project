import pdfplumber
import hashlib
import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError
from prompts import (
    SYS_PROMPT_ESTRUCTURACION, SYS_PROMPT_EVALUACION,
    CVSchema, EvaluacionSchema,
    get_user_prompt_estructuracion, get_user_prompt_evaluacion
)
# ==========================================
# 1. CONFIGURACIÓN DEL ENTORNO
# ==========================================
# Credenciales de Supabase
load_dotenv()  # Carga las variables de entorno desde el archivo .env
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client | None = None

# Configuración de OpenAI (GitHub Models)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
llm_client: OpenAI | None = None
MODELO_NUBE = "gpt-4o"


def get_supabase_client() -> Client:
    """
    Inicializa Supabase solo cuando se va a persistir.
    Esto permite importar el módulo y probar schemas sin credenciales.
    """
    global supabase

    if supabase is not None:
        return supabase

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Faltan las variables SUPABASE_URL o SUPABASE_KEY en el entorno o .env")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


def get_llm_client() -> OpenAI:
    """
    Inicializa el cliente LLM solo cuando se necesita llamar al modelo.
    """
    global llm_client

    if llm_client is not None:
        return llm_client

    if not GITHUB_TOKEN:
        raise ValueError("Falta la variable GITHUB_TOKEN en el entorno o .env")

    llm_client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN,
    )
    return llm_client

# ==========================================
# 2. FUNCIONES CORE
# ==========================================

def extraer_texto_pdf(ruta_pdf: str) -> tuple[str, int]:
    """
    Fase de Molienda: Extrae el texto crudo y el número de páginas del CV.
    """
    texto_extraido = ""
    num_paginas = 0
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            num_paginas = len(pdf.pages)
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_extraido += texto + "\n"
        print(f"[+] Texto extraído exitosamente de {ruta_pdf}")
        return texto_extraido.strip(), num_paginas
    except Exception as e:
        print(f"[-] Error al extraer texto: {e}")
        return "", 0

def interactuar_con_gpt(prompt: str, rol_sistema: str) -> dict:
    """
    Fase de Percolación: Función genérica para hablar con GPT-4o vía GitHub (igual que en app.py).
    """
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": rol_sistema},
                {"role": "user", "content": prompt}
            ],
            model=MODELO_NUBE,
            temperature= 0, # Temperatura baja para que sea analítico, no creativo
            response_format={"type": "json_object"} # Forzamos la salida a JSON puro
        )
        contenido = response.choices[0].message.content
        return json.loads(contenido)
    except Exception as e:
        print(f"[-] Error en la comunicación con OpenAI: {e}")
        return {}

def estructurar_cv(texto_crudo: str) -> dict:
    """
    Transforma el texto desordenado en un JSON estructurado usando OpenAI.
    """
    print(f"[*] Estructurando CV con OpenAI ({MODELO_NUBE})...")
    
    prompt = get_user_prompt_estructuracion(texto_crudo)
    resultado = interactuar_con_gpt(prompt, SYS_PROMPT_ESTRUCTURACION)

    if not resultado:
        print("[-] OpenAI no devolvió un JSON de estructuración válido.")
        return {}

    try:
        cv_validado = CVSchema.model_validate(resultado)
        return cv_validado.model_dump()
    except ValidationError as e:
        print("[-] La estructuración del CV no cumple el schema Pydantic.")
        print(e)
        return {}

def evaluar_candidato(cv_json: dict, job_spec: str) -> dict:
    """
    El núcleo de la IA: Compara el CV estructurado con los requerimientos del puesto.
    Aquí garantizamos la transparencia (el "porqué").
    """
    print(f"[*] Evaluando candidato frente al Job Spec con OpenAI ({MODELO_NUBE})...")
    
    prompt = get_user_prompt_evaluacion(json.dumps(cv_json), job_spec)
    resultado = interactuar_con_gpt(prompt, SYS_PROMPT_EVALUACION)

    if not resultado:
        print("[-] OpenAI no devolvió un JSON de evaluación válido.")
        return {}

    try:
        evaluacion_validada = EvaluacionSchema.model_validate(resultado)
        return evaluacion_validada.model_dump()
    except ValidationError as e:
        print("[-] La evaluación comercial no cumple el schema Pydantic.")
        print(e)
        return {}

# ==========================================
# 3. PIPELINE PRINCIPAL 
# ==========================================

def procesar_candidato(ruta_pdf: str, job_spec: str, proceso_nombre: str = "Sin nombre"):
    # 1. Extracción
    texto_cv, num_paginas = extraer_texto_pdf(ruta_pdf)
    if not texto_cv:
        return

    # 2. Estructuración
    cv_estructurado = estructurar_cv(texto_cv)
    if not cv_estructurado:
        print("[-] Se detiene el pipeline: CV estructurado inválido.")
        return
    print(
        "[+] CV estructurado: "
        f"{cv_estructurado.get('candidate_name', 'Desconocido')} "
        f"(DNI={cv_estructurado.get('dni')})"
    )

    # 3. Evaluación
    evaluacion = evaluar_candidato(cv_estructurado, job_spec)
    if not evaluacion:
        print("[-] Se detiene el pipeline: evaluación comercial inválida.")
        return
    print(
        "[+] Score obtenido: "
        f"{evaluacion.get('score_total')} - {evaluacion.get('assignment_readiness')}"
    )
    print(
        "[+] Perfil comercial: "
        f"{evaluacion.get('salesperson_type')} "
        f"(confianza={evaluacion.get('salesperson_type_confidence')})"
    )
    print(f"[+] Explicación XAI: {evaluacion.get('xai_explanation')}")

    # 4. Guardar en Supabase — Arquitectura Medallion
    try:
        db = get_supabase_client()

        # Bronze — PDF crudo
        with open(ruta_pdf, "rb") as f:
            pdf_bytes = f.read()
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()

        resp_bronze = db.schema("bronze").table("cv_raw_text").insert({
            "proceso_nombre": proceso_nombre,
            "filename":       os.path.basename(ruta_pdf),
            "file_hash":      file_hash,
            "raw_text":       texto_cv,
            "num_pages":      num_paginas,
            "file_size_bytes": len(pdf_bytes),
            "extraction_status": "success",
        }).execute()
        raw_cv_id = resp_bronze.data[0]["id"]

        # Silver — CV estructurado
        db.schema("silver").table("candidates_structured").insert({
            "raw_cv_id": raw_cv_id,
            **cv_estructurado,
        }).execute()

        # Gold — Perfil comercial final para Módulo 3
        db.schema("gold").table("candidates_final").insert({
            "candidate_id": cv_estructurado["dni"],
            "candidate_name": cv_estructurado.get("candidate_name"),
            **evaluacion,
        }).execute()

        print("[+] Datos guardados exitosamente en Supabase (Bronze → Silver → Gold).")

    except Exception as e:
        print(f"[-] Error al guardar en base de datos: {e}")

# ==========================================
# PRUEBA LOCAL
# ==========================================
if __name__ == "__main__":
    # Simulación de un requerimiento comercial de preventista B2B
    job_requerimientos = """
    Buscamos un preventista B2B para distribución de bebidas en canal tradicional.
    Responsabilidades: visitas diarias a bodegas y minimarkets, toma de pedidos,
    gestión de ruta, apertura de clientes, retención de cartera, cobranza,
    cumplimiento de cuota y ejecución en punto de venta.
    """

    # Ejecuta el pipeline con un PDF local de prueba.
    procesar_candidato("tests/pdfs/cv_prueba.pdf", job_requerimientos, proceso_nombre="Preventista B2B Q1 2026")
