"""FirmwareGym REST + async jobs + custom reward quickstart."""

from __future__ import annotations

import os
from pathlib import Path

from firmwaregym import Evaluation, FirmwareGym, compute_reward


def custom_speed_aware_reward(ev: Evaluation) -> float:
    """Example user-defined RL reward function over raw Evaluation signals."""
    if not ev.compiled:
        return 0.0
    sim_frac = ev.simulation.passed / max(ev.simulation.total, 1)
    formal_frac = ev.formal.passed / max(ev.formal.total, 1)
    if ev.simulation.passed < ev.simulation.total or ev.formal.passed < ev.formal.total:
        return 0.4 * (0.5 * sim_frac + 0.5 * formal_frac)
    if ev.budgets and not ev.budgets.passed:
        return 0.3
    max_step = (ev.metrics.max_step_instructions or 500) if ev.metrics else 500
    speed_bonus = 50.0 / (50.0 + max_step)
    return 0.5 + 0.5 * speed_bonus


def main() -> None:
    base_url = os.environ.get("FIRMWAREGYM_URL", "http://127.0.0.1:8080")
    gym = FirmwareGym(base_url)  # reads FIRMWAREGYM_API_KEY automatically

    print("Health:", gym.health())
    print("Identity:", gym.whoami())

    tasks = gym.list_tasks()
    print(f"Available tasks ({len(tasks)}):", [t.id for t in tasks])

    task = gym.get_task("overcurrent-trip")
    starter_path = Path(__file__).parent / "overcurrent_starter" / "starter" / "src" / "lib.rs"
    code = starter_path.read_text() if starter_path.is_file() else task.files["src/lib.rs"]

    # Async evaluation is recommended for Renode + Lean 4 proofs
    result = gym.evaluate_async(task.id, files={"src/lib.rs": code})
    print("Compiled:", result.compiled)
    print("Formal:", f"{result.formal.passed}/{result.formal.total}", result.formal.feedback)
    print("Simulation:", f"{result.simulation.passed}/{result.simulation.total}", result.simulation.feedback)
    print("Metrics:", result.metrics)
    print("Default reward:", result.reward)
    print("Helper custom reward:", compute_reward(result, alpha=0.6))
    print("User-defined reward:", custom_speed_aware_reward(result))


if __name__ == "__main__":
    main()
