# Phase 10A Demo Verification Report

## Executive status

**PASS WITH DOCUMENTED RISKS**

Phase 10A local demo automation, health verification, and real screenshot capture completed successfully on the core profile. Documented risks from Phase 9 remain (optional artifacts not generated, ROS2/Nav2 offline in core-only, artifact-only FL/RL panels).

## Git context

| Field | Value |
|-------|-------|
| PR | [#18](https://github.com/dannzapper-cmd/project-5/pull/18) |
| Branch | `feat/phase-10a-demo-automation` |
| Phase 10A commit | `f582f70` (initial); closeout audit may add follow-up commit |
| Base commit (PR #17) | `f8d5e1b643a122bf6197ecef9f3818f2933df841` |
| Capture timestamp (UTC) | 2026-06-09T05:47:40 |
| Machine | macOS darwin 25.5.0, Docker Compose local, arm64 |

## Commands run

```bash
git fetch origin && git checkout main && git pull --ff-only origin main
git checkout -b feat/phase-10a-demo-automation
docker compose --profile core config
docker compose --profile core up -d --build
ASSUME_UP=true bash scripts/demo/phase10a_verify_demo.sh
.venv/bin/pip install playwright && .venv/bin/playwright install chromium
.venv/bin/python scripts/demo/capture_phase10a_screenshots.py
.venv/bin/python scripts/scan_claims.py docs/evidence/phase10/demo/
bash scripts/verify_phase9.sh
```

## Docker compose config

`docker compose --profile core config` — **PASS**

## Services started (core)

| Service | Status |
|---------|--------|
| mosquitto | Up (healthy) |
| redis | Up (healthy) |
| api | Up (healthy) |
| sensor-generators | Up |
| edge-inference | Up (healthy) |
| dashboard | Up |

## Health endpoint table

| Endpoint | HTTP | Critical |
|----------|------|----------|
| `/health` | 200 | Yes |
| `/health/live` | 200 | Yes |
| `/health/ready` | 200 | Yes |
| `/status/services` | 200 | Yes |
| `/telemetry/status` | 200 | Yes |
| `/model-scores/status` | 200 | Yes |
| `/mission/status` | 200 | No |
| `/api/v1/twin/status` | 200 | No |
| `/api/v1/nav-slam/status` | 200 | No |
| `/metrics` | 200 | No |
| `/openapi.json` | 200 | No |
| Dashboard `/` | 200 | Yes |

Sample telemetry at capture: `received_events` ≈ 195+, `model_scores_received` ≈ 39+.

## Dashboard availability

- URL: http://localhost:3000/
- WebSocket channels connect when browser loads dashboard
- Live sensor and model score counters increment during warm-up

## Screenshot capture result

**8/8 PASS** — saved to:

- `docs/evidence/phase10/demo/screenshots/20260609-054740/`
- `docs/evidence/phase10/demo/screenshots/latest/`

## Bugs found

1. No Node.js on capture host — `npm` unavailable for `.mjs` script path.
2. Verify script `docker compose ps` failed under sandboxed curl-only run (permission denied on docker.sock) — non-blocking when health curls pass.

## Bugs fixed

1. Added `data-testid` attributes to dashboard sections for stable Playwright selectors.
2. Added Python Playwright capture script (`capture_phase10a_screenshots.py`) as primary path when Node is absent.
3. Added `scripts/demo/phase10a_verify_demo.sh` with `ASSUME_UP` flag and evidence log output.

## Bugs deferred

1. Dashboard `status/services` reports dashboard as `inactive` (expected — static file server not probed by API).
2. Mission scenario runner not executed during capture (live telemetry sufficient).
3. ROS2/Nav2/SLAM live screenshots require `ros2-nav-slam` profile — documented as offline/compose-validated only.
4. IMU model score card may show `—` in section crop if no IMU score at capture instant (EMG scores present).

## Closeout audit (final)

- PNG validation: 8/8 PASS via `scripts/demo/validate_phase10a_screenshots.py` (section crops; not full-page).
- Visual review: performed on committed screenshots — loaded UI, live counters, synthetic disclaimers visible; screenshot 07 shows **MiniLab — offline** honestly.
- `latest/` byte-identical to `20260609-054740/`.
- CI smoke initially failed on ruff lint in `capture_phase10a_screenshots.py` — fixed in closeout commit.
- Full test suite: **not run**. Ran `make lint`, `verify_phase9.sh`, `tests/phase9/test_scan_claims.py` only.

## Claim scan result

- `scripts/scan_claims.py docs/evidence/phase10/demo/` — **PASS**
- `bash scripts/verify_phase9.sh` — **PASS** (evidence index 67 items, 3 not_generated)

## Runtime artifact hygiene

- No new tracked `artifacts/phase8/phase8_scenario_*.json` files committed.
- Screenshot PNGs committed under `docs/evidence/phase10/demo/` per evidence policy.

## Risks carried into Phase 10B

- ROS2/Nav2/SLAM not live in core demo screenshots (offline panel only).
- FL/RL/MLOps panels artifact-only unless on-demand scripts run.
- ONNX models gitignored — fresh clone requires `make models-generate`.
- Playwright Chromium download required once per machine.
- No video script in repo by design — manual screen recording recommended outside repository.

## Demo recording readiness

The demo path is ready for manual screen recording. Recommended recording flow should be handled **outside the repository**. No video script or shot list was committed by design.

## Recommendation

**Ready for Phase 10B** — portfolio README, case study, and release packaging can proceed using this evidence set. Phase 10B should not re-capture fake screenshots; re-run capture script after any dashboard changes.
