"""Agent trace：记录 graph 节点、LLM 输入/输出、工具入参/出参。"""
from __future__ import annotations

import json
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def estimate_tokens(text: str) -> int:
    # 只用于本地 trace 的成本估算；真实模型以 usage 为准。
    return max(1, len(text or "") // 4)


_PII_PATTERNS = [
    (re.compile(r"(1[3-9]\d{9})"), lambda m: m.group(1)[:3] + "****" + m.group(1)[-4:]),
    (re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})"), lambda m: m.group(1)[:2] + "***@" + m.group(2)),
]


def redact(value: Any) -> Any:
    """递归脱敏；trace 中不保存完整手机号/邮箱。"""
    if isinstance(value, str):
        text = value
        for pattern, repl in _PII_PATTERNS:
            text = pattern.sub(repl, text)
        return text
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key.lower() in {"authorization", "token", "access_token", "password", "secret"}:
                result[key] = "***"
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


@dataclass
class TraceRecord:
    run_id: str
    trace_id: str
    session_id: str
    customer_id: str | None
    channel: str
    message: str
    started_at: str = field(default_factory=now_iso)
    finished_at: str | None = None
    intent: str = ""
    agent: str = ""
    status: str = "running"
    answer: str = ""
    error: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
    llm_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    retrievals: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0

    def add_step(self, name: str, status: str = "ok", detail: Any = None) -> None:
        self.steps.append(
            {"name": name, "status": status, "at": now_iso(), "detail": redact(detail)}
        )

    def add_llm(
        self,
        *,
        model: str,
        prompt: str,
        response: str,
        latency_ms: float,
        node: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        self.llm_calls.append(
            {
                "node": node,
                "model": model,
                "prompt": redact(prompt),
                "response": redact(response),
                "input_tokens": input_tokens if input_tokens is not None else estimate_tokens(prompt),
                "output_tokens": output_tokens if output_tokens is not None else estimate_tokens(response),
                "latency_ms": round(latency_ms, 3),
                "at": now_iso(),
            }
        )

    def add_tool(
        self,
        *,
        name: str,
        args: Any,
        result: Any,
        status: str,
        latency_ms: float,
    ) -> None:
        self.tool_calls.append(
            {
                "name": name,
                "args": redact(args),
                "result": redact(result),
                "status": status,
                "latency_ms": round(latency_ms, 3),
                "at": now_iso(),
            }
        )

    def add_retrieval(
        self,
        *,
        query: str,
        backend: str,
        hits: list[dict[str, Any]],
        fallback: bool = False,
        error: str | None = None,
    ) -> None:
        self.retrievals.append(
            {
                "query": redact(query),
                "backend": backend,
                "hits": redact(hits),
                "fallback": fallback,
                "error": redact(error),
                "at": now_iso(),
            }
        )

    def finish(self, *, status: str, answer: str, agent: str, intent: str) -> None:
        self.finished_at = now_iso()
        self.status = status
        self.answer = answer
        self.agent = agent
        self.intent = intent
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.finished_at)
        self.latency_ms = round((end - start).total_seconds() * 1000, 3)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TraceStore:
    """本地参考实现：内存 + JSONL。"""

    backend = "jsonl"

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, TraceRecord] = {}
        self._lock = threading.Lock()

    def save(self, trace: TraceRecord) -> None:
        with self._lock:
            self._records[trace.run_id] = trace
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")

    def get(self, run_id: str) -> dict[str, Any] | None:
        trace = self._records.get(run_id)
        return trace.to_dict() if trace else None

    def list(self) -> list[dict[str, Any]]:
        return [trace.to_dict() for trace in self._records.values()]


class PostgresTraceStore:
    """生产参考：run 元数据 + 完整 trace JSONB 落 PostgreSQL。"""

    backend = "postgres"

    def __init__(self, dsn: str, table: str = "agent_run_trace"):
        if not table.replace("_", "").isalnum():
            raise ValueError(f"invalid table name: {table}")
        self.dsn = dsn
        self.table = table
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _connect(self):
        import psycopg

        return psycopg.connect(self.dsn, connect_timeout=5)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table} (
                        run_id TEXT PRIMARY KEY,
                        trace_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        customer_id TEXT,
                        channel TEXT,
                        message TEXT,
                        intent TEXT,
                        agent TEXT,
                        status TEXT,
                        answer TEXT,
                        latency_ms DOUBLE PRECISION,
                        started_at TIMESTAMPTZ,
                        finished_at TIMESTAMPTZ,
                        payload JSONB NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table}_started_idx ON {self.table} (started_at DESC)"
                )
                cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table}_session_idx ON {self.table} (session_id)"
                )

    def save(self, trace: TraceRecord) -> None:
        data = trace.to_dict()
        with self._lock:
            self._cache[trace.run_id] = data
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.table}
                        (run_id, trace_id, session_id, customer_id, channel, message,
                         intent, agent, status, answer, latency_ms, started_at, finished_at, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s::timestamptz, %s::timestamptz, %s::jsonb)
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        answer = EXCLUDED.answer,
                        latency_ms = EXCLUDED.latency_ms,
                        finished_at = EXCLUDED.finished_at,
                        payload = EXCLUDED.payload
                    """,
                    (
                        trace.run_id,
                        trace.trace_id,
                        trace.session_id,
                        trace.customer_id,
                        trace.channel,
                        trace.message,
                        trace.intent,
                        trace.agent,
                        trace.status,
                        trace.answer,
                        trace.latency_ms,
                        trace.started_at,
                        trace.finished_at,
                        json.dumps(data, ensure_ascii=False),
                    ),
                )

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            cached = self._cache.get(run_id)
        if cached is not None:
            return cached
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT payload FROM {self.table} WHERE run_id = %s", (run_id,))
                row = cur.fetchone()
        if row is None:
            return None
        with self._lock:
            self._cache[run_id] = row[0]
        return row[0]

    def list(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload FROM {self.table} ORDER BY started_at DESC LIMIT %s",
                    (limit,),
                )
                return [row[0] for row in cur.fetchall()]


class TraceCallback(BaseCallbackHandler):
    """LangGraph/LangChain 回调：记录 graph 节点起止，验证 callback 链路可用。"""

    def __init__(self, trace: TraceRecord):
        self.trace = trace

    def on_chain_start(self, serialized, inputs, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or "chain"
        if name not in {"LangGraph", "__start__"}:
            self.trace.add_step(f"chain_start:{name}", "running")

    def on_chain_end(self, outputs, **kwargs):
        name = kwargs.get("name") or "chain"
        if name not in {"LangGraph", "__start__"}:
            self.trace.add_step(f"chain_end:{name}", "ok")

    def on_chain_error(self, error, **kwargs):
        self.trace.add_step(f"chain_error:{kwargs.get('name', 'chain')}", "failed", str(error)[:500])
