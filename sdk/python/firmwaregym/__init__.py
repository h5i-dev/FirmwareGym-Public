"""Thin client for the FirmwareGym evaluation API (standard library only)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = [
    "BudgetReport",
    "Evaluation",
    "FirmwareGym",
    "FirmwareGymError",
    "Identity",
    "Job",
    "Metrics",
    "ObligationResult",
    "OpenEnvClient",
    "OpenEnvStepResult",
    "PerformanceReport",
    "RewardFn",
    "RewardReport",
    "Section",
    "Task",
    "TaskSummary",
    "compute_reward",
]

__version__ = "0.2.0"


class FirmwareGymError(Exception):
    """An HTTP or transport failure from the evaluation API."""

    def __init__(self, status: int, message: str, retry_after: int | None = None) -> None:
        super().__init__(f"{status}: {message}")
        self.status = status
        self.message = message
        self.retry_after = retry_after


@dataclass(frozen=True)
class Identity:
    key_id: str
    role: str
    rate_limit_per_min: int
    rate_limit_remaining: int
    active_jobs: int = 0
    max_concurrent_jobs: int = 0
    monthly_used: int = 0
    monthly_quota: int = 0
    monthly_remaining: int | None = None
    month: str = ""


@dataclass(frozen=True)
class TaskSummary:
    id: str
    title: str
    summary: str
    family: str = "control"
    level: str = "L1"
    tags: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.tags is None:
            object.__setattr__(self, "tags", [])


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    summary: str
    readme: str
    files: dict[str, str]
    formal: str
    simulation: str
    family: str = "control"
    level: str = "L1"
    tags: list[str] = None  # type: ignore[assignment]
    budgets: dict[str, Any] = None  # type: ignore[assignment]
    optimization: dict[str, Any] | None = None
    obligations: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.tags is None:
            object.__setattr__(self, "tags", [])
        if self.budgets is None:
            object.__setattr__(self, "budgets", {})


@dataclass(frozen=True)
class Section:
    passed: int
    total: int
    feedback: list[str]


@dataclass(frozen=True)
class Metrics:
    binary_bytes: int | None
    static_ram_bytes: int | None
    state_bytes: int | None
    total_ram_bytes: int | None
    executed_instructions: int | None
    signals: dict[str, float]
    peak_stack_bytes: int | None = None
    max_step_instructions: int | None = None
    avg_step_instructions: float | None = None


@dataclass(frozen=True)
class BudgetReport:
    passed: bool
    violations: list[str]
    limits: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.limits is None:
            object.__setattr__(self, "limits", {})


@dataclass(frozen=True)
class PerformanceReport:
    score: float
    efficiency: float
    ratios: dict[str, float]
    baselines: dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.baselines is None:
            object.__setattr__(self, "baselines", {})


@dataclass(frozen=True)
class RewardReport:
    alpha: float
    correctness: float
    budget_passed: bool
    efficiency: float
    reward: float
    gated: bool
    scheme: str = "correctness_gated_v1"


@dataclass(frozen=True)
class ObligationResult:
    id: str
    status: str
    feedback: str


@dataclass(frozen=True)
class Evaluation:
    compiled: bool
    formal: Section
    simulation: Section
    fuzz: Section | None = None
    metrics: Metrics | None = None
    budgets: BudgetReport | None = None
    performance: PerformanceReport | None = None
    reward: RewardReport | None = None
    obligations: list[ObligationResult] = field(default_factory=list)
    held_out: Section | None = None
    provenance: dict[str, Any] | None = None


@dataclass(frozen=True)
class Job:
    job_id: str
    task_id: str
    status: str
    created_at: int
    finished_at: int | None = None
    result: Evaluation | None = None
    error: str | None = None


class FirmwareGym:
    """Client for the FirmwareGym v1 HTTP API.

    Reads `FIRMWAREGYM_API_KEY` from the environment if `api_key` is omitted.
    Evaluation always runs against the public spec; hidden evaluation is operator-only.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("FIRMWAREGYM_API_KEY")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        return dict(self._request("GET", "/health", None))

    def whoami(self) -> Identity:
        body = self._request("GET", "/v1/me", None)
        usage = body.get("usage") or {}
        return Identity(
            key_id=str(body["key_id"]),
            role=str(body["role"]),
            rate_limit_per_min=int(body["rate_limit_per_min"]),
            rate_limit_remaining=int(body["rate_limit_remaining"]),
            active_jobs=int(usage.get("active_jobs", 0)),
            max_concurrent_jobs=int(usage.get("max_concurrent_jobs", 0)),
            monthly_used=int(usage.get("monthly_used", 0)),
            monthly_quota=int(usage.get("monthly_quota", 0)),
            monthly_remaining=(
                int(usage["monthly_remaining"])
                if usage.get("monthly_remaining") is not None
                else None
            ),
            month=str(usage.get("month", "")),
        )

    def list_tasks(self, *, family: str | None = None, level: str | None = None) -> list[TaskSummary]:
        params = {}
        if family:
            params["family"] = family
        if level:
            params["level"] = level
        qs = f"?{urllib.parse.urlencode(params)}" if params else ""
        body = self._request("GET", f"/v1/tasks{qs}", None)
        return [
            TaskSummary(
                id=item["id"],
                title=item["title"],
                summary=item["summary"],
                family=item.get("family", "control"),
                level=item.get("level", "L1"),
                tags=list(item.get("tags", [])),
            )
            for item in body["tasks"]
        ]

    def get_task(self, task_id: str) -> Task:
        body = self._request("GET", f"/v1/tasks/{task_id}", None)
        return Task(
            id=body["id"],
            title=body["title"],
            summary=body["summary"],
            readme=body["readme"],
            files=dict(body["files"]),
            formal=body["formal"],
            simulation=body["simulation"],
            family=body.get("family", "control"),
            level=body.get("level", "L1"),
            tags=list(body.get("tags", [])),
            budgets=dict(body.get("budgets", {})),
            optimization=body.get("optimization"),
            obligations=dict(body.get("obligations", {})),
        )

    def evaluate(self, task_id: str, files: dict[str, str], *, proof: str | None = None) -> Evaluation:
        payload: dict[str, Any] = {"files": files}
        if proof is not None:
            payload["proof"] = proof
        return _evaluation(self._request("POST", f"/v1/tasks/{task_id}/evaluate", payload))

    def submit_job(
        self,
        task_id: str,
        files: dict[str, str],
        *,
        proof: str | None = None,
        idempotency_key: str | None = None,
    ) -> Job:
        payload: dict[str, Any] = {"task_id": task_id, "files": files}
        if proof is not None:
            payload["proof"] = proof
        headers = {} if idempotency_key is None else {"Idempotency-Key": idempotency_key}
        return _job(self._request("POST", "/v1/jobs", payload, extra_headers=headers))

    def list_jobs(self) -> list[Job]:
        return [_job(body) for body in self._request("GET", "/v1/jobs", None)]

    def cancel_job(self, job_id: str) -> Job:
        return _job(self._request("DELETE", f"/v1/jobs/{job_id}", None))

    def get_job(self, job_id: str) -> Job:
        body = self._request("GET", f"/v1/jobs/{job_id}", None)
        return _job(body)

    def evaluate_async(
        self,
        task_id: str,
        files: dict[str, str],
        *,
        proof: str | None = None,
        poll_interval: float = 0.5,
        max_wait: float = 600.0,
    ) -> Evaluation:
        """Submit an async job and poll until completion (recommended for Renode / Lean 4)."""
        job = self.submit_job(task_id, files, proof=proof)
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            cur = self.get_job(job.job_id)
            if cur.status == "completed" and cur.result is not None:
                return cur.result
            if cur.status == "failed":
                raise FirmwareGymError(500, cur.error or "evaluation job failed")
            if cur.status == "canceled":
                raise FirmwareGymError(409, "evaluation job was canceled")
            time.sleep(poll_interval)
        raise FirmwareGymError(408, f"job {job.job_id} did not finish within {max_wait}s")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        data = None if payload is None else json.dumps(payload).encode()
        headers = dict(extra_headers or {})
        if data is not None:
            headers["content-type"] = "application/json"
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.base_url + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as err:
            raw = err.read().decode(errors="replace")
            message = raw
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "error" in parsed:
                    message = str(parsed["error"])
            except json.JSONDecodeError:
                pass
            retry_after = None
            ra = err.headers.get("Retry-After") if err.headers else None
            if ra and ra.isdigit():
                retry_after = int(ra)
            raise FirmwareGymError(err.code, message, retry_after=retry_after) from err
        except urllib.error.URLError as err:
            raise FirmwareGymError(0, str(err.reason)) from err


