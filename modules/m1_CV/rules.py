from typing import Any


METRICAS_WEIGHT = 0.70
SUPERVISOR_WEIGHT = 0.30
AMBIGUITY_MARGIN = 10.0
INCONSISTENCY_MARGIN = 50.0

PERFILES_COMERCIALES = {"captacion", "fidelizacion", "ejecucion_campo"}

SUPERVISOR_SCORE_BY_DIMENSION = {
    "score_captacion": "score_supervisor_captacion",
    "score_fidelizacion": "score_supervisor_fidelizacion",
    "score_cobertura_ruta": "score_supervisor_cobertura_ruta",
    "score_disciplina_comunicacion": (
        "score_supervisor_disciplina_comunicacion"
    ),
}

SUPERVISOR_EVIDENCE_BY_SCORE = {
    "score_supervisor_captacion": "evidencia_captacion",
    "score_supervisor_fidelizacion": "evidencia_fidelizacion",
    "score_supervisor_cobertura_ruta": "evidencia_cobertura_ruta",
    "score_supervisor_disciplina_comunicacion": (
        "evidencia_disciplina_comunicacion"
    ),
}

METRIC_KEY_BY_DIMENSION = {
    "score_captacion": "score_metrica_captacion",
    "score_fidelizacion": "score_metrica_fidelizacion",
    "score_cobertura_ruta": "score_metrica_cobertura_ruta",
    "score_disciplina_comunicacion": "score_metrica_disciplina_comunicacion",
}

REQUIRED_METRICS = {
    "periodo_inicio",
    "periodo_fin",
    "periodo_meses",
    "cumplimiento_cuota_pct",
    "cobertura_ruta_pct",
    "meta_cobertura_ruta_pct",
    "retencion_cartera_pct",
    "meta_retencion_cartera_pct",
    "cuentas_nuevas_abiertas",
    "meta_cuentas_nuevas",
    "reportes_a_tiempo_pct",
    "meta_reportes_a_tiempo_pct",
}

NARRATIVE_DIMENSIONS = tuple(SUPERVISOR_EVIDENCE_BY_SCORE.values())


def puntuar_cumplimiento_pct(cumplimiento_pct: float | None) -> float | None:
    """Convierte el cumplimiento de una meta a 0, 25, 50, 75 o 100."""

    if cumplimiento_pct is None:
        return None
    if cumplimiento_pct == 0:
        return 0.0
    if cumplimiento_pct < 70:
        return 25.0
    if cumplimiento_pct < 90:
        return 50.0
    if cumplimiento_pct < 105:
        return 75.0
    return 100.0


def calcular_cumplimiento_pct(
    resultado: float | int | None,
    meta: float | int | None,
) -> float | None:
    if resultado is None or meta is None or float(meta) <= 0:
        return None
    return float(resultado) / float(meta) * 100


def promedio_completo(valores: list[float | None]) -> float | None:
    """No confunde un dato ausente con desempeno cero."""

    if not valores or any(valor is None for valor in valores):
        return None
    return round(sum(float(valor) for valor in valores) / len(valores), 2)


def calcular_scores_metricas(perfil: dict[str, Any]) -> dict[str, float | None]:
    metricas = perfil.get("metricas_campo") or {}

    cumplimiento_captacion = calcular_cumplimiento_pct(
        metricas.get("cuentas_nuevas_abiertas"),
        metricas.get("meta_cuentas_nuevas"),
    )
    cumplimiento_fidelizacion = calcular_cumplimiento_pct(
        metricas.get("retencion_cartera_pct"),
        metricas.get("meta_retencion_cartera_pct"),
    )
    cumplimiento_cobertura = calcular_cumplimiento_pct(
        metricas.get("cobertura_ruta_pct"),
        metricas.get("meta_cobertura_ruta_pct"),
    )
    cumplimiento_reportes = calcular_cumplimiento_pct(
        metricas.get("reportes_a_tiempo_pct"),
        metricas.get("meta_reportes_a_tiempo_pct"),
    )

    score_cuota = puntuar_cumplimiento_pct(
        metricas.get("cumplimiento_cuota_pct")
    )
    score_reportes = puntuar_cumplimiento_pct(cumplimiento_reportes)

    return {
        "score_metrica_captacion": puntuar_cumplimiento_pct(
            cumplimiento_captacion
        ),
        "score_metrica_fidelizacion": puntuar_cumplimiento_pct(
            cumplimiento_fidelizacion
        ),
        "score_metrica_cobertura_ruta": puntuar_cumplimiento_pct(
            cumplimiento_cobertura
        ),
        "score_metrica_disciplina_comunicacion": promedio_completo(
            [score_cuota, score_reportes]
        ),
    }


