# API — KINETIQ

FastAPI service. Base path `/v1`. JSON over HTTPS; one WebSocket for live sessions. The OpenAPI spec at `/openapi.json` is the source of truth; the app's TypeScript client is generated from it.

## Conventions

- Auth: `Authorization: Bearer <JWT>` issued by `services/auth` (Better Auth) and verified against its JWKS. The API maps `sub` → `users.auth_subject`.
- IDs, times, units and versioning follow the shared [conventions](../../CLAUDE.md#conventions); the client converts units for display.
- Errors: RFC 9457 problem details (`type`, `title`, `status`, `detail`, `instance`).
- Pagination: cursor based, `?cursor=…&limit=…`, response `{items, next_cursor}`.
- Idempotency: `Idempotency-Key` header on POSTs that create resources.
- Responses that contain computed values include their `method_version` / `model_version`.

## REST endpoints

### Identity

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/me` | Current user, role, linked patients or clinicians |
| POST | `/v1/consents` | Record a consent (`consent_type`, `document_version`) |
| DELETE | `/v1/consents/{id}` | Withdraw a consent |

### Patients and care links (clinician)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/patients` | Clinician's active patients, with drift flags |
| POST | `/v1/patients/invite` | Invite a patient by email, creates `care_links` |
| GET | `/v1/patients/{id}` | Patient profile and programme summary |

### Programmes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/exercises` | Exercise library |
| POST | `/v1/programmes` | Create programme (clinician) |
| PATCH | `/v1/programmes/{id}` | Update exercises, limits, status |
| GET | `/v1/patients/{id}/programme` | Current programme |

### Sessions and scans

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/sessions` | Start a session → `{session_id}` |
| PATCH | `/v1/sessions/{id}` | End a session |
| POST | `/v1/scans` | Create scan (header JSON) → `{scan_id, upload_url, expires_at}` |
| POST | `/v1/scans/{id}/complete` | Confirm upload with `sha256` → enqueues `scan.process` |
| GET | `/v1/scans/{id}` | Status + results when `done` |

### Results

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/patients/{id}/measurements?metric=…&from=…&to=…` | Time series |
| GET | `/v1/patients/{id}/tests?test=…` | Outcome test history |
| GET | `/v1/patients/{id}/forecasts` | Current forecast curves + drift |
| GET | `/v1/patients/{id}/twin` | Twin metadata + signed URLs (glb, usdz) |
| POST | `/v1/patients/{id}/summary` | Generate or fetch an LLM explanation (guardrailed) |
| POST | `/v1/pain-reports` | Manual pain report |

### Data rights

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/me/export` | Start subject access export → job ID |
| DELETE | `/v1/me` | Request account deletion |

### Ops

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/healthz` | Liveness |
| GET | `/readyz` | DB + storage reachability |

## Example: create scan

```http
POST /v1/scans
Idempotency-Key: 6f1c…

{
  "session_id": "…",
  "kind": "test",
  "segment_code": "sts_30s",
  "captured_at": "2026-10-03T09:15:00Z",
  "skeleton_version": "kq-skel-v1",
  "pose_model_version": "1.0.0",
  "frame_count": 900
}
```

```json
{
  "scan_id": "…",
  "upload_url": "https://…signed…",
  "expires_at": "2026-10-03T09:30:00Z"
}
```

## Live session WebSocket

`WSS /v1/sessions/{id}/live?token=<JWT>`

All messages are JSON with a `type`. Client → server:

| type | Payload | Notes |
| --- | --- | --- |
| `hello` | `{skeleton_version, pose_model_version, platform}` | First message; server rejects unsupported versions |
| `set_start` | `{exercise_code, set_index}` | |
| `kp_batch` | `{t0_ms, frames: [[x,y,z,c] × 21] × n}` | ~10 Hz batches of 30 Hz frames |
| `rep_event` | `{rep_index, start_ms, end_ms}` | From on-device segmenter |
| `cue_shown` | `{code, at_ms}` | On-device compensation cue was given |
| `audio_chunk` | `{seq, pcm16_b64}` | 16 kHz mono, for Riva ASR |
| `set_end` | `{set_index}` | |
| `bye` | `{}` | |

Server → client:

| type | Payload | Notes |
| --- | --- | --- |
| `ready` | `{session_id, limits}` | Programme limits for adaptation |
| `coach_say` | `{text, audio_b64?}` | Riva TTS |
| `adjust` | `{exercise_code, reps?, rest_s?, reason}` | Within clinician limits only |
| `pain_ack` | `{score, report_id}` | Voice pain report recorded |
| `error` | `{code, detail}` | |

Latency-critical form cues are generated **on device**; the server never sits in the cue loop.
