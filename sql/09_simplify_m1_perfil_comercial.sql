-- Simplifica M1: Silver conserva estados de procesamiento y Gold solo perfiles
-- finales. Requiere que 08_create_m1_informe_medallion.sql ya este aplicada.

begin;

alter table silver.perfil_preventista_estructurado
    drop constraint perfil_preventista_validation_status_catalog;

update silver.perfil_preventista_estructurado
set validation_status = case
    when validation_status = 'valid' then 'valid'
    else 'needs_correction'
end;

alter table silver.perfil_preventista_estructurado
    rename column validation_status to processing_status;

alter table silver.perfil_preventista_estructurado
    alter column nombre_colaborador drop not null;

alter table silver.perfil_preventista_estructurado
    add constraint perfil_preventista_processing_status_catalog check (
        processing_status in (
            'valid',
            'needs_correction',
            'needs_profile_selection'
        )
    );

alter table gold.preventistas_evaluados
    drop constraint preventistas_evaluados_scores_range,
    drop constraint preventistas_evaluados_perfil_catalog,
    drop constraint preventistas_evaluados_nivel_catalog,
    drop constraint preventistas_evaluados_claridad_catalog,
    drop constraint preventistas_evaluados_review_status_catalog,
    drop constraint preventistas_evaluados_review_consistency,
    drop constraint preventistas_evaluados_score_nivel_consistency,
    drop constraint preventistas_evaluados_m3_consistency,
    drop constraint preventistas_evaluados_explicacion_valid,
    drop constraint preventistas_evaluados_json_arrays;

alter table gold.preventistas_evaluados
    rename column explicacion to explicacion_final;

alter table gold.preventistas_evaluados
    drop column score_total,
    drop column diferencia_perfiles,
    drop column nivel_asignacion,
    drop column claridad_perfil,
    drop column requires_human_review,
    drop column review_status,
    drop column m3_eligible,
    drop column metricas_faltantes,
    drop column inconsistencias;

alter table gold.preventistas_evaluados
    alter column zona_actual set not null,
    alter column score_captacion set not null,
    alter column score_fidelizacion set not null,
    alter column score_cobertura_ruta set not null,
    alter column score_disciplina_comunicacion set not null,
    alter column perfil_comercial set not null;

alter table gold.preventistas_evaluados
    add constraint preventistas_evaluados_scores_range check (
        score_captacion between 0 and 100
        and score_fidelizacion between 0 and 100
        and score_cobertura_ruta between 0 and 100
        and score_disciplina_comunicacion between 0 and 100
    ),
    add constraint preventistas_evaluados_perfil_catalog check (
        perfil_comercial in (
            'captacion',
            'fidelizacion',
            'ejecucion_campo'
        )
    ),
    add constraint preventistas_evaluados_explicacion_final_valid check (
        btrim(explicacion_final) <> ''
        and char_length(explicacion_final) <= 1200
    ),
    add constraint preventistas_evaluados_json_arrays check (
        jsonb_typeof(fortalezas) = 'array'
        and jsonb_typeof(aspectos_mejora) = 'array'
    );

comment on column silver.perfil_preventista_estructurado.processing_status is
    'Estado tecnico: valid, needs_correction o needs_profile_selection.';
comment on column gold.preventistas_evaluados.perfil_comercial is
    'Perfil final: captacion (Hunter), fidelizacion (Farmer) o ejecucion_campo (Ejecutor).';
comment on column gold.preventistas_evaluados.explicacion_final is
    'Explicacion XAI detallada, generada sin modificar puntajes ni perfil.';

notify pgrst, 'reload schema';

commit;
