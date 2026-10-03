# Roadmap — KINETIQ

The Inception showcase lands at the end of phase 2.

## Phase 1 — Core twin

- Contracts: `kq-skel-v1`, `.kqk.gz` encoder/decoder (Python + TS)
- `kinetiq-core`: QC, angles, ROM, symmetry, stability, variability
- Database + API: users, patients, sessions, scans, measurements
- App: guided scan, on-device pose with an existing open model (native + web), upload, Day 1/7/30 comparison
- Capture guidance in the app (camera view, distance, height) and scan rejection when the setup is wrong
- Validation study, then bias correction fitted and cross-validated on it (plan in [AI_INFRASTRUCTURE.md](../architecture/AI_INFRASTRUCTURE.md#evaluation-gates-provisional-thresholds-see-decision-022))
- **Gate:** knee flexion vs long-arm goniometer in the standard setup: mean bias within ±2°, mean absolute error ≤ 5°, 95% limits of agreement within ±10° (provisional, decision 024)

## Phase 2 — Rehab showcase

- Compensation detection (live cue + recorded events)
- Auto-scored tests from the `rehab-knee` battery: heel-slide knee flexion, squat, 30 s sit-to-stand, single-leg balance, single-leg squat
- Voice coach (Riva), pain reports, adaptive sessions within limits
- Recovery forecast + drift flag
- Clinician dashboard
- LLM explanation of measured results (NIM + NeMo Guardrails)
- Showcase setup: online demo on any camera device, NVIDIA parts served from the cloud (NIM, Riva)
- **Gate:** NVIDIA Inception showcase demo

## Phase 3 — Simulation depth

- Warp/Newton musculoskeletal sim, PhysicsNeMo surrogate, joint-load estimates
- What-if replay; OpenUSD twin with glTF/USDZ export
- Synthetic data loop (Replicator, Cosmos) training our own pose model with TAO, replacing the existing one, and retraining the compensation model
- GPU jobs on DGX Cloud Lepton
- **Gate:** physio pilot with real patients

## Phase 4 — Clinic and edge

- Jetson clinic box (DeepStream, multi-camera)
- MHRA / UKCA pathway, clinical validation
- New domains: sport, neuro rehab, occupational health, clinical trial endpoints
