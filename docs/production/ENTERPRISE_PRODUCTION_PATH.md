# AXON Enterprise Production Path

*A staged, investment-heavy roadmap for hardening an AXON-like Bio-Robotics Edge Command System toward enterprise non-clinical robotics operations — without claiming current production readiness.*

---

## 1. Production path summary

AXON (Autonomous eXecution and Operations Network) is a **simulated-only, synthetic-only, local-first** command system prototype for **Simulated Rehab Robot Ops**. The repository demonstrates integrated patterns — synthetic telemetry transport, edge-like ONNX inference, safety-aware agent orchestration, digital twin visualization, observability endpoints, and an Evidence Center — within Docker Compose profiles on a single developer machine.

**AXON is not enterprise-production-ready today.** Transition to a supported enterprise operations platform requires multi-quarter engineering across security, scalability, reliability, hardware integration, operator experience, model lifecycle governance, and legal review. This is **not** a low-cost or quick configuration change.

The production path documented here:

1. Preserves AXON's **profile-based modular activation** (`core`, `obs`, `learning`, `ros2`, `ros2-nav-slam`, etc.).
2. Keeps **ROS2 / Nav2 / SLAM** as **compose-validated** and **offline in the default `core` demo** unless `ros2` or `ros2-nav-slam` profiles are explicitly started.
3. Keeps **FL / RL / MLOps** as **on-demand** and **artifact-backed** in the default UI — not always-on fleet training.
4. Uses **synthetic retraining / candidate refresh loop** language for classical model iteration — not unqualified fine-tuning claims.
5. Maintains **non-clinical** boundaries: AXON is not a medical device, not a diagnostic system, not for clinical use, and does not diagnose or treat any condition.

The path targets a **non-clinical robotics operations product** direction. A regulated or clinical-adjacent product line is a separate, exceptional program (Stage 5) and is **not** implied by the current prototype.

---

## 2. Eight enterprise hardening workstreams

Each workstream is a multi-sprint program with explicit deliverables, evidence artifacts, and go/no-go gates. None are complete in the current repository.

### Workstream 1 — Identity, access, and secrets

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| Authentication | Dev-oriented; no enterprise IdP | OIDC/SAML integration, MFA, session lifecycle |
| Authorization | Minimal role separation | RBAC/ABAC model mapped to operator actions |
| Secrets | Local `.env` variables | Vault/KMS, rotation, audit of secret access |
| Service identity | Compose-internal networking | mTLS between services, workload identity |
| Evidence | Health endpoints only | Pen-test report, access review records |

### Workstream 2 — Audit, compliance, and data governance

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| Audit trail | Partial structured JSON logs | Immutable audit store, retention tiers, legal hold |
| Data classification | Synthetic-only policy | Classification labels if real operational data added |
| Claim governance | `scripts/scan_claims.py`, disclaimers | Release-time claim gate in CI, counsel sign-off |
| Privacy | No real patient data | Consent, minimization, DLP if PII introduced |
| Evidence | Phase 9 seal, claim scanner tests | Compliance mapping doc per target market |

### Workstream 3 — Scalable event processing and persistence

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| Event buffer | Redis Streams on single node | Horizontal stream consumers, backpressure policies |
| Historical analysis | Limited retention in Redis | TSDB or data lake with tiered retention |
| Replay | JSONL replay scripts, mission scenarios | Fleet-scale replay service, access controls |
| Contracts | Pydantic event schemas | Schema registry, compatibility testing |
| Evidence | Live telemetry on `core` | Load-test reports, ingest SLO evidence |

### Workstream 4 — Reliability, SRE, and incident response

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| Health | `/health/live`, `/health/ready`, `/status/services` | Dependency SLOs, synthetic probes per site |
| Degradation | Documented optional vs required deps | Error budgets, graceful degradation runbooks |
| Alerting | No paging integration | On-call rotation, alert routing, noise controls |
| DR / HA | Single-node compose | Multi-AZ deployment, RPO/RTO targets |
| Evidence | Phase 7 reliability artifacts | Postmortem library, SLO dashboards |

### Workstream 5 — Security and supply chain

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| Network exposure | Localhost-oriented | Segmentation, WAF, egress controls |
| Vulnerability mgmt | Dev dependency tree | CI SBOM, image scanning, patch SLAs |
| Container hardening | Compose for development | Non-root images, read-only FS where possible |
| Threat modeling | Informal | STRIDE review, annual pentest |
| Evidence | `make compose-config` validation | SBOM artifacts, scan reports |

