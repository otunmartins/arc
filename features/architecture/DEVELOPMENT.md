# Development — KINETIQ

Local setup, environment variables, testing and CI. Commands for the full target layout are in [CLAUDE.md](../../CLAUDE.md#commands); this doc covers what you need to get running and what exists today.

## What exists today

| Part | State |
| --- | --- |
| `apps/mobile` | Expo SDK 57 scaffold (default template: Expo Router, TypeScript, routes in `src/app/`). |
| Repo root | pnpm workspace (`pnpm-workspace.yaml`, root `package.json` with shortcut scripts). |
| Repo root (Python) | `uv` workspace (`pyproject.toml`, `uv.lock`, Python 3.12) with ruff, pyright and pytest. |
| `packages/contracts` | `kq-skel-v1` skeleton, scan header schema, `.kqk.gz` encoder/decoder in Python and TypeScript, with tests. Measurement schemas not yet added. |
| `packages/kinetiq-core` | Preprocessing (confidence mask, resample, gap fill, smoothing), capture quality, joint angles, the first seven metrics and a synthetic pose generator, with known-answer tests. Status per metric is in [DATA.md](../data/DATA.md#implementation-status-kinetiq-core-010). |
| Pose spike (web) | The app's Scan tab runs BlazePose on the webcam in the browser, maps it to `kq-skel-v1` and saves a `.kqk.gz` file plus the raw model output as JSON. iOS and Android capture is not built. |
| `tools/inspect_scan.py` | Prints capture quality and metrics for a `.kqk.gz` file. |
| `services/`, `infra/` | Not started. Build order: database → API → workers → app. |

## Prerequisites

- Node 24 and pnpm 12
- `uv` (Python 3.12 is installed by `uv` when the backend lands)
- For native builds: Android Studio (Android) or Xcode on macOS (iOS); or EAS Build in the cloud

## App

Run from the repo root:

```bash
pnpm install
pnpm mobile                    # Expo dev server
pnpm web                       # run in the browser
pnpm --filter mobile android   # run on Android
pnpm --filter mobile ios       # run on iOS (macOS only)
pnpm lint
pnpm typecheck
pnpm --filter mobile exec expo export -p web   # static web build into apps/mobile/dist
```

- Add dependencies with `pnpm --filter mobile exec expo install <package>` so versions match the SDK.
- Expo ships breaking changes each SDK release; check the versioned docs (`https://docs.expo.dev/versions/v57.0.0/`) before using an Expo API.
- Camera and on-device pose need native modules, so the app needs a development build (`npx expo run:android|ios` or `eas build --profile development`) rather than Expo Go.
- Never edit generated `ios/` or `android/` folders by hand; configure native behaviour in `app.json` and config plugins.

## Trying a scan end to end

```bash
pnpm web                                             # open the Scan tab, start the camera, record, stop
uv run python tools/inspect_scan.py path/to/scan-….kqk.gz
```

- The browser downloads two files per recording: the `.kqk.gz` scan and a `.raw.json` with the model's image-plane and world landmarks per frame, kept for the validation study.
- The pose library, its wasm files and the model are loaded from public CDNs (jsDelivr and Google) at run time; the browser fetches them, the video does not leave the page. Self-hosting them is a to-do before any real use.
- Metro cannot bundle `@mediapipe/tasks-vision`, so the app loads it as a browser module at run time and the npm package is installed for its types only. Keep the version in `apps/mobile/src/pose/web-pose-session.ts` in step with `package.json`.
- Browsers do not report gravity, so web scans have `camera.gravity` set to `null`.

## Python and contracts

Run from the repo root:

```bash
uv sync                                       # create .venv and install the workspace
uv run pytest                                 # Python tests
uv run ruff check . && uv run ruff format .   # lint + format
uv run pyright                                # type check (strict on contracts and kinetiq-core)
pnpm test                                     # TypeScript tests
uv run python packages/contracts/build.py     # after changing the Pydantic models
```

The Pydantic models in `packages/contracts/src` are the source of truth. `build.py` regenerates `schema/scan-header.schema.json`, `ts/src/skeleton.generated.ts` and `ts/src/header.generated.ts`; a Python test fails if the first two are stale.

To refresh the cross-language fixtures after a format change, run each suite once with `UPDATE_FIXTURES=1`.

## Environment variables

Names other than `EXPO_PUBLIC_POSE_ENDPOINT` are proposed and become fixed when the code that reads them is written. Secrets live in `.env` files (gitignored) locally and in DigitalOcean / CI secrets elsewhere.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `EXPO_PUBLIC_API_URL` | App | Base URL of the API |
| `EXPO_PUBLIC_POSE_ENDPOINT` | App (web, showcase rig) | Local TensorRT pose server |
| `DATABASE_URL` | API, workers | Neon pooled connection string |
| `DATABASE_URL_DIRECT` | Alembic | Neon direct connection string |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | API, workers | Object storage |
| `EXPO_PUBLIC_AUTH_URL` | App | Base URL of the auth service |
| `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL` | Auth service | Signing secret and public base URL |
| `AUTH_JWKS_URL`, `AUTH_ISSUER` | API | Verifying JWTs issued by the auth service |
| `NVIDIA_API_KEY` | API | Hosted NIM and Riva |
| `SENTRY_DSN`, `LOGFIRE_TOKEN` | API, workers, app | Observability |

Anything prefixed `EXPO_PUBLIC_` is bundled into the app and visible to users; never put a secret there.

## Testing

Rules are in the shared [conventions](../../CLAUDE.md#conventions). In practice:

- `kinetiq-core`: unit tests with known-answer fixtures (synthetic keypoints with known angles).
- API: integration tests against a Neon branch or local Postgres.
- App: lint and typecheck on every change; run on web plus at least one native platform before merging UI work.

## CI (planned)

1. Python: `ruff check`, `ruff format --check`, `pyright`, `pytest`.
2. Schema changes: create a Neon branch for the PR, run migrations, run the test suite against it (see [DATABASE.md](../data/DATABASE.md#migrations-and-branching)).
3. App: `lint`, `typecheck`, web export build.
4. Contracts: regenerate Pydantic + TS types and the API client; fail if the output differs from what is committed.
5. Dependency updates and vulnerability scanning.
