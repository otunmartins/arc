# KINETIQ

AI movement intelligence platform: a phone or webcam captures movement, on-device pose estimation turns it into 3D keypoints, and the platform builds a Movement Twin of each person. First application: clinician-supervised musculoskeletal rehabilitation.

## Getting started

Requires Node 24 and pnpm 12.

```bash
pnpm install
pnpm web          # app in the browser
pnpm mobile       # Expo dev server (iOS / Android)
pnpm lint
pnpm typecheck
```

## Layout

| Path | What |
| --- | --- |
| [apps/mobile](apps/mobile) | Expo (React Native) app for iOS, Android and web |
| [features](features/README.md) | Project documentation |
| [CLAUDE.md](CLAUDE.md) | Golden rules, stack and conventions |

Backend services, shared packages and infrastructure are planned; see [DEVELOPMENT.md](features/architecture/DEVELOPMENT.md) for what exists today and [ROADMAP.md](features/product/ROADMAP.md) for what comes next.
