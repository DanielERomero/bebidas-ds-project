"""Prueba manual end-to-end con PDF, tres llamadas LLM y Supabase reales."""

import glob
import os

from main import procesar_preventista


def test_evaluacion() -> None:
    archivos_pdf = glob.glob(os.path.join("tests", "pdfs", "*.pdf"))
    if not archivos_pdf:
        print("[-] No se encontraron informes PDF en tests/pdfs.")
        return

    for ruta_pdf in archivos_pdf:
        resultado = procesar_preventista(ruta_pdf)
        evaluacion = resultado.get("evaluation")
        if not evaluacion:
            continue
        print(
            "[+] Estado: "
            f"{evaluacion['processing_status']}; perfil: "
            f"{evaluacion.get('perfil_comercial') or 'pendiente de RR. HH.'}"
        )


if __name__ == "__main__":
    test_evaluacion()
