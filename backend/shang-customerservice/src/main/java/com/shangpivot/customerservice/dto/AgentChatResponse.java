package com.shangpivot.customerservice.dto;

import java.util.List;
import java.util.Map;

/**
 * C 端 AI 助手响应；字段从 Agent 服务的 snake_case 映射为 camelCase。
 */
public record AgentChatResponse(
        String runId,
        String traceId,
        String sessionId,
        String intent,
        String agent,
        String status,
        String answer,
        List<Map<String, Object>> tools,
        Double latencyMs
) {
}