def _evaluation(body: dict[str, Any]) -> Evaluation:
    return Evaluation(
        compiled=bool(body["compiled"]),
        provenance=body.get("provenance"),
        formal=_section(body["formal"]),
        simulation=_section(body["simulation"]),
        held_out=_section(body["held_out"]) if body.get("held_out") else None,
        fuzz=_section(body["fuzz"]) if body.get("fuzz") else None,
        metrics=_metrics(body.get("metrics")),
        budgets=_budgets(body.get("budgets")),
        performance=_performance(body.get("performance")),
        reward=_reward(body.get("reward")),
        obligations=[ObligationResult(**item) for item in body.get("obligations", [])],
    )


def _job(body: dict[str, Any]) -> Job:
    return Job(
        job_id=str(body["job_id"]),
        task_id=str(body["task_id"]),
        status=str(body["status"]),
        created_at=int(body["created_at"]),
        finished_at=int(body["finished_at"]) if body.get("finished_at") is not None else None,
        result=_evaluation(body["result"]) if body.get("result") else None,
        error=str(body["error"]) if body.get("error") is not None else None,
    )


def _section(body: dict[str, Any]) -> Section:
    return Section(
        passed=int(body["passed"]),
        total=int(body["total"]),
        feedback=[str(line) for line in body["feedback"]],
    )