### Workstream 6 — ML lifecycle and model operations

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| Training | On-demand MLOps pipeline; synthetic retraining / candidate refresh loop for classical models | Scheduled retrain jobs with approval gates |
| Registry | Local ONNX artifacts via `make models-generate` | Versioned model registry, promotion workflow |
| FL / RL | Flower FedAvg, Gymnasium PPO — `learning` profile, artifact-backed in core UI | Isolated training environments, cost controls |
| Drift | Drift recommend + on-demand retrain docs | Continuous monitoring, automated rollback |
| Evidence | Model cards, promotion workflow docs | Production model audit trail per deployment |

### Workstream 7 — Hardware integration and robotics safety

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| ROS2 bridge | Thin adapter; compose-validated | Field-tested adapters per robot class |
| Nav2 / SLAM | Headless MiniLab in `ros2-nav-slam`; offline in core demo | Site-specific maps, safety-rated navigation review |
| Physical safety | Simulated ops only | Hardware interlocks, e-stop integration, FMEA |
| Synthetic-to-real | Replay and synthetic streams | Calibration pipelines, domain adaptation program |
| Evidence | Phase 5 / 5.5 evidence, compose config | Field test reports, safety review sign-off |

### Workstream 8 — Operator UX, supportability, and product operations

| Item | Current AXON state | Production target |
|------|-------------------|-------------------|
| Dashboard | Static HTML/JS operational panels | Workflow-validated operator UX, alert design review |
| Documentation | Evidence Center, runbooks, ADRs | Versioned operator docs, LTS release notes |
| Support | Self-serve verification scripts | Ticketing, escalation tiers, customer success playbooks |
| Multi-tenancy | Single-tenant local stack | Tenant isolation, per-customer config |
| Evidence | Phase 10A screenshots (core profile) | UX study summaries, support SLA records |

---

## 3. Staged path — Stage 0 through Stage 5

AXON remains at **Stage 0** today. Later stages require explicit investment and gates; skipping stages increases operational and safety risk.

### Stage 0 — Current prototype (today)

| Field | Detail |
|-------|--------|
| **Goal** | Prove integrated architecture locally with synthetic data |
| **Required work** | Maintain evidence honesty; pass verification gates |
| **Evidence** | Phase 10A screenshots, `scripts/verify_phase9.sh`, Phase 9 seal |
| **Risks** | Overclaiming medical or enterprise readiness |
| **Go/no-go** | Continue R&D if claim and evidence gates pass; do not sell as product |

### Stage 1 — Internal technical demo hardening

| Field | Detail |
|-------|--------|
| **Goal** | Repeatable demos for internal stakeholders and design partners |
| **Required work** | Scripted profiles, demo SLOs, operator runbooks, CI green on doc gates |
| **Evidence** | Updated verification reports, demo session logs |
| **Risks** | Demo-only quality masquerading as product |
| **Go/no-go** | Stable `core` profile + documented risks accepted |

### Stage 2 — Synthetic / benign operational pilot

| Field | Detail |
|-------|--------|
| **Goal** | Pilot with partner using synthetic or non-sensitive operational data |
| **Required work** | Auth basics (Workstream 1), audit logs (Workstream 2), environment isolation |
| **Evidence** | Pilot incident logs, replay captures, signed scope boundary |
| **Risks** | Scope creep toward clinical or PII data |
| **Go/no-go** | Legal review of data handling; no clinical claims |

### Stage 3 — Hardware-integrated pilot

| Field | Detail |
|-------|--------|
| **Goal** | Connect real sensors / robots behind same Pydantic contracts |
| **Required work** | Workstream 7 field adapters, calibration, physical safety interlocks |
| **Evidence** | Hardware test reports, failure mode analysis |
| **Risks** | Physical harm, unreliable inference under real noise |
| **Go/no-go** | Robotics safety review; staged rollout per site |

### Stage 4 — Enterprise non-clinical robotics ops product

| Field | Detail |
|-------|--------|
| **Goal** | Multi-site, supported operations platform for robotics fleets |
| **Required work** | All eight workstreams at production depth; readiness matrix green |
| **Evidence** | SLAs, security audits, customer reference pilots |
| **Risks** | Security breaches, downtime, support cost overrun |
| **Go/no-go** | Enterprise readiness checklist complete; executive sign-off |

