# Database — KINETIQ

Neon Postgres (London region). Schema managed with Alembic; this doc is the human-readable reference and the source for the first migration.

## Conventions

Units, time, IDs and versioning follow the shared [conventions](../../CLAUDE.md#conventions). Database-specific points:

- `uuid` primary keys use `gen_random_uuid()`; switch to `uuidv7()` if the Neon project runs Postgres 18+.
- `created_at` and `updated_at` on mutable tables.
- Large arrays (keypoints, meshes) never go in Postgres; store an object key + SHA-256.
- Two connection strings: **pooled** (API, workers) and **direct** (Alembic).

## Entity overview

```
organisations ─< memberships >─ users ─┬─ patients ─< programmes ─< programme_exercises >─ exercises
                                       │      │
                                       │      ├─< sessions ─< scans ─┬─< measurements >─ metric_definitions
                                       │      │                      ├─< compensation_events
                                       │      │                      ├─< outcome_tests
                                       │      │                      └─< sim_results
                                       │      ├─< pain_reports
                                       │      ├─ twins
                                       │      └─< forecasts
                                       ├─< care_links (clinician ↔ patient)
                                       └─< consents
model_registry · audit_log · llm_summaries
```

## Schema (initial migration)

```sql
create extension if not exists pgcrypto;

-- Enums
create type user_role        as enum ('patient', 'clinician', 'admin');
create type side_t           as enum ('left', 'right', 'none');
create type scan_kind        as enum ('assessment', 'exercise', 'test');
create type scan_status      as enum ('uploading', 'queued', 'processing', 'done', 'failed', 'rejected');
create type platform_t       as enum ('ios', 'android', 'web', 'edge');
create type link_status      as enum ('invited', 'active', 'ended');
create type programme_status as enum ('draft', 'active', 'paused', 'completed');

-- Organisations and people
create table organisations (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  created_at  timestamptz not null default now()
);

create table users (
  id               uuid primary key default gen_random_uuid(),
  auth_subject     text not null unique,          -- Better Auth user ID (JWT sub)
  role             user_role not null,
  email            text not null unique,
  display_name     text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  deleted_at       timestamptz
);

create table memberships (
  organisation_id  uuid not null references organisations(id) on delete cascade,
  user_id          uuid not null references users(id) on delete cascade,
  is_admin         boolean not null default false,
  primary key (organisation_id, user_id)
);

create table patients (
  user_id          uuid primary key references users(id) on delete cascade,
  birth_year       smallint check (birth_year between 1900 and 2100),
  sex              text,                            -- as recorded clinically
  height_m         numeric(4,3),
  condition_code   text,                            -- e.g. 'acl_recon', 'knee_oa'
  index_date       date,                            -- e.g. surgery date
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create table care_links (
  id               uuid primary key default gen_random_uuid(),
  clinician_id     uuid not null references users(id),
  patient_id       uuid not null references patients(user_id) on delete cascade,
  organisation_id  uuid not null references organisations(id),
  status           link_status not null default 'invited',
  created_at       timestamptz not null default now(),
  ended_at         timestamptz,
  unique (clinician_id, patient_id)
);

create table consents (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references users(id) on delete cascade,
  consent_type     text not null,                   -- 'terms', 'health_processing', 'research_training'
  document_version text not null,
  granted_at       timestamptz not null default now(),
  withdrawn_at     timestamptz
);
create index on consents (user_id, consent_type);

-- Exercises and programmes
create table exercises (
  code             text primary key,                -- e.g. 'sit_to_stand', 'heel_slide'
  name             text not null,
  description      text,
  primary_joint    text not null,                   -- kq-skel-v1 joint name
  checks           jsonb not null default '[]',     -- compensation checks enabled
  version          int not null default 1
);

create table programmes (
  id               uuid primary key default gen_random_uuid(),
  patient_id       uuid not null references patients(user_id) on delete cascade,
  clinician_id     uuid references users(id),
  condition_code   text not null,
  status           programme_status not null default 'draft',
  starts_on        date not null,
  limits           jsonb not null default '{}',     -- clinician-set bounds for adaptation
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create table programme_exercises (
  id               uuid primary key default gen_random_uuid(),
  programme_id     uuid not null references programmes(id) on delete cascade,
  exercise_code    text not null references exercises(code),
  position         smallint not null,
  sets             smallint not null,
  reps             smallint,
  hold_s           numeric(5,1),
  rest_s           numeric(5,1),
  progression      jsonb not null default '{}',
  unique (programme_id, position)
);

-- Sessions and scans
create table sessions (
  id               uuid primary key default gen_random_uuid(),
  patient_id       uuid not null references patients(user_id) on delete cascade,
  programme_id     uuid references programmes(id),
  platform         platform_t not null,
  app_version      text not null,
  started_at       timestamptz not null,
  ended_at         timestamptz
);
create index on sessions (patient_id, started_at desc);

create table scans (
  id               uuid primary key default gen_random_uuid(),
  patient_id       uuid not null references patients(user_id) on delete cascade,
  session_id       uuid references sessions(id) on delete set null,
  kind             scan_kind not null,
  segment_code     text,                            -- exercise or test code
  status           scan_status not null default 'uploading',
  captured_at      timestamptz not null,
  skeleton_version text not null,                   -- 'kq-skel-v1'
  pose_model_version text not null,
  keypoints_key    text,                            -- object storage key
  keypoints_sha256 text,
  frame_count      int,
  quality_score    real,                            -- 0..1 from kinetiq-core QC
  failure_reason   text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index on scans (patient_id, captured_at desc);
create index on scans (status) where status in ('queued', 'processing');

-- Measurements
create table metric_definitions (
  code             text primary key,
  domain           text not null,                   -- mobility, symmetry, stability, ...
  unit             text not null,                   -- SI unit
  description      text not null,
  version          int not null default 1
);

create table measurements (
  id               bigint generated always as identity primary key,
  scan_id          uuid not null references scans(id) on delete cascade,
  patient_id       uuid not null references patients(user_id) on delete cascade,
  metric_code      text not null references metric_definitions(code),
  side             side_t not null default 'none',
  base_metric      text references metric_definitions(code), -- for symmetry_index
  rep_index        smallint,                        -- null = whole scan aggregate
  value            double precision not null,
  method_version   text not null,
  measured_at      timestamptz not null
);
create index on measurements (patient_id, metric_code, measured_at);
create index on measurements (scan_id);

create table compensation_events (
  id               bigint generated always as identity primary key,
  scan_id          uuid not null references scans(id) on delete cascade,
  code             text not null,                   -- 'knee_valgus', 'trunk_lean', ...
  side             side_t not null default 'none',
  rep_index        smallint,
  start_ms         int not null,
  end_ms           int not null,
  severity         real not null,                   -- 0..1
  confidence       real not null,                   -- 0..1
  model_version    text not null
);
create index on compensation_events (scan_id);

create table outcome_tests (
  id               uuid primary key default gen_random_uuid(),
  scan_id          uuid not null references scans(id) on delete cascade,
  patient_id       uuid not null references patients(user_id) on delete cascade,
  test_code        text not null,                   -- 'sts_30s', 'tug', 'slb', 'knee_rom'
  score            double precision not null,
  unit             text not null,
  is_valid         boolean not null default true,
  invalid_reason   text,
  method_version   text not null,
  measured_at      timestamptz not null
);
create index on outcome_tests (patient_id, test_code, measured_at);

create table pain_reports (
  id               uuid primary key default gen_random_uuid(),
  patient_id       uuid not null references patients(user_id) on delete cascade,
  session_id       uuid references sessions(id) on delete set null,
  reported_at      timestamptz not null,
  score            smallint check (score between 0 and 10),
  location         text,
  source           text not null check (source in ('voice', 'manual'))
);
create index on pain_reports (patient_id, reported_at);

-- Twin, forecasts, simulation
create table twins (
  patient_id       uuid primary key references patients(user_id) on delete cascade,
  version          int not null default 1,
  usd_key          text,
  glb_key          text,
  usdz_key         text,
  body_model       jsonb not null default '{}',     -- segment lengths, joint limits
  updated_at       timestamptz not null default now()
);

create table forecasts (
  id               uuid primary key default gen_random_uuid(),
  patient_id       uuid not null references patients(user_id) on delete cascade,
  metric_code      text not null references metric_definitions(code),
  model_name       text not null,
  model_version    text not null,
  fitted_at        timestamptz not null,
  horizon_days     int not null,
  curve            jsonb not null,                  -- [{t_days, median, lo, hi}]
  drift_score      real,
  drift_flag       boolean not null default false,
  is_current       boolean not null default true
);
create unique index on forecasts (patient_id, metric_code) where is_current;

create table sim_results (
  id               uuid primary key default gen_random_uuid(),
  scan_id          uuid not null references scans(id) on delete cascade,
  kind             text not null,                   -- 'joint_load_surrogate', 'msk_full', 'what_if'
  outputs          jsonb not null,
  artefact_key     text,
  model_version    text not null,
  created_at       timestamptz not null default now()
);

-- AI governance
create table model_registry (
  id               uuid primary key default gen_random_uuid(),
  model_id         text not null,                   -- 'kq-pose', 'kq-comp', 'kq-forecast', ...
  version          text not null,
  kind             text not null,
  artefact_prefix  text not null,
  metrics          jsonb not null default '{}',
  status           text not null check (status in ('candidate', 'approved', 'retired')),
  created_at       timestamptz not null default now(),
  unique (model_id, version)
);

create table llm_summaries (
  id               uuid primary key default gen_random_uuid(),
  patient_id       uuid not null references patients(user_id) on delete cascade,
  input_sha256     text not null,
  output_text      text not null,
  model_name       text not null,
  model_version    text not null,
  prompt_version   text not null,
  guardrail_passed boolean not null,
  created_at       timestamptz not null default now()
);

create table audit_log (
  id               bigint generated always as identity primary key,
  actor_id         uuid references users(id),
  action           text not null,                   -- 'read', 'create', 'update', 'delete', 'export'
  entity           text not null,
  entity_id        text not null,
  at               timestamptz not null default now(),
  details          jsonb not null default '{}'      -- never health values
);
create index on audit_log (entity, entity_id, at);
```

The job queue tables are created by Procrastinate's own migration in a separate `procrastinate` schema. Better Auth's tables (users, sessions, accounts, two-factor, signing keys) live in a separate `auth` schema, created by its own migrations and owned by the auth service's database role; the application links to them only through `users.auth_subject`.

## Row-level security

The API runs each request in a transaction and sets the caller's identity with `SET LOCAL`, which works with Neon's pooled (transaction-mode) connections.

```sql
-- In every request transaction:
--   select set_config('app.user_id', '<uuid>', true);
--   select set_config('app.role', 'patient|clinician|admin', true);

create function app_user_id() returns uuid language sql stable
  as $$ select nullif(current_setting('app.user_id', true), '')::uuid $$;

create function can_access_patient(p uuid) returns boolean language sql stable as $$
  select p = app_user_id()
      or exists (select 1 from care_links cl
                 where cl.patient_id = p and cl.clinician_id = app_user_id()
                   and cl.status = 'active')
      or current_setting('app.role', true) = 'admin'
$$;

alter table scans enable row level security;
create policy scans_access on scans
  using (can_access_patient(patient_id))
  with check (can_access_patient(patient_id));
-- Repeat for: patients, programmes, sessions, measurements, outcome_tests,
-- pain_reports, twins, forecasts, llm_summaries. Child tables keyed by scan_id
-- (compensation_events, sim_results) check via a join to scans.
```

The API role is not a superuser and does not have `BYPASSRLS`. Workers use a separate role that may bypass RLS, because they act on behalf of the system; worker code still filters by `patient_id` explicitly.

## Migrations and branching

- One Alembic revision per concern; never edit an applied revision.
- Every PR that touches the schema runs migrations against a fresh **Neon branch** in CI, then the test suite against that branch.
- Production migrations run from CI with the direct connection string, before the new API version is deployed. Migrations must be backward compatible with the previous API version (expand, then contract).

## Common queries

```sql
-- Latest value of a metric per side for a patient
select distinct on (side) side, value, measured_at
from measurements
where patient_id = $1 and metric_code = 'knee_flexion_peak'
order by side, measured_at desc;

-- Patients with an active drift flag for a clinician
select f.patient_id, f.metric_code, f.drift_score
from forecasts f
join care_links cl on cl.patient_id = f.patient_id
where cl.clinician_id = $1 and cl.status = 'active'
  and f.is_current and f.drift_flag;
```
