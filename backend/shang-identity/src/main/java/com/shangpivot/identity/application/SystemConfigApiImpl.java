package com.shangpivot.identity.application;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.shangpivot.identity.api.SystemConfigApi;
import com.shangpivot.identity.entity.SystemConfig;
import com.shangpivot.identity.mapper.SystemConfigMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.Duration;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class SystemConfigApiImpl implements SystemConfigApi {

    private final SystemConfigMapper systemConfigMapper;

    /**
     * 配置低频变更，缓存 5 分钟；更新接口通过 evict 主动失效。
     * 下单链路每单 3 次配置读取，缓存后不再打数据库。
     */
    private final Cache<String, Optional<String>> cache = Caffeine.newBuilder()
            .maximumSize(200)
            .expireAfterWrite(Duration.ofMinutes(5))
            .build();

    @Override
    public String getValue(String configKey, String defaultValue) {
        Optional<String> cached = cache.get(configKey, this::load);
        return cached == null || cached.isEmpty() ? defaultValue : cached.get();
    }

    @Override
    public int getInt(String configKey, int defaultValue) {
        String v = getValue(configKey, null);
        if (!StringUtils.hasText(v)) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(v.trim());
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    @Override
    public void evict(String configKey) {
        if (StringUtils.hasText(configKey)) {
            cache.invalidate(configKey);
        }
    }

    private Optional<String> load(String configKey) {
        SystemConfig cfg = systemConfigMapper.selectOne(new LambdaQueryWrapper<SystemConfig>()
                .eq(SystemConfig::getConfigKey, configKey));
        return cfg == null || !StringUtils.hasText(cfg.getConfigValue())
                ? Optional.empty()
                : Optional.of(cfg.getConfigValue());
    }
}
