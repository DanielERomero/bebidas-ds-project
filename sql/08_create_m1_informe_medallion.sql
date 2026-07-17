-- Modulo 1: informe interno de desempeno -> perfil comercial para M3.
-- Ejecutar en la misma instancia Supabase/PostgreSQL utilizada por M2.
-- Esta migracion es aditiva: conserva las tablas antiguas basadas en CV.

create extension if not exists pgcrypto;
create schema if not exists bronze;
create schema if not exists silver;
create schema if not exists gold;

create table if not exists bronze.raw_informe_preventista (
    raw_informe_id uuid primary key default gen_random_uuid(),
    employee_id varchar(8),
    file_name text not null,
    file_hash varchar(64) not null,
    extracted_text text,
    page_count integer not null default 0,
    periodo_inicio date not null,
    periodo_fin date not null,
    periodo_meses smallint not null,
    extraction_status text not null,
    error_message text,
    loaded_at timestamptz not null default now(),
    constraint raw_informe_employee_id_format check (
        employee_id is null or employee_id ~ '^[0-9]{8}$'
    ),
    constraint raw_informe_file_name_not_empty check (
        btrim(file_name) <> ''
    ),
    constraint raw_informe_file_hash_format check (
        file_hash ~ '^[0-9a-f]{64}$'
    ),
    constraint raw_informe_page_count_nonnegative check (
        page_count >= 0
    ),
    constraint raw_informe_periodo_m1 check (
        periodo_inicio = date '2025-01-01'
        and periodo_fin = date '2025-06-30'
        and periodo_meses = 6
    ),
    constraint raw_informe_extraction_status_catalog check (
        extraction_status in (
            'success',
            'invalid_pdf',
            'empty_text',
            'invalid_dni',
            'error'
        )
    ),
    constraint raw_informe_success_has_data check (
        extraction_status <> 'success'
        or (
            employee_id is not null
            and extracted_text is not null
            and btrim(extracted_text) <> ''
        )
    ),
    constraint raw_informe_error_message_consistency check (
        (
            extraction_status = 'success'
            and error_message is null
        )
        or (
            extraction_status <> 'success'
            and error_message is not null
            and btrim(error_message) <> ''
        )
    )
);

create index if not exists idx_raw_informe_employee_id
    on bronze.raw_informe_preventista (employee_id);

create index if not exists idx_raw_informe_file_hash
    on bronze.raw_informe_preventista (file_hash);

create index if not exists idx_raw_informe_loaded_at
    on bronze.raw_informe_preventista (loaded_at desc);

create table if not exists silver.perfil_preventista_estructurado (
    perfil_estructurado_id uuid primary key default gen_random_uuid(),
    raw_informe_id uuid not null unique references
        bronze.raw_informe_preventista (raw_informe_id),
    dni varchar(8) not null,
    nombre_colaborador text not null,
    antiguedad_meses_empresa integer,
    zona_actual text,
    metricas_campo jsonb not null,
    evidencia_supervisor jsonb not null,
    validation_status text not null,
    model_name text not null,
    prompt_version text not null,
    created_at timestamptz not null default now(),
    constraint perfil_preventista_dni_format check (
        dni ~ '^[0-9]{8}$'
    ),
    constraint perfil_preventista_nombre_not_empty check (
        btrim(nombre_colaborador) <> ''
    ),
    constraint perfil_preventista_antiguedad_nonnegative check (
        antiguedad_meses_empresa is null
        or antiguedad_meses_empresa >= 0
    ),
    constraint perfil_preventista_zona_not_empty check (
        zona_actual is null or btrim(zona_actual) <> ''
    ),
    constraint perfil_preventista_metricas_object check (
        jsonb_typeof(metricas_campo) = 'object'
    ),
    constraint perfil_preventista_metricas_keys check (
        metricas_campo ?& array[
            'periodo_inicio',
            'periodo_fin',
            'periodo_meses',
            'cumplimiento_cuota_pct',
            'cobertura_ruta_pct',
            'meta_cobertura_ruta_pct',
            'retencion_cartera_pct',
            'meta_retencion_cartera_pct',
            'cuentas_nuevas_abiertas',
            'meta_cuentas_nuevas',
            'reportes_a_tiempo_pct',
            'meta_reportes_a_tiempo_pct'
        ]
    ),
    constraint perfil_preventista_periodo_m1 check (
        metricas_campo @> '{
            "periodo_inicio": "2025-01-01",
            "periodo_fin": "2025-06-30",
            "periodo_meses": 6
        }'::jsonb
    ),
    constraint perfil_preventista_evidencia_object check (
        jsonb_typeof(evidencia_supervisor) = 'object'
    ),
    constraint perfil_preventista_evidencia_keys check (
        evidencia_supervisor ?& array[
            'evidencia_captacion',
            'evidencia_fidelizacion',
            'evidencia_cobertura_ruta',
            'evidencia_disciplina_comunicacion',
            'fortalezas_reportadas',
            'aspectos_mejora_reportados'
        ]
    ),
    constraint perfil_preventista_validation_status_catalog check (
        validation_status in ('valid', 'invalid')
    )
);

