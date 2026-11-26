# FirmwareGym API & OpenEnv Protocol Specification

**API Version**: `0.2.0`  
**OpenAPI Schema**: [`openapi.json`](openapi.json) (also served live at `GET /openapi.json`, with interactive docs at `GET /docs`)

All public API endpoints evaluate submissions against **public specifications only**. Some tasks also run public development checks. Final held-out scenarios and private fuzzing remain operator-only.

---

## 1. Authentication & Quotas

Pass your API key on every authenticated request via either header:

```http
Authorization: Bearer fg_live_<token>
# or
X-API-Key: fg_live_<token>
```

Send the authorization header on the WebSocket upgrade request. The Python OpenEnv client sets it automatically.

### Rate Limits & Tenant Quotas

Quotas are enforced server-side per tenant:
- **Burst rate limit**: Sliding 60-second window (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `429 Too Many Requests` + `Retry-After`).
- **Per-tenant concurrency cap**: Limits simultaneous in-flight/queued evaluations per tenant (`429 Too Many Requests` + `Retry-After`).
- **Monthly quota**: Persistent UTC calendar-month evaluation cap (`429 Too Many Requests`). Rejected `400 Bad Request` submissions do **not** consume your monthly quota.
- **Per-tenant waiting queue**: Returns `429 Too Many Requests` when your tenant fills its waiting allocation.
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
| `GET` | `/v1/tasks/{id}` | Required | Fetch task README, starter Rust crate, public Lean 4 spec, fixed `obligations` keyed by theorem ID, budgets, optimization config, and public scenario YAML |
| `POST` | `/v1/tasks/{id}/evaluate` | Required | Synchronous evaluation with `files` and optional `proof` |
| `POST` | `/v1/jobs` | Required | Submit `task_id`, `files`, and optional `proof`. Returns `202 Accepted` with a job ID |
| `GET` | `/v1/jobs` | Required | List the caller’s jobs, newest first |
| `GET` | `/v1/jobs/{job_id}` | Required | Poll the job and read its evaluation once it completes |
| `DELETE` | `/v1/jobs/{job_id}` | Required | Cancel a queued or running job owned by the caller |

For an async retry, send the same `Idempotency-Key` header and the same payload. While the job is retained, this returns the existing job ID. Reusing the key with a different request returns `409 Conflict`. Each tenant has its own key namespace.

Jobs start as `queued`, then become `running`. Terminal states are `completed`, `failed`, and `canceled`. A running job enters `canceling` while the worker stops its subprocesses. A queued cancellation releases reserved quota. An evaluation that already started retains its charge. When persistent job storage is enabled, completed results survive restart and interrupted jobs become `failed`.

### Submission Rules

- Files must live under `src/` and end with `.rs` (`src/lib.rs` required; up to 16 files, max 64 KiB/file, 256 KiB total).
- Submissions must be safe `#![no_std]` Rust (`-F unsafe-code` enforced; `unsafe`, `extern`, compile-time host exfiltration macros such as `include_str!`/`env!`, and linker attributes such as `#[link_section]`/`#[no_mangle]` are rejected with `400 Bad Request`).

For formal credit, pass `proof` as the UTF-8 contents of one Lean module (up to 256 KiB). Import `Firmware` and `Spec` as required by the task and implement each fixed theorem as `FirmwareGymSubmission.<id>`. Keep the statement unchanged. Put any helper definitions and lemmas in the same module. The grader extracts `Firmware` from the submitted Rust for the Cortex-M target used by Renode. A theorem that depends on `sorry` cannot earn credit. See the [sample proof template](../examples/overcurrent_starter/proofs/Submission.lean).

### `Evaluation` Response Schema

```json
{
  "compiled": true,
  "formal": {
    "passed": 1,
    "total": 1,
    "feedback": []
  },
  "obligations": [
    { "id": "trips_on_overcurrent", "status": "proved", "feedback": "" }
  ],
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
    "scheme": "correctness_gated_proof_v2",
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

A proof submission includes an independent verdict for each fixed theorem. `proved` earns credit, `unproved` means the theorem was not accepted, and `not_checked` means the grader could not reach that check. Rust-only evaluation can return a formal total of zero. Check that the formal total is positive when a custom reward requires proof.

The server returns the reward scheme in `reward.scheme`. Proof submissions use `correctness_gated_proof_v2` and need all required proof checks, public runtime checks, and resource budgets to pass for the performance bonus. Rust-only evaluation uses `correctness_gated_v1`. Use the reported metrics and baseline ratios for custom rewards and handle metrics that are absent.

---

## 3. OpenEnv-Compatible Adapter (`/ws`, `/mcp`, `/metadata`, `/schema`)

Use REST for proof submissions. OpenEnv steps submit Rust for development feedback. FirmwareGym implements the OpenEnv wire protocol (`openenv/OpenEnv`) so RL trainers and unmodified OpenEnv Python clients (`EnvClient` / `TextArenaEnv`) can run multi-turn episodes directly:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/metadata` | Environment metadata (`name`, `version`, `description`) |
| `GET` | `/schema` | JSON Schemas for `action`, `observation`, and `state` |
| `POST` | `/mcp` | JSON-RPC 2.0 (`openenv/session/create`, `openenv/session/close`, `tools/list`, `tools/call` for `list_tasks` & `get_task`) |
| `GET` | `/ws` | WebSocket RL episode endpoint (optional `?session_id=` for reconnects) |

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
