# Roadmap — KINETIQ

The Inception showcase lands at the end of phase 2.

## Phase 1 — Core twin

- Contracts: `kq-skel-v1`, `.kqk.gz` encoder/decoder (Python + TS)
- `kinetiq-core`: QC, angles, ROM, symmetry, stability, variability
- Database + API: users, patients, sessions, scans, measurements
- App: guided scan, on-device pose with an existing open model (native + web), upload, Day 1/7/30 comparison
- **Gate:** measures agree with clinician goniometry within agreed tolerance

## Phase 2 — Rehab showcase

- Compensation detection (live cue + recorded events)
- Auto-scored tests: 30 s sit-to-stand, TUG, single-leg balance, knee ROM
- Voice coach (Riva), pain reports, adaptive sessions within limits
- Recovery forecast + drift flag
- Clinician dashboard
- LLM explanation of measured results (NIM + NeMo Guardrails)
- Showcase rig: RTX laptop / Jetson, the same pose model converted to TensorRT and run locally
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