### Stage 5 — Regulated or clinical-adjacent path (optional, exceptional)

| Field | Detail |
|-------|--------|
| **Goal** | Separate product line only if business and legal justify |
| **Required work** | Full regulatory program, clinical validation, QMS — far beyond current AXON |
| **Evidence** | Formal validation studies, regulatory submissions |
| **Risks** | High cost, long timelines, claim liability |
| **Go/no-go** | Executive and legal mandate; **not** implied by current prototype |

---

## 4. Enterprise readiness matrix

Legend: **Demonstrated** = committed evidence in repo · **Partial** = pattern exists with documented gaps · **Not started** = required for enterprise production · **N/A** = out of scope for non-clinical path

| Capability area | Demonstrated today | Partial today | Not started (enterprise) | Notes |
|-----------------|-------------------|---------------|--------------------------|-------|
| Synthetic telemetry pipeline | Yes | — | Fleet-scale ingest | `core` profile live path |
| Edge-like ONNX inference | Yes | — | Fleet model deployment | `make models-generate` required |
| Agent orchestration + HITL | Yes | — | Production override metrics | LangGraph + safety envelope |
| Digital twin mirror | Yes | — | Production-grade twin sync | SVG mirror only |
| Observability endpoints | Yes | — | Centralized observability platform | `obs` profile optional |
| Mission control / Evidence Center | Yes | Partial | Multi-tenant evidence | Runtime scenario JSONs local-only |
| MLOps / synthetic retraining / candidate refresh loop | Partial | Yes | Continuous production ML ops | On-demand; not always-on |
| FL / RL modules | Partial | Yes | Isolated fleet training | `learning` profile; artifact-backed in core UI |
| ROS2 thin adapter | Partial | Yes | Field-certified adapters | Compose-validated |
| Nav2 + SLAM MiniLab | Partial | Yes | Site-specific navigation prod | `ros2-nav-slam`; offline in core demo |
| Auth / RBAC | — | — | Yes | Workstream 1 |
| Secrets management | — | — | Yes | Workstream 1 |
| Immutable audit logs | — | Partial | Yes | Workstream 2 |
| Durable TSDB / data lake | — | — | Yes | Workstream 3 |
| Horizontal event processing | — | — | Yes | Workstream 3 |
| SLOs / on-call / DR | — | Partial | Yes | Workstream 4 |
| SBOM / vuln management | — | — | Yes | Workstream 5 |
| Model monitoring / rollback | — | Partial | Yes | Workstream 6 |
| Hardware safety systems | — | — | Yes | Workstream 7 |
| Operator UX validation | — | Partial | Yes | Workstream 8 |
| Enterprise support model | — | — | Yes | Workstream 8 |
| Medical / clinical claims | N/A | — | N/A | Explicitly out of scope |

**Verdict:** AXON demonstrates **architecture patterns and evidence discipline** suitable for Stage 0–1. It does **not** meet Stage 4 enterprise production criteria.

---

## 5. Deployment options (future)

All options below assume completion of relevant workstreams. None are available as turnkey AXON products today.

| Option | Description | Fit | Complexity | When to consider |
|--------|-------------|-----|------------|------------------|
| **Single-site self-hosted** | On-prem Compose or orchestrated stack per facility | R&D labs, internal robotics ops | Medium | Stage 2 pilots |
| **Edge appliance** | Hardened edge node + local dashboard per robot cell | Factory floor, edge AI vendors | High | Stage 3 hardware pilots |
| **Centralized ops hub** | Regional ingest + inference + dashboard for fleet | Multi-robot operations centers | High | Stage 4 |
| **Hybrid edge + cloud** | Edge inference locally; central TSDB and evidence | Distributed fleets with intermittent connectivity | Very high | Stage 4 with DR requirements |
| **Managed platform (SaaS)** | Vendor-operated multi-tenant service | Customers without on-prem SRE | Very high | Stage 4+ with strong isolation |

**Not in scope for this documentation pass:** Kubernetes manifests, cloud IaC, VM images, or new runtime deployment features. Profile-based Compose remains the **current** reproducible baseline.

---

## 6. Risks and guardrails

### Technical and operational risks

