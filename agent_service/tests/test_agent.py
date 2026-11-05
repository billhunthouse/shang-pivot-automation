"""Phase-0 Agent 服务单测：路由、工具、trace、确认边界。"""
from __future__ import annotations

import pytest

from app.llm import RuleBasedLlmGateway
from app.main import AgentRuntime
from app.tools import FakeCommerceTools
from app.tracing import TraceStore


def runtime(tmp_path):
    return AgentRuntime(
        llm=RuleBasedLlmGateway(),
        tools=FakeCommerceTools(),
        trace_store=TraceStore(tmp_path / "traces.jsonl"),
    )


@pytest.mark.asyncio
async def test_shopping_routes_and_traces(tmp_path):
    rt = runtime(tmp_path)
    response = await rt.chat("帮我找一顶露营帐篷")
    assert response.intent == "shopping"
    assert response.agent == "ShoppingGuideAgent"
    assert response.status == "ok"
    assert "帐篷" in response.answer
    trace = rt.trace_store.get(response.run_id)
    assert trace is not None
    assert trace["llm_calls"], "应记录模型输入/输出"
    assert trace["tool_calls"][0]["name"] == "searchProducts"
    assert trace["tool_calls"][0]["args"]["query"]
    assert trace["steps"], "应记录 LangGraph 节点事件"


@pytest.mark.asyncio
async def test_order_without_token_requires_auth(tmp_path):
    rt = runtime(tmp_path)
    response = await rt.chat("我的订单到哪了？")
    assert response.intent == "order_status"
    assert response.agent == "OrderAgent"
    assert response.status == "need_auth"
    assert "登录" in response.answer


@pytest.mark.asyncio
async def test_order_with_token_calls_tool(tmp_path):
    rt = runtime(tmp_path)
    response = await rt.chat("我的订单到哪了？", authorization="Bearer test-token")
    assert response.status == "ok"
    assert "O202611050001" in response.answer
    trace = rt.trace_store.get(response.run_id)
    assert any(call["name"] == "getOrders" for call in trace["tool_calls"])
    assert "test-token" not in str(trace), "trace 不能保存 token"


@pytest.mark.asyncio
async def test_after_sale_is_confirmation_only(tmp_path):
    rt = runtime(tmp_path)
    response = await rt.chat("鞋不合脚，想退货", authorization="Bearer test-token")
    assert response.intent == "after_sale"
    assert response.agent == "AfterSaleAgent"
    assert response.status == "need_confirmation"
    trace = rt.trace_store.get(response.run_id)
    tool_names = [call["name"] for call in trace["tool_calls"]]
    assert "searchFaq" in tool_names
    # Phase-0 没有写工具；未来接入 createAfterSale 后，这里应断言“确认前不调用”
    assert "createAfterSale" not in tool_names


@pytest.mark.asyncio
async def test_handoff(tmp_path):
    rt = runtime(tmp_path)
    response = await rt.chat("我要投诉，转人工")
    assert response.intent == "handoff"
    assert response.agent == "HandoffAgent"
    assert response.status == "handoff"


@pytest.mark.asyncio
async def test_session_history_is_in_prompt(tmp_path):
    rt = runtime(tmp_path)
    first = await rt.chat("帮我找一顶露营帐篷")
    second = await rt.chat("再推荐一个", session_id=first.session_id)
    trace = rt.trace_store.get(second.run_id)
    answer_calls = [c for c in trace["llm_calls"] if c["node"] == second.agent]
    assert answer_calls
    assert "历史对话" in answer_calls[0]["prompt"]
    assert "帮我找一顶露营帐篷" in answer_calls[0]["prompt"]


class FakeKnowledgeBase:
    backend = "fake-vector"

    async def search(self, query: str, limit: int = 2):
        return [
            {
                "source": "faq.md",
                "title": "退款到账",
                "content": "退款审核通过后通常 1-3 个工作日到账。",
                "score": 0.93,
            }
        ][:limit]


class BrokenKnowledgeBase:
    backend = "broken"

    async def search(self, query: str, limit: int = 2):
        raise RuntimeError("vector db unavailable")


@pytest.mark.asyncio
async def test_retrieval_is_traced(tmp_path):
    rt = AgentRuntime(
        llm=RuleBasedLlmGateway(),
        tools=FakeCommerceTools(knowledge_base=FakeKnowledgeBase()),
        trace_store=TraceStore(tmp_path / "traces.jsonl"),
    )
    response = await rt.chat("退款一般多久到账？")
    assert response.agent == "KnowledgeAgent"
    trace = rt.trace_store.get(response.run_id)
    assert trace["retrievals"][0]["backend"] == "fake-vector"
    assert trace["retrievals"][0]["hits"][0]["score"] == 0.93
    assert trace["retrievals"][0]["fallback"] is False


@pytest.mark.asyncio
async def test_retrieval_failure_falls_back_to_keyword(tmp_path):
    rt = AgentRuntime(
        llm=RuleBasedLlmGateway(),
        tools=FakeCommerceTools(knowledge_base=BrokenKnowledgeBase()),
        trace_store=TraceStore(tmp_path / "traces.jsonl"),
    )
    response = await rt.chat("退款一般多久到账？")
    assert response.status == "ok"
    trace = rt.trace_store.get(response.run_id)
    retrieval = trace["retrievals"][0]
    assert retrieval["backend"] == "keyword"
    assert retrieval["fallback"] is True
    assert "vector db unavailable" in retrieval["error"]
