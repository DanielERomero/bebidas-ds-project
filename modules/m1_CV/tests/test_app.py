import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class StreamlitAppTest(unittest.TestCase):
    def setUp(self):
        self.app_path = Path(__file__).resolve().parents[1] / "app.py"

    def evaluacion_base(self) -> dict:
        return {
            "employee_name": "Ana Pérez",
            "score_captacion": 80,
            "score_fidelizacion": 75,
            "score_cobertura_ruta": 70,
            "score_disciplina_comunicacion": 70,
            "indicadores_perfil": {
                "captacion": 80,
                "fidelizacion": 75,
                "ejecucion_campo": 70,
            },
            "diferencia_perfiles": 5,
            "perfil_comercial": None,
            "fortalezas": ["Prospección"],
            "aspectos_mejora": ["Seguimiento"],
            "explicacion_final": "Los perfiles están cercanos y requieren revisión.",
            "inconsistencias": [],
            "datos_faltantes": [],
        }

    def test_initial_screen_renders_without_service_calls(self):
        app = AppTest.from_file(str(self.app_path)).run(timeout=10)

        self.assertEqual(app.exception, [])
        self.assertEqual(
            app.title[0].value, "Módulo 1 — Perfil comercial de preventistas"
        )
        self.assertEqual(len(app.get("file_uploader")), 1)

    def test_renders_correction_state(self):
        app = AppTest.from_file(str(self.app_path))
        evaluacion = self.evaluacion_base()
        evaluacion.update(
            {
                "processing_status": "needs_correction",
                "datos_faltantes": ["zona_actual"],
            }
        )
        app.session_state["resultado_m1"] = {"evaluation": evaluacion}
        app.run(timeout=10)

        self.assertEqual(app.exception, [])
        self.assertTrue(any("Corrige el informe" in item.value for item in app.warning))

    def test_renders_profile_selection_state(self):
        app = AppTest.from_file(str(self.app_path))
        evaluacion = self.evaluacion_base()
        evaluacion["processing_status"] = "needs_profile_selection"
        app.session_state["resultado_m1"] = {
            "evaluation": evaluacion,
            "perfil_estructurado_id": "silver-1",
        }
        app.run(timeout=10)

        self.assertEqual(app.exception, [])
        self.assertEqual(len(app.selectbox), 1)
        self.assertTrue(
            any("Confirmar perfil" in item.label for item in app.button)
        )

    def test_renders_final_state(self):
        app = AppTest.from_file(str(self.app_path))
        evaluacion = self.evaluacion_base()
        evaluacion.update(
            {"processing_status": "valid", "perfil_comercial": "captacion"}
        )
        app.session_state["resultado_m1"] = {"evaluation": evaluacion}
        app.run(timeout=10)

        self.assertEqual(app.exception, [])
        self.assertTrue(any("Perfil final" in item.value for item in app.success))


if __name__ == "__main__":
    unittest.main()
