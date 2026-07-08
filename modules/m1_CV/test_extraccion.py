import os
import glob
import sys
import json
import hashlib
from datetime import datetime
from main import extraer_texto_pdf


def imprimir_seguro(texto: str) -> None:
    """
    Evita errores de encoding en consolas Windows con caracteres especiales del PDF.
    """
    sys.stdout.buffer.write(texto.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


def calcular_hash_archivo(ruta_archivo: str) -> str:
    with open(ruta_archivo, "rb") as archivo:
        return hashlib.sha256(archivo.read()).hexdigest()


def guardar_resultado_extraccion(ruta_pdf: str, texto: str, num_paginas: int) -> str:
    fecha_extraccion = datetime.now().isoformat(timespec="seconds")
    timestamp_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_base = os.path.splitext(os.path.basename(ruta_pdf))[0]
    output_dir = os.path.join("tests", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    resultado = {
        "schema_version": "m1_cv_extraction_test_v1",
        "filename": os.path.basename(ruta_pdf),
        "source_path": ruta_pdf,
        "file_hash": calcular_hash_archivo(ruta_pdf),
        "extraction_date": fecha_extraccion,
        "num_pages": num_paginas,
        "extraction_status": "success" if texto else "failed",
        "text_length_chars": len(texto),
        "extracted_text": texto,
    }

    output_path = os.path.join(output_dir, f"{nombre_base}_extraccion_{timestamp_archivo}.json")
    with open(output_path, "w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, indent=4, ensure_ascii=False)

    return output_path


def test_extraccion():
    # Buscar PDFs de prueba dentro del módulo.
    archivos_pdf = glob.glob(os.path.join("tests", "pdfs", "*.pdf"))
    
    if not archivos_pdf:
        print("[-] No se encontraron archivos PDF en la carpeta actual.")
        return

    print(f"[*] Se encontraron {len(archivos_pdf)} archivo(s) PDF: {', '.join(archivos_pdf)}\n")

    for ruta_al_pdf in archivos_pdf:
        print(f"[*] Iniciando prueba de extracción para: {ruta_al_pdf}...")
        
        # Llamamos a la función original en main.py
        texto, num_paginas = extraer_texto_pdf(ruta_al_pdf)
        output_path = guardar_resultado_extraccion(ruta_al_pdf, texto, num_paginas)

        print("\n" + "="*40)
        print(f"--- INICIO DEL TEXTO EXTRAÍDO ({ruta_al_pdf}) ---")
        print(f"--- PÁGINAS: {num_paginas} ---")
        print(f"--- JSON: {output_path} ---")
        print("="*40 + "\n")
        
        imprimir_seguro(texto)
        
        print("\n" + "="*40)
        print(f"--- FIN DEL TEXTO EXTRAÍDO ({ruta_al_pdf}) ---")
        print("="*40 + "\n")

if __name__ == "__main__":
    test_extraccion()
