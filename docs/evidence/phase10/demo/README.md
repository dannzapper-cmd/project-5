# Phase 10A — Visual Demo Automation Evidence

Local-only, synthetic-only screenshot evidence and reproducibility artifacts for Phase 10A.

**Not Phase 10B:** no final README rewrite, portfolio copy, release tags, or video scripts live in this folder.

## Contents

| Artifact | Purpose |
|----------|---------|
| [runbook-phase10a.md](runbook-phase10a.md) | Reproducible demo commands |
| [screenshot-index.md](screenshot-index.md) | Screenshot catalog with provenance |
| [demo-verification-report.md](demo-verification-report.md) | Executive verification status |
| [commands-summary.md](commands-summary.md) | Latest verification run summary |
| `screenshots/latest/` | Most recent capture set |
| `screenshots/<timestamp>/` | Timestamped capture runs |

## Quick start

```bash
# From repo root — ensure ONNX models exist locally
make models-generate

# Start core stack
docker compose --profile core up -d --build

# Verify health
bash scripts/demo/phase10a_verify_demo.sh

# Capture screenshots (Python path — recommended)
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python scripts/demo/capture_phase10a_screenshots.py

# Alternate if Node.js is installed:
# cd scripts/demo && npm install && npm run install-browsers && npm run capture
```

## Claims boundary

Synthetic biomedical-inspired signals only. Simulated rehab robot operations. Not a medical device. No clinical diagnosis or treatment claims. ROS2/Nav2/SLAM is compose-validated unless the `ros2-nav-slam` profile is explicitly started.
