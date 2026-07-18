from supabase import Client


def asignar_mejor_territorio(
    supabase: Client,
    employee_id: str,
) -> dict:
    """
    Ejecuta el matching secuencial de M3 para un preventista.
    """

    if not employee_id:
        raise ValueError("employee_id es obligatorio")

    asignacion_existente = (
        supabase
        .schema("gold")
        .table("m3_assignments")
        .select(
            "territory_code, compatibility_score, assignment_method, "
            "assignment_rationale"
        )
        .eq("employee_id", employee_id)
        .limit(1)
        .execute()
    )

    if asignacion_existente.data:
        return asignacion_existente.data[0]

    response = (
        supabase
        .schema("gold")
        .rpc(
            "m3_assign_best_territory",
            {"p_employee_id": employee_id},
        )
        .execute()
    )

    datos = response.data
    if not datos:
        raise RuntimeError(
            "La función no devolvió una asignación."
        )

    if isinstance(datos, dict):
        return datos

    if isinstance(datos, list) and isinstance(datos[0], dict):
        return datos[0]

    raise RuntimeError(
        "La función devolvió una respuesta con formato inesperado."
    )
