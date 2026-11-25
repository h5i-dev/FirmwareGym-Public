"""Multi-turn RL rollout example using FirmwareGym's OpenEnv WebSocket adapter (`/ws`)."""

from __future__ import annotations

import os

from firmwaregym import OpenEnvClient


def main() -> None:
    base_url = os.environ.get("FIRMWAREGYM_URL", "http://127.0.0.1:8080")

    with OpenEnvClient(base_url) as env:
        reset_obs = env.reset(task_id="overcurrent-trip", max_steps=4)
        print("Task:", reset_obs.observation["task_id"])
        print("Prompt preview:", reset_obs.observation["prompt"][:240], "...\n")

        # Turn 1: submit the starter code wrapped in a markdown fence (TextArenaEnv style)
        starter = reset_obs.observation["files"]["src/lib.rs"]
        step1 = env.step(message=f"Attempt 1:\n```rust\n{starter}\n```")
        print(
            "Step 1 -> reward:",
            step1.reward,
            "done:",
            step1.done,
            "sim:",
            step1.observation["simulation"],
        )

        # Inspect episode state
        print("Episode state:", env.state())


if __name__ == "__main__":
    main()
