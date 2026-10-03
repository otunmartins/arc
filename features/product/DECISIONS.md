# Decisions — KINETIQ

Architecture decision log. Newest first. Add a row for every decision that changes stack, data handling or scope.

| # | Date | Decision | Why | Alternatives considered |
| --- | --- | --- | --- | --- |
| 020 | 2026-10-03 | Pose model through the showcase is an existing open model: TensorRT-accelerated on the showcase rig, mobile runtimes on phones. Our own TAO-trained model moves to Phase 3. Refines 008 | No labelled training data yet, so a self-trained model would be worse than existing ones; the keypoint contract lets the model be swapped later without downstream changes | TAO-trained model for the showcase (weeks of data collection and training; TAO support for trainable 3D body pose still to be verified) |
| 019 | 2026-10-03 | Object storage on DigitalOcean Spaces (UK/EU region) | Same provider, network and data processing agreement as the API and workers; S3-compatible, so a later move is a config change | Cloudflare R2 (no egress fees, but a second provider holding health data; keypoint files are small, so egress is minor) |
| 018 | 2026-10-03 | Working assumption for the first condition: post-ACL reconstruction. Conditions named in these docs are examples, not a shortlist; the final condition and its test battery are chosen with the advising physiotherapists | Surgery date gives a clear time zero and an expected recovery trajectory, which the forecast and drift flag need; knee ROM, extension deficit and knee valgus are already core metrics | Knee osteoarthritis, as one other example (larger population and a good match for sit-to-stand and TUG, but no time zero and no recovery curve to forecast); other conditions not yet assessed |
| 017 | 2026-10-03 | Self-hosted Better Auth (`services/auth`, small Node service) storing users and sessions in Neon; issues JWTs that FastAPI verifies via JWKS | Free; documented Expo (iOS, Android, web) integration and two-factor plugin; identity data stays in our own London database | Clerk (paid, third party holds identities); Neon Auth (managed Better Auth; docs cover neither React Native nor MFA); Auth.js (maintenance mode, web only) |
| 016 | 2026-10-03 | GPU jobs as portable containers; DigitalOcean GPU Droplets (create-run-destroy) now, DGX Cloud Lepton Batch Jobs for heavy work and showcase | Pay only while jobs run; familiar platform; NVIDIA cloud strengthens Inception story | Modal (good fit, new platform, lock-in); always-on GPU (≈$547/month idle) |
| 015 | 2026-10-03 | API and CPU workers on DigitalOcean (LON1) | Existing experience, predictable cost | Fly.io, Render, AWS |
| 014 | 2026-10-03 | Postgres-backed job queue (Procrastinate) | No Redis to operate | Celery + Redis, arq |
| 013 | 2026-10-03 | Neon Postgres (London) as system of record | Managed Postgres, branching for dev/CI, UK residency | Supabase, DO Managed Postgres |
| 012 | 2026-10-03 | FastAPI + Pydantic v2 + async SQLAlchemy 2.0; Python for all backend and ML | Typed, fast, same language as ML stack | Django, Node |
| 011 | 2026-10-03 | TS client generated from OpenAPI | Frontend and backend cannot drift | Hand-written client |
| 010 | 2026-10-03 | Keypoints and twin assets in object storage, pointers in Postgres | Keeps DB small and fast | Arrays in Postgres |
| 009 | 2026-10-03 | Expo (React Native) for iOS, Android and web from one codebase | One codebase; platform splits only for camera, pose, audio, 3D | Separate native apps, web-only PWA |
| 008 | 2026-10-03 | TensorRT only on NVIDIA hardware; phones run TFLite/Core ML/ONNX exports of TAO-trained models | TensorRT does not run on phones | — |
| 007 | 2026-10-03 | Movement Twin stored as OpenUSD; glTF/USDZ exports for the app | Aligns with NVIDIA digital twin ecosystem; USDZ enables iPhone AR | Custom JSON only |
| 006 | 2026-10-03 | Real-time joint loads via PhysicsNeMo surrogate trained on Warp/Newton musculoskeletal sim | NVIDIA real-time digital twin pattern; milliseconds per scan | Full sim per scan |
| 005 | 2026-10-03 | Recovery forecasting with population NLME models | Pharmacometrics methods applied to recovery; core differentiator | Per-patient regression only |
| 004 | 2026-10-03 | LLM explains stored measurements only; guardrail checks numbers | Safety; no invented values or diagnoses | Free-form chat |
| 003 | 2026-10-03 | Video never leaves the device | Privacy, UK GDPR minimisation, NHS acceptability | Cloud video processing |
| 002 | 2026-10-03 | First application: clinician-supervised rehab for one condition | Focus; measurable outcomes; regulatory clarity | Multi-condition, consumer-first |
| 001 | 2026-10-03 | Build KINETIQ as the NVIDIA Inception showcase | Strong fit with NVIDIA perception, simulation and digital twin stack | NeuroSim as showcase |

## Pending

The single list of open decisions; other docs link here.

- [ ] Final first condition and test battery (working assumption: post-ACL reconstruction, decision 018)
- [ ] Which existing pose model to use (must give 3D keypoints mappable to `kq-skel-v1`, convert to TensorRT and run on phones and web; licence must allow commercial use)
- [ ] Whether TAO offers a trainable 3D body pose model; if not, the Phase 3 training route (decision 020)
- [ ] Advising physiotherapists (one or two)
- [ ] MHRA classification route for the rehab application
