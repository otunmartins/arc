# Security, privacy and compliance — KINETIQ

KINETIQ processes health data about patients. This doc sets the rules; it is not legal advice. Confirm the regulatory route with a regulatory specialist before clinical use.

## Principles

1. **Data minimisation:** no video, no images of patients, keypoints only.
2. **Purpose limitation:** care data is used for care. Training reuse needs separate, explicit research consent.
3. **UK/EU residency** for all patient data and backups.
4. **Clinician as decision-maker:** the product supports, never replaces, clinical judgement.
5. **Least privilege** everywhere: RLS, scoped API roles, short-lived signed URLs.

## UK GDPR

- Lawful basis and special-category condition documented in the DPIA before pilot.
- **DPIA** required (health data, new technology, potentially vulnerable users).
- Privacy notice and consent flows versioned (`consents.document_version`).
- Data subject rights: access (export job), rectification, erasure (account deletion), withdrawal of research consent.
- Processor agreements (DPAs) with: Neon, DigitalOcean, NVIDIA (hosted NIM/Riva), Sentry, Logfire.
- Records of processing maintained.
- ICO registration for Algonix AI Ltd.

## Medical device regulation (MHRA)

- The **consumer Movement Twin scan** is positioned as general wellness; copy must avoid diagnostic or treatment claims.
- **KINETIQ Rehab** likely qualifies as software as a medical device once it assesses a condition or adapts treatment. Plan for UKCA marking before making clinical claims; until then, run pilots under appropriate research or evaluation arrangements with clinicians in control.
- Maintain from day one: intended-purpose statement, risk management file (ISO 14971 approach), software lifecycle records (IEC 62304 approach), clinical evaluation plan, post-market surveillance plan.
- NHS DTAC and DSPT become relevant if selling into NHS organisations.

## Product wording rules

| Do | Don't |
| --- | --- |
| "Estimated knee bend: 95°" | "Your knee is damaged" |
| "Your recovery is behind the expected curve; your physio has been notified" | "Your recovery has failed" |
| "Stop if you feel sharp pain and tell your physio" | Any instruction outside the clinician's programme |
| "Estimate", "measured", "compared with" | "Diagnosis", "detects injury", "medical-grade" |

LLM outputs inherit these rules via the system prompt and guardrails.

## Security controls

| Area | Control |
| --- | --- |
| Transport | TLS 1.2+ everywhere; HSTS on web |
| Auth | Self-hosted Better Auth, kept patched; MFA for clinicians and admins; short JWT lifetime; signing keys rotated |
| Authorisation | API checks + Postgres RLS (defence in depth) |
| Storage | Private buckets, SSE, pre-signed URLs ≤ 15 min |
| Secrets | Environment secrets in DigitalOcean / CI; never in the repo |
| Database | Separate roles for API, workers, migrations; no superuser in apps |
| Logging | No health values, keypoints or identifiers in logs or traces |
| Audit | `audit_log` for reads/writes of patient data and all exports |
| Dependencies | Automated updates and vulnerability scanning in CI |
| GPU jobs | Run with scoped storage credentials; machines destroyed after each job |
| Backups | Neon point-in-time restore; storage versioning on critical buckets |
| Incidents | Breach response plan; ICO notification within 72 hours where required |

## AI-specific risks

| Risk | Mitigation |
| --- | --- |
| Pose errors on unusual bodies, clothing, lighting | Synthetic data diversity, quality score gating, low-confidence scans flagged not scored |
| LLM invents numbers or diagnoses | Structured input only, guardrail number check, templated fallback |
| Forecast over-confidence | Calibrated intervals, wording as "expected range", clinician review of drift flags |
| Unsafe adaptation | Adaptation only within clinician-set limits; pain reports pause progression |
| Bias across populations | Evaluate accuracy by age band, sex and body size; record in model cards |
