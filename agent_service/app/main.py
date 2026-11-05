"""FastAPI entrypoint for the Phase-0 agent service."""
from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.graph import build_graph
from app.llm import build_llm
from app.models import ChatRequest, ChatResponse
from app.tools import CommerceTools
from app.tracing import PostgresTraceStore, TraceCallback, TraceRecord, TraceStore, new_id

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_DIR = ROOT / "artifacts"
STATIC_DIR = ROOT / "static"
EVAL_REPORTS = {
    "rule": {"label": "规则模型", "file": "report.json"},
    "real": {"label": "DeepSeek 真实模型", "file": "report-real.json"},
}


def build_trace_store(trace_dir: Path):
    backend = os.getenv("AGENT_TRACE_BACKEND", "jsonl").strip().lower()
    if backend == "postgres":
        return PostgresTraceStore(os.getenv("AGENT_PG_DSN", "").strip())
    return TraceStore(trace_dir / "agent-traces.jsonl")


class SessionStore:
    """本地参考实现：只保留最近几轮；生产应换 Redis/PostgreSQL。"""

    def __init__(self, limit: int = 6):
        self.limit = limit
        self._sessions: dict[str, list[dict[str, str]]] = {}

    def get(self, session_id: str) -> list[dict[str, str]]:
        return self._sessions.get(session_id, [])[-self.limit :]

    def append(self, session_id: str, role: str, content: str) -> None:
        rows = self._sessions.setdefault(session_id, [])
        rows.append({"role": role, "content": content})
        self._sessions[session_id] = rows[-self.limit :]


class AgentRuntime:
    def __init__(
        self,
        llm=None,
        tools=None,
        trace_store: TraceStore | None = None,
        knowledge_base=None,
    ):
        self.llm = llm or build_llm()
        base_url = os.getenv("COMMERCE_BASE_URL", "http://127.0.0.1:8086/api")
        if tools is None:
            from app.rag import build_knowledge_base

            self.knowledge_base = knowledge_base if knowledge_base is not None else build_knowledge_base()
            self.tools = CommerceTools(base_url, knowledge_base=self.knowledge_base)
        else:
            self.tools = tools
            self.knowledge_base = knowledge_base if knowledge_base is not None else getattr(tools, "knowledge_base", None)
        self.rag_error: str | None = None
        self.trace_error: str | None = None
        self._rag_initialized = False
        self._trace_initialized = False
        trace_dir = Path(os.getenv("AGENT_TRACE_DIR", str(DEFAULT_TRACE_DIR)))
        self.trace_dir = trace_dir
        self.trace_store = trace_store or build_trace_store(trace_dir)
        self.sessions = SessionStore()
        self.graph = build_graph()

    async def startup(self) -> None:
        await self._startup_trace()
        await self._startup_rag()

    async def _startup_trace(self) -> None:
        """PostgreSQL trace 建表；失败时降级 JSONL 并在 health 暴露原因。"""
        if self._trace_initialized or not isinstance(self.trace_store, PostgresTraceStore):
            return
        self._trace_initialized = True
        try:
            await asyncio.to_thread(self.trace_store.ensure_schema)
        except Exception as exc:  # noqa: BLE001 - trace 存储失败不阻止服务启动
            self.trace_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            self.trace_store = TraceStore(self.trace_dir / "agent-traces.jsonl")

    async def _startup_rag(self) -> None:
        """建表/首次入库；失败时降级关键词检索，并在 health 暴露原因。"""
        if self._rag_initialized or self.knowledge_base is None:
            return
        self._rag_initialized = True
        try:
            await asyncio.to_thread(self.knowledge_base.ensure_schema)
            count = await asyncio.to_thread(self.knowledge_base.count)
            if count == 0 and os.getenv("AGENT_RAG_AUTO_INGEST", "1").strip().lower() in {"1", "true", "yes", "on"}:
                from app.rag import faq_documents

                rows = faq_documents(ROOT / "data" / "faq.json")
                await asyncio.to_thread(self.knowledge_base.ingest, rows)
        except Exception as exc:  # noqa: BLE001 - RAG 失败不阻止服务启动
            self.rag_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            self.tools.knowledge_base = None
            self.knowledge_base = None

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        authorization: str | None = None,
        customer_id: str | None = None,
        trace_id: str | None = None,
    ) -> ChatResponse:
        started = time.perf_counter()
        session_id = session_id or new_id("sess")
        trace_id = trace_id or new_id("trace")
        run_id = new_id("run")
        trace = TraceRecord(
            run_id=run_id,
            trace_id=trace_id,
            session_id=session_id,
            customer_id=customer_id,
            channel="web_mall",
            message=message,
        )
        history = self.sessions.get(session_id)
        state = {
            "message": message,
            "session_id": session_id,
            "customer_id": customer_id,
            "authorization": authorization,
            "history": history,
            "tool_results": [],
            "trace": trace,
            "llm": self.llm,
            "tools": self.tools,
        }
        self.sessions.append(session_id, "user", message)
        try:
            result = await self.graph.ainvoke(
                state,
                config={
                    "callbacks": [TraceCallback(trace)],
                    "metadata": {
                        "trace_id": trace_id,
                        "session_id": session_id,
                        "customer_id": customer_id or "",
                        "channel": "web_mall",
                    },
                    "tags": ["phase0", "web_mall"],
                },
            )
            answer = result.get("answer") or "我暂时没有生成回答。"
            status = result.get("status") or "ok"
            agent = result.get("agent") or "UnknownAgent"
            intent = result.get("intent") or "unknown"
        except Exception as exc:  # noqa: BLE001 - 返回可读错误，服务不崩
            trace.add_step("runtime_error", "failed", str(exc)[:1000])
            answer = "Agent 服务暂时不可用，请稍后重试或转人工。"
            status = "failed"
            agent = "Supervisor"
            intent = "unknown"
            result = {}
        trace.finish(status=status, answer=answer, agent=agent, intent=intent)
        trace.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        try:
            self.trace_store.save(trace)
        except Exception as exc:  # noqa: BLE001 - trace 存储故障降级 JSONL，不影响回答
            self.trace_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            trace.add_step("trace_store_error", "failed", self.trace_error)
            self.trace_store = TraceStore(self.trace_dir / "agent-traces.jsonl")
            self.trace_store.save(trace)
        self.sessions.append(session_id, "assistant", answer)
        return ChatResponse(
            run_id=run_id,
            trace_id=trace_id,
            session_id=session_id,
            intent=intent,
            agent=agent,
            status=status,
            answer=answer,
            tools=(result.get("tool_results") or []),
            latency_ms=trace.latency_ms,
        )


