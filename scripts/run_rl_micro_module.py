#!/usr/bin/env python3
"""Run the Phase 6B RL micro-module experiment (Gymnasium + Stable-Baselines3 PPO).

Synthetic RL operational policy. No real patient data. No medical decisions.
Human review required for high-risk actions.

Examples:
    python scripts/run_rl_micro_module.py                 # default portfolio run (seed 42)
    python scripts/run_rl_micro_module.py --seed 123
    python scripts/run_rl_micro_module.py --ci            # tiny CI-friendly run
    python scripts/run_rl_micro_module.py --eval          # inspect latest policy (table)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from apps.learning.rl.config import (
    DEFAULT_EVAL_EPISODES,
    DEFAULT_SEED,
    DEFAULT_TOTAL_TIMESTEPS,
    LATEST_REPORT_PATH,
)


def _run(args: argparse.Namespace) -> None:
    from apps.learning.rl.runner import run_and_persist

    report = run_and_persist(
        seed=args.seed,
        total_timesteps=args.total_timesteps,
        eval_episodes=args.eval_episodes,
        log_mlflow=not args.no_mlflow,
    )
    print(
        json.dumps(
            {
                "experiment_id": report["experiment_id"],
                "env_name": report["env_name"],
                "algorithm": report["algorithm"],
                "seed": report["seed"],
                "total_timesteps_or_episodes": report["total_timesteps_or_episodes"],
                "baseline_reward": report["baseline_reward"],
                "trained_policy_reward": report["trained_policy_reward"],
                "policy_improvement_ratio": report["policy_improvement_ratio"],
                "unsafe_action_rate": report["unsafe_action_rate"],
                "hitl_suggestion_rate": report["hitl_suggestion_rate"],
                "mlflow_run_id": report["mlflow_run_id"],
                "report_path": str(LATEST_REPORT_PATH),
                "disclaimer": report["disclaimer"],
            },
            indent=2,
        )
    )


def _eval(args: argparse.Namespace) -> None:
    """Print a small state -> action inspection table for manual review."""
    from apps.learning.rl.config import POLICY_MODEL_PATH
    from apps.learning.rl.environment import AxonTriageEnvV1
    from apps.learning.rl.reward import compute_reward

    if not POLICY_MODEL_PATH.exists():
        print(f"No trained policy at {POLICY_MODEL_PATH}. Run without --eval first.")
        sys.exit(1)

    from stable_baselines3 import PPO

    model = PPO.load(str(POLICY_MODEL_PATH))
    env = AxonTriageEnvV1()
    obs, _ = env.reset(seed=args.seed)
    print(f"{'step':>4} {'risk':>5} {'conf':>5} {'drop':>5} {'load':>5}  action")
    for step in range(args.eval_steps):
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        rb = compute_reward(obs, action)
        print(
            f"{step:>4} {obs[0]:>5.2f} {obs[1]:>5.2f} {obs[3]:>5.2f} {obs[5]:>5.2f}  "
            f"{env.action_names[action]:<32} r={rb.total:+.2f}"
        )
        obs, _, terminated, truncated, _ = env.step(action)
        if terminated or truncated:
            obs, _ = env.reset(seed=args.seed + step + 1)
    print("\nSynthetic RL operational policy. No real patient data. No medical decisions.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AXON Phase 6B RL micro-module")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--total-timesteps", type=int, default=DEFAULT_TOTAL_TIMESTEPS)
    parser.add_argument("--eval-episodes", type=int, default=DEFAULT_EVAL_EPISODES)
    parser.add_argument("--no-mlflow", action="store_true", help="Skip MLflow logging")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Tiny CI-friendly run (sets RL_CI_MODE=true: 500 timesteps, 5 eval episodes)",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Inspect the latest trained policy (state -> action table), no training",
    )
    parser.add_argument("--eval-steps", type=int, default=20)
    args = parser.parse_args()

    if args.ci:
        os.environ["RL_CI_MODE"] = "true"

    if args.eval:
        _eval(args)
    else:
        _run(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
