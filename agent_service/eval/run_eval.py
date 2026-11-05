#!/usr/bin/env python3
"""Phase-0 离线评测：确定性指标 + 可读报告。"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.llm import RuleBasedLlmGateway, build_llm  # noqa: E402
from app.main import AgentRuntime  # noqa: E402
from app.tools import FakeCommerceTools  # noqa: E402
from app.tracing import TraceStore  # noqa: E402


async def run_case(runtime: AgentRuntime, case: dict) -> dict:
    response = await runtime.chat(
        message=case["message"],
        authorization=case.get("auth"),
        session_id=f"eval-{case['case_id']}",
    )
    trace = runtime.trace_store.get(response.run_id) or {}
    tools = [tool["name"] for tool in trace.get("tool_calls") or []]
    expected_tool = case.get("expected_tool")
    answer = response.answer or ""
    required_facts = case.get("answer_facts") or []
    any_facts = case.get("answer_any") or []
    fact_hit = all(fact in answer for fact in required_facts) and (
        not any_facts or any(fact in answer for fact in any_facts)
    )
    return {
        "case_id": case["case_id"],
        "message": case["message"],
        "run_id": response.run_id,
        "trace_id": response.trace_id,
        "actual_intent": response.intent,
        "expected_intent": case["expected_intent"],
        "intent_ok": response.intent == case["expected_intent"],
        "actual_agent": response.agent,
        "expected_agent": case["expected_agent"],
        "agent_ok": response.agent == case["expected_agent"],
        "actual_status": response.status,
        "expected_status": case["expected_status"],
        "status_ok": response.status == case["expected_status"],
        "tools": tools,
        "expected_tool": expected_tool,
        "tool_ok": (expected_tool in tools) if expected_tool else True,
        "answer_facts": required_facts,
        "answer_any": any_facts,
        "answer": answer,
        "fact_ok": fact_hit,
        "latency_ms": response.latency_ms,
        "trace_llm_calls": len(trace.get("llm_calls") or []),
        "trace_tool_calls": len(trace.get("tool_calls") or []),
        "trace": trace,
    }


def select_llm(kind: str):
    if kind == "rule":
        return RuleBasedLlmGateway()
    if kind != "openai":
        raise ValueError(f"unknown llm kind: {kind}")
    llm = build_llm()
    if llm.model == "rule-based":
        raise SystemExit("OpenAI-compatible LLM 未配置：请设置 AGENT_LLM_BASE_URL/AGENT_LLM_MODEL/AGENT_LLM_API_KEY_FILE")
    return llm


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", choices=["rule", "openai"], default=os.getenv("EVAL_LLM", "rule"))
    parser.add_argument("--report", default="")
    args = parser.parse_args()
    cases = [json.loads(line) for line in (ROOT / "eval" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    llm = select_llm(args.llm)
    with tempfile.TemporaryDirectory() as temp:
        runtime = AgentRuntime(
            llm=llm,
            tools=FakeCommerceTools(),
            trace_store=TraceStore(Path(temp) / "eval-traces.jsonl"),
        )
        results = [await run_case(runtime, case) for case in cases]
    total = len(results)
    metrics = {
        "total": total,
        "intent_accuracy": round(sum(r["intent_ok"] for r in results) / total, 4),
        "agent_accuracy": round(sum(r["agent_ok"] for r in results) / total, 4),
        "status_accuracy": round(sum(r["status_ok"] for r in results) / total, 4),
        "tool_accuracy": round(sum(r["tool_ok"] for r in results) / total, 4),
        "answer_fact_accuracy": round(sum(r["fact_ok"] for r in results) / total, 4),
        "trace_coverage": round(sum(r["trace_llm_calls"] > 0 for r in results) / total, 4),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / total, 3),
    }
    metrics["case_pass_rate"] = round(
        sum(all(r[k] for k in ["intent_ok", "agent_ok", "status_ok", "tool_ok", "fact_ok"]) for r in results) / total,
        4,
    )
    report = {"llm": llm.model, "metrics": metrics, "results": results}
    out = ROOT / "eval" / (args.report or ("report.json" if args.llm == "rule" else "report-real.json"))
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\nreport: {out}")
    return 0 if metrics["case_pass_rate"] >= 0.8 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
