# CLAUDE.md — KINETIQ

Context for Claude Code working in this repository. Read this first, then the doc that matches the task (see the [docs index](#docs-index) below).

## What KINETIQ is

KINETIQ is an AI movement intelligence platform. A phone or webcam captures movement, on-device pose estimation turns it into 3D keypoints, and the platform builds a **Movement Twin** of each person: a longitudinal, simulatable record of how they move. The first application is clinician-supervised musculoskeletal rehabilitation (KINETIQ Rehab). It is the NVIDIA Inception showcase product for Algonix AI Ltd.

Full context: [features/product/PROJECT_OVERVIEW.md](features/product/PROJECT_OVERVIEW.md).

## Golden rules (never break these)

1. **Raw video never leaves the device.** Only keypoints and derived data reach the backend. Never add an endpoint, upload, log line or analytics event that carries video frames or images of patients.
2. **The LLM never computes or invents numbers.** Every number shown to a user comes from `kinetiq-core` (biomechanics), a simulation, or a fitted model. The language layer only reads structured measurements and explains them, and it never diagnoses.
3. **No heavy compute inside an API request.** Endpoints validate, persist and enqueue. Workers do the work.
4. **One keypoint contract.** All platforms emit the canonical skeleton defined in `packages/contracts` (see [features/data/DATA.md](features/data/DATA.md)). Never let a platform-specific format reach the backend.
5. **`kinetiq-core` stays pure.** No FastAPI, SQLAlchemy, cloud SDK or provider imports. Pure Python + NumPy/SciPy (plus `kinetiq-contracts` for the skeleton definition), fully unit-tested.
6. **GPU jobs are portable containers.** No provider-specific code inside job logic. DigitalOcean today, DGX Cloud Lepton later: a deployment change, never a rewrite.
7. **Health data stays in the UK/EU.** Neon (London), DigitalOcean (LON1). Never introduce a service that stores patient data elsewhere without a recorded decision in [features/product/DECISIONS.md](features/product/DECISIONS.md).
8. **Clinical claims are not ours to make in code comments, copy or prompts.** Measures are estimates that support a clinician. Wording rules: [features/data/SECURITY_PRIVACY_COMPLIANCE.md](features/data/SECURITY_PRIVACY_COMPLIANCE.md).

## Stack

| Layer | Technology |
| --- | --- |
| App (iOS, Android, web) | Expo SDK 57 (React Native), Expo Router, TypeScript strict, react-native-web |
| On-device pose | VisionCamera + TFLite/ONNX (native), MediaPipe Tasks Vision / ONNX Runtime Web (web) |
| 3D | react-three-fiber (native via expo-gl) |
| API | Python 3.12, FastAPI, Pydantic v2, async SQLAlchemy 2.0 + asyncpg |
| Database | Neon Postgres (London), Alembic migrations |
| Queue | Postgres-backed (Procrastinate) |
| Workers | Python containers; CPU on DigitalOcean, GPU on DigitalOcean GPU Droplets → DGX Cloud Lepton Batch Jobs |
| Object storage | S3-compatible (DigitalOcean Spaces) |
| AI services | NVIDIA NIM (LLM), Riva (voice), TAO, TensorRT, Warp/Newton, PhysicsNeMo, Omniverse/OpenUSD, Replicator, Cosmos |
| Auth | Self-hosted Better Auth (Node service, data in Neon), two-factor for clinicians and admins, JWT verified in FastAPI via JWKS, Postgres RLS |
| Observability | Sentry, Logfire |

Detail: [features/architecture/ARCHITECTURE.md](features/architecture/ARCHITECTURE.md), [features/architecture/AI_INFRASTRUCTURE.md](features/architecture/AI_INFRASTRUCTURE.md).

## Repository layout

```
kinetiq/
├── CLAUDE.md
├── apps/mobile/              # Expo app (iOS, Android, web)
├── services/auth/            # Better Auth (Node): sign-in, sessions, two-factor, JWT + JWKS
├── services/api/             # FastAPI: routes, JWT verification, WebSocket, job enqueue
├── services/workers/         # Job handlers: scan processing, twin, forecast, sim, surrogate
├── packages/kinetiq-core/    # Pure-Python biomechanics, twin and forecasting logic
├── packages/contracts/       # Keypoint + measurement schemas → Pydantic + generated TS
├── infra/                    # Alembic, Dockerfiles, deploy and GPU scripts
└── features/                 # Project documentation (index below)
    ├── product/              # Overview, roadmap, decisions
    ├── architecture/         # System, AI infrastructure, API, deployment
    └── data/                 # Data contract, database, security and compliance
```

## Commands

Python uses a `uv` workspace; JS uses `pnpm`.

```bash
# Python
uv sync                                        # install workspace deps
uv run fastapi dev services/api/app/main.py    # API on :8000
uv run procrastinate --app=workers.app worker  # local worker
uv run pytest                                  # all Python tests
uv run ruff check . && uv run ruff format .    # lint + format
uv run pyright                                 # type check

# Database
uv run alembic -c infra/alembic.ini upgrade head
uv run alembic -c infra/alembic.ini revision --autogenerate -m "msg"

# Contracts (after changing packages/contracts)
uv run python packages/contracts/build.py      # regenerate JSON Schema + TS types from the Pydantic models

# App
pnpm install
pnpm --filter mobile start                     # Expo dev server (dev build required)
pnpm --filter mobile web                       # web build in browser
pnpm --filter mobile typecheck && pnpm --filter mobile lint
pnpm --filter mobile api:gen                   # regenerate TS client from OpenAPI
```

## Conventions

- **Python:** type hints everywhere; Pydantic v2 for I/O schemas; SQLAlchemy 2.0 typed ORM; async in the API, sync is fine in workers. Ruff for lint/format, pyright strict on `kinetiq-core` and `contracts`.
- **TypeScript:** strict mode; no `any`; API calls only through the generated client.
- **Platform splits:** `*.native.ts` / `*.web.ts` behind one shared interface in the same folder.
- **Units:** SI internally (metres, seconds, radians). Convert to degrees and cm only at the presentation layer. Every metric has a unit in `metric_definitions`.
- **Time:** UTC `timestamptz` everywhere; ISO 8601 in JSON.
- **IDs:** UUIDs; never expose sequential IDs.
- **Versioning:** every computed value records the method or model version that produced it.
- **Migrations:** one concern per migration; never edit an applied migration; test on a Neon branch first.
- **Tests:** every `kinetiq-core` function has unit tests with known-answer fixtures (synthetic keypoints with known angles). API routes get integration tests against a Neon branch or local Postgres.
- **Logging:** structured logs; never log keypoint arrays, pain reports, free-text notes or personal identifiers.

## How to work in this repo

- Start backend-first: contracts → `kinetiq-core` → database → API → workers → app.
- Before changing a schema, metric or contract, read [features/data/DATA.md](features/data/DATA.md) and update it in the same change.
- Before adding a dependency or service, check [features/product/DECISIONS.md](features/product/DECISIONS.md); record new decisions there.
- When unsure whether something is a clinical claim or touches patient data, stop and ask.
- There is no clinical advisor yet. Where a clinical input is needed (thresholds, test choice, protocols), set it provisionally from published evidence, mark it "provisional", and add it to the review item in [features/product/DECISIONS.md](features/product/DECISIONS.md) (decision 022). Do not leave it undefined or defer it to an advisor.

## Docs index

| Doc | Read when |
| --- | --- |
| [features/product/PROJECT_OVERVIEW.md](features/product/PROJECT_OVERVIEW.md) | Any product or scope question |
| [features/architecture/ARCHITECTURE.md](features/architecture/ARCHITECTURE.md) | Adding services, flows or integrations |
| [features/architecture/AI_INFRASTRUCTURE.md](features/architecture/AI_INFRASTRUCTURE.md) | Models, training, inference, simulation, GPU jobs |
| [features/data/DATA.md](features/data/DATA.md) | Keypoint contract, metrics, storage, data lifecycle |
| [features/data/DATABASE.md](features/data/DATABASE.md) | Schema, migrations, RLS, queries |
| [features/architecture/API.md](features/architecture/API.md) | Endpoints and the live-session WebSocket protocol |
| [features/data/SECURITY_PRIVACY_COMPLIANCE.md](features/data/SECURITY_PRIVACY_COMPLIANCE.md) | Anything touching patient data, auth or product claims |
| [features/architecture/DEVELOPMENT.md](features/architecture/DEVELOPMENT.md) | Local setup, env vars, testing, CI |
| [features/architecture/DEPLOYMENT.md](features/architecture/DEPLOYMENT.md) | Hosting, releases, GPU job scripts |
| [features/product/DECISIONS.md](features/product/DECISIONS.md) | Why things are the way they are |
| [features/product/ROADMAP.md](features/product/ROADMAP.md) | What to build next |
