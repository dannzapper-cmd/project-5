# Candidate Promotion Workflow

## Endpoint

`POST /api/v1/mlops/promote-candidate`

```json
{
  "signal_type": "emg",
  "dry_run": true,
  "confirm_manual_promotion": false,
  "operator_note": "optional"
}
```

## Rules

1. **Default (`dry_run: true`):** Returns review preview; writes review record to `artifacts/mlops/promotion_reviews/`; does not copy or rename model files.
2. **Manual confirm (`dry_run: false`, `confirm_manual_promotion: true`):** Copies candidate to timestamped backup; updates registry candidate status to `manual_review_complete`. **Never overwrites Phase 2 active model path.**
3. `assert_not_protected()` enforces Phase 2 path protection.

## Dashboard

"MLOps" panel includes "Manual Review Only — Simulated" button calling dry-run promotion.

## Safety Notice

Simulated candidate review only. No clinical use. No automatic deployment.
