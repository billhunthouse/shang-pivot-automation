package com.shangpivot.customerservice.controller;

import com.shangpivot.common.result.Result;
import com.shangpivot.customerservice.application.CustomerServiceAgentClient;
import com.shangpivot.customerservice.dto.AgentChatRequest;
import com.shangpivot.customerservice.dto.AgentChatResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 商城 C 端 AI 助手 API。
 */
@RestController
@RequestMapping("/api/customer-service")
@Tag(name = "AI 助手", description = "商品推荐、知识问答、订单查询")
public class CustomerServiceController {

    private final CustomerServiceAgentClient agentClient;

    public CustomerServiceController(CustomerServiceAgentClient agentClient) {
        this.agentClient = agentClient;
    }

    @PostMapping("/chat")
    @Operation(summary = "AI 助手对话", description = "匿名可用；订单查询需透传商城登录态")
    public Result<AgentChatResponse> chat(
            @Valid @RequestBody AgentChatRequest request,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization
    ) {
        return Result.ok(agentClient.chat(request, authorization));
    }
}
