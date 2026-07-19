import sys
import unittest
from copy import deepcopy
from pathlib import Path

from pydantic import ValidationError

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from prompts import (  # noqa: E402
    EvaluacionSupervisorSchema,
    ExplicacionFinalSchema,
    PerfilPreventistaSchema,
    PeriodoEvaluacion,
)


def valid_perfil_payload() -> dict:
    return {
        "dni": "01234567",
        "nombre_colaborador": "Ana Pérez",
        "antiguedad_meses_empresa": 24,
        "zona_actual": "Lima Norte",
        "metricas_campo": {
            "periodo_inicio": "2025-01-01",
            "periodo_fin": "2025-06-30",
            "periodo_meses": 6,
            "cumplimiento_cuota_pct": 100,
            "cobertura_ruta_pct": 95,
            "meta_cobertura_ruta_pct": 95,
            "retencion_cartera_pct": 90,
            "meta_retencion_cartera_pct": 90,
            "cuentas_nuevas_abiertas": 11,
            "meta_cuentas_nuevas": 10,
            "reportes_a_tiempo_pct": 100,
            "meta_reportes_a_tiempo_pct": 100,
        },
        "evidencia_supervisor": {
            "evidencia_captacion": ["Abrió once cuentas nuevas."],
            "evidencia_fidelizacion": ["Realizó seguimiento semanal."],
            "evidencia_cobertura_ruta": ["Cumplió las visitas programadas."],
            "evidencia_disciplina_comunicacion": [
                "Entregó reportes y comunicó incidencias."
            ],
            "fortalezas_reportadas": ["Constancia comercial."],
            "aspectos_mejora_reportados": [
                "Mejorar el registro de incidencias."
            ],
        },
    }


def valid_evaluacion_payload() -> dict:
    return {
        "score_supervisor_captacion": 100,
        "score_supervisor_fidelizacion": 50,
        "score_supervisor_cobertura_ruta": 50,
        "score_supervisor_disciplina_comunicacion": 50,
    }


class PerfilPreventistaSchemaTest(unittest.TestCase):
    def test_accepts_valid_internal_report(self):
        validated = PerfilPreventistaSchema.model_validate(valid_perfil_payload())

        self.assertEqual(validated.dni, "01234567")
        self.assertEqual(validated.metricas_campo.periodo_meses, 6)
        self.assertEqual(
            validated.evidencia_supervisor.evidencia_captacion,
            ["Abrió once cuentas nuevas."],
        )

    def test_requires_valid_eight_digit_dni(self):
        for dni in [None, "1234567", "123456789", "ABC45678", ""]:
            with self.subTest(dni=dni), self.assertRaises(ValidationError):
                payload = valid_perfil_payload()
                if dni is None:
                    payload.pop("dni")
                else:
                    payload["dni"] = dni
                PerfilPreventistaSchema.model_validate(payload)

    def test_allows_missing_administrative_data_for_correction_in_silver(self):
        payload = valid_perfil_payload()
        payload["nombre_colaborador"] = None
        payload["antiguedad_meses_empresa"] = None
        payload["zona_actual"] = None

        validated = PerfilPreventistaSchema.model_validate(payload)

        self.assertIsNone(validated.nombre_colaborador)
        self.assertIsNone(validated.antiguedad_meses_empresa)
        self.assertIsNone(validated.zona_actual)

    def test_requires_complete_and_ordered_period(self):
        invalid_periods = [
            {"periodo_inicio": "2025-07-01"},
            {"periodo_fin": "2024-12-31"},
            {"periodo_meses": 0},
            {"periodo_meses": 25},
        ]
        for changes in invalid_periods:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                payload = valid_perfil_payload()
                payload["metricas_campo"].update(changes)
                PerfilPreventistaSchema.model_validate(payload)

        for missing_field in ("periodo_inicio", "periodo_fin", "periodo_meses"):
            with self.subTest(missing=missing_field), self.assertRaises(
                ValidationError
            ):
                payload = valid_perfil_payload()
                payload["metricas_campo"].pop(missing_field)
                PerfilPreventistaSchema.model_validate(payload)

    def test_rejects_metric_outside_allowed_range(self):
        invalid_cases = [
            ("cumplimiento_cuota_pct", 201),
            ("cobertura_ruta_pct", 101),
            ("retencion_cartera_pct", -1),
            ("meta_cuentas_nuevas", 0),
            ("reportes_a_tiempo_pct", 101),
        ]
        for field, value in invalid_cases:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                payload = valid_perfil_payload()
                payload["metricas_campo"][field] = value
                PerfilPreventistaSchema.model_validate(payload)

    def test_rejects_unexpected_fields_and_empty_evidence(self):
        payload = valid_perfil_payload()
        payload["campo_inventado"] = True
        with self.assertRaises(ValidationError):
            PerfilPreventistaSchema.model_validate(payload)

        payload = valid_perfil_payload()
        payload["evidencia_supervisor"]["evidencia_captacion"] = [""]
        with self.assertRaises(ValidationError):
            PerfilPreventistaSchema.model_validate(payload)


class EvaluacionSupervisorSchemaTest(unittest.TestCase):
    def test_accepts_closed_score_catalog(self):
        for score in (0, 25, 50, 75, 100):
            with self.subTest(score=score):
                payload = valid_evaluacion_payload()
                payload["score_supervisor_captacion"] = score
                validated = EvaluacionSupervisorSchema.model_validate(payload)
                self.assertEqual(validated.score_supervisor_captacion, score)

    def test_rejects_scores_outside_catalog(self):
        for score in (-1, 10, 70, 101):
            with self.subTest(score=score), self.assertRaises(ValidationError):
                payload = valid_evaluacion_payload()
                payload["score_supervisor_captacion"] = score
                EvaluacionSupervisorSchema.model_validate(payload)

    def test_rejects_unexpected_evaluation_fields(self):
        payload = deepcopy(valid_evaluacion_payload())
        payload["score_total"] = 90
        with self.assertRaises(ValidationError):
            EvaluacionSupervisorSchema.model_validate(payload)


class ExplicacionFinalSchemaTest(unittest.TestCase):
    def test_accepts_detailed_explanation_up_to_1200_characters(self):
        validated = ExplicacionFinalSchema.model_validate(
            {"explicacion_final": "x" * 1200}
        )
        self.assertEqual(len(validated.explicacion_final), 1200)

    def test_rejects_explanation_over_1200_characters(self):
        with self.assertRaises(ValidationError):
            ExplicacionFinalSchema.model_validate(
                {"explicacion_final": "x" * 1201}
            )

    def test_rejects_decision_fields_from_explanation_llm(self):
        with self.assertRaises(ValidationError):
            ExplicacionFinalSchema.model_validate(
                {
                    "explicacion_final": "Comparación detallada.",
                    "perfil_comercial": "captacion",
                }
            )


class PeriodoEvaluacionTest(unittest.TestCase):
    def test_accepts_streamlit_period_metadata(self):
        periodo = PeriodoEvaluacion.model_validate(
            {
                "periodo_inicio": "2025-01-01",
                "periodo_fin": "2025-06-30",
                "periodo_meses": 6,
            }
        )
        self.assertEqual(periodo.periodo_meses, 6)


if __name__ == "__main__":
    unittest.main()
