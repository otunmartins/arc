# KINETIQ documentation

Start with [CLAUDE.md](../CLAUDE.md) for the golden rules, stack and conventions, then go to the doc that matches the task.

## Product

| Doc | Covers |
| --- | --- |
| [PROJECT_OVERVIEW.md](product/PROJECT_OVERVIEW.md) | What KINETIQ is, users, MVP scope, success criteria |
| [ROADMAP.md](product/ROADMAP.md) | Phases and their gates |
| [DECISIONS.md](product/DECISIONS.md) | Decision log and pending decisions |

## Architecture

| Doc | Covers |
| --- | --- |
| [ARCHITECTURE.md](architecture/ARCHITECTURE.md) | System overview, components, key flows, targets |
| [AI_INFRASTRUCTURE.md](architecture/AI_INFRASTRUCTURE.md) | Models, pipelines, simulation, GPU jobs, evaluation gates |
| [API.md](architecture/API.md) | REST endpoints and the live-session WebSocket protocol |
| [DEVELOPMENT.md](architecture/DEVELOPMENT.md) | Local setup, what exists today, env vars, testing, CI |
| [DEPLOYMENT.md](architecture/DEPLOYMENT.md) | Environments, hosting, GPU job lifecycle, release checklist |

## Data

| Doc | Covers |
| --- | --- |
| [DATA.md](data/DATA.md) | Keypoint contract, metric catalogue, storage layout, data lifecycle |
| [DATABASE.md](data/DATABASE.md) | Schema, row-level security, migrations, common queries |
| [SECURITY_PRIVACY_COMPLIANCE.md](data/SECURITY_PRIVACY_COMPLIANCE.md) | UK GDPR, MHRA, wording rules, security controls, AI risks |

## Keeping docs in sync

- A change to `packages/contracts` or a `kinetiq-core` metric updates [DATA.md](data/DATA.md) in the same commit.
- A change to stack, data handling or scope adds a row to [DECISIONS.md](product/DECISIONS.md).
- The OpenAPI spec is the source of truth for endpoints; [API.md](architecture/API.md) is the readable summary.
