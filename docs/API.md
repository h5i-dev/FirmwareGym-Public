# FirmwareGym API & OpenEnv Protocol Specification

**API Version**: `0.2.0`  
**OpenAPI Schema**: [`openapi.json`](openapi.json) (also served live at `GET /openapi.json`, with interactive docs at `GET /docs`)

All public API endpoints evaluate submissions against **public specifications only**. Hidden verification suites and adversarial property-based fuzzers run strictly on operator evaluation pipelines.

---

## 1. Authentication & Quotas

Pass your API key on every authenticated request via either header:

```http
Authorization: Bearer fg_live_<token>
# or
X-API-Key: fg_live_<token>
```

For WebSocket clients (`/ws`) that cannot set custom headers, `?api_key=fg_live_<token>` is also accepted.

### Rate Limits & Tenant Quotas

Quotas are enforced server-side per tenant:
- **Burst rate limit**: Sliding 60-second window (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `429 Too Many Requests` + `Retry-After`).
- **Per-tenant concurrency cap**: Limits simultaneous in-flight/queued evaluations per tenant (`429 Too Many Requests` + `Retry-After`).
- **Monthly quota**: Persistent UTC calendar-month evaluation cap (`429 Too Many Requests`). Rejected `400 Bad Request` submissions do **not** consume your monthly quota.
- **Global queue backpressure**: Returns `503 Service Unavailable` + `Retry-After` when the server evaluation queue is full.

---

## 2. REST Endpoints (`/v1`)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | Liveness & capacity probe (`ok: true`, `status: "healthy"`) |
| `GET` | `/openapi.json` | Public | OpenAPI 3.1 JSON schema |
| `GET` | `/docs` | Public | Interactive HTML API documentation |
| `GET` | `/v1/me` | Required | Caller identity, role, burst rate remaining, and `usage` snapshot |
| `GET` | `/v1/tasks` | Required | List tasks (optional `?family=` and `?level=` query filters) |
| `GET` | `/v1/tasks/{id}` | Required | Fetch task README, starter Rust crate, public Lean 4 spec, budgets, optimization config, and public scenario YAML |
| `POST` | `/v1/tasks/{id}/evaluate` | Required | Synchronous evaluation (`{"files": {"src/lib.rs": "..."}}`) |
| `POST` | `/v1/jobs` | Required | Submit async evaluation job (`{"task_id": "...", "files": {...}}`) → `202 Accepted` (**recommended for Renode + Lean 4**) |
| `GET` | `/v1/jobs/{job_id}` | Required | Poll async job status (`queued`, `running`, `completed`, `failed`) and full `Evaluation` payload |

### Submission Rules

- Files must live under `src/` and end with `.rs` (`src/lib.rs` required; up to 16 files, max 64 KiB/file, 256 KiB total).
- Submissions must be safe `#![no_std]` Rust (`-F unsafe-code` enforced; `unsafe`, `extern`, compile-time host exfiltration macros such as `include_str!`/`env!`, and linker attributes such as `#[link_section]`/`#[no_mangle]` are rejected with `400 Bad Request`).

### `Evaluation` Response Schema

```json
{
  "compiled": true,
  "formal": {
    "passed": 3,
    "total": 3,
    "feedback": ["formal verification closed every obligation (fast prebuilt LEAN_PATH)"]
  },
  "simulation": {
    "passed": 3,
    "total": 3,
    "feedback": []
  },
  "metrics": {
    "binary_bytes": 1508,
    "static_ram_bytes": 0,
    "state_bytes": 16,
    "peak_stack_bytes": 16,
    "total_ram_bytes": 16,
    "executed_instructions": 83,
    "max_step_instructions": 31,
    "avg_step_instructions": 27.666666666666668,
    "signals": { "fault": 1.0, "relay_closed": 0.0 }
  },
  "budgets": {
    "passed": true,
    "limits": {
      "max_ram_bytes": 256,
      "max_peak_stack_bytes": 256,
      "max_binary_bytes": 8192,
      "max_step_instructions": 500
    },
    "violations": []
  },
  "performance": {
    "score": 1.0,
    "efficiency": 0.5,
    "ratios": { "instructions": 1.0, "ram_bytes": 1.0 },
    "baselines": { "instructions": 83.0, "ram_bytes": 16.0 }
  },
  "reward": {
    "scheme": "correctness_gated_v1",
    "alpha": 0.5,
    "correctness": 1.0,
    "budget_passed": true,
    "efficiency": 0.5,
    "reward": 0.75,
    "gated": true
  }
}
```

