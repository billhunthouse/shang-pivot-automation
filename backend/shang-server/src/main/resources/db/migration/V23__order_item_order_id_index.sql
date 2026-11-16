-- 订单明细按 order_id 查询（订单详情、关单、售后关联）缺少索引。
CREATE INDEX IF NOT EXISTS idx_order_item_order_id
    ON commerce.order_item (order_id)
    WHERE deleted = false;
