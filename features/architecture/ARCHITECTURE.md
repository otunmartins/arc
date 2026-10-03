# Architecture — KINETIQ

## System overview

```
┌──────────────────────────── On device ─────────────────────────────┐
│ Expo app (iOS / Android / web)                                     │
│  camera → pose model (TFLite / ONNX / MediaPipe / TensorRT*)       │
│        → canonical keypoints (kq-skel-v1) → live cues, local UI    │
└───────────────┬──────────────────────────────────────┬─────────────┘
                │ HTTPS (REST)                          │ WSS (live session)
                ▼                                       ▼
┌──────────────────────── FastAPI service (DigitalOcean, LON1) ──────┐
│ auth (JWT) · REST · WebSocket session hub · job enqueue            │
│ calls: NVIDIA NIM (LLM), Riva (ASR/TTS)                            │
└───────┬───────────────────────┬────────────────────────┬───────────┘
        │ SQL (pooled)          │ S3 API                 │ enqueue
        ▼                       ▼                        ▼
┌──────────────┐     ┌────────────────────┐     ┌──────────────────────┐
│ Neon Postgres│◄────│ Object storage     │◄────│ Workers               │
│ (London)     │     │ keypoints, USD,    │     │ CPU: scan, twin,      │
│ records,     │     │ glTF/USDZ, models, │     │      forecast         │
│ queue, RLS   │────►│ synthetic data     │     │ GPU: sim, surrogate,  │
└──────────────┘     └────────────────────┘     │      synthetic, train │
                                                └──────────────────────┘
* TensorRT only on NVIDIA hardware (RTX laptop, Jetson) — the showcase setup.
```

## Components

| Component | Responsibility | Runs on |
| --- | --- | --- |
| `apps/mobile` | Capture, on-device pose, live cues, 3D twin viewer, dashboard | iOS, Android, web (Expo) |
| `services/auth` | Better Auth: sign-up, sign-in, sessions, two-factor; issues JWTs and serves the JWKS | DigitalOcean (LON1), beside the API |
| `services/api` | JWT verification, REST, WebSocket sessions, persistence, enqueue, LLM/voice proxy | DigitalOcean App Platform or Droplet |
| `services/workers` (CPU) | Scan processing, twin update, forecast refit | DigitalOcean Droplet |
| `services/workers` (GPU) | Musculoskeletal sim, surrogate training, synthetic data, model training | DO GPU Droplet (create-run-destroy) → DGX Cloud Lepton Batch Jobs |
| `packages/kinetiq-core` | Biomechanics, metrics, twin logic, forecasting maths | Imported by API and workers |
| `packages/contracts` | Keypoint and measurement schemas | Source of Pydantic + TS types |
| Neon Postgres | System of record, job queue, RLS | Neon, London |
| Object storage | Large binary artefacts | DigitalOcean Spaces (LON/AMS region) |
| NVIDIA hosted services | LLM (NIM), speech (Riva) | build.nvidia.com endpoints |

## Key flows

### 0. Sign-in

The app signs in against `services/auth` (Better Auth), which stores users and sessions in Neon and issues a short-lived JWT. The app sends that JWT to the API; the API verifies it against the auth service's JWKS and maps `sub` → `users.auth_subject`. The API never handles passwords or second factors.

### 1. Scan (assessment or exercise set)

1. App runs pose on device, produces `kq-skel-v1` keypoint frames.
2. App requests an upload URL: `POST /v1/scans` → API creates `scans` row (status `uploading`), returns pre-signed PUT URL.
3. App uploads compressed keypoints to object storage, then `POST /v1/scans/{id}/complete`.
4. API verifies checksum, sets status `queued`, enqueues `scan.process`.
5. Worker: load keypoints → `kinetiq-core` quality checks → features and metrics → compensation events → outcome tests → write rows → enqueue `twin.update` and `forecast.refit`.
6. App polls `GET /v1/scans/{id}` or receives a push when status is `done`.

### 2. Live session

1. App opens `WSS /v1/sessions/{id}/live`.
2. App streams keypoint batches (~10 Hz batches of 30 Hz frames). Real-time compensation checks run **on device** for latency; the server receives batches for session-level tracking and voice.
3. Voice: app streams audio; API proxies to Riva ASR, intents (e.g. "that hurts") become `pain_reports`; coach replies via Riva TTS.
4. On close, the session's sets become scans and follow flow 1.

### 3. Twin update and forecast

- `twin.update`: append the scan's signature to the twin, update body-model parameters, regenerate USD → glTF/USDZ exports.
- `forecast.refit`: refit the patient's posterior under the population model, compute expected curve with intervals, compute drift score, set `drift_flag`.

### 4. Explanation

`POST /v1/patients/{id}/summary` → API gathers structured measurements and forecast → NIM LLM with a fixed system prompt and NeMo Guardrails → text that cites only provided values. Output is cached and versioned.

### 5. GPU batch job

API or operator enqueues a GPU job → launcher script creates a GPU Droplet (or submits a Lepton Batch Job) with the job container → job reads inputs from object storage, writes outputs back, records results in Postgres → instance destroyed.

## Boundaries and interfaces

- App ↔ API: REST + WebSocket defined in [API.md](API.md); TS client generated from OpenAPI.
- API ↔ workers: jobs via Postgres queue only; payloads carry IDs, never data blobs.
- Workers ↔ storage: object keys from [DATA.md](../data/DATA.md).
- Everything numeric flows through `kinetiq-core`.

## Non-functional targets (proposed)

| Concern | Target |
| --- | --- |
| On-device pose | ≥ 25 fps on a mid-range phone; ≥ 30 fps on RTX/Jetson |
| Live cue latency | < 200 ms from movement to spoken or visual cue (on-device path) |
| Scan processing | Results within 60 s of upload for a standard battery |
| Availability | Best effort for MVP; no single patient session depends on GPU availability |
| Data residency | All patient data in UK/EU regions |