def _metrics(body: dict[str, Any] | None) -> Metrics | None:
    if not body:
        return None
    return Metrics(
        binary_bytes=body.get("binary_bytes"),
        static_ram_bytes=body.get("static_ram_bytes"),
        state_bytes=body.get("state_bytes"),
        total_ram_bytes=body.get("total_ram_bytes"),
        executed_instructions=body.get("executed_instructions"),
        signals={str(k): float(v) for k, v in body.get("signals", {}).items()},
        peak_stack_bytes=body.get("peak_stack_bytes"),
        max_step_instructions=body.get("max_step_instructions"),
        avg_step_instructions=(
            float(body["avg_step_instructions"])
            if body.get("avg_step_instructions") is not None
            else None
        ),
    )


def _budgets(body: dict[str, Any] | None) -> BudgetReport | None:
    if not body:
        return None
    return BudgetReport(
        passed=bool(body["passed"]),
        violations=[str(v) for v in body.get("violations", [])],
        limits=dict(body.get("limits", {})),
    )


def _performance(body: dict[str, Any] | None) -> PerformanceReport | None:
    if not body:
        return None
    return PerformanceReport(
        score=float(body["score"]),
        efficiency=float(body["efficiency"]),
        ratios={str(k): float(v) for k, v in body.get("ratios", {}).items()},
        baselines={str(k): float(v) for k, v in body.get("baselines", {}).items()},
    )


def _reward(body: dict[str, Any] | None) -> RewardReport | None:
    if not body:
        return None
    return RewardReport(
        scheme=str(body.get("scheme", "correctness_gated_v1")),
        alpha=float(body["alpha"]),
        correctness=float(body["correctness"]),
        budget_passed=bool(body["budget_passed"]),
        efficiency=float(body["efficiency"]),
        reward=float(body["reward"]),
        gated=bool(body["gated"]),
    )


RewardFn = Callable[[Evaluation], float]


