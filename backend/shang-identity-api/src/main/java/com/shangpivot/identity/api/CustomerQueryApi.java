package com.shangpivot.identity.api;

/**
 * Cross-context customer query. Implemented by {@code shang-identity}.
 */
public interface CustomerQueryApi {

    /** 顾客是否存在且状态为 NORMAL；不存在或冻结返回 false。 */
    boolean isActive(Long customerId);

    /** 脱敏手机号；不存在返回 null。 */
    String maskedPhone(Long customerId);

    /**
     * 一次查询返回活跃顾客的脱敏手机号；不存在或冻结返回 null。
     * 用于下单链路替代 isActive + maskedPhone 两次查询。
     */
    ActiveCustomer findActive(Long customerId);

    record ActiveCustomer(String maskedPhone) {
    }
}
