package com.shangpivot.customerservice.application;

import com.shangpivot.common.exception.BizException;
import com.shangpivot.common.result.ErrorCode;
import com.shangpivot.customerservice.dto.AgentChatRequest;
import com.shangpivot.customerservice.dto.AgentChatResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Agent 服务的薄代理：只负责协议转换和登录态透传，不解析 JWT、不保存 token。
 */
@Component
public class CustomerServiceAgentClient {

    private static final Logger log = LoggerFactory.getLogger(CustomerServiceAgentClient.class);

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String baseUrl;
    private final Duration timeout;

    public CustomerServiceAgentClient(
            @Value("${shang.agent.base-url:http://127.0.0.1:8088}") String baseUrl,
            @Value("${shang.agent.timeout-seconds:60}") int timeoutSeconds,
            ObjectMapper objectMapper
    ) {
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.timeout = Duration.ofSeconds(timeoutSeconds);
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public AgentChatResponse chat(AgentChatRequest request, String authorization) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("message", request.message());
        if (StringUtils.hasText(request.sessionId())) {
            payload.put("session_id", request.sessionId());
        }

        try {
            HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(baseUrl + "/agent/chat"))
                    .timeout(timeout)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(payload)));
            if (StringUtils.hasText(authorization)) {
                builder.header(HttpHeaders.AUTHORIZATION, authorization);
            }
            HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 400) {
                log.warn("Agent 服务返回 HTTP {}: {}", response.statusCode(), response.body());
                throw new BizException(ErrorCode.SYSTEM_ERROR, "AI 助手暂时不可用，请稍后重试");
            }
            Map<String, Object> raw = objectMapper.readValue(
                    response.body(),
                    new TypeReference<Map<String, Object>>() {
                    }
            );
            return new AgentChatResponse(
                    text(raw, "run_id"),
                    text(raw, "trace_id"),
                    text(raw, "session_id"),
                    text(raw, "intent"),
                    text(raw, "agent"),
                    text(raw, "status"),
                    text(raw, "answer"),
                    tools(raw.get("tools")),
                    number(raw.get("latency_ms"))
            );
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new BizException(ErrorCode.SYSTEM_ERROR, "AI 助手请求被中断");
        } catch (IOException exception) {
            log.warn("Agent 服务调用失败: {}", exception.getMessage(), exception);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "AI 助手暂时不可用，请稍后重试");
        }
    }

    private static String text(Map<String, Object> raw, String key) {
        Object value = raw.get(key);
        return value == null ? "" : String.valueOf(value);
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> tools(Object value) {
        if (value instanceof List<?> list) {
            return (List<Map<String, Object>>) list;
        }
        return List.of();
    }

    private static Double number(Object value) {
        return value instanceof Number number ? number.doubleValue() : null;
    }
}
