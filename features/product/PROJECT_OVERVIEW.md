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

Clinician-supervised home rehabilitation for **one condition**: post-ACL reconstruction, chosen provisionally (decisions 018 and 023). Other conditions named in these docs, such as knee osteoarthritis, are examples of where the platform could go next.

MVP features:

1. Guided scan with a hands-free voice coach (Riva)
2. Real-time compensation detection with spoken correction
3. Auto-scored tests from the `rehab-knee` battery (below)
4. Adaptive sessions within physio-set limits (fatigue and voice-reported pain)
5. Recovery forecast: measured vs expected curve, drift flag
6. Clinician dashboard: adherence, movement quality, tests, joint-load estimates, forecast

### Test battery `rehab-knee` v1 (provisional)

Set without a clinical advisor (see [DECISIONS.md](DECISIONS.md), decisions 022 and 023); a registered physiotherapist reviews it before any pilot with patients. The clinician enables each test for a patient when it is appropriate for their stage.

| Test | Camera | What is reported | Typical stage |
| --- | --- | --- | --- |
| Heel-slide knee flexion (long sitting) | Side-on, operated leg nearest | Peak knee flexion; knee extension as a low-precision estimate | From the first weeks |
| Squat to comfortable depth | Side-on | Peak knee and hip flexion, forward trunk angle | Once the clinician allows loaded bending |
| 30-second sit-to-stand | Side-on | Number of full stands | Early and mid rehab; expected to stop discriminating later |
| Single-leg balance, up to 30 s | Front-on | Time held, each leg | Strength and control stage |
| Single-leg squat | Front-on | Frontal knee projection angle and trunk lean, each leg | Strength and control stage |

Not in this battery: Timed Up and Go (kept in the metric catalogue for other conditions) and hop tests (clinic-only; unsupervised landings are a safety risk).

Two limits the app and dashboard must state:

- **Knee extension is not measured precisely enough to act on.** A loss of 3–5° matters clinically after ACL reconstruction, which is below what a single camera resolves. The clinician checks extension in person.
- **The frontal knee projection angle is a 2D proxy for knee valgus**, not a measure of true valgus. It is repeatable enough to follow change in one patient (differences under about 8° are within measurement noise).

Provisional pain rule for adaptive sessions: a report of 5/10 or more, or any sharp pain, stops the set and notifies the clinician; 3–4/10 holds progression. The clinician can set stricter limits per patient, never looser ones through the app.

## Showcase demo story

A patient scans → the app catches a compensation and corrects it by voice → it scores a weekly sit-to-stand → the clinician dashboard shows the forecast curve with a drift flag. Pose runs on the demo device; the voice coach (Riva), the explanation (NIM) and the GPU jobs behind the forecast and simulation run on NVIDIA in the cloud.

## Scope boundaries

In scope for MVP: one condition, one exercise battery, patient app, clinician dashboard, forecasting, compensation detection.

Out of scope for MVP: diagnosis, treatment decisions without a clinician, multi-condition support, sports performance, insurer integrations, native wearables.

## Success criteria (provisional; see decision 022)

- Knee flexion agrees with long-arm goniometry on a validation set: mean bias within ±2°, mean absolute error ≤ 5°, 95% limits of agreement within ±10° (decision 024).
- Compensation detector precision and recall reviewed and accepted by a registered physiotherapist.
- A complete showcase demo runs end to end, with its NVIDIA parts served from the cloud.
- A pilot with at least one physiotherapy practice.

## Open decisions

Tracked in one place: the Pending list in [DECISIONS.md](DECISIONS.md#pending), which also logs decisions already made. See [ROADMAP.md](ROADMAP.md) for phases.
