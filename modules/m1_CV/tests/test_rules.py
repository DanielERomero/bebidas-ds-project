import sys
import unittest
from copy import deepcopy
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIR))
sys.path.insert(0, str(TESTS_DIR))

from rules import (  # noqa: E402
    construir_evaluacion_intermedia,
    determinar_perfil_comercial,
    encontrar_inconsistencias,
    puntuar_cumplimiento_pct,
    seleccionar_perfil,
)
from test_schemas import (  # noqa: E402
    valid_evaluacion_payload,
    valid_perfil_payload,
)


class ReglasPuntuacionTest(unittest.TestCase):
    def test_metric_score_boundaries(self):
        cases = [
            (0, 0.0),
            (0.01, 25.0),
            (69.99, 25.0),
            (70, 50.0),
            (89.99, 50.0),
            (90, 75.0),
            (104.99, 75.0),
            (105, 100.0),
        ]
        for cumplimiento, expected in cases:
            with self.subTest(cumplimiento=cumplimiento):
                self.assertEqual(puntuar_cumplimiento_pct(cumplimiento), expected)

    def test_difference_of_10_requires_selection_and_11_is_automatic(self):
        base = {
            "score_fidelizacion": 70,
            "score_cobertura_ruta": 50,
            "score_disciplina_comunicacion": 50,
        }

        perfil, diferencia, ambiguo = determinar_perfil_comercial(
            {**base, "score_captacion": 80}
        )
        self.assertEqual((perfil, diferencia, ambiguo), ("captacion", 10.0, True))

        perfil, diferencia, ambiguo = determinar_perfil_comercial(
            {**base, "score_captacion": 81}
        )
        self.assertEqual((perfil, diferencia, ambiguo), ("captacion", 11.0, False))

    def test_combines_sources_without_total_score(self):
        result = construir_evaluacion_intermedia(
            valid_perfil_payload(), valid_evaluacion_payload()
        )

        self.assertEqual(result["employee_id"], "01234567")
        self.assertEqual(result["score_captacion"], 100.0)
        self.assertEqual(result["score_fidelizacion"], 67.5)
        self.assertEqual(result["perfil_comercial"], "captacion")
        self.assertEqual(result["processing_status"], "valid")
        self.assertNotIn("score_total", result)
        self.assertNotIn("m3_eligible", result)


class ReglasEstadosTest(unittest.TestCase):
    def test_missing_metric_requires_correction(self):
        perfil = valid_perfil_payload()
        perfil["metricas_campo"]["meta_cuentas_nuevas"] = None

        result = construir_evaluacion_intermedia(perfil, valid_evaluacion_payload())

        self.assertEqual(result["processing_status"], "needs_correction")
        self.assertIn("meta_cuentas_nuevas", result["datos_faltantes"])
        self.assertIsNone(result["perfil_comercial"])

    def test_all_narrative_dimensions_empty_require_correction(self):
        perfil = valid_perfil_payload()
        for campo in (
            "evidencia_captacion",
            "evidencia_fidelizacion",
            "evidencia_cobertura_ruta",
            "evidencia_disciplina_comunicacion",
        ):
            perfil["evidencia_supervisor"][campo] = []

        result = construir_evaluacion_intermedia(perfil, valid_evaluacion_payload())

        self.assertEqual(result["processing_status"], "needs_correction")
        self.assertIn(
            "evaluacion_narrativa_supervisor", result["datos_faltantes"]
        )

    def test_one_empty_dimension_is_valid_and_scores_zero(self):
        perfil = valid_perfil_payload()
        perfil["evidencia_supervisor"]["evidencia_cobertura_ruta"] = []
        evaluacion = valid_evaluacion_payload()
        evaluacion["score_supervisor_cobertura_ruta"] = 0

        result = construir_evaluacion_intermedia(perfil, evaluacion)

        self.assertNotEqual(result["processing_status"], "needs_correction")
        self.assertEqual(result["score_supervisor_cobertura_ruta"], 0)

    def test_inconsistency_threshold_is_50_not_49(self):
        perfil = valid_perfil_payload()
        evaluacion = valid_evaluacion_payload()
        scores_metricas = {
            "score_metrica_captacion": 75,
            "score_metrica_fidelizacion": 75,
            "score_metrica_cobertura_ruta": 75,
            "score_metrica_disciplina_comunicacion": 75,
        }
        evaluacion["score_supervisor_captacion"] = 26
        self.assertFalse(
            any(
                "score_supervisor_captacion" in item
                for item in encontrar_inconsistencias(
                    perfil, evaluacion, scores_metricas
                )
            )
        )

        evaluacion["score_supervisor_captacion"] = 25
        self.assertTrue(
            any(
                "score_supervisor_captacion" in item
                for item in encontrar_inconsistencias(
                    perfil, evaluacion, scores_metricas
                )
            )
        )

    def test_exact_tie_requires_manual_profile(self):
        perfil = valid_perfil_payload()
        perfil["metricas_campo"]["cuentas_nuevas_abiertas"] = 9
        evaluacion = {
            **valid_evaluacion_payload(),
            "score_supervisor_captacion": 50,
            "score_supervisor_fidelizacion": 50,
            "score_supervisor_cobertura_ruta": 50,
            "score_supervisor_disciplina_comunicacion": 50,
        }

        result = construir_evaluacion_intermedia(perfil, evaluacion)

        self.assertIsNone(result["perfil_comercial"])
        self.assertEqual(result["diferencia_perfiles"], 0.0)
        self.assertEqual(result["processing_status"], "needs_profile_selection")

        selected = seleccionar_perfil(result, "fidelizacion")
        self.assertEqual(selected["perfil_comercial"], "fidelizacion")
        self.assertEqual(selected["processing_status"], "valid")

    def test_manual_profile_is_only_allowed_for_pending_selection(self):
        valid_result = construir_evaluacion_intermedia(
            valid_perfil_payload(), valid_evaluacion_payload()
        )
        with self.assertRaises(ValueError):
            seleccionar_perfil(valid_result, "fidelizacion")

        pending = deepcopy(valid_result)
        pending["processing_status"] = "needs_profile_selection"
        with self.assertRaises(ValueError):
            seleccionar_perfil(pending, "Hunter")


if __name__ == "__main__":
    unittest.main()
