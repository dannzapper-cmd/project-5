# Docker Compose Profiles

AXON uses profiles to prevent all systems from running simultaneously. Activate only what the current development phase requires.

## Profile Summary

| Profile | Purpose | Activate When |
|---------|---------|---------------|
| `core` | API, dashboard placeholder, Redis, Mosquitto | Phase 0–1 local dev |
| `obs` | Prometheus, Grafana placeholders | Phase 7 observability work |
| `learning` | MLflow placeholder | Phase 4+ MLOps work |
| `ros2` | ROS2 bridge placeholder | Phase 5 robotics integration |
| `ros2-nav-slam` | Nav2 + SLAM MiniLab placeholder | Phase 5.5 mandatory advanced |
| `sim` | Simulation orchestrator placeholder | Phase 1+ sensor simulation |
| `llm` | LLM copilot placeholder (optional) | Phase 3+ agent copilot experiments |
| `full` | All services (staged union) | Integration demos only |

## Profile Details

### `core`

- **Purpose:** Minimal runnable stack for API and infrastructure contracts
- **Services:** `api`, `dashboard`, `redis`, `mosquitto`
- **When to activate:** Default for Phase 0–1 development
- **Evidence:** Health check, compose config validation, dashboard placeholder screenshot
- **Do not run by default:** MLflow, ROS2, full observability stack

### `obs`

- **Purpose:** Metrics and dashboards
- **Future services:** Prometheus (minimal config in Phase 0), Grafana (Phase 7)
- **When to activate:** Observability phase or debugging metrics pipelines
- **Evidence:** Prometheus targets, Grafana dashboard screenshots, OTel traces
- **Do not run by default:** During early telemetry-only development

### `learning`

- **Purpose:** MLOps tracking and training loops
- **Future services:** MLflow tracking server, training workers
- **When to activate:** Phase 4+ model training and experiment tracking
- **Evidence:** MLflow run screenshots, model cards
- **Do not run by default:** During Phase 0–3 work

### `ros2`

- **Purpose:** ROS2 thin adapter bridge
- **Future services:** `ros2-bridge` node container
- **When to activate:** Phase 5 digital twin + robotics integration
- **Evidence:** ROS2 topic/service screenshots
- **Do not run by default:** Before Phase 5

### `ros2-nav-slam`

- **Purpose:** Mandatory advanced Nav2 + SLAM MiniLab
- **Future services:** Nav2 stack, SLAM toolbox, simulated robot
- **When to activate:** Phase 5.5 (required advanced phase)
- **Evidence:** Navigation demo video, map artifacts
- **Do not run by default:** Heavy; isolated lab profile only

### `sim`

- **Purpose:** Coordinated synthetic sensor simulation
- **Future services:** Sensor generator orchestrator
- **When to activate:** Phase 1+ telemetry demos
- **Evidence:** MQTT publish proof, telemetry video
- **Do not run by default:** When testing API-only changes

### `llm`

- **Purpose:** Optional LLM copilot for explanatory agent output
- **Future services:** External API client or optional local model wrapper
- **When to activate:** Phase 3+ agent experiments requiring copilot
- **Evidence:** Tool/RAG traces (not authoritative decisions)
- **Do not run by default:** No local always-on LLM required

### `full`

- **Purpose:** Staged integration of all profiles for portfolio demos
- **When to activate:** Late-phase integration only
- **Evidence:** End-to-end demo video, final case study
- **Do not run by default:** Too heavy for daily development

## Commands

```bash
# Validate core profile (Phase 0)
make compose-config

# Start core skeleton
make compose-core

# Future examples
docker compose --profile obs up
docker compose --profile ros2-nav-slam up
```