def compute_reward(
    evaluation: Evaluation,
    *,
    alpha: float = 0.5,
    formal_weight: float = 0.5,
    metric_weights: dict[str, float] | None = None,
    require_formal: bool = True,
    require_budgets: bool = True,
) -> float:
    """Customizable client-side reward function built from raw Evaluation signals.

    The server's `evaluation.reward` is only one reference formula (`correctness_gated_v1`).
    Users can call `compute_reward(...)` with custom weights/gating or write their own
    `RewardFn = Callable[[Evaluation], float]` directly over `evaluation.formal`,
    `evaluation.simulation`, `evaluation.metrics`, and `evaluation.budgets`.
    """
    if not evaluation.compiled:
        return 0.0
    sim_frac = (
        evaluation.simulation.passed / evaluation.simulation.total
        if evaluation.simulation.total > 0
        else 0.0
    )
    formal_frac = (
        evaluation.formal.passed / evaluation.formal.total
        if evaluation.formal.total > 0
        else 0.0
    )
    sim_ok = evaluation.simulation.total > 0 and evaluation.simulation.passed == evaluation.simulation.total
    formal_ok = (not require_formal) or (
        evaluation.formal.total > 0 and evaluation.formal.passed == evaluation.formal.total
    )
    budget_ok = (not require_budgets) or (
        evaluation.budgets is None or evaluation.budgets.passed
    )

    w_f = formal_weight if require_formal else 0.0
    w_s = 1.0 - w_f
    correctness = w_f * formal_frac + w_s * sim_frac

    if not (sim_ok and formal_ok and budget_ok):
        return alpha * correctness * (1.0 if budget_ok else 0.5)

    efficiency = 0.5
    if evaluation.performance is not None:
        if metric_weights and evaluation.performance.ratios:
            import math

            log_sum = 0.0
            w_sum = 0.0
            for name, w in metric_weights.items():
                if w > 0.0 and name in evaluation.performance.ratios:
                    log_sum += w * math.log(max(evaluation.performance.ratios[name], 1e-6))
                    w_sum += w
            if w_sum > 0.0:
                score = math.exp(log_sum / w_sum)
                efficiency = score / (1.0 + score)
            else:
                efficiency = evaluation.performance.efficiency
        else:
            efficiency = evaluation.performance.efficiency
    return alpha + (1.0 - alpha) * efficiency


@dataclass(frozen=True)
class OpenEnvStepResult:
    observation: dict[str, Any]
    reward: float | None
    done: bool
    metadata: dict[str, Any]