def combinar_fuentes(
    score_metrica: float | None,
    score_supervisor: float,
) -> float | None:
    if score_metrica is None:
        return None
    return round(
        score_metrica * METRICAS_WEIGHT
        + float(score_supervisor) * SUPERVISOR_WEIGHT,
        2,
    )


def calcular_scores_dimensiones(
    perfil: dict[str, Any],
    evaluacion_supervisor: dict[str, Any],
) -> tuple[dict[str, float | None], dict[str, float | None]]:
    scores_metricas = calcular_scores_metricas(perfil)
    scores_dimensiones = {}

    for dimension, supervisor_key in SUPERVISOR_SCORE_BY_DIMENSION.items():
        metric_key = METRIC_KEY_BY_DIMENSION[dimension]
        scores_dimensiones[dimension] = combinar_fuentes(
            scores_metricas[metric_key],
            float(evaluacion_supervisor[supervisor_key]),
        )

    return scores_metricas, scores_dimensiones


def calcular_indicadores_perfil(
    evaluacion: dict[str, Any],
) -> dict[str, float | None]:
    return {
        "captacion": evaluacion.get("score_captacion"),
        "fidelizacion": evaluacion.get("score_fidelizacion"),
        "ejecucion_campo": promedio_completo(
            [
                evaluacion.get("score_cobertura_ruta"),
                evaluacion.get("score_disciplina_comunicacion"),
            ]
        ),
    }


def determinar_perfil_comercial(
    evaluacion: dict[str, Any],
) -> tuple[str | None, float | None, bool]:
    indicadores = calcular_indicadores_perfil(evaluacion)
    if any(valor is None for valor in indicadores.values()):
        return None, None, True

    ordenados = sorted(
        ((perfil, float(valor)) for perfil, valor in indicadores.items()),
        key=lambda item: (-item[1], item[0]),
    )
    diferencia = round(ordenados[0][1] - ordenados[1][1], 2)
    perfil_propuesto = ordenados[0][0] if diferencia > 0 else None
    return perfil_propuesto, diferencia, diferencia <= AMBIGUITY_MARGIN


def narrativa_totalmente_vacia(perfil: dict[str, Any]) -> bool:
    evidencia = perfil.get("evidencia_supervisor") or {}
    return not any(evidencia.get(campo) for campo in NARRATIVE_DIMENSIONS)


def encontrar_datos_faltantes(perfil: dict[str, Any]) -> list[str]:
    faltantes = []
    if not str(perfil.get("nombre_colaborador") or "").strip():
        faltantes.append("nombre_colaborador")
    if perfil.get("antiguedad_meses_empresa") is None:
        faltantes.append("antiguedad_meses_empresa")
    if not str(perfil.get("zona_actual") or "").strip():
        faltantes.append("zona_actual")

    metricas = perfil.get("metricas_campo") or {}
    faltantes.extend(
        sorted(campo for campo in REQUIRED_METRICS if metricas.get(campo) is None)
    )
    if narrativa_totalmente_vacia(perfil):
        faltantes.append("evaluacion_narrativa_supervisor")
    return faltantes


