# Data — KINETIQ

The keypoint contract, metric definitions, storage layout and data lifecycle. Change this doc in the same commit as any change to `packages/contracts` or `kinetiq-core` metrics.

## Data classes

| Class | Examples | Where it lives | Sensitivity |
| --- | --- | --- | --- |
| Identity | Name, email, auth ID | Postgres (`auth` schema + `users`) | Personal data |
| Clinical context | Condition, surgery date, programme, pain reports, clinician notes | Postgres | Special category (health) |
| Movement data | Keypoint sequences | Object storage (`keypoints/`) | Special category (health) |
| Derived measures | Metrics, tests, compensation events, forecasts, joint loads | Postgres | Special category (health) |
| Twin assets | USD, glTF, USDZ | Object storage (`twins/`) | Special category (health) |
| Training data | De-identified keypoint sets (consented), synthetic data | Object storage (`datasets/`) | Pseudonymised / synthetic |
| Operational | Logs, traces, job metadata | Logfire, Sentry, Postgres | Must contain no health data |
| **Video** | — | **Never stored or transmitted** | — |

## Canonical keypoint contract: `kq-skel-v1`

All platforms convert their pose model output into this skeleton before anything leaves the device.

### Joints (index → name)

| # | Joint | # | Joint | # | Joint |
| --- | --- | --- | --- | --- | --- |
| 0 | pelvis | 7 | left_shoulder | 14 | right_knee |
| 1 | left_hip | 8 | right_shoulder | 15 | left_ankle |
| 2 | right_hip | 9 | left_elbow | 16 | right_ankle |
| 3 | spine_mid | 10 | right_elbow | 17 | left_heel |
| 4 | chest | 11 | left_wrist | 18 | right_heel |
| 5 | neck | 12 | right_wrist | 19 | left_foot_index |
| 6 | head | 13 | left_knee | 20 | right_foot_index |

Left/right are the **subject's** left and right.

### Coordinates

- 3D, camera space, metres. Right-handed: +X to the camera's right, +Y up, +Z toward the camera.
- Per joint: `x, y, z, confidence` (confidence 0–1). Missing joint: `confidence = 0`, coordinates `NaN`.
- Timestamps: milliseconds from scan start, monotonic.
- Target 30 Hz; workers resample to 30 Hz.
- Body-frame transforms, smoothing and gap filling happen in `kinetiq-core`, never on device.

### Scan header (JSON)

```json
{
  "format": "kqk",
  "format_version": 1,
  "skeleton": "kq-skel-v1",
  "scan_id": "uuid",
  "pose_model": {"id": "kq-pose", "version": "1.0.0", "runtime": "tflite"},
  "device": {"platform": "ios", "model": "iPhone15,3", "app_version": "0.1.0"},
  "camera": {"fps": 30, "width": 1280, "height": 720, "orientation": "portrait", "height_m": null, "gravity": [0, -1, 0]},
  "battery": {"id": "rehab-knee", "version": "1"},
  "segment": {"kind": "test", "code": "sts_30s"},
  "frame_count": 900,
  "started_at": "2026-10-03T09:15:00Z"
}
```

Header rules, enforced by the Pydantic model in `packages/contracts` (the source of the JSON Schema and TS types):

- All fields are required; unknown fields are rejected. A new field means a new `format_version`.
- `pose_model.runtime`: `tflite`, `coreml`, `onnx`, `mediapipe` or `tensorrt`.
- `device.platform`: `ios`, `android`, `web` or `edge`. `segment.kind`: `assessment`, `exercise` or `test`.
- `camera.orientation`: `portrait` or `landscape`. `camera.height_m` may be `null`.
- `camera.gravity`: unit vector pointing down in camera space, from the device's motion sensor at scan start; `null` if the device cannot report it (for example a desktop webcam). Workers use it as the vertical reference; with `null` they fall back to the camera's +Y axis.
- `started_at` must carry a timezone.

### Binary file `*.kqk.gz`

gzip of: `"KQK1"` (4 bytes) · `uint32 LE` header length · header JSON (UTF-8) · `frame_count` frames, each `int32 LE t_ms` + 21 × 4 `float32 LE` (x, y, z, confidence). Chosen because it is trivial to write from TypeScript (`DataView`) and Python (`numpy.frombuffer`). Workers convert to Parquet for analytics.

Frame rules, checked on encode and decode in both languages:

- The frame bytes must be exactly `frame_count × 340` (4 + 21 × 4 × 4 bytes per frame).
- Timestamps start at 0 or later and never decrease (equal consecutive timestamps are allowed).
- Confidence is between 0 and 1. Coordinates are finite, or `NaN` for a missing joint; a joint with any `NaN` coordinate must have confidence 0.
- The Python decoder caps the decompressed size (64 MB by default) so an oversized upload is rejected.

Two committed fixtures in `packages/contracts/fixtures/`, one written by each language, are decoded by both test suites to prove the implementations agree.

## Metric catalogue (v1)

Internal units are SI; presentation converts. Every metric row records `method_version`.

