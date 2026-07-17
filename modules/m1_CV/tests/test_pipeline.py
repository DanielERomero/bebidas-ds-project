import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIR))
sys.path.insert(0, str(TESTS_DIR))

import main  # noqa: E402
from rules import construir_evaluacion_intermedia  # noqa: E402
from test_schemas import (  # noqa: E402
    valid_evaluacion_payload,
    valid_perfil_payload,
)


def carga_bronze_valida() -> dict:
    return {
        "raw_informe_id": "raw-1",
        "employee_id": "01234567",
        "extracted_text": "DNI: 01234567",
        "periodo_inicio": "2025-01-01",
        "periodo_fin": "2025-06-30",
        "periodo_meses": 6,
        "extraction_status": "success",
    }


class ExplicacionPipelineTest(unittest.TestCase):
    def test_context_contains_locked_scores_evidence_and_decision_facts(self):
        perfil = valid_perfil_payload()
        evaluacion = construir_evaluacion_intermedia(
            perfil, valid_evaluacion_payload()
        )

        contexto = main.construir_contexto_explicacion(perfil, evaluacion)

        self.assertEqual(contexto["processing_status"], "valid")
        self.assertEqual(contexto["scores_finales"]["score_captacion"], 100.0)
        self.assertIn("ejecucion_campo", contexto["indicadores_perfil"])
        self.assertIn("evidencia_captacion", contexto["evidencia_supervisor"])
        self.assertNotIn("score_total", str(contexto))

    @patch("main.interactuar_con_gpt")
    def test_third_llm_only_returns_detailed_explanation(self, mock_llm):
        mock_llm.return_value = {
            "explicacion_final": (
                "Captación lidera porque la apertura de cuentas superó la meta y "
                "el supervisor registró evidencia concreta. Fidelización y "
                "ejecución quedaron por debajo; conviene reforzar el seguimiento."
            )
        }
        perfil = valid_perfil_payload()
        evaluacion = construir_evaluacion_intermedia(
            perfil, valid_evaluacion_payload()
        )

        explicacion = main.generar_explicacion_final(perfil, evaluacion)

        self.assertIn("Captación lidera", explicacion)
        prompt, system_prompt = mock_llm.call_args.args
        self.assertIn("scores_finales", prompt)
        self.assertIn("diferencia_perfiles", prompt)
        self.assertIn("evidencia_supervisor", prompt)
        self.assertIn("No recalcules ni modifiques", system_prompt)
        self.assertIn("Recomendacion orientativa:", system_prompt)
        self.assertIn("lenguaje cotidiano", system_prompt)
        self.assertIn("Hunter, Farmer y Ejecutor", system_prompt)

    @patch("main.interactuar_con_gpt")
    def test_third_llm_cannot_return_a_profile_decision(self, mock_llm):
        mock_llm.return_value = {
            "explicacion_final": "Explicación válida.",
            "perfil_comercial": "captacion",
        }
        perfil = valid_perfil_payload()
        evaluacion = construir_evaluacion_intermedia(
            perfil, valid_evaluacion_payload()
        )

        with self.assertRaisesRegex(ValueError, "explicación final"):
            main.generar_explicacion_final(perfil, evaluacion)


class OrquestacionMedallionTest(unittest.TestCase):
    @patch("main.registrar_gold")
    @patch("main.generar_explicacion_final")
    @patch("main.evaluar_preventista")
    @patch("main.registrar_silver", return_value="silver-1")
    @patch("main.estructurar_informe")
    def test_incomplete_report_stops_in_silver(
        self,
        mock_estructurar,
        mock_silver,
        mock_evaluar,
        mock_explicacion,
        mock_gold,
    ):
        perfil = valid_perfil_payload()
        perfil["metricas_campo"]["meta_cuentas_nuevas"] = None
        mock_estructurar.return_value = perfil

        result = main.estructurar_evaluar_y_guardar(carga_bronze_valida())

        self.assertEqual(result["evaluation"]["processing_status"], "needs_correction")
        self.assertIsNone(result["gold"])
        mock_silver.assert_called_once()
        mock_evaluar.assert_not_called()
        mock_explicacion.assert_not_called()
        mock_gold.assert_not_called()

    @patch("main.registrar_gold")
    @patch("main.registrar_silver")
    @patch("main.generar_explicacion_final", side_effect=RuntimeError("LLM caído"))
    @patch("main.evaluar_preventista")
    @patch("main.estructurar_informe")
    def test_explanation_failure_writes_neither_silver_nor_gold_for_complete_case(
        self,
        mock_estructurar,
        mock_evaluar,
        _mock_explicacion,
        mock_silver,
        mock_gold,
    ):
        perfil = valid_perfil_payload()
        mock_estructurar.return_value = perfil
        mock_evaluar.return_value = construir_evaluacion_intermedia(
            perfil, valid_evaluacion_payload()
        )

        with self.assertRaisesRegex(RuntimeError, "LLM caído"):
            main.estructurar_evaluar_y_guardar(carga_bronze_valida())

        mock_silver.assert_not_called()
        mock_gold.assert_not_called()


if __name__ == "__main__":
    unittest.main()
