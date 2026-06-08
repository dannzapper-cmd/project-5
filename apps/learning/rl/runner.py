"""Persist an RL experiment: run -> artifacts -> MLflow -> status.

This module is the integration point used by the CLI script
(``scripts/run_rl_micro_module.py``) and the Docker ``rl-runner`` service. It
writes the evidence artifacts the dashboard/API and the Evidence Center read.

Synthetic RL operational policy. No real patient data. No medical decisions.
Human review required for high-risk actions.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.learning.rl.config import (
    LATEST_REPORT_PATH,
    POLICY_MODEL_PATH,
    POLICY_SUMMARY_PATH,
    REWARD_CURVE_CSV_PATH,
    REWARD_CURVE_JSON_PATH,
    RL_ARTIFACTS,
    RUNS_DIR,
    SAFETY_ENVELOPE_PATH,
    STATUS_PATH,
)
from apps.learning.rl.disclaimer import DISCLAIMER, SAFETY_SCOPE
from apps.learning.rl.experiment import run_rl_experiment
from apps.learning.rl.mlflow_utils import log_rl_run


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def write_status(status: str, extra: dict | None = None) -> None:
    """Write a lightweight idle/running/completed/failed status marker."""
    payload = {
        "status": status,
        "updated_utc": datetime.now(UTC).isoformat(),
        "disclaimer": DISCLAIMER,
    }
    if extra:
        payload.update(extra)
    _write_json(STATUS_PATH, payload)


def _write_reward_curve(report: dict) -> None:
    curve = report.get("reward_curve", [])
    _write_json(REWARD_CURVE_JSON_PATH, {"reward_curve": curve, "disclaimer": DISCLAIMER})
    REWARD_CURVE_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REWARD_CURVE_CSV_PATH.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timesteps", "mean_episode_reward"])
        for entry in curve:
            writer.writerow([entry["timesteps"], entry["mean_episode_reward"]])


def _write_policy_summary(report: dict) -> None:
    summary = {
        "env_name": report["env_name"],
        "algorithm": report["algorithm"],
        "reward_version": report["reward_version"],
        "safety_mode": report["safety_mode"],
        "observation_names": report["observation_names"],
        "action_names": report["action_names"],
        "baseline_reward": report["baseline_reward"],
        "trained_policy_reward": report["trained_policy_reward"],
        "policy_improvement_ratio": report["policy_improvement_ratio"],
        "unsafe_action_rate": report["unsafe_action_rate"],
        "hitl_suggestion_rate": report["hitl_suggestion_rate"],
        "episode_length_mean": report["episode_length_mean"],
        "synthetic_only": True,
        "disclaimer": DISCLAIMER,
    }
    _write_json(POLICY_SUMMARY_PATH, summary)


def _write_safety_envelope(report: dict) -> None:
    text = f"""# RL Micro-module Safety Envelope (Phase 6B)

> {DISCLAIMER}

{SAFETY_SCOPE}

## What this policy optimizes (allowed)
- Alert prioritization (raise / lower / keep).
- Conservative threshold suggestions.
- Simulated resource allocation to triage/safety.
- Human-in-the-loop (HITL) escalation suggestions.

## What this policy must never do (prohibited)
- Medical diagnosis, treatment, or clinical recommendations.
- Real robot / hardware control or movement.
- Irreversible or autonomous safety-critical actions.

## Human-in-the-loop requirement
Human review is required for high-risk (`risk_score > 0.6`) or low-confidence
(`fusion_confidence < 0.4`) situations. The `request_hitl` action exists for
exactly this purpose and is rewarded under REWARD_V1.

## Measured safety behavior (latest run)
- Environment: `{report['env_name']}`  ·  Algorithm: `{report['algorithm']}`
- Reward version: `{report['reward_version']}`  ·  Seed: `{report['seed']}`
- Baseline (random) reward: {report['baseline_reward']}
- Trained policy reward: {report['trained_policy_reward']}
- Policy improvement ratio: {report['policy_improvement_ratio']}
- Unsafe action rate: {report['unsafe_action_rate']}
- HITL suggestion rate: {report['hitl_suggestion_rate']}

Trained and evaluated on synthetic data only. No real patient data. No medical
decisions. Not a medical device.
"""
    SAFETY_ENVELOPE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAFETY_ENVELOPE_PATH.write_text(text)


def run_and_persist(
    *,
    seed: int = 42,
    total_timesteps: int | None = None,
    eval_episodes: int | None = None,
    log_mlflow: bool = True,
    save_policy: bool = True,
) -> dict:
    """Run the experiment, write all artifacts, optionally log MLflow."""
    RL_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    write_status("running", {"seed": seed})
    try:
        report = run_rl_experiment(
            seed=seed,
            total_timesteps=total_timesteps,
            eval_episodes=eval_episodes,
        )
        model = report.pop("_model", None)

        # Optionally persist the (small) trained policy artifact.
        if save_policy and model is not None:
            try:
                model.save(str(POLICY_MODEL_PATH))
            except Exception:  # noqa: BLE001 - policy artifact is best-effort
                pass

        _write_reward_curve(report)
        _write_policy_summary(report)
        _write_safety_envelope(report)

        artifacts = [
            LATEST_REPORT_PATH,
            REWARD_CURVE_JSON_PATH,
            REWARD_CURVE_CSV_PATH,
            POLICY_SUMMARY_PATH,
            SAFETY_ENVELOPE_PATH,
        ]
        if save_policy and POLICY_MODEL_PATH.exists():
            artifacts.append(POLICY_MODEL_PATH)

        # Write report once (without run id) so MLflow can log it, then rewrite.
        _write_json(LATEST_REPORT_PATH, report)

        run_id = log_rl_run(report, artifacts) if log_mlflow else None
        report["mlflow_run_id"] = run_id
        _write_json(LATEST_REPORT_PATH, report)
        _write_json(RUNS_DIR / f"{report['experiment_id']}.json", report)

        write_status(
            "completed",
            {
                "seed": seed,
                "baseline_reward": report["baseline_reward"],
                "trained_policy_reward": report["trained_policy_reward"],
                "policy_improvement_ratio": report["policy_improvement_ratio"],
                "unsafe_action_rate": report["unsafe_action_rate"],
                "hitl_suggestion_rate": report["hitl_suggestion_rate"],
                "mlflow_run_id": run_id,
                "report_path": str(LATEST_REPORT_PATH),
            },
        )
        return report
    except Exception as exc:  # noqa: BLE001
        write_status("failed", {"error": str(exc)})
        raise
