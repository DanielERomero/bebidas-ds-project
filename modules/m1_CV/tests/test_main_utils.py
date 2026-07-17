import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

import main  # noqa: E402
from main import detectar_dni, enmascarar_dni, extraer_texto_pdf  # noqa: E402


class MainUtilitiesTest(unittest.TestCase):
    def test_detects_labeled_dni(self):
        self.assertEqual(detectar_dni("DNI: 12345678"), "12345678")

    def test_rejects_ambiguous_unlabeled_numbers(self):
        self.assertIsNone(detectar_dni("12345678 y 87654321"))

    def test_masks_dni_for_logs(self):
        self.assertEqual(enmascarar_dni("12345678"), "****5678")

    def test_invalid_pdf_returns_empty_result(self):
        text, pages = extraer_texto_pdf(b"esto no es un PDF")
        self.assertEqual((text, pages), ("", 0))

    @patch("main.registrar_bronze", return_value="raw-1")
    @patch(
        "main.extraer_texto_pdf_detallado",
        return_value=("Informe sin identificador", 1, None),
    )
    def test_invalid_dni_stops_in_bronze(self, _mock_extract, _mock_bronze):
        carga = main.cargar_informe_en_bronze(
            "informe.pdf",
            b"pdf",
            periodo_inicio="2025-01-01",
            periodo_fin="2025-06-30",
            periodo_meses=6,
        )

        self.assertEqual(carga["extraction_status"], "invalid_dni")
        self.assertIsNone(carga["employee_id"])
        with self.assertRaisesRegex(ValueError, "registro Bronze exitoso"):
            main.estructurar_evaluar_y_guardar(carga)


if __name__ == "__main__":
    unittest.main()
