import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from prompts import CVSchema, EvaluacionSchema  # noqa: E402


def valid_cv_payload() -> dict:
    return {
        "dni": "12345678",
        "candidate_name": "Juan Perez",
        "email": "juan@example.com",
        "phone": "999999999",
        "location": "Lima, Peru",
        "summary_profile": "Preventista con experiencia en canal tradicional.",
        "commercial_experience_years": 3,
        "last_position": "Preventista",
        "last_company": "Distribuidora Lima",
        "education_level": "Tecnico",
        "education_career": "Administracion",
        "education_institution": "Instituto Comercial",
        "field_sales_experience": "Visitas diarias a bodegas y minimarkets.",
        "traditional_channel_experience": "Gestion de clientes en bodegas.",
        "route_management_experience": "Cobertura de ruta asignada.",
        "new_account_opening_experience": "Apertura de nuevos clientes.",
        "client_retention_experience": "Seguimiento de cartera recurrente.",
        "portfolio_management_experience": "Gestion de cartera de clientes.",
        "collection_experience": "Cobranza preventiva.",
        "daily_visits_experience": "25 visitas diarias.",
        "sales_quota_experience": "Cumplimiento de cuota mensual.",
        "point_of_sale_execution_experience": "Ejecucion en punto de venta.",
        "commercial_tools": ["Excel", "app de pedidos"],
        "sales_kpis_mentioned": ["cuota", "cobertura"],
        "experience_detail": [
            {
                "company": "Distribuidora Lima",
                "position": "Preventista",
                "start": "2021",
                "end": "2024",
                "description": "Gestion de ruta y toma de pedidos.",
            }
        ],
        "education_detail": [
            {
                "institution": "Instituto Comercial",
                "career": "Administracion",
                "start": "2018",
                "end": "2020",
            }
        ],
        "commercial_evidence": [
            "visitas diarias a bodegas",
            "cumplimiento de cuota mensual",
        ],
    }


def valid_evaluation_payload() -> dict:
    return {
        "score_commercial_experience": 82,
        "score_traditional_channel": 80,
        "score_prospecting": 70,
        "score_retention": 75,
        "score_route_coverage": 85,
        "score_discipline_communication": 78,
        "score_fit_preventista": 84,
        "score_total": 80,
        "assignment_readiness": "apto_operativo",
        "salesperson_type": "Ejecutor",
        "salesperson_type_confidence": 0.82,
        "commercial_seniority": "semi_senior",
        "rotation_risk_level": "bajo",
        "recommended_assignment": "Plata",
        "requires_human_review": False,
        "xai_explanation": (
            "El candidato muestra experiencia en ruta, visitas diarias y toma de pedidos. "
            "Se clasifica como Ejecutor porque la evidencia principal esta en cobertura operativa."
        ),
        "strengths": ["Experiencia de ruta"],
        "gaps": ["Menor evidencia de cuentas Diamante"],
        "risks": ["Podria requerir acompanamiento en negociacion compleja"],
        "raw_llm_evaluation": "Evaluacion basada en evidencia comercial del CV.",
    }


class SchemaValidationTest(unittest.TestCase):
    def test_cv_schema_accepts_valid_commercial_payload(self):
        validated = CVSchema.model_validate(valid_cv_payload())

        self.assertEqual(validated.candidate_name, "Juan Perez")
        self.assertEqual(validated.dni, "12345678")
        self.assertEqual(validated.commercial_tools, ["Excel", "app de pedidos"])
        self.assertEqual(validated.experience_detail[0].position, "Preventista")

    def test_cv_schema_requires_dni(self):
        payload = valid_cv_payload()
        payload.pop("dni")

        with self.assertRaises(ValidationError):
            CVSchema.model_validate(payload)

    def test_cv_schema_rejects_invalid_dni_format(self):
        invalid_dnis = ["1234567", "123456789", "ABC45678", ""]

        for dni in invalid_dnis:
            with self.subTest(dni=dni):
                payload = valid_cv_payload()
                payload["dni"] = dni

                with self.assertRaises(ValidationError):
                    CVSchema.model_validate(payload)

    def test_cv_schema_rejects_invalid_nested_list_item(self):
        payload = valid_cv_payload()
        payload["experience_detail"] = ["texto plano invalido"]

        with self.assertRaises(ValidationError):
            CVSchema.model_validate(payload)

    def test_evaluation_schema_accepts_valid_commercial_payload(self):
        validated = EvaluacionSchema.model_validate(valid_evaluation_payload())

        self.assertEqual(validated.salesperson_type, "Ejecutor")
        self.assertEqual(validated.salesperson_type_confidence, 0.82)
        self.assertEqual(validated.assignment_readiness, "apto_operativo")

    def test_evaluation_schema_rejects_invalid_catalogs_and_ranges(self):
        invalid_cases = [
            ("salesperson_type", "hire_cluster"),
            ("assignment_readiness", "contratar"),
            ("score_total", 101),
            ("salesperson_type_confidence", 1.5),
        ]

        for field, value in invalid_cases:
            with self.subTest(field=field, value=value):
                payload = valid_evaluation_payload()
                payload[field] = value

                with self.assertRaises(ValidationError):
                    EvaluacionSchema.model_validate(payload)

    def test_evaluation_schema_requires_xai_explanation(self):
        payload = valid_evaluation_payload()
        payload.pop("xai_explanation")

        with self.assertRaises(ValidationError):
            EvaluacionSchema.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