class OpenEnvClient:
    """Zero-dependency OpenEnv WebSocket client for FirmwareGym (`/ws`).

    Speaks the OpenEnv wire protocol (`reset`, `step`, `state`, `close`) over RFC 6455
    WebSockets using only the Python standard library. Official OpenEnv Python clients
    (`TextArenaEnv` / `EnvClient`) can also connect to `/ws` directly.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("FIRMWAREGYM_API_KEY")
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._buf = bytearray()

    def connect(self, session_id: str | None = None) -> "OpenEnvClient":
        parsed = urllib.parse.urlparse(self.base_url)
        use_tls = parsed.scheme in ("https", "wss")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if use_tls else 80)
        path = (parsed.path.rstrip("/") or "") + "/ws"
        if session_id:
            path += f"?session_id={urllib.parse.quote(session_id)}"

        raw = socket.create_connection((host, port), timeout=self.timeout)
        if use_tls:
            ctx = ssl.create_default_context()
            raw = ctx.wrap_socket(raw, server_hostname=host)
        raw.settimeout(self.timeout)

        ws_key = base64.b64encode(os.urandom(16)).decode("ascii")
        lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {host}:{port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {ws_key}",
            "Sec-WebSocket-Version: 13",
        ]
        if self.api_key:
            lines.append(f"Authorization: Bearer {self.api_key}")
        req = ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
        raw.sendall(req)

        buf = bytearray()
        while b"\r\n\r\n" not in buf:
            chunk = raw.recv(4096)
            if not chunk:
                raw.close()
                raise FirmwareGymError(0, "WebSocket handshake closed unexpectedly")
            buf.extend(chunk)
        header_end = buf.index(b"\r\n\r\n") + 4
        header_text = buf[:header_end].decode("utf-8", errors="replace")
        status_line = header_text.splitlines()[0] if header_text else ""
        if " 101 " not in status_line:
            raw.close()
            raise FirmwareGymError(400, f"WebSocket upgrade rejected: {status_line}")
        expected_accept = base64.b64encode(
            hashlib.sha1((ws_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode("ascii")
        if expected_accept not in header_text:
            raw.close()
            raise FirmwareGymError(400, "invalid Sec-WebSocket-Accept header")

        self._sock = raw
        self._buf = bytearray(buf[header_end:])
        return self

    def __enter__(self) -> "OpenEnvClient":
        return self.connect()

    def __exit__(self, *_: Any) -> None:
        self.close()

    def reset(
        self,
        *,
        task_id: str | None = None,
        seed: int | None = None,
        episode_id: str | None = None,
        max_steps: int | None = None,
    ) -> OpenEnvStepResult:
        data: dict[str, Any] = {}
        if task_id is not None:
            data["task_id"] = task_id
        if seed is not None:
            data["seed"] = seed
        if episode_id is not None:
            data["episode_id"] = episode_id
        if max_steps is not None:
            data["max_steps"] = max_steps
        return self._expect_obs(self._exchange({"type": "reset", "data": data}))

    def step(
        self,
        *,
        files: dict[str, str] | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> OpenEnvStepResult:
        data: dict[str, Any] = {}
        if files is not None:
            data["files"] = files
        elif code is not None:
            data["code"] = code
        elif message is not None:
            data["message"] = message
        else:
            raise ValueError("step() requires one of `files`, `code`, or `message`")
        return self._expect_obs(self._exchange({"type": "step", "data": data}))

    def state(self) -> dict[str, Any]:
        msg = self._exchange({"type": "state"})
        if msg.get("type") == "error":
            err = msg.get("data", {})
            raise FirmwareGymError(400, f"{err.get('code')}: {err.get('message')}")
        return dict(msg.get("data", {}))

    def close(self) -> None:
        if self._sock is None:
            return
        try:
            self._send_text(json.dumps({"type": "close"}))
        except OSError:
            pass
        try:
            self._sock.close()
        finally:
            self._sock = None
            self._buf.clear()

    def _expect_obs(self, msg: dict[str, Any]) -> OpenEnvStepResult:
        if msg.get("type") == "error":
            err = msg.get("data", {})
            raise FirmwareGymError(400, f"{err.get('code')}: {err.get('message')}")
        data = msg.get("data", {})
        reward = data.get("reward")
        return OpenEnvStepResult(
            observation=dict(data.get("observation", {})),
            reward=float(reward) if reward is not None else None,
            done=bool(data.get("done", False)),
            metadata=dict(data.get("metadata", {})),
        )

    def _exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._sock is None:
            self.connect()
        self._send_text(json.dumps(payload))
        return json.loads(self._recv_text())

    def _send_text(self, text: str) -> None:
        assert self._sock is not None
        data = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(data))
        self._sock.sendall(header + masked)

    def _read_exact(self, n: int) -> bytes:
        assert self._sock is not None
        while len(self._buf) < n:
            chunk = self._sock.recv(max(4096, n - len(self._buf)))
            if not chunk:
                raise FirmwareGymError(0, "WebSocket closed by server")
            self._buf.extend(chunk)
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def _recv_text(self) -> str:
        while True:
            b0, b1 = self._read_exact(2)
            opcode = b0 & 0x0F
            masked = (b1 & 0x80) != 0
            length = b1 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise FirmwareGymError(0, "WebSocket closed by server")
            if opcode == 0x9:
                # Reply to ping with pong
                continue
            if opcode == 0x1:
                return payload.decode("utf-8")
