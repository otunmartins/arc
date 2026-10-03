# Project overview — KINETIQ

**Owner:** Algonix AI Ltd (Scotland) · **Status:** pre-MVP · **Purpose:** NVIDIA Inception showcase product

## One-line pitch

KINETIQ applies NVIDIA's real-time digital twin pattern to the human body: it builds a Movement Twin of each person from camera data, measures how they move, and simulates where that movement is heading.

## Problem

Camera-based fitness and rehab apps answer one question: *did the user do the exercise?* They count reps, check basic form and show past progress. Physiotherapists get self-reported adherence and no objective data between appointments. Nobody forecasts whether a patient's recovery is on track.

## What KINETIQ does differently

| Typical AI fitness / rehab app | KINETIQ |
| --- | --- |
| Counts reps, checks basic form | Detects named compensations clinicians use (knee valgus, hip hike, trunk lean, shoulder shrug) |
| Single-session scores | Longitudinal Movement Twin |
| Self-reported progress | Auto-scored validated outcome tests |
| No view of internal load | Physics-based joint-load estimates |
| Shows past progress | Forecasts the expected recovery curve and flags drift |
| Video sent to the cloud | Keypoints only; video never leaves the device |
| LLM chat bolted on | LLM explains measured numbers and cannot invent them |

## Users

| User | Needs | Surface |
| --- | --- | --- |
| Patient | Guided sessions, clear feedback, visible progress | Mobile app (iOS, Android) and web |
| Physiotherapist | Prescribe programmes, objective data, early warning on patients falling behind | Clinician dashboard (web, desktop-first) |
| Consumer (later) | "Create your Movement Twin", track mobility over time | Mobile app |

## Core concepts

- **Movement Signature:** the scored output of one scan across mobility, symmetry, stability, coordination, velocity, consistency, compensation and fatigue response.
- **Movement Twin:** the longitudinal record for one person: dated signatures, a personalised musculoskeletal body model, a fitted recovery curve, stored as an OpenUSD asset plus database rows.
- **Simulation layer:** synthetic training data, musculoskeletal simulation (joint loads), recovery trajectory forecasting (population NLME models), and what-if movement replay.

## First application: KINETIQ Rehab

Clinician-supervised home rehabilitation for **one condition**. The working assumption is post-ACL reconstruction; conditions named in these docs (ACL reconstruction, knee osteoarthritis) are examples, and the final choice is made with the advising physiotherapists.

MVP features:

1. Guided scan with a hands-free voice coach (Riva)
2. Real-time compensation detection with spoken correction
3. Auto-scored standard tests: 30-second sit-to-stand, Timed Up and Go, single-leg balance, knee range of motion
4. Adaptive sessions within physio-set limits (fatigue and voice-reported pain)
5. Recovery forecast: measured vs expected curve, drift flag
6. Clinician dashboard: adherence, movement quality, tests, joint-load estimates, forecast

## Showcase demo story

A patient scans → the app catches a compensation and corrects it by voice → it scores a weekly sit-to-stand → the clinician dashboard shows the forecast curve with a drift flag. Run on an RTX laptop or Jetson Orin with local TensorRT pose so the demo is offline-capable and genuinely NVIDIA-accelerated.

## Scope boundaries

In scope for MVP: one condition, one exercise battery, patient app, clinician dashboard, forecasting, compensation detection.

Out of scope for MVP: diagnosis, treatment decisions without a clinician, multi-condition support, sports performance, insurer integrations, native wearables.

## Success criteria (proposed, to confirm with clinical advisors)

- Joint-angle measures agree with clinician goniometry within an agreed tolerance on a validation set.
- Compensation detector precision and recall reviewed and accepted by advising physiotherapists.
- A complete showcase demo runs end to end on NVIDIA hardware without network dependency.
- A pilot with at least one physiotherapy practice.

## Open decisions

Tracked in one place: the Pending list in [DECISIONS.md](DECISIONS.md#pending), which also logs decisions already made. See [ROADMAP.md](ROADMAP.md) for phases.