| Code | Domain | Unit | Side | Definition |
| --- | --- | --- | --- | --- |
| `knee_flexion_peak` | Mobility | rad | L/R | Max angle between thigh (hip→knee) and shank (knee→ankle) vectors, as flexion from full extension |
| `knee_extension_deficit` | Mobility | rad | L/R | Min flexion reached (0 = full extension) |
| `hip_flexion_peak` | Mobility | rad | L/R | Max sagittal angle between trunk and thigh |
| `shoulder_abduction_peak` | Mobility | rad | L/R | Max frontal angle between trunk and upper arm |
| `knee_valgus_peak` | Compensation | rad | L/R | Max frontal-plane projection angle of hip-knee-ankle |
| `trunk_lean_peak` | Compensation | rad | — | Max trunk deviation from vertical in the frontal plane |
| `pelvic_drop_peak` | Compensation | rad | L/R | Max pelvic obliquity during single-leg stance |
| `symmetry_index` | Symmetry | % | — | `100 × |L − R| / ((L + R) / 2)` for a named base metric (stored with `base_metric`) |
| `com_sway_area` | Stability | m² | — | 95% confidence ellipse area of estimated centre-of-mass ground projection |
| `single_leg_balance_time` | Stability | s | L/R | Time until stance loss or 30 s cap |
| `sts_30s_count` | Test | count | — | Full stands completed in 30 seconds |
| `tug_time` | Test | s | — | Timed Up and Go duration |
| `rep_angular_velocity_mean` | Velocity | rad/s | L/R | Mean peak angular velocity of the primary joint per rep |
| `rep_variability_cv` | Consistency | ratio | — | Coefficient of variation of primary-joint ROM across reps |
| `fatigue_slope` | Fatigue | ratio/rep | — | Slope of normalised rep quality score across a set |
| `knee_load_peak_est` | Load (sim) | N·m/kg | L/R | Peak knee joint moment estimate from S2 surrogate |

### Implementation status (`kinetiq-core` 0.1.0)

Implemented: `knee_flexion_peak`, `knee_extension_deficit`, `hip_flexion_peak`, `shoulder_abduction_peak`, `knee_valgus_peak`, `trunk_lean_peak`, `symmetry_index`. Pelvic obliquity is available as a time series; `pelvic_drop_peak` waits for single-leg stance detection. The stability, test, velocity, consistency, fatigue and load metrics are not yet implemented.

How the angles are measured:

- **Body frame:** lateral axis from right hip to left hip, up axis from pelvis to neck (made perpendicular to lateral), forward axis as their cross product. Angles in this frame do not depend on camera position.
- **Sign conventions:** hip flexion is positive forward; shoulder abduction is positive away from the body; knee valgus is positive when the knee moves toward the midline; trunk lean is positive toward the subject's left (the peak metric takes the larger of either direction).
- **Knee flexion is unsigned**, so hyperextension reads as a small positive angle and `knee_extension_deficit` cannot go below 0.
- **Trunk lean and pelvic obliquity are measured against vertical**, taken from `camera.gravity` in the scan header so a tilted phone does not bias them. When gravity is `null` the camera's +Y axis is used and a tilted camera does bias the reading.
- A metric is not produced when the joints it needs were never visible; frames with a missing joint are skipped.

### Preprocessing defaults (provisional; see decision 022)

Applied by `kinetiq_core.prepare` before any metric:

| Step | Default |
| --- | --- |
| Joint treated as missing below confidence | 0.5 |
| Resample to an even rate | 30 Hz, linear interpolation |
| Longest gap filled by interpolation | 200 ms; longer gaps stay missing |
| Smoothing | Zero-lag Butterworth low-pass, 6 Hz cutoff |

`scans.quality_score` is currently the share of (frame, joint) samples that are usable, over the joints a test needs.

Adding a metric: add it to `metric_definitions` (migration), implement it in `kinetiq-core` with known-answer tests, document it here.

## Capture protocol (provisional)

Measurement error depends heavily on how the phone is placed, so each test fixes the setup and the app checks it before scoring. Provisional values (decision 022):

| Item | Requirement |
| --- | --- |
| View | Side-on for flexion tests, with the operated leg nearest the camera; front-on for balance and single-leg squat |
| Distance | 2.5–3 m from the subject |
| Camera height | About hip height (roughly 1 m) |
| Phone | Portrait, stationary on a stable surface, tilted no more than about 10° from upright (checked with `camera.gravity`) |
| Framing | Whole body in frame with a margin, one person only |
| Subject | Knees and ankles visible (shorts or fitted clothing), even lighting, plain background where possible |

A scan outside these limits is flagged and not scored. The scan header does not yet record which view was used; that field is added with the pose spike.

## Object storage layout

```
keypoints/{patient_id}/{scan_id}/v1.kqk.gz
keypoints-parquet/{patient_id}/{scan_id}/v1.parquet
twins/{patient_id}/{twin_version}/twin.usd | twin.glb | twin.usdz
models/{model_id}/{version}/...            # artefacts + model card
datasets/{name}/{version}/manifest.json     # immutable, hashes of every file
sim/{job_id}/inputs|outputs/...
exports/{request_id}/...                    # subject access request exports
```

Rules: buckets are private; access through short-lived pre-signed URLs only; server-side encryption on; object keys never contain names or emails.

## Data lifecycle

1. **Capture:** video stays on device and is discarded after pose.
2. **Upload:** keypoints via pre-signed URL; checksum verified.
3. **Process:** derived measures written to Postgres with versions.
4. **Use:** patient and their linked clinicians only (RLS).
5. **Training reuse:** only with explicit, separate research consent (`consents.consent_type = 'research_training'`). Data is copied into a pseudonymised dataset (random dataset IDs, no direct identifiers, dates shifted per subject).
6. **Retention:** periods set in the DPIA, aligned with professional record-keeping guidance. Raw keypoints may have a shorter retention than derived clinical measures.
7. **Deletion:** account deletion removes identity, clinical rows and objects; consented training datasets follow the consent terms recorded at collection.
8. **Subject access:** export job produces a JSON + CSV bundle under `exports/`.

## Synthetic data

Synthetic sets carry `source = synthetic` in manifests and are never mixed into evaluation sets that gate real-world accuracy.
