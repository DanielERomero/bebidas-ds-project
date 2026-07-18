import sys
from pathlib import Path

import streamlit as st


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from main import (  # noqa: E402
    PERIODO_FIN,
    PERIODO_INICIO,
    PERIODO_MESES,
    cargar_informe_en_bronze,
    confirmar_perfil,
    enmascarar_dni,
    estructurar_evaluar_y_guardar,
    get_supabase_client,
)
from services.matching_service import asignar_mejor_territorio  # noqa: E402


PERFIL_LABELS = {
    "captacion": "Hunter — Captación de clientes",
    "fidelizacion": "Farmer — Fidelización de cartera",
    "ejecucion_campo": "Ejecutor — Ejecución en campo",
}
CAMPO_LABELS = {
    "nombre_colaborador": "Nombre del colaborador",
    "antiguedad_meses_empresa": "Antigüedad en la empresa",
    "zona_actual": "Zona actual",
    "evaluacion_narrativa_supervisor": "Evaluación narrativa del supervisor",
    "periodo_inicio": "Inicio del periodo",
    "periodo_fin": "Fin del periodo",
    "periodo_meses": "Duración del periodo",
    "cumplimiento_cuota_pct": "Cumplimiento de cuota",
    "cobertura_ruta_pct": "Cobertura de ruta",
    "meta_cobertura_ruta_pct": "Meta de cobertura de ruta",
    "retencion_cartera_pct": "Retención de cartera",
    "meta_retencion_cartera_pct": "Meta de retención de cartera",
    "cuentas_nuevas_abiertas": "Cuentas nuevas abiertas",
    "meta_cuentas_nuevas": "Meta de cuentas nuevas",
    "reportes_a_tiempo_pct": "Reportes entregados a tiempo",
    "meta_reportes_a_tiempo_pct": "Meta de reportes a tiempo",
}


def mostrar_score(valor: float | None) -> str:
    return f"{float(valor):.2f}" if valor is not None else "Pendiente"


def mostrar_asignacion_m3(supabase, employee_id: str) -> None:
    """Muestra la asignación territorial una vez confirmado el perfil M1."""
    st.subheader("Asignación territorial")
    st.write(
        "El sistema comparará las fortalezas del preventista "
        "con los territorios que todavía están disponibles."
    )

    if st.button("Asignar mejor territorio disponible", type="primary"):
        try:
            with st.spinner("Calculando compatibilidad..."):
                asignacion = asignar_mejor_territorio(
                    supabase=supabase,
                    employee_id=employee_id,
                )

            st.success("Territorio asignado correctamente")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Territorio", asignacion["territory_code"])
            with col2:
                st.metric(
                    "Compatibilidad",
                    f'{asignacion["compatibility_score"]:.2f}',
                )

            st.write("**Método:**", asignacion["assignment_method"])
            st.write("**Justificación:**", asignacion["assignment_rationale"])
        except Exception as error:
            st.error(f"No se pudo realizar la asignación: {error}")


st.set_page_config(page_title="M1 - Perfil de preventistas", page_icon="📄")
st.title("Módulo 1 — Perfil comercial de preventistas")
st.caption(
    "Evalúa un informe interno de desempeño para apoyar la asignación de "
    "carteras. No toma decisiones laborales automáticas."
)

st.info(
    "Periodo de evaluación: "
    f"{PERIODO_INICIO.strftime('%d/%m/%Y')} al "
    f"{PERIODO_FIN.strftime('%d/%m/%Y')} ({PERIODO_MESES} meses)."
)
archivo = st.file_uploader("Informe interno del preventista", type=["pdf"])

if "carga_bronze" not in st.session_state:
    st.session_state.carga_bronze = None
if "resultado_m1" not in st.session_state:
    st.session_state.resultado_m1 = None

if archivo and st.button("1. Cargar informe", type="primary"):
    try:
        with st.spinner("Extrayendo texto y registrando Bronze..."):
            carga = cargar_informe_en_bronze(
                archivo.name,
                archivo.getvalue(),
                periodo_inicio=PERIODO_INICIO,
                periodo_fin=PERIODO_FIN,
                periodo_meses=PERIODO_MESES,
            )
        st.session_state.carga_bronze = carga
        st.session_state.resultado_m1 = None

        if carga["extraction_status"] == "success":
            st.success(
                f"Informe cargado. DNI: {enmascarar_dni(carga['employee_id'])}. "
                f"Páginas: {carga['page_count']}."
            )
        else:
            st.error(carga["error_message"])
    except Exception as exc:
        st.error(f"No se pudo registrar el informe: {exc}")

carga = st.session_state.carga_bronze
if carga and carga.get("extracted_text"):
    with st.expander("Vista previa del texto extraído"):
        st.text(carga["extracted_text"][:2000])

