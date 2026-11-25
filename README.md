# FirmwareGym

**FirmwareGym** is a benchmark and reinforcement learning environment for generating formally verifiable, high-performance firmware. This benchmark challenges AI agents to develop Rust (`#![no_std]`) firmware for realistic embedded systems, satisfying formal specifications and hardware-level tests while optimizing the performance.

## Evaluation

FirmwareGym evaluates each firmware submission across four dimensions:

- **Formal verification**: The number and proportion of successfully proven properties using [h5i](https://github.com/h5i-dev/h5i) and Lean 4.
- **Simulation pass rate**: The number and proportion of passed test scenarios when executing compiled firmware on virtual hardware using [Renode](https://github.com/renode/renode).
- **Execution efficiency**: Total, average, and maximum per-step CPU instruction counts.
- **Memory efficiency**: Binary size, RAM usage, and peak stack usage.

All raw evaluation metrics are accessible through the SDK, allowing researchers to define custom reward functions for their RL training objectives.

## Tasks

FirmwareGym aims to provide over 100 realistic firmware engineering tasks across five difficulty levels (L1–L5), ranging from basic device controllers to complex, fault-tolerant embedded systems.

Examples of tasks include:

| Task | Engineering challenges |
|---|---|
| Battery Management System | Thermal protection, voltage monitoring, fault recovery |
| Crash-Consistent Flash Storage | Power failures, atomic updates, garbage collection, wear leveling |
| Reliable Communication Protocol | Packet loss, reordering, duplicate execution, reboots |
| Real-Time Scheduler | Deadline satisfaction, resource contention, interrupt handling |
| Robust Sensor Fusion | Byzantine sensor faults, measurement noise, uncertainty |
| Embedded Virtual Machine | Operational semantics, capability isolation, execution metering |
| Autonomous Warehouse Robots | Multi-agent coordination, collision avoidance, energy management |

Each task defines formal specifications, simulation scenarios, resource budgets, and performance baselines. Selected sample tasks are publicly available, while the full task collection, reference implementations, and hidden evaluation specifications remain private.

## Getting Started

This repository provides the open-source Python SDK, API specifications, OpenEnv integration, and runnable examples.

### Installation

Requires Python 3.11+. The SDK has no external Python dependencies.

```bash
pip install "git+https://github.com/h5i-dev/FirmwareGym-Public.git#subdirectory=sdk/python"
```

### Firmware Evaluation

```python
from firmwaregym import FirmwareGym

gym = FirmwareGym(
    "https://api.example.com",
    api_key="fg_live_..."
)

# Browse available tasks
tasks = gym.list_tasks(level="L4")
task = gym.get_task("overcurrent-trip")

# Submit firmware for evaluation
result = gym.evaluate_async(
    task.id,
    files={"src/lib.rs": rust_source}
)

print("Formal verification:", result.formal.passed, "/", result.formal.total)
print("Simulation:", result.simulation.passed, "/", result.simulation.total)
print("Performance:", result.metrics)
print("Reward:", result.reward)
```

### Reinforcement Learning with OpenEnv

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

### Custom Reward Functions

Researchers can define their own reward functions using raw verification results and performance metrics.

```python
from firmwaregym import Evaluation

def custom_reward(ev: Evaluation) -> float:
    if not ev.compiled:
        return 0.0

    if ev.formal.passed < ev.formal.total:
        return 0.0

    if ev.simulation.passed < ev.simulation.total:
        return 0.0

    if ev.metrics is None:
        return 0.0

    instructions = ev.metrics.max_step_instructions

    if instructions is None:
        return 0.0

    return 0.5 + 0.5 * (100.0 / (100.0 + instructions))
```

## Access

The Python SDK, API specifications, and selected sample tasks are publicly available under the Apache 2.0 license.

Access to the full task collection and hosted evaluation environment requires an API key.

## Documentation

- [API Reference](docs/API.md) — REST and OpenEnv API documentation.
- [OpenAPI Schema](docs/openapi.json) — Machine-readable API specification.
- [Python SDK](sdk/python/) — Client library and reward utilities.
- [Quickstart Example](examples/quickstart.py) — Firmware evaluation and custom rewards.
- [OpenEnv Example](examples/openenv_rollout.py) — Multi-turn RL rollouts.
- [Sample Task](examples/overcurrent_starter/) — Public firmware task and starter code.

## License

Apache License 2.0. See [LICENSE](LICENSE).
