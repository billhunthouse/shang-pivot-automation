"""Request/response and graph state models."""
from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    run_id: str
    trace_id: str
    session_id: str
    intent: str
    agent: str
    status: str
    answer: str
    tools: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float


class AgentState(TypedDict, total=False):
    """LangGraph 共享状态；trace 只在进程内传递，不参与持久化。"""

    message: str
    session_id: str
    customer_id: str | None
    authorization: str | None
    intent: str
    agent: str
    answer: str
    status: str
    tool_results: list[dict[str, Any]]
    history: list[dict[str, str]]
    llm: Any
    tools: Any
    trace: Any
