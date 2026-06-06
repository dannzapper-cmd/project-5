# Local vs Cloud Profiles

AXON defaults to **local-first** development with optional cloud/VM execution for heavy phases.

## Principles

1. **Local-first default** — daily work uses `core` profile only
2. **Cloud/VM on demand** — activate for long training, Nav2 MiniLab, or portfolio recording
3. **Heavy profiles run separately** — never require `full` for routine PRs
4. **Cost awareness** — document what each profile consumes before demos
5. **No mandatory Kubernetes** — Docker Compose profiles suffice

## What Stays Off by Default

| Component | Profile | Reason |
|-----------|---------|--------|
| MLflow | `learning` | Training not needed in Phase 0–3 |
| Grafana full stack | `obs` | Observability is Phase 7 |
| ROS2 Nav2 + SLAM | `ros2-nav-slam` | Heavy; isolated lab |
| LLM copilot | `llm` | Optional; no always-on local LLM |
| Full integration | `full` | Demo-only |

## Optional Hardware Path (Future)

| Hardware | Use Case | Phase |
|----------|----------|-------|
| ESP32 | Tiny sensor node prototype | 8 |
| Raspberry Pi | Edge gateway prototype | 8 |
| Jetson Nano | ONNX edge inference | 8 |
| Edge Impulse / TFLite Micro | TinyML path | 8 |

Physical hardware is **optional** — simulation remains the default.

## Future Cost / Hardware Report

| Profile | Environment | Estimated Cost Driver | Notes |
|---------|-------------|----------------------|-------|
| `core` | Local | Container images | Daily dev |
| `learning` | Local / VM | GPU time, storage | Phase 4+ |
| `ros2-nav-slam` | Local / VM | CPU, GPU (sim) | Phase 5.5 lab |
| `full` | Cloud VM | Combined | Portfolio demos only |

*Table to be completed in Phase 8 with measured profiles.*

## Phase 0 Note

No cost measurements yet. This document establishes policy only.
