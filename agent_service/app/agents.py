"""Supervisor + 子 Agent：每个子 Agent 只做自己域内的事。"""
from __future__ import annotations

import json
import re
from typing import Any

from app.llm import LlmGateway
from app.models import AgentState
from app.tools import CommerceTools, ToolAuthError, ToolError, ToolResult


INTENT_AGENT = {
    "shopping": "ShoppingGuideAgent",
    "order_status": "OrderAgent",
    "after_sale": "AfterSaleAgent",
    "knowledge": "KnowledgeAgent",
    "handoff": "HandoffAgent",
}


def _trace(state: AgentState):
    return state.get("trace")


async def _call_answer(state: AgentState, prompt: str, fallback: str):
    trace = _trace(state)
    history = state.get("history") or []
    if history:
        history_text = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in history[-4:])
        prompt = f"历史对话：\n{history_text}\n\n当前任务：\n{prompt}"
    result = await state["llm"].answer(prompt, fallback)
    if trace:
        trace.add_llm(
            model=result.model,
            prompt=result.prompt,
            response=result.text,
            latency_ms=result.latency_ms,
            node=state.get("agent", "agent"),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    return result.text


async def _record_tool(state: AgentState, tool: ToolResult) -> None:
    trace = _trace(state)
    if trace:
        trace.add_tool(
            name=tool.name,
            args=tool.args,
            result=tool.result,
            status=tool.status,
            latency_ms=tool.latency_ms,
        )
        if tool.retrieval:
            trace.add_retrieval(
                query=str(tool.retrieval.get("query", "")),
                backend=str(tool.retrieval.get("backend", "unknown")),
                hits=tool.retrieval.get("hits") or [],
                fallback=bool(tool.retrieval.get("fallback")),
                error=tool.retrieval.get("error"),
            )


async def route(state: AgentState) -> dict[str, Any]:
    trace = _trace(state)
    result = await state["llm"].classify(state["message"])
    if trace:
        trace.add_llm(
            model=result.model,
            prompt=result.prompt,
            response=result.text,
            latency_ms=result.latency_ms,
            node="route",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    intent = "knowledge"
    match = re.search(r"\{.*\}", result.text, re.S)
    if match:
        try:
            intent = str(json.loads(match.group(0)).get("intent") or "knowledge")
        except Exception:
            pass
    if intent not in INTENT_AGENT:
        intent = "knowledge"
    return {"intent": intent, "agent": INTENT_AGENT[intent], "status": "routing"}


def route_to_agent(state: AgentState) -> str:
    return state.get("intent", "knowledge")


async def shopping_agent(state: AgentState) -> dict[str, Any]:
    tools: CommerceTools = state["tools"]
    tool = await tools.search_products(state["message"], 3)
    await _record_tool(state, tool)
    products = tool.result or []
    if not products:
        fallback = "暂时没有找到匹配商品。你可以换个关键词，或者告诉我预算和用途。"
    else:
        lines = [
            f"- {p.get('name')}：¥{p.get('price')}" + (f"–¥{p.get('priceMax')}" if p.get("priceMax") else "")
            for p in products
        ]
        fallback = "我找到这些商品：\n" + "\n".join(lines) + "\n需要我按价格或用途再筛一轮吗？"
    prompt = f"用户想购物：{state['message']}\n工具结果：{json.dumps(products, ensure_ascii=False)}\n请用简洁中文回答。"
    answer = await _call_answer(state, prompt, fallback)
    return {"agent": "ShoppingGuideAgent", "status": "ok", "answer": answer, "tool_results": [tool.to_dict()]}


async def order_agent(state: AgentState) -> dict[str, Any]:
    trace = _trace(state)
    token = state.get("authorization")
    if not token:
        return {
            "agent": "OrderAgent",
            "status": "need_auth",
            "answer": "查订单需要先登录。你可以在商城登录后再问我，或者我帮你转人工。",
            "tool_results": [],
        }
    try:
        tool = await state["tools"].get_orders(token, 5)
    except ToolAuthError:
        return {"agent": "OrderAgent", "status": "need_auth", "answer": "登录状态已失效，请重新登录后再试。", "tool_results": []}
    except ToolError as exc:
        if trace:
            trace.add_step("tool_error:getOrders", "failed", str(exc))
        return {"agent": "OrderAgent", "status": "failed", "answer": "订单服务暂时不可用，请稍后重试或转人工。", "tool_results": []}
    await _record_tool(state, tool)
    orders = tool.result or []
    if not orders:
        fallback = "你当前没有查到订单。如果刚下单，可能是数据还没同步。"
    else:
        lines = [
            f"- {o.get('orderNo')}：{o.get('status')}，应付 ¥{o.get('payAmount')}"
            for o in orders
        ]
        fallback = "我查到这些订单：\n" + "\n".join(lines) + "\n你想看哪一笔的物流？"
    prompt = f"用户问订单/物流：{state['message']}\n订单工具结果：{json.dumps(orders, ensure_ascii=False)}\n请回答并保留订单号。"
    answer = await _call_answer(state, prompt, fallback)
    return {"agent": "OrderAgent", "status": "ok", "answer": answer, "tool_results": [tool.to_dict()]}


async def after_sale_agent(state: AgentState) -> dict[str, Any]:
    trace = _trace(state)
    faq = await state["tools"].search_faq(state["message"], 2)
    await _record_tool(state, faq)
    rows = faq.result or []
    policy = rows[0].get("answer") if rows else "售后政策暂时不可用。"
    token = state.get("authorization")
    existing = []
    if token:
        try:
            sales = await state["tools"].get_after_sales(token, 5)
            await _record_tool(state, sales)
            existing = sales.result or []
        except ToolAuthError:
            existing = []
        except ToolError as exc:
            if trace:
                trace.add_step("tool_error:getAfterSales", "failed", str(exc))
    lines = [f"政策：{policy}"]
    if existing:
        lines.append("你已有的售后单：")
        lines.extend(f"- {r.get('id')}：{r.get('type')} / {r.get('status')}" for r in existing)
    lines.append("如果要发起退货/换货，我需要你确认订单和原因；写操作不会在本阶段自动执行。")
    fallback = "\n".join(lines)
    prompt = f"用户问售后：{state['message']}\n售后工具结果：{json.dumps(rows + existing, ensure_ascii=False)}\n请说明政策，并提示需要确认后才能创建售后。"
    answer = await _call_answer(state, prompt, fallback)
    return {
        "agent": "AfterSaleAgent",
        "status": "need_confirmation",
        "answer": answer,
        "tool_results": [faq.to_dict()],
    }


async def knowledge_agent(state: AgentState) -> dict[str, Any]:
    tool = await state["tools"].search_faq(state["message"], 2)
    await _record_tool(state, tool)
    rows = tool.result or []
    fallback = "\n".join(f"{r.get('question')}：{r.get('answer')}" for r in rows) or "我暂时没有找到相关答案。"
    prompt = f"用户问题：{state['message']}\n知识库：{json.dumps(rows, ensure_ascii=False)}\n只根据知识库回答，并说明政策可能变化。"
    answer = await _call_answer(state, prompt, fallback)
    return {"agent": "KnowledgeAgent", "status": "ok", "answer": answer, "tool_results": [tool.to_dict()]}


async def handoff_agent(state: AgentState) -> dict[str, Any]:
    return {
        "agent": "HandoffAgent",
        "status": "handoff",
        "answer": "这个问题需要人工进一步处理，我已经为你标记转人工。请补充订单号或联系方式，坐席会尽快接入。",
        "tool_results": [],
    }


AGENT_NODES = {
    "shopping": shopping_agent,
    "order_status": order_agent,
    "after_sale": after_sale_agent,
    "knowledge": knowledge_agent,
    "handoff": handoff_agent,
}