create index if not exists idx_perfil_preventista_dni_created_at
    on silver.perfil_preventista_estructurado (dni, created_at desc);

create table if not exists gold.preventistas_evaluados (
    employee_id varchar(8) primary key,
    employee_name text not null,
    zona_actual text,
    score_captacion numeric(5, 2),
    score_fidelizacion numeric(5, 2),
    score_cobertura_ruta numeric(5, 2),
    score_disciplina_comunicacion numeric(5, 2),
    score_total numeric(5, 2),
    perfil_comercial text,
    diferencia_perfiles numeric(5, 2),
    nivel_asignacion text,
    claridad_perfil text not null,
    requires_human_review boolean not null,
    review_status text not null,
    m3_eligible boolean not null default false,
    fortalezas jsonb not null default '[]'::jsonb,
    aspectos_mejora jsonb not null default '[]'::jsonb,
    explicacion text not null,
    metricas_faltantes jsonb not null default '[]'::jsonb,
    inconsistencias jsonb not null default '[]'::jsonb,
    raw_informe_id uuid not null references
        bronze.raw_informe_preventista (raw_informe_id),
    perfil_estructurado_id uuid not null references
        silver.perfil_preventista_estructurado (perfil_estructurado_id),
    evaluated_at timestamptz not null default now(),
    constraint preventistas_evaluados_employee_id_format check (
        employee_id ~ '^[0-9]{8}$'
    ),
    constraint preventistas_evaluados_employee_name_not_empty check (
        btrim(employee_name) <> ''
    ),
    constraint preventistas_evaluados_zona_not_empty check (
        zona_actual is null or btrim(zona_actual) <> ''
    ),
    constraint preventistas_evaluados_scores_range check (
        (score_captacion is null or score_captacion between 0 and 100)
        and (
            score_fidelizacion is null
            or score_fidelizacion between 0 and 100
        )
        and (
            score_cobertura_ruta is null
            or score_cobertura_ruta between 0 and 100
        )
        and (
            score_disciplina_comunicacion is null
            or score_disciplina_comunicacion between 0 and 100
        )
        and (score_total is null or score_total between 0 and 100)
        and (
            diferencia_perfiles is null
            or diferencia_perfiles between 0 and 100
        )
    ),
    constraint preventistas_evaluados_perfil_catalog check (
        perfil_comercial is null
        or perfil_comercial in (
            'captacion',
            'fidelizacion',
            'ejecucion_campo'
        )
    ),
    constraint preventistas_evaluados_nivel_catalog check (
        nivel_asignacion is null
        or nivel_asignacion in (
            'en_desarrollo',
            'listo_asignacion',
            'listo_cartera_prioritaria'
        )
    ),
    constraint preventistas_evaluados_claridad_catalog check (
        claridad_perfil in (
            'claro',
            'requiere_revision',
            'aprobado_por_rrhh',
            'rechazado'
        )
    ),
    constraint preventistas_evaluados_review_status_catalog check (
        review_status in (
            'not_required',
            'pending',
            'approved',
            'rejected'
        )
    ),
    constraint preventistas_evaluados_review_consistency check (
        requires_human_review = (review_status = 'pending')
        and (
            (review_status = 'not_required' and claridad_perfil = 'claro')
            or (
                review_status = 'pending'
                and claridad_perfil = 'requiere_revision'
            )
            or (
                review_status = 'approved'
                and claridad_perfil = 'aprobado_por_rrhh'
            )
            or (
                review_status = 'rejected'
                and claridad_perfil = 'rechazado'
            )
        )
    ),
    constraint preventistas_evaluados_score_nivel_consistency check (
        (score_total is null and nivel_asignacion is null)
        or (
            score_total is not null
            and nivel_asignacion is not null
            and (
                (
                    score_total < 70
                    and nivel_asignacion = 'en_desarrollo'
                )
                or (
                    score_total >= 70
                    and score_total < 85
                    and nivel_asignacion = 'listo_asignacion'
                )
                or (
                    score_total >= 85
                    and nivel_asignacion = 'listo_cartera_prioritaria'
                )
            )
        )
    ),
    constraint preventistas_evaluados_m3_consistency check (
        not m3_eligible
        or (
            score_total is not null
            and nivel_asignacion is not null
            and perfil_comercial is not null
            and nivel_asignacion in (
                'listo_asignacion',
                'listo_cartera_prioritaria'
            )
            and review_status in ('not_required', 'approved')
            and perfil_comercial in (
                'captacion',
                'fidelizacion',
                'ejecucion_campo'
            )
        )
    ),
    constraint preventistas_evaluados_explicacion_valid check (
        btrim(explicacion) <> ''
        and char_length(explicacion) <= 400
    ),
    constraint preventistas_evaluados_json_arrays check (
        jsonb_typeof(fortalezas) = 'array'
        and jsonb_typeof(aspectos_mejora) = 'array'
        and jsonb_typeof(metricas_faltantes) = 'array'
        and jsonb_typeof(inconsistencias) = 'array'
    )
);

