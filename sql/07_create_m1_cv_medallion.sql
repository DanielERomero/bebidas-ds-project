-- Modulo 1: CV de postulantes -> perfil comercial para M3.
-- Ejecutar en el SQL Editor de la misma instancia Supabase usada por M2.

create extension if not exists pgcrypto;
create schema if not exists bronze;
create schema if not exists silver;
create schema if not exists gold;

create table if not exists bronze.raw_cv (
    raw_cv_id uuid primary key default gen_random_uuid(),
    candidate_id varchar(8),
    file_name text not null,
    file_hash char(64) not null,
    extracted_text text,
    job_spec text,
    page_count integer not null default 0 check (page_count >= 0),
    extraction_status text not null check (
        extraction_status in ('success', 'invalid_pdf', 'empty_text', 'invalid_dni', 'error')
    ),
    error_message text,
    loaded_at timestamptz not null default now(),
    constraint raw_cv_candidate_id_format check (
        candidate_id is null or candidate_id ~ '^[0-9]{8}$'
    ),
    constraint raw_cv_success_has_data check (
        extraction_status <> 'success'
        or (candidate_id is not null and extracted_text is not null)
    )
);

-- Permite aplicar esta ampliacion aunque la tabla ya haya sido creada.
alter table bronze.raw_cv
    add column if not exists job_spec text;

create index if not exists idx_raw_cv_candidate_id
    on bronze.raw_cv (candidate_id);
create index if not exists idx_raw_cv_file_hash
    on bronze.raw_cv (file_hash);

create table if not exists silver.cv_estructurado (
    structured_cv_id uuid primary key default gen_random_uuid(),
    raw_cv_id uuid not null unique references bronze.raw_cv (raw_cv_id),
    candidate_id varchar(8) not null check (candidate_id ~ '^[0-9]{8}$'),
    candidate_name text not null,
    work_experience jsonb not null default '[]'::jsonb,
    skills jsonb not null default '[]'::jsonb,
    commercial_evidence jsonb not null default '[]'::jsonb,
    traditional_channel_evidence jsonb not null default '[]'::jsonb,
    prospecting_evidence jsonb not null default '[]'::jsonb,
    retention_evidence jsonb not null default '[]'::jsonb,
    route_coverage_evidence jsonb not null default '[]'::jsonb,
    communication_evidence jsonb not null default '[]'::jsonb,
    validation_status text not null check (validation_status in ('valid', 'invalid')),
    model_name text not null,
    prompt_version text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_cv_estructurado_candidate_id
    on silver.cv_estructurado (candidate_id);

create table if not exists gold.cv_evaluados (
    candidate_id varchar(8) primary key check (candidate_id ~ '^[0-9]{8}$'),
    candidate_name text not null,
    score_commercial_experience numeric(5,2) not null,
    score_traditional_channel numeric(5,2) not null,
    score_prospecting numeric(5,2) not null,
    score_retention numeric(5,2) not null,
    score_route_coverage numeric(5,2) not null,
    score_discipline_communication numeric(5,2) not null,
    score_total numeric(5,2) not null check (score_total between 0 and 100),
    assignment_readiness text not null check (
        assignment_readiness in (
            'requiere_revision',
            'requiere_acompanamiento',
            'apto_operativo',
            'apto_cartera_critica'
        )
    ),
    salesperson_type text not null check (
        salesperson_type in ('Hunter', 'Farmer', 'Ejecutor')
    ),
    salesperson_type_confidence numeric(4,3) not null check (
        salesperson_type_confidence between 0 and 1
    ),
    requires_human_review boolean not null,
    review_status text not null check (
        review_status in ('not_required', 'pending', 'approved', 'rejected')
    ),
    rotation_risk_level text check (
        rotation_risk_level is null or rotation_risk_level in ('bajo', 'medio', 'alto')
    ),
    m3_eligible boolean not null default false,
    strengths jsonb not null default '[]'::jsonb,
    gaps jsonb not null default '[]'::jsonb,
    xai_explanation text not null,
    raw_cv_id uuid not null references bronze.raw_cv (raw_cv_id),
    structured_cv_id uuid not null references silver.cv_estructurado (structured_cv_id),
    evaluated_at timestamptz not null default now(),
    constraint cv_evaluados_dimension_catalog check (
        score_commercial_experience in (0, 25, 50, 75, 100)
        and score_traditional_channel in (0, 25, 50, 75, 100)
        and score_prospecting in (0, 25, 50, 75, 100)
        and score_retention in (0, 25, 50, 75, 100)
        and score_route_coverage in (0, 25, 50, 75, 100)
        and score_discipline_communication in (0, 25, 50, 75, 100)
    ),
    constraint cv_evaluados_m3_consistency check (
        not m3_eligible
        or (
            assignment_readiness in ('apto_operativo', 'apto_cartera_critica')
            and review_status in ('not_required', 'approved')
            and salesperson_type_confidence >= 0.60
            and rotation_risk_level is not null
        )
    )
);

alter table bronze.raw_cv enable row level security;
alter table silver.cv_estructurado enable row level security;
alter table gold.cv_evaluados enable row level security;

-- La aplicacion Streamlit se conecta desde el servidor con service_role.
-- RLS protege las tablas frente a anon/authenticated, pero service_role tambien
-- necesita USAGE sobre los esquemas personalizados y permisos sobre las tablas.
grant usage on schema bronze, silver, gold to service_role;
grant select, insert, update on table bronze.raw_cv to service_role;
grant select, insert, update on table silver.cv_estructurado to service_role;
grant select, insert, update on table gold.cv_evaluados to service_role;
grant usage, select on all sequences in schema bronze, silver, gold to service_role;

-- Conserva los permisos para futuras tablas o secuencias creadas por postgres.
alter default privileges for role postgres in schema bronze
    grant all privileges on tables to service_role;
alter default privileges for role postgres in schema silver
    grant all privileges on tables to service_role;
alter default privileges for role postgres in schema gold
    grant all privileges on tables to service_role;
alter default privileges for role postgres in schema bronze
    grant usage, select on sequences to service_role;
alter default privileges for role postgres in schema silver
    grant usage, select on sequences to service_role;
alter default privileges for role postgres in schema gold
    grant usage, select on sequences to service_role;

comment on table bronze.raw_cv is
    'Texto extraido y metadatos del CV; no almacena el PDF original.';
comment on table silver.cv_estructurado is
    'CV estructurado y evidencias comerciales validadas con Pydantic.';
comment on table gold.cv_evaluados is
    'Perfil comercial vigente por candidato para consumo futuro de M3.';

-- Fuerza a la API REST de Supabase a reconocer columnas agregadas por migracion.
notify pgrst, 'reload schema';
