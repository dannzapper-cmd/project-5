# Model Card: IMU v2_candidate

See generated artifact at `artifacts/mlops/evals/<eval_id>/model_card_imu_v2_candidate.md` after running `make mlops-pipeline`.

## Model Details

- Signal type: imu
- Version: v2_candidate
- Architecture: LogisticRegression Pipeline
- Promotion status: candidate_not_promoted

## Synthetic Only

Trained exclusively on synthetic biomedical-inspired signals. No real patient data.

## Labels

`normal`, `spike`, `dropout`

## Features

range_x, range_y, range_z, jerk, mean_mag (from `extract_imu_features`)