def encontrar_inconsistencias(
    perfil: dict[str, Any],
    evaluacion_supervisor: dict[str, Any],
    scores_metricas: dict[str, float | None],
) -> list[str]:
    evidencia = perfil.get("evidencia_supervisor") or {}
    inconsistencias = []

    for score_key, evidence_key in SUPERVISOR_EVIDENCE_BY_SCORE.items():
        if float(evaluacion_supervisor[score_key]) > 0 and not evidencia.get(
            evidence_key
        ):
            inconsistencias.append(
                f"{score_key} es mayor que cero sin evidencia en {evidence_key}."
            )

    metric_key_by_supervisor = {
        supervisor_key: METRIC_KEY_BY_DIMENSION[dimension]
        for dimension, supervisor_key in SUPERVISOR_SCORE_BY_DIMENSION.items()
    }
    for supervisor_key, metric_key in metric_key_by_supervisor.items():
        score_metrica = scores_metricas.get(metric_key)
        if score_metrica is None:
            continue
        score_supervisor = float(evaluacion_supervisor[supervisor_key])
        diferencia = abs(score_supervisor - score_metrica)
        if diferencia >= INCONSISTENCY_MARGIN:
            inconsistencias.append(
                f"{supervisor_key} ({score_supervisor:.0f}) y {metric_key} "
                f"({score_metrica:.0f}) difieren en {diferencia:.0f} puntos."
            )

    return inconsistencias


def construir_resultado_correccion(perfil: dict[str, Any]) -> dict[str, Any]:
    evidencia = perfil.get("evidencia_supervisor") or {}
    return {
        "employee_id": perfil["dni"],
        "employee_name": perfil.get("nombre_colaborador"),
        "zona_actual": perfil.get("zona_actual"),
        "processing_status": "needs_correction",
        "datos_faltantes": encontrar_datos_faltantes(perfil),
        "inconsistencias": [],
        "perfil_propuesto": None,
        "perfil_comercial": None,
        "fortalezas": evidencia.get("fortalezas_reportadas") or [],
        "aspectos_mejora": evidencia.get("aspectos_mejora_reportados") or [],
    }


def construir_evaluacion_intermedia(
    perfil_estructurado: dict[str, Any],
    evaluacion_supervisor: dict[str, Any],
) -> dict[str, Any]:
    datos_faltantes = encontrar_datos_faltantes(perfil_estructurado)
    if datos_faltantes:
        return construir_resultado_correccion(perfil_estructurado)

    scores_metricas, scores_dimensiones = calcular_scores_dimensiones(
        perfil_estructurado,
        evaluacion_supervisor,
    )
    resultado = {
        "employee_id": perfil_estructurado["dni"],
        "employee_name": perfil_estructurado["nombre_colaborador"],
        "zona_actual": perfil_estructurado["zona_actual"],
        **evaluacion_supervisor,
        **scores_metricas,
        **scores_dimensiones,
    }
    indicadores = calcular_indicadores_perfil(resultado)
    perfil_propuesto, diferencia_perfiles, perfil_ambiguo = (
        determinar_perfil_comercial(resultado)
    )
    inconsistencias = encontrar_inconsistencias(
        perfil_estructurado,
        evaluacion_supervisor,
        scores_metricas,
    )
    necesita_seleccion = bool(inconsistencias or perfil_ambiguo)
    evidencia = perfil_estructurado["evidencia_supervisor"]

    resultado.update(
        {
            "indicadores_perfil": indicadores,
            "perfil_propuesto": perfil_propuesto,
            "perfil_comercial": (
                None if necesita_seleccion else perfil_propuesto
            ),
            "diferencia_perfiles": diferencia_perfiles,
            "processing_status": (
                "needs_profile_selection" if necesita_seleccion else "valid"
            ),
            "datos_faltantes": [],
            "inconsistencias": inconsistencias,
            "fortalezas": evidencia.get("fortalezas_reportadas") or [],
            "aspectos_mejora": evidencia.get("aspectos_mejora_reportados") or [],
        }
    )
    return resultado


def seleccionar_perfil(
    evaluacion: dict[str, Any],
    perfil_comercial: str,
) -> dict[str, Any]:
    if evaluacion.get("processing_status") != "needs_profile_selection":
        raise ValueError("Solo un caso pendiente permite seleccion manual.")
    if perfil_comercial not in PERFILES_COMERCIALES:
        raise ValueError("perfil_comercial no pertenece al catalogo permitido.")

    resultado = dict(evaluacion)
    resultado["perfil_comercial"] = perfil_comercial
    resultado["processing_status"] = "valid"
    return resultado
