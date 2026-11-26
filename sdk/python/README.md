# firmwaregym

Thin Python client for the FirmwareGym v1 evaluation API (Python 3.11+ standard library only).

## Quickstart

```python
from firmwaregym import FirmwareGym

# Reads FIRMWAREGYM_API_KEY automatically if api_key is not passed explicitly
gym = FirmwareGym("https://api.example.com", api_key="fg_live_...")

print(gym.whoami())
tasks = gym.list_tasks(level="L4")
task = gym.get_task("overcurrent-trip")

# Synchronous evaluation (fast checks)
result = gym.evaluate(task.id, files={"src/lib.rs": rust_code})

# Asynchronous evaluation (recommended for Renode + Lean 4 proofs behind load balancers)
result = gym.evaluate_async(task.id, files={"src/lib.rs": rust_code}, proof=lean_source)
print(result.simulation, result.obligations, result.reward)

# Retriable job creation. Reuse the key with the same payload after a network error.
job = gym.submit_job(
    task.id, files={"src/lib.rs": rust_code}, proof=lean_source, idempotency_key="experiment-42"
)
print(gym.get_job(job.job_id))
print(gym.list_jobs())
# gym.cancel_job(job.job_id)
```

## Custom Reward Functions

`result.reward.scheme` identifies the server scoring mode. Proof submissions use `correctness_gated_proof_v2`. You can use the available raw signals (`compiled`, `formal`, `simulation`, `metrics`, `budgets.limits`, `performance.ratios`, `performance.baselines`), so you can compute your own reward logic on the client side:

```python
from firmwaregym import Evaluation, compute_reward

# Option 1: Customize weights/alpha/gating with the built-in helper
r = compute_reward(result, alpha=0.7, metric_weights={"ram_bytes": 0.8, "avg_step_instructions": 0.2})

# Option 2: Write any custom RL reward function directly over raw observations
def my_reward(ev: Evaluation) -> float:
    if not ev.compiled or ev.simulation.passed < ev.simulation.total:
        return 0.0
    ram = (ev.metrics.total_ram_bytes or 0) if ev.metrics else 0
    return 1.0 - min(ram / 4096.0, 1.0) * 0.3
```

All API routes evaluate against the **public** spec only. Final held-out workloads are operator-only.
