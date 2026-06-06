# Biomedical Claims Policy

AXON simulates biomedical-inspired monitoring for **software engineering demonstration** only.

## What AXON Uses

- **Synthetic biomedical-inspired signals only** (EMG-like, ECG-like, IMU, SpO2-proxy)
- Simulated rehabilitation robot operations
- Software-generated telemetry with explicit quality/confidence metadata

## What AXON Does NOT Do

- **No diagnosis** of medical conditions
- **No treatment advice** or clinical recommendations
- **No patient data** — real or de-identified
- **No claims of clinical accuracy** or medical-grade monitoring
- **No emergency response claims**
- **No medical device certification claims**

## Prohibited Language

Avoid in code, docs, demos, and marketing:

- "Medical-grade"
- "Clinical deployment"
- "Diagnoses arrhythmia / fatigue / hypoxia"
- "FDA" / "HIPAA compliant" (unless factually accurate for unrelated infrastructure — default: do not claim)
- "Patient monitoring system"

## Engineering Framing

AXON is a **portfolio intelligent systems project** demonstrating:

- Event-driven architecture
- Edge inference pipelines
- Agent coordination with safety boundaries
- Observability and evidence collection

It is **not** a product for hospitals, clinics, or patient care.

## Enforcement

Contributors and AI tools must review UI copy, agent prompts, and documentation against this policy before merge.
