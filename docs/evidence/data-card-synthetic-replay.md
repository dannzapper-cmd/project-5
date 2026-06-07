# Data Card: Synthetic Replay Dataset

Generated at runtime under `artifacts/mlops/datasets/<dataset_id>/data_card.md`.

## Overview

- Type: Synthetic signal dataset
- Generator: `apps/mlops/dataset.py` (`axon-mlops-v1`)
- Scenarios: normal_session, fatigue_event, movement_spike, sensor_dropout, low_confidence_drift, multi_anomaly
- Signal types: emg, imu

## Synthetic Only

All data is synthetically generated. No real patient data. No real sensor hardware.

## Prohibited Use

Not for clinical use. Not for medical diagnosis. Not for treatment decisions.

## Feature Description

- **EMG:** rms, zcr, variance, peak2peak, mean_abs
- **IMU:** range_x, range_y, range_z, jerk, mean_mag