| Risk | Why it matters | Current mitigation | Production still needs |
|------|----------------|-------------------|------------------------|
| **Medical overclaim** | Legal liability, unsafe market positioning | Claim scanner, disclaimers, synthetic-only policy | Counsel review, release gates |
| **Enterprise overclaim** | Customer contract exposure | Honest status tables, this document | Sales/engineering alignment |
| **Automation bias** | Operators trust flawed recommendations | HITL gates, advisory LLM | UX testing, override metrics |
| **Synthetic-to-real gap** | Models fail on real noise | Replay, staged hardware path | Field datasets, calibration |
| **Model drift** | Stale models in operations | Drift docs, on-demand synthetic retraining / candidate refresh loop | Continuous monitoring, rollback |
| **ROS2 / Nav2 scope creep** | Heavy stack mistaken for default prod path | Profiles, offline core demo labeling | Per-site robotics safety review |
| **FL/RL cost sprawl** | Always-on training uneconomical | On-demand `learning` profile | Cost controls, isolation |
| **Single-node fragility** | No HA | Health endpoints | Multi-AZ, DR (Workstream 4) |
| **Security exposure** | Lateral movement, data breach | Local dev scope | Pentest, hardening (Workstream 5) |

### Guardrails (non-negotiable for AXON communications)

1. **Synthetic data only** in default product narrative — no real patient data.
2. **No clinical diagnosis or treatment claims** — AXON does not diagnose or treat any condition; no hospital deployment claims.
3. **ROS2/Nav2/SLAM:** describe as compose-validated; live runtime requires explicit profiles; core demo remains offline for robotics stack unless stated.
4. **FL/RL/MLOps:** on-demand and artifact-backed unless a profile is explicitly started and evidence generated.
5. **MLOps wording:** synthetic retraining / candidate refresh loop — not unqualified fine-tuning.
6. **No easy production transition** — staged investment with go/no-go gates.
7. **Evidence-driven** — every production milestone produces auditable artifacts in the Evidence Center tradition.

---

## 7. Evidence links

| Artifact | Path |
|----------|------|
| Production path closeout report | [docs/evidence/phase10/production-path-report.md](../evidence/phase10/production-path-report.md) |
| Phase 10C-1 release readiness audit | [docs/evidence/phase10/final-release-readiness-audit.md](../evidence/phase10/final-release-readiness-audit.md) |
| Phase 10A demo verification | [docs/evidence/phase10/demo/demo-verification-report.md](../evidence/phase10/demo/demo-verification-report.md) |
| Screenshot index | [docs/evidence/phase10/demo/screenshot-index.md](../evidence/phase10/demo/screenshot-index.md) |
| Demo runbook | [docs/evidence/phase10/demo/runbook-phase10a.md](../evidence/phase10/demo/runbook-phase10a.md) |
| Phase 9 final seal | [docs/evidence/phase9_final_seal_report.md](../evidence/phase9_final_seal_report.md) |
| Capability truth matrix | [docs/evidence/phase9_capability_truth_matrix.md](../evidence/phase9_capability_truth_matrix.md) |
| Business case (stages overview) | [docs/business/AXON_BUSINESS_CASE.md](../business/AXON_BUSINESS_CASE.md) |
| Compose profiles | [docs/architecture/profiles.md](../architecture/profiles.md) |
| Nav2 MiniLab scope | [docs/adr/ADR-009-nav2-slam-minilab-scope.md](../adr/ADR-009-nav2-slam-minilab-scope.md) |
| MLOps / candidate promotion | [docs/evidence/candidate-promotion-workflow.md](../evidence/candidate-promotion-workflow.md) |
| Claim scanner | `scripts/scan_claims.py` |
| Phase 9 verification gate | `scripts/verify_phase9.sh` |
| Evidence Center index | [docs/evidence/README.md](../evidence/README.md) |

---

## 8. Final verdict

AXON provides a **credible prototype and evidence-backed reference architecture** for simulated rehab robot operations with honest scope boundaries. It is not enterprise-production-ready today. AXON is not a medical device and not for clinical use — not a substitute for regulated systems engineering.

Organizations evaluating an AXON-like platform should plan for **eight parallel hardening workstreams**, **five gated stages**, and **significant sustained engineering investment** before any enterprise non-clinical production commitment. This document defines that path; it does not shorten it.
