import glob
import hashlib
import json
import os
from datetime import datetime

from main import evaluar_candidato, extraer_texto_pdf, estructurar_cv


JOB_SPEC_COMERCIAL = """
Preventista B2B para distribucion de bebidas en canal tradicional.
Responsabilidades principales:
- visitar bodegas, minimarkets y pequenos comercios;
- tomar pedidos y asegurar cobertura de ruta;
- abrir nuevos clientes y reactivar clientes inactivos;
- gestionar cartera recurrente y fidelizar clientes;
- cumplir cuota comercial, cobranza y protocolos de visita;
- ejecutar acciones en punto de venta y reportar KPIs comerciales.
"""

RECOMMENDED_ASSIGNMENT_BY_TYPE = {
    "Hunter": "Bronce/Nuevo",
    "Farmer": "Diamante/Oro",
    "Ejecutor": "Plata",
}


def calcular_hash_archivo(ruta_archivo: str) -> str:
    with open(ruta_archivo, "rb") as archivo:
        return hashlib.sha256(archivo.read()).hexdigest()


def validar_reglas_negocio(evaluacion: dict) -> list[str]:
    errores = []

    if not evaluacion:
        return ["La evaluacion esta vacia o no fue valida."]

    score_total = evaluacion.get("score_total")
    assignment_readiness = evaluacion.get("assignment_readiness")
    salesperson_type = evaluacion.get("salesperson_type")
    confidence = evaluacion.get("salesperson_type_confidence")
    requires_human_review = evaluacion.get("requires_human_review")
    recommended_assignment = evaluacion.get("recommended_assignment")

    if score_total is not None:
        expected_readiness = None
        if score_total < 50:
            expected_readiness = "requiere_revision"
        elif score_total < 70:
            expected_readiness = "requiere_acompanamiento"
        elif score_total < 85:
            expected_readiness = "apto_operativo"
        else:
            expected_readiness = "apto_cartera_critica"

        if assignment_readiness != expected_readiness:
            errores.append(
                "assignment_readiness inconsistente: "
                f"score_total={score_total}, esperado={expected_readiness}, "
                f"recibido={assignment_readiness}"
            )

    if confidence is not None and confidence < 0.60 and requires_human_review is not True:
        errores.append("requires_human_review debe ser true cuando la confianza es menor a 0.60.")

    expected_assignment = RECOMMENDED_ASSIGNMENT_BY_TYPE.get(salesperson_type)
    if expected_assignment and recommended_assignment not in {expected_assignment, "Revisión humana"}:
        errores.append(
            "recommended_assignment inconsistente: "
            f"salesperson_type={salesperson_type}, esperado={expected_assignment}, "
            f"recibido={recommended_assignment}"
        )

    return errores


def guardar_resultado_flujo(ruta_pdf: str, resultado: dict) -> str:
    output_dir = os.path.join("tests", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    nombre_base = os.path.splitext(os.path.basename(ruta_pdf))[0]
    timestamp_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"{nombre_base}_flujo_completo_{timestamp_archivo}.json")

    with open(output_path, "w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, indent=4, ensure_ascii=False)

    return output_path


def evaluar_pdf(ruta_pdf: str) -> str:
    run_date = datetime.now().isoformat(timespec="seconds")
    errores = []
    structured_cv = {}
    evaluation = {}

    texto, num_paginas = extraer_texto_pdf(ruta_pdf)
    extraction_status = "success" if texto else "failed"

    if not texto:
        errores.append("No se pudo extraer texto del PDF.")
    else:
        structured_cv = estructurar_cv(texto)
        if not structured_cv:
            errores.append("La estructuracion no devolvio un CV valido.")
        else:
            evaluation = evaluar_candidato(structured_cv, JOB_SPEC_COMERCIAL)
            if not evaluation:
                errores.append("La evaluacion no devolvio una salida valida.")
            else:
                errores.extend(validar_reglas_negocio(evaluation))

    resultado = {
        "schema_version": "m1_cv_full_evaluation_test_v1",
        "filename": os.path.basename(ruta_pdf),
        "source_path": ruta_pdf,
        "file_hash": calcular_hash_archivo(ruta_pdf),
        "run_date": run_date,
        "extraction": {
            "num_pages": num_paginas,
            "text_length_chars": len(texto),
            "extraction_status": extraction_status,
        },
        "structured_cv": structured_cv,
        "evaluation": evaluation,
        "validation_status": "success" if not errores else "failed",
        "errors": errores,
    }

    output_path = guardar_resultado_flujo(ruta_pdf, resultado)

    print("\n" + "=" * 60)
    print(f"PDF: {ruta_pdf}")
    print(f"DNI: {structured_cv.get('dni', 'No disponible')}")
    print(f"Candidato: {structured_cv.get('candidate_name', 'No disponible')}")
    print(f"Score: {evaluation.get('score_total', 'No disponible')}")
    print(f"Tipo: {evaluation.get('salesperson_type', 'No disponible')}")
    print(f"Readiness: {evaluation.get('assignment_readiness', 'No disponible')}")
    print(f"Revisión humana: {evaluation.get('requires_human_review', 'No disponible')}")
    print(f"Estado validación: {resultado['validation_status']}")
    print(f"Output: {output_path}")
    if errores:
        print("Errores:")
        for error in errores:
            print(f"- {error}")
    print("=" * 60 + "\n")

    return output_path


def test_evaluacion():
    archivos_pdf = glob.glob(os.path.join("tests", "pdfs", "*.pdf"))

    if not archivos_pdf:
        print("[-] No se encontraron archivos PDF en tests/pdfs.")
        return

    print(f"[*] Se encontraron {len(archivos_pdf)} archivo(s) PDF.")

    for ruta_pdf in archivos_pdf:
        evaluar_pdf(ruta_pdf)


if __name__ == "__main__":
    test_evaluacion()
