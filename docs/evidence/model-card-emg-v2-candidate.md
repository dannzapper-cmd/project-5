# Model Card: EMG v2_candidate

See generated artifact at `artifacts/mlops/evals/<eval_id>/model_card_emg_v2_candidate.md` after running `make mlops-pipeline`.

## Model Details

- Signal type: emg
- Version: v2_candidate
- Architecture: LogisticRegression Pipeline (StandardScaler + LogisticRegression)
- Promotion status: candidate_not_promoted

## Synthetic Only

Trained exclusively on synthetic biomedical-inspired signals. No real patient data.

## Intended Use

Simulated edge inference for portfolio demonstration.

## Out of Scope

Clinical use. Medical diagnosis. Treatment decisions. Real patient monitoring.

## Labels

`normal`, `fatigue`, `anomaly`

## Features

rms, zcr, variance, peak2peak, mean_abs (from `extract_emg_features`)
