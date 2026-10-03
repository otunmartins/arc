# Deployment — KINETIQ

## Environments

| Env | Database | API | Storage bucket | Notes |
| --- | --- | --- | --- | --- |
| dev | Neon branch per developer | local | `kinetiq-dev` | |
| preview | Neon branch per PR | DO App Platform preview (optional) | `kinetiq-dev` | Auto-created in CI |
| prod | Neon main branch (London) | DigitalOcean LON1 | `kinetiq-prod` | |

## Services

| Service | Platform | How |
| --- | --- | --- |
| API | DigitalOcean App Platform (or Droplet + Docker) | Container from `infra/docker/api.Dockerfile`, health check `/readyz` |
| Auth | DigitalOcean (LON1), same platform as the API | Node container running Better Auth; pooled Neon connection |
| CPU workers | DigitalOcean Droplet | Container running the Procrastinate worker (`cpu` queue) |
| Database | Neon | Pooled string for apps, direct string for migrations |
| Object storage | DigitalOcean Spaces | Private buckets, CORS limited to app origins |
| Web app | `expo export -p web` → static hosting (DO App Platform static site or Vercel) | |
| iOS / Android | EAS Build + EAS Submit | Store releases; JS updates via EAS Update where allowed |
| LLM / voice | NVIDIA hosted NIM and Riva | API keys in secrets |

## GPU jobs: create → run → destroy

GPU Droplets bill per second (5-minute minimum) from creation until **destroyed**; powering off does not stop billing. Never leave a GPU Droplet idle.

`infra/gpu/run_job.py` (DigitalOcean) does:

1. Create a GPU Droplet (RTX 4000 Ada by default) from a base image with Docker and NVIDIA drivers, tagged `kinetiq-gpu-job`, with a cloud-init script.
2. Cloud-init pulls `kinetiq-gpu-job:<tag>` from the registry and runs `python -m workers.gpu <job_type> --job-id <id>`.
3. The job reads inputs from storage, writes outputs to `sim/{job_id}/` or `models/…`, updates Postgres, and exits.
4. The launcher polls job status in Postgres; on success, failure or **hard timeout**, it destroys the Droplet in a `finally` block.
5. A nightly safety sweep destroys any Droplet tagged `kinetiq-gpu-job` older than its timeout.

Set a DigitalOcean **billing alert** at your monthly GPU budget.

Cost guide at $0.76/hr (RTX 4000 Ada): two 4-hour sessions a week ≈ $27/month; left running all month ≈ $547.

### Moving GPU jobs to DGX Cloud Lepton

The same container image runs as a Lepton **Batch Job**: the launcher submits the job with the image, command, GPU type and region (UK/EU), and Lepton releases the GPU when it finishes. Only `infra/gpu/` changes; job code does not. Confirm RTX-class GPUs for Omniverse jobs.

## Showcase rig

- RTX laptop or Jetson Orin, webcam.
- Local TensorRT pose server on `localhost`; web build pointed at it via `EXPO_PUBLIC_POSE_ENDPOINT`.
- Local API + local Postgres (or a dedicated Neon branch) with demo data; works offline except NIM/Riva (cache demo responses as fallback).

## Release checklist

- [ ] Migrations backward compatible; run before API deploy
- [ ] Model versions pinned; registry status `approved`
- [ ] Sentry release created; source maps uploaded
- [ ] Smoke test: scan → results → forecast → summary in the preview environment
- [ ] GPU sweep job active; billing alert set
