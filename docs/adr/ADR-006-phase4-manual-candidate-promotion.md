# ADR-006: Manual Candidate Promotion for Safety-Critical Simulation

## Status

Accepted

## Context

Phase 4 trains candidate v2 models that could theoretically replace Phase 2 active ONNX artifacts. Automatic promotion on metric improvement would hide the operator decision trail and risk overwriting working edge models.

## Decision

- Candidate promotion is **always manual/dry-run by default**.
- `POST /api/v1/mlops/promote-candidate` with `dry_run: true` writes a review record only.
- Real promotion requires `confirm_manual_promotion: true` and copies candidate to a **timestamped backup path**, never the Phase 2 active path.
- `assert_not_protected()` blocks writes to discovered Phase 2 ONNX paths.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Automated promotion on metric delta | Unsafe; no human review trail |
| Canary/staged rollout | Overkill for single-laptop portfolio demo |

## Consequences

- Operator must review eval report and explicitly confirm promotion.
- Every promotion attempt creates a JSON review record under `artifacts/mlops/promotion_reviews/`.
- Phase 2 active models remain unchanged after Phase 4 pipeline runs.
