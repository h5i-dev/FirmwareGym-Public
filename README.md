# FirmwareGym

**FirmwareGym** is a benchmark and reinforcement-learning environment for formally verified, resource-constrained embedded Rust (`#![no_std]`) firmware.

Agents submit safe `#![no_std]` Rust firmware crates and receive structured feedback across four dimensions:
- **Formal Verification (Lean 4 / Charon / Aeneas)**: Proves safety, liveness, and functional properties directly on the extracted Rust implementation (checked against Lean's standard axioms only).
- **Hardware Simulation (Renode Cortex-M4)**: Links the submission into a bare-metal ARM Cortex-M4 ELF and executes declarative multi-step hardware scenarios.
- **Exact Binary & Runtime Performance Metrics**: Measures ARM ELF code size (`binary_bytes`), static + state RAM (`total_ram_bytes`), runtime peak stack watermark (`peak_stack_bytes`), and idle-free per-step Cortex-M4 instruction counts (`executed_instructions`, `max_step_instructions`, `avg_step_instructions`).
- **Resource Budgets & Customizable Rewards**: Returns all raw signals, budget limits, reference baselines, and a default correctness-gated reward (`correctness_gated_v1`) so you can plug in your own RL reward function.

This public repository contains the **Python SDK**, **API & OpenEnv protocol specifications**, and **runnable client examples**.

---

## Install the Python SDK

Requires Python 3.11+ (zero external dependencies — standard library only):

```bash
pip install ./sdk/python
# or directly from GitHub:
pip install "git+https://github.com/h5i-dev/FirmwareGym-Public.git#subdirectory=sdk/python"
```

---

## Quickstart (REST & Async Jobs)

```python
from firmwaregym import FirmwareGym, Evaluation, compute_reward

# Reads FIRMWAREGYM_API_KEY automatically if `api_key` is omitted
gym = FirmwareGym("https://api.example.com", api_key="fg_live_...")

# Check identity and remaining quota
print(gym.whoami())

# Browse tasks by difficulty or family
tasks = gym.list_tasks(level="L4")
task = gym.get_task("overcurrent-trip")

# Submit asynchronously (recommended for Renode + Lean 4 proofs)
result = gym.evaluate_async(task.id, files={"src/lib.rs": rust_source})
print("formal:", result.formal.passed, "/", result.formal.total)
print("simulation:", result.simulation.passed, "/", result.simulation.total)
print("metrics:", result.metrics)
print("default reward:", result.reward)

# Compute a custom RL reward directly from raw metrics
def custom_reward(ev: Evaluation) -> float:
    if not ev.compiled or ev.simulation.passed < ev.simulation.total:
        return 0.0
    instrs = (ev.metrics.max_step_instructions or 10_000) if ev.metrics else 10_000
    return 0.5 + 0.5 * (100.0 / (100.0 + instrs))

print("custom reward:", custom_reward(result))
```

---

## Quickstart (OpenEnv WebSocket RL Rollouts)

FirmwareGym exposes an **OpenEnv-compatible adapter** (`/ws`, `/mcp`, `/metadata`, `/schema`) compatible with both official OpenEnv Python clients (`EnvClient` / `TextArenaEnv`) and the built-in zero-dependency `OpenEnvClient`:

```python
from firmwaregym import OpenEnvClient

with OpenEnvClient("https://api.example.com", api_key="fg_live_...") as env:
    obs = env.reset(task_id="overcurrent-trip", max_steps=6)
    print(obs.observation["prompt"])

    # Accepts structured `files=`/`code=` OR TextArenaEnv markdown `message=`
    step = env.step(code=rust_source)
    print("reward:", step.reward, "done:", step.done)
    print("state:", env.state())
```

---

## Task Families (`L1`–`L5`)

| Family | Levels | Example Tasks | Core Engineering Properties |
| --- | --- | --- | --- |
| `classic` | `L1` | `overcurrent-trip`, `thermostat`, `watchdog`, `traffic-light`, `motor-controller`, `battery-manager`, `elevator`, `http-server` | Safety invariants, temporal latches, bounded actuation |
| `storage` | `L2`, `L4` | `durable-slot`, `flash-kv-store` | All-or-nothing crash consistency, bit-monotone NOR flash, GC safety, wear leveling |
| `network` | `L2`, `L4` | `idempotent-cmd`, `reliable-cmd-protocol` | Multi-client at-most-once execution across packet loss, reordering, wraparound, and reboots |
| `scheduler` | `L4` | `rtos-scheduler` | Real-time deadline satisfaction, mutex exclusion, priority inheritance, IRQ preemption |
| `sensor-fusion` | `L2`, `L4` | `sensor-median`, `robust-sensor-fusion` | Sound interval estimation under Byzantine sensor faults, heterogeneous noise, and drift |
| `vm` | `L2`, `L5` | `step-machine`, `embedded-vm` | Operational semantics equivalence, capability confinement, gas metering, snapshot recovery |
| `coordination` | `L5` | `warehouse-robots` | Multi-agent collision & swap freedom, battery safety, deadlock-free delivery under packet loss |

---

## Repository Contents

- [`docs/API.md`](docs/API.md) — Full REST (`/v1/...`) and OpenEnv (`/ws`, `/mcp`) API reference
- [`docs/openapi.json`](docs/openapi.json) — Machine-readable OpenAPI 3.1 schema
- [`sdk/python/`](sdk/python/) — Zero-dependency Python SDK (`FirmwareGym`, `OpenEnvClient`, `compute_reward`)
- [`examples/quickstart.py`](examples/quickstart.py) — Async evaluation & custom reward script
- [`examples/openenv_rollout.py`](examples/openenv_rollout.py) — Multi-turn OpenEnv WebSocket rollout loop
- [`examples/overcurrent_starter/`](examples/overcurrent_starter/) — Sample public task starter & specification

## License

Apache License 2.0. See [LICENSE](LICENSE).