create index if not exists idx_preventistas_evaluados_raw_informe
    on gold.preventistas_evaluados (raw_informe_id);

create index if not exists idx_preventistas_evaluados_perfil_estructurado
    on gold.preventistas_evaluados (perfil_estructurado_id);

alter table bronze.raw_informe_preventista enable row level security;
alter table silver.perfil_preventista_estructurado enable row level security;
alter table gold.preventistas_evaluados enable row level security;

-- Los informes contienen datos laborales sensibles. La aplicacion Streamlit
-- accede desde el servidor con service_role; no se habilita acceso publico.
revoke all privileges on table bronze.raw_informe_preventista
    from anon, authenticated;
revoke all privileges on table silver.perfil_preventista_estructurado
    from anon, authenticated;
revoke all privileges on table gold.preventistas_evaluados
    from anon, authenticated;

grant usage on schema bronze, silver, gold to service_role;
grant select, insert, update
    on table bronze.raw_informe_preventista to service_role;
grant select, insert, update
    on table silver.perfil_preventista_estructurado to service_role;
grant select, insert, update
    on table gold.preventistas_evaluados to service_role;

comment on table bronze.raw_informe_preventista is
    'Texto y metadatos del informe interno; no almacena el PDF original.';
comment on table silver.perfil_preventista_estructurado is
    'Metricas y evidencia del supervisor estructuradas y validadas.';
comment on table gold.preventistas_evaluados is
    'Perfil comercial vigente por preventista para consumo de M3.';

notify pgrst, 'reload schema';