#### Performance Metric Definitions

- `binary_bytes`: ARM Cortex-M4 ELF Flash occupancy (`.text` + `.rodata` + `.data`).
- `static_ram_bytes`: Static `.data` + `.bss` bytes from the ELF.
- `state_bytes`: `core::mem::size_of::<firmware::State>()`.
- `peak_stack_bytes`: Runtime peak stack depth inside `firmware::transition`, measured on Cortex-M4 via stack canary painting.
- `total_ram_bytes`: `static_ram_bytes + state_bytes`.
- `executed_instructions`: Exact sum of Cortex-M4 ARM Thumb-2 instructions spent inside `firmware::transition` across all scenario steps (idle polling `nop`s and harness I/O excluded).
- `max_step_instructions`: Worst-case single-step instruction count (WCET proxy).
- `avg_step_instructions`: Mean instructions per step.

#### Default Reward vs. Custom Rewards

The built-in `reward` field implements `correctness_gated_v1`:
- Reference-relative performance: weighted geometric mean $S(P) = \prod_i S_i(P)^{w_i}$ (reference = `1.0`; faster/smaller beats `1.0`).
- Efficiency: $E(P) = S(P) / (1 + S(P)) \in [0, 1)$.
- Reward: $R(P) = \alpha + (1 - \alpha) E(P)$ when formal, simulation, and budgets all pass (`gated: true`); strictly below $\alpha$ otherwise.

This is only one reference formula. Every response includes all raw `metrics`, `budgets.limits`, `performance.ratios`, and `performance.baselines` so you can compute any custom reward function client-side (see `firmwaregym.compute_reward` in the Python SDK).

---

## 3. OpenEnv-Compatible Adapter (`/ws`, `/mcp`, `/metadata`, `/schema`)

FirmwareGym implements the OpenEnv wire protocol (`openenv/OpenEnv`) so RL trainers and unmodified OpenEnv Python clients (`EnvClient` / `TextArenaEnv`) can run multi-turn episodes directly:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/metadata` | Environment metadata (`name`, `version`, `description`) |
| `GET` | `/schema` | JSON Schemas for `action`, `observation`, and `state` |
| `POST` | `/mcp` | JSON-RPC 2.0 (`openenv/session/create`, `openenv/session/close`, `tools/list`, `tools/call` for `list_tasks` & `get_task`) |
| `GET` | `/ws` | WebSocket RL episode endpoint (optional `?session_id=` and `?api_key=`) |

### WebSocket Messages (`/ws`)

**Client → Server**:
```json
{"type": "reset", "data": {"task_id": "overcurrent-trip", "seed": 0, "episode_id": "ep-1", "max_steps": 6}}
{"type": "step",  "data": {"files": {"src/lib.rs": "#![no_std] ..."}}}
{"type": "step",  "data": {"code": "#![no_std] ..."}}
{"type": "step",  "data": {"message": "```rust\n#![no_std] ...\n```"}}
{"type": "state"}
{"type": "close"}
```
- If `task_id` is omitted in `reset`, the server deterministically selects a task from `seed % num_tasks`.
- `step` accepts structured `files`, shorthand `code` (`src/lib.rs`), or a TextArenaEnv/LLM `message` containing a fenced Rust block.
- Episodes end (`done: true`) when `reward.gated == true` or `step_count >= max_steps`.

**Server → Client**:
```json
{"type": "observation", "data": {"observation": {...}, "reward": 0.75, "done": true, "metadata": {...}}}
{"type": "state", "data": {"episode_id": "ep-1", "task_id": "overcurrent-trip", "step_count": 1, "max_steps": 6, "done": true, "last_reward": 0.75, "best_reward": 0.75}}
{"type": "error", "data": {"code": "VALIDATION_ERROR", "message": "..."}}
```
