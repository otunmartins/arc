# AI infrastructure — KINETIQ

How models are trained, served, simulated and governed. Every layer is built on NVIDIA tooling; phones run mobile exports of NVIDIA-trained models.

## Model and simulation inventory

| ID | Component | Purpose | Tech | Runs where |
| --- | --- | --- | --- | --- |
| M1 | Pose model | Video → 3D keypoints | TAO Toolkit (3D body pose), fine-tuned on real + synthetic data | Phone: TFLite / Core ML / ONNX export · Web: ONNX Runtime Web or MediaPipe · NVIDIA HW: TensorRT |
| M2 | Rep segmenter | Split a set into reps, phases | Small temporal model (1D CNN / transformer) on keypoint sequences, PyTorch | On device (live) + worker (authoritative) |
| M3 | Compensation classifier | Detect valgus, hip hike, trunk lean, shrug, etc. | Rule features from `kinetiq-core` + temporal classifier, PyTorch | On device (live cue) + worker (recorded event) |
| C1 | Biomechanics engine | Joint angles, ROM, symmetry, stability, velocity, variability | Deterministic code in `kinetiq-core` (NumPy/SciPy) | Worker, API, notebooks |
| F1 | Recovery forecaster | Expected curve per patient, drift score | Bayesian nonlinear mixed-effects (NumPyro on JAX, CUDA when available) | CPU worker per patient; GPU for population fits |
| S1 | Musculoskeletal sim | Joint loads, muscle demand from motion | NVIDIA Warp / Newton (MuJoCo Warp), MyoSuite- or OpenSim-derived models | GPU batch |
| S2 | Physics-AI surrogate | Real-time joint-load prediction | PhysicsNeMo trained on S1 outputs | Worker / API (CPU or GPU) |
| S3 | Synthetic data generator | Labelled movement video across bodies, cameras, lighting | Omniverse Replicator, OpenUSD avatars, Cosmos Transfer | GPU batch (RTX-class) |
| S4 | What-if replay | Corrected-movement and programme projections | S1 + Omniverse rendering; glTF/USDZ export | GPU batch |
| L1 | Explanation LLM | Plain-language explanation of measured data | NVIDIA NIM-hosted LLM (e.g. Nemotron) + NeMo Guardrails | NVIDIA hosted endpoint |
| V1 | Voice coach | ASR + TTS for hands-free sessions | NVIDIA Riva | NVIDIA hosted endpoint via API proxy |

## Pipelines

### Training pipeline (M1–M3)

```
real capture (consented)  ─┐
                           ├─► dataset build (object storage, versioned manifest)
synthetic (S3)            ─┘          │
                                      ▼
                         TAO / PyTorch training (GPU batch job)
                                      │
                         evaluation gates (see below)
                                      │
                 export: ONNX → TFLite / Core ML · TensorRT engine (RTX, Jetson)
                                      │
                         model_registry row + artefacts in storage
                                      │
                         app release / OTA model download (pinned version)
```

### Online inference (per scan)

1. M1 on device → keypoints.
2. M2 + M3 lite on device → live cues.
3. Worker re-runs M2 + M3 authoritatively on the uploaded sequence.
4. C1 computes metrics; S2 estimates joint loads; F1 refits forecast.
5. L1 explains on request using only stored values.

### Simulation pipeline (S1 → S2)

1. Sample motions from the movement library (real + synthetic) across body models.
2. Run S1 at scale on GPU → (motion, body params) → joint loads.
3. Train S2 on those pairs with PhysicsNeMo; validate against held-out S1 runs.
4. Register S2; workers call S2 per scan (milliseconds) instead of running S1.

### Synthetic data pipeline (S3)

1. OpenUSD avatar library with varied body shapes, ages, clothing.
2. Motion retargeting: correct and compensated variants of each exercise.
3. Replicator randomises camera pose, lens, lighting, background, occlusion.
4. Cosmos Transfer adds photoreal variation.
5. Output: video + ground-truth 3D keypoints + compensation labels → dataset manifest.

## GPU compute

| Stage | Where | Billing behaviour |
| --- | --- | --- |
| MVP batch jobs, GPU dev | DigitalOcean GPU Droplet (RTX 4000 Ada, has RT cores) | Billed until destroyed; see [DEPLOYMENT.md](DEPLOYMENT.md#gpu-jobs-create--run--destroy) |
| Heavy training and sim | NVIDIA DGX Cloud Lepton Batch Jobs | Runs, then releases GPU; marketplace pricing |
| Interactive GPU dev | Lepton Dev Pods or NVIDIA Brev | Stop when done |
| Showcase | RTX laptop or Jetson Orin | Owned hardware |

Rules:

- Every GPU job is a container: `infra/docker/gpu-job.Dockerfile` based on an NGC image.
- Inputs and outputs live in object storage; nothing persists on the GPU machine.
- The launcher (`infra/gpu/run_job.py`) creates, runs and destroys the machine; its steps, billing and cost guide are in [DEPLOYMENT.md](DEPLOYMENT.md#gpu-jobs-create--run--destroy).
- Omniverse rendering (S3, S4) requires RTX-class GPUs (L40S, RTX Ada). A100/H100 lack RT cores.

## Job types

| Job | Queue | Compute | Trigger |
| --- | --- | --- | --- |
| `scan.process` | `cpu` | CPU | Scan upload complete |
| `twin.update` | `cpu` | CPU | After `scan.process` |
| `forecast.refit` | `cpu` | CPU | After `scan.process`; nightly sweep |
| `summary.generate` | `cpu` | NIM call | On request |
| `sim.run` | `gpu` | GPU | Batch, operator |
| `surrogate.train` | `gpu` | GPU | Batch, operator |
| `synthetic.generate` | `gpu` | RTX GPU | Batch, operator |
| `model.train` | `gpu` | GPU | Batch, operator |

## Evaluation gates (proposed thresholds to confirm with clinical advisors)

| Model | Gate before release |
| --- | --- |
| M1 pose | Joint-angle error vs lab motion capture / goniometry within agreed tolerance on held-out real data; no regression vs current version |
| M3 compensation | Precision and recall per compensation on physio-labelled real data; reviewed by advising physiotherapists |
| F1 forecaster | Calibration of predictive intervals on held-out patients; drift flag false-alarm rate reviewed |
| S2 surrogate | Error vs held-out S1 runs within agreed tolerance across body types |
| L1 explanations | Guardrail test suite: zero invented numbers, zero diagnoses, every number traceable to input |

Every release records metrics in `model_registry.metrics`.

## LLM rules (L1)

- Input is a JSON bundle of measurements, tests, forecast and their units. No free text from the patient is passed without sanitisation.
- The system prompt forbids diagnosis, treatment instructions beyond the prescribed programme, and any number not in the input.
- NeMo Guardrails output check: every number in the response must appear in the input bundle; otherwise regenerate or fall back to a templated summary.
- Responses store `model_name`, `model_version`, `prompt_version` and input hash.

## Versioning and reproducibility

- Model artefacts and dataset manifests are versioned in object storage (paths in [DATA.md](../data/DATA.md#object-storage-layout)); one `model_registry` row per model version.
- Dataset manifests are immutable and list every file with its hash.
- Apps pin model versions; the API rejects keypoints from unsupported skeleton or model versions.
