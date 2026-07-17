"""Prueba manual de extracción y estructuración con el primer LLM."""

import glob
import json
import os

from main import (
    PERIODO_FIN,
    PERIODO_INICIO,
    PERIODO_MESES,
    extraer_texto_pdf,
    estructurar_informe,
)


def test_estructuracion() -> None:
    archivos_pdf = glob.glob(os.path.join("tests", "pdfs", "*.pdf"))
    if not archivos_pdf:
        print("[-] No se encontraron informes PDF en tests/pdfs.")
        return

    for ruta_pdf in archivos_pdf:
        texto, paginas = extraer_texto_pdf(ruta_pdf)
        if not texto:
            print(f"[-] El informe {ruta_pdf} no contiene texto extraíble.")
            continue

        perfil = estructurar_informe(
            texto,
            periodo_inicio=PERIODO_INICIO,
            periodo_fin=PERIODO_FIN,
            periodo_meses=PERIODO_MESES,
        )
        perfil_visible = dict(perfil)
        perfil_visible["dni"] = f"****{perfil['dni'][-4:]}"
        print(f"[+] {ruta_pdf}: {paginas} página(s)")
        print(json.dumps(perfil_visible, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_estructuracion()
