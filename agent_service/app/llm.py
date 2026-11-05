"""LLM 网关：默认规则模型，支持切换到 OpenAI-compatible 接口。"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import httpx
from pathlib import Path


@dataclass
class LlmResult:
    text: str
    model: str
    prompt: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None


class LlmGateway:
    model: str = "rule-based"

    async def classify(self, message: str) -> LlmResult:
        raise NotImplementedError

    async def answer(self, prompt: str, fallback: str) -> LlmResult:
        raise NotImplementedError


class RuleBasedLlmGateway(LlmGateway):
    """无外部依赖的本地参考模型。

    它不是“假装大模型”：它明确作为规则兜底/Phase-0 验证模型，
    用来验证 LangGraph 编排、工具调用、trace 字段和评测流程。
    配置真实 OpenAI-compatible 网关后由 OpenAiCompatibleLlmGateway 替换。
    """

    model = "rule-based"

    async def classify(self, message: str) -> LlmResult:
        started = time.perf_counter()
        text = message.lower()
        if any(word in message for word in ["订单", "物流", "发货", "到哪", "快递", "order"]):
            intent = "order_status"
        elif any(word in message for word in ["退货", "换货", "售后"]) or (
            "退款" in message and any(word in message for word in ["想", "申请", "我要", "帮我退"])
        ):
            intent = "after_sale"
        elif any(word in message for word in ["退款", "到账", "发票", "开票", "政策", "怎么", "多久", "支持"]):
            intent = "knowledge"
        elif any(word in message for word in ["推荐", "找", "买", "商品", "搜索", "帐篷", "鞋"]):
            intent = "shopping"
        elif any(word in message for word in ["转人工", "人工", "投诉"]):
            intent = "handoff"
        else:
            intent = "knowledge"
        prompt = f"你是电商意图路由器。用户消息：{message}\n只输出意图 JSON。"
        response = json.dumps({"intent": intent, "confidence": 0.82}, ensure_ascii=False)
        return LlmResult(
            text=response,
            model=self.model,
            prompt=prompt,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def answer(self, prompt: str, fallback: str) -> LlmResult:
        started = time.perf_counter()
        return LlmResult(
            text=fallback,
            model=self.model,
            prompt=prompt,
            latency_ms=(time.perf_counter() - started) * 1000,
        )


class OpenAiCompatibleLlmGateway(LlmGateway):
    """OpenAI-compatible /chat/completions；不绑定具体供应商。"""

    def __init__(self, base_url: str, api_key: str, model: str, max_tokens: int = 512):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    async def _chat(self, system: str, user: str) -> tuple[str, int | None, int | None, float]:
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "max_tokens": self.max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            body = response.json()
        usage = body.get("usage") or {}
        content = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return (
            content,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            (time.perf_counter() - started) * 1000,
        )

    async def classify(self, message: str) -> LlmResult:
        system = """你是尚品汇电商意图路由器。只输出一个 JSON 对象，不要解释。
intent 只能是：shopping | order_status | after_sale | knowledge | handoff。
判定优先级：
1. 投诉、要求转人工 -> handoff
2. 明确要发起退货、换货、退款申请或售后 -> after_sale
3. 查询自己的订单、物流、发货进度 -> order_status
4. 找商品、推荐商品、购买商品 -> shopping
5. 咨询政策、规则、时效、发票、退款到账、流程 -> knowledge
示例：
用户：帮我找一顶露营帐篷 -> {"intent":"shopping","confidence":0.97}
用户：我的订单到哪了？ -> {"intent":"order_status","confidence":0.96}
用户：鞋不合脚，想退货 -> {"intent":"after_sale","confidence":0.95}
用户：退款一般多久到账？ -> {"intent":"knowledge","confidence":0.95}
用户：支持开票吗？ -> {"intent":"knowledge","confidence":0.95}
用户：我要投诉，转人工 -> {"intent":"handoff","confidence":0.98}"""
        content, pin, pout, latency = await self._chat(system, message)
        return LlmResult(content, self.model, f"{system}\n用户：{message}", latency, pin, pout)

    async def answer(self, prompt: str, fallback: str) -> LlmResult:
        system = "你是尚品汇电商客服。只根据给定事实回答；不确定时建议转人工。"
        content, pin, pout, latency = await self._chat(system, prompt)
        if not content.strip():
            content = fallback
        return LlmResult(content, self.model, f"{system}\n{prompt}", latency, pin, pout)


def _read_api_key() -> str:
    key_file = os.getenv("AGENT_LLM_API_KEY_FILE", "").strip()
    if key_file:
        return Path(os.path.expanduser(key_file)).read_text(encoding="utf-8").strip()
    return os.getenv("AGENT_LLM_API_KEY", "").strip()


def build_llm() -> LlmGateway:
    base_url = os.getenv("AGENT_LLM_BASE_URL", "").strip()
    api_key = _read_api_key()
    model = os.getenv("AGENT_LLM_MODEL", "").strip()
    max_tokens = int(os.getenv("AGENT_LLM_MAX_TOKENS", "512"))
    if base_url and api_key and model:
        return OpenAiCompatibleLlmGateway(base_url, api_key, model, max_tokens)
    return RuleBasedLlmGateway()
