# FirmwareGym

**FirmwareGym is a benchmark and reinforcement learning environment for building high-performance firmware with Lean 4 proofs.** Agents submit Rust (`#![no_std]`) firmware and proofs that the implementation meets a fixed specification. They then improve the measured performance of the firmware while continuing to satisfy the same proof obligations, runtime requirements, and resource limits.

## 1. Overview

Each task provides a fixed contract and measured resource metrics. Once two implementations pass the contract, compare their instruction counts, stack, RAM, and binary footprint to see what each optimization saves.

- **Prove the implementation** against each fixed Lean 4 obligation using the [h5i](https://github.com/h5i-dev/h5i) toolchain. The grader extracts the Lean model from the submitted Rust for the Cortex-M target used in simulation.
- **Test the firmware** on virtual hardware in [Renode](https://github.com/renode/renode). The development API reports public checks; final grading can also include held-out scenarios and randomized workloads.
- **Improve measured performance** by reducing total, average, or peak per-step instruction counts, binary size, RAM usage, or peak stack. Resource limits define acceptable usage, and the raw measurements show how much an optimization saves within those limits.

The default proof reward unlocks its performance component once the required proof and runtime checks pass within budget. The SDK exposes individual proof verdicts and raw resource measurements for custom RL rewards. A proof pass rate describes an agent run under its stated time budget. Compare performance across fully passing submissions on the same task revision and workloads.

## 2. Tasks

The hosted catalog spans five difficulty levels (L1–L5), from single-device controllers to fault-tolerant embedded logic. Use `gym.list_tasks()` to discover the tasks available to your API key.

Examples of tasks include:

| Task | Engineering challenges |
|---|---|
| Battery Management System | Thermal protection, voltage monitoring, fault recovery |
| Crash-Consistent Flash Storage | Power failures, atomic updates, garbage collection, wear leveling |
| Reliable Communication Protocol | Packet loss, reordering, duplicate execution, reboots |
| Real-Time Scheduler | Admission control, scheduling decisions, deadline tracking |
| Robust Sensor Fusion | Byzantine sensor faults, measurement noise, uncertainty |
| Embedded Virtual Machine | Operational semantics, capability isolation, execution metering |
| Autonomous Warehouse Robots | Multi-agent coordination, collision avoidance, energy management |

The task API provides the README, Rust starter, public Lean specification, fixed theorem obligations, Renode scenario, and resource budgets. This repository includes two samples: Overcurrent Trip and an L4 crash-consistent NOR flash key-value store. The hosted public grader returns development feedback. Organizers run final evaluation separately.

## 3. Getting Started

This repository provides the open-source Python SDK, API specifications, OpenEnv integration, and runnable examples.

### 3.1. Installation

Requires Python 3.11+. The SDK has no external Python dependencies.

```bash
pip install "git+https://github.com/h5i-dev/FirmwareGym-Public.git#subdirectory=sdk/python"
```

### 3.2. Firmware Evaluation

Set `FIRMWAREGYM_URL` and `FIRMWAREGYM_API_KEY` to the endpoint and key provided by your operator. Implement the Rust starter, then fill the corresponding Lean proof template in `proofs/Submission.lean`.

```python
import os
from pathlib import Path
from firmwaregym import FirmwareGym

gym = FirmwareGym(os.environ["FIRMWAREGYM_URL"])
task = gym.get_task("overcurrent-trip")

result = gym.evaluate_async(
    task.id,
    files={"src/lib.rs": Path("src/lib.rs").read_text()},
    proof=Path("proofs/Submission.lean").read_text(),
)

print("Renode:", result.simulation.passed, "/", result.simulation.total)
for obligation in result.obligations:
    print(obligation.id, obligation.status, obligation.feedback)
print("Reward:", result.reward)
if result.metrics is not None:
    print("Peak instructions per step:", result.metrics.max_step_instructions)
    print("Peak stack bytes:", result.metrics.peak_stack_bytes)
```

Submit without `proof` to test the Rust implementation in Renode. Use the REST proof path for joint Rust and Lean evaluation.

### 3.3. Reinforcement Learning with OpenEnv

FirmwareGym supports the OpenEnv protocol for multi-turn RL rollouts, allowing agents to iteratively develop, verify, and optimize firmware based on structured evaluation feedback.

```python
from firmwaregym import OpenEnvClient

with OpenEnvClient(
    "https://api.example.com",
    api_key="fg_live_..."
) as env:
    obs = env.reset(
        task_id="overcurrent-trip",
        max_steps=6
    )

    print(obs.observation["prompt"])

    step = env.step(code=rust_source)

    print("Reward:", step.reward)
    print("Done:", step.done)
```

### 3.4. Custom Reward Functions

Researchers can define their own reward functions using raw verification results and performance metrics. This example rewards lower peak instruction counts after the development correctness checks and resource budgets pass.

```python
from firmwaregym import Evaluation

def custom_reward(ev: Evaluation) -> float:
    if not ev.compiled:
        return 0.0

    if ev.formal.total == 0 or ev.formal.passed < ev.formal.total:
        return 0.0

    if ev.simulation.passed < ev.simulation.total:
        return 0.0

    if ev.budgets is None or not ev.budgets.passed or ev.metrics is None:
        return 0.0

    instructions = ev.metrics.max_step_instructions

    if instructions is None:
        return 0.0

    return 0.5 + 0.5 * (100.0 / (100.0 + instructions))
```

## 4. Access

The Python SDK, API specifications, and selected sample tasks are publicly available under the Apache 2.0 license. Access 
to the full task collection and hosted evaluation environment requires an API key.

## 5. Documentation

- [API Reference](docs/API.md): REST and OpenEnv API documentation.
- [OpenAPI Schema](docs/openapi.json): Machine-readable API specification.
- [Python SDK](sdk/python/): Client library and reward utilities.
- [Quickstart Example](examples/quickstart.py): Firmware evaluation and custom rewards.
- [OpenEnv Example](examples/openenv_rollout.py): Multi-turn RL rollouts.
- [Overcurrent Trip](examples/overcurrent_starter/): Introductory task and starter code.
- [Crash-consistent NOR flash store](examples/flash_kv_nor_starter/): L4 task with a Rust starter and Lean proof template.

## 6. License

Apache License 2.0. See [LICENSE](LICENSE).
