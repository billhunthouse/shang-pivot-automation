package com.shangpivot.customerservice.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * C 端 AI 助手聊天请求。
 */
public record AgentChatRequest(
        @NotBlank(message = "message 不能为空")
        @Size(max = 2000, message = "message 不能超过 2000 字")
        String message,
        @Size(max = 128, message = "sessionId 不能超过 128 字")
        String sessionId
) {
}