if carga and carga["extraction_status"] == "success":
    if st.button("2. Evaluar preventista"):
        try:
            with st.spinner(
                "Estructurando, calculando puntajes y preparando la explicación..."
            ):
                resultado = estructurar_evaluar_y_guardar(carga)
            st.session_state.resultado_m1 = resultado
            estado = resultado["evaluation"]["processing_status"]
            if estado == "valid":
                st.success("Perfil final guardado en Gold.")
            elif estado == "needs_profile_selection":
                st.info("La evaluación está lista para que RR. HH. elija el perfil.")
            else:
                st.warning("El informe debe corregirse antes de generar un perfil.")
        except Exception as exc:
            st.error(
                "No se pudo completar la evaluación. No se escribió un resultado "
                f"Gold; puedes reintentar. Detalle: {exc}"
            )

resultado = st.session_state.resultado_m1
if resultado:
    evaluacion = resultado["evaluation"]
    st.subheader(evaluacion.get("employee_name") or "Informe por corregir")

    if all(
        evaluacion.get(campo) is not None
        for campo in (
            "score_captacion",
            "score_fidelizacion",
            "score_cobertura_ruta",
            "score_disciplina_comunicacion",
        )
    ):
        st.write("**Puntajes por dimensión**")
        st.dataframe(
            {
                "Dimensión": [
                    "Captación",
                    "Fidelización",
                    "Cobertura de ruta",
                    "Disciplina y comunicación",
                ],
                "Puntaje": [
                    evaluacion["score_captacion"],
                    evaluacion["score_fidelizacion"],
                    evaluacion["score_cobertura_ruta"],
                    evaluacion["score_disciplina_comunicacion"],
                ],
            },
            hide_index=True,
            width="stretch",
        )

        indicadores = evaluacion["indicadores_perfil"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Hunter / Captación", mostrar_score(indicadores["captacion"]))
        col2.metric(
            "Farmer / Fidelización", mostrar_score(indicadores["fidelizacion"])
        )
        col3.metric(
            "Ejecutor / Campo", mostrar_score(indicadores["ejecucion_campo"])
        )

    if evaluacion.get("explicacion_final"):
        st.write("**Explicación para la decisión**")
        st.write(evaluacion["explicacion_final"])

    st.write("**Fortalezas:**", evaluacion.get("fortalezas") or ["No registradas"])
    st.write(
        "**Aspectos por mejorar:**",
        evaluacion.get("aspectos_mejora") or ["No registrados"],
    )

    estado = evaluacion["processing_status"]
    if estado == "needs_correction":
        faltantes = [
            CAMPO_LABELS.get(campo, campo)
            for campo in evaluacion.get("datos_faltantes", [])
        ]
        st.warning(
            "Corrige el informe y vuelve a cargarlo. Información faltante: "
            + ", ".join(faltantes)
            + "."
        )

    elif estado == "needs_profile_selection":
        if evaluacion.get("inconsistencias"):
            st.warning(
                "Existen diferencias importantes entre métricas y evaluación "
                "narrativa. Revisa la explicación antes de elegir."
            )
            for inconsistencia in evaluacion["inconsistencias"]:
                st.write(f"- {inconsistencia}")
        else:
            st.warning(
                "Los dos indicadores principales están separados por "
                f"{mostrar_score(evaluacion['diferencia_perfiles'])} puntos."
            )

        perfil_seleccionado = st.selectbox(
            "Perfil confirmado por RR. HH.",
            options=list(PERFIL_LABELS),
            format_func=lambda valor: PERFIL_LABELS[valor],
        )
        if st.button("Confirmar perfil y guardar en Gold", type="primary"):
            try:
                finalizado = confirmar_perfil(
                    raw_informe_id=carga["raw_informe_id"],
                    perfil_estructurado_id=resultado["perfil_estructurado_id"],
                    evaluacion=evaluacion,
                    perfil_comercial=perfil_seleccionado,
                )
                st.session_state.resultado_m1["evaluation"] = finalizado[
                    "evaluation"
                ]
                st.session_state.resultado_m1["gold"] = finalizado["gold"]
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo guardar el perfil seleccionado: {exc}")

    elif estado == "valid":
        perfil = evaluacion["perfil_comercial"]
        st.success(f"Perfil final: {PERFIL_LABELS[perfil]}")
        resultado_gold = resultado.get("gold")
        if resultado_gold:
            supabase = get_supabase_client()
            mostrar_asignacion_m3(
                supabase=supabase,
                employee_id=resultado_gold["employee_id"],
            )
        else:
            st.warning("No se encontró la evaluación Gold para la asignación.")
