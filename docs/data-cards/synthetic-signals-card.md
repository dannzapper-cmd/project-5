# Synthetic Signals Data Card

## Dataset Status

**Future synthetic dataset** — not generated in Phase 0.

## Allowed Use

- Local development and testing
- Portfolio demonstrations
- Model training on synthetic biomedical-inspired signals
- Replay and failure injection scenarios

## Prohibited Use

- Clinical decision support
- Real patient monitoring
- Claims of medical accuracy
- Distribution as real biomedical data
- Regulatory submissions

## Synthetic Signal Types

| Signal | Description |
|--------|-------------|
| EMG | Muscle activation proxy (synthetic) |
| ECG-like | Cardiac rhythm inspired waveform (not clinical ECG) |
| IMU | Accelerometer/gyro motion data |
| SpO2-proxy | Oxygen saturation inspired proxy (not pulse oximetry) |
| Robot state | Joint angles, torques, session phase |
| Environment | Temperature, humidity, zone occupancy (simulated) |

## Known Limitations

- Does not replicate real physiology
- Noise models are simplified
- No inter-patient variability grounded in clinical studies
- Artifacts and sensor dropouts are scripted, not real-world

## Bias and Realism Limitations

- Generator parameters may over-represent demo-friendly scenarios
- Edge cases from real rehab robotics may be underrepresented
- Demographic and anatomical diversity not modeled in early phases

## No Medical Validity Claim

This data has **zero medical validity**. It exists to exercise software pipelines only.

## Planned Future Evidence

- Generator configuration documentation (Phase 1)
- Sample payload archive (Phase 1)
- Statistical summary of synthetic distributions (Phase 2)
- Missing-data and corruption scenario datasets (Phase 2)