runtime = AgentRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await runtime.startup()
    yield


app = FastAPI(title="ShangPivot Phase-0 Agent", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "UP",
        "llm": runtime.llm.model,
        "graph": "langgraph",
        "rag": runtime.knowledge_base.backend if runtime.knowledge_base else "disabled",
        "rag_error": runtime.rag_error,
        "trace_store": runtime.trace_store.backend,
        "trace_error": runtime.trace_error,
    }


@app.get("/eval", include_in_schema=False)
async def eval_dashboard():
    page = STATIC_DIR / "eval.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="eval dashboard not found")
    return FileResponse(page, media_type="text/html")


@app.get("/eval/reports")
async def eval_reports() -> list[dict[str, Any]]:
    rows = []
    for name, config in EVAL_REPORTS.items():
        path = ROOT / "eval" / config["file"]
        row: dict[str, Any] = {
            "name": name,
            "label": config["label"],
            "file": config["file"],
            "exists": path.exists(),
            "case_count": 0,
            "llm": None,
        }
        if path.exists():
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
                row["case_count"] = len(report.get("results") or [])
                row["llm"] = report.get("llm")
            except (OSError, json.JSONDecodeError):
                row["exists"] = False
        rows.append(row)
    return rows


@app.get("/eval/reports/{name}")
async def eval_report(name: str) -> JSONResponse:
    config = EVAL_REPORTS.get(name)
    if config is None:
        raise HTTPException(status_code=404, detail="report not found")
    path = ROOT / "eval" / config["file"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="report not generated yet")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"invalid report: {exc}") from exc
    return JSONResponse(report)


@app.post("/agent/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
    x_customer_id: str | None = Header(default=None),
    x_trace_id: str | None = Header(default=None),
) -> ChatResponse:
    return await runtime.chat(
        message=request.message,
        session_id=request.session_id,
        authorization=authorization,
        customer_id=x_customer_id,
        trace_id=x_trace_id,
    )


@app.get("/agent/runs/{run_id}")
async def get_run(run_id: str) -> JSONResponse:
    trace = runtime.trace_store.get(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="run not found")
    return JSONResponse(trace)


@app.get("/agent/runs")
async def list_runs() -> list[dict[str, Any]]:
    return runtime.trace_store.list()


@app.get("/agent/metrics")
async def metrics() -> dict[str, Any]:
    rows = runtime.trace_store.list()
    total = len(rows)
    by_status: dict[str, int] = {}
    by_intent: dict[str, int] = {}
    llm_calls = 0
    tool_calls = 0
    retrieval_calls = 0
    input_tokens = 0
    output_tokens = 0
    for row in rows:
        by_status[row.get("status", "unknown")] = by_status.get(row.get("status", "unknown"), 0) + 1
        by_intent[row.get("intent", "unknown")] = by_intent.get(row.get("intent", "unknown"), 0) + 1
        llm_calls += len(row.get("llm_calls") or [])
        tool_calls += len(row.get("tool_calls") or [])
        retrieval_calls += len(row.get("retrievals") or [])
        for call in row.get("llm_calls") or []:
            input_tokens += int(call.get("input_tokens") or 0)
            output_tokens += int(call.get("output_tokens") or 0)
    return {
        "runs": total,
        "by_status": by_status,
        "by_intent": by_intent,
        "llm_calls": llm_calls,
        "tool_calls": tool_calls,
        "retrieval_calls": retrieval_calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "avg_latency_ms": round(sum(row.get("latency_ms", 0) for row in rows) / total, 3) if total else 0,
    }
