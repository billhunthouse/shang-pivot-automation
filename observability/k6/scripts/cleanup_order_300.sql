-- 清理 300 并发下单测试产生的数据，并恢复 SKU 10012 的本地初始库存。
-- 仅用于本地演示库；执行前确认没有真实数据使用 1390001% 手机号。
BEGIN;

CREATE TEMP TABLE tmp_customers AS
SELECT id FROM identity.customer WHERE phone LIKE '1390001%';

DELETE FROM commerce.stock_log
WHERE operator_id IN (SELECT id FROM tmp_customers)
  AND sku_id = 10012;

DELETE FROM commerce.order_item
WHERE order_id IN (
  SELECT id FROM commerce."order" WHERE customer_id IN (SELECT id FROM tmp_customers)
);

DELETE FROM commerce."order"
WHERE customer_id IN (SELECT id FROM tmp_customers);

DELETE FROM commerce.address
WHERE customer_id IN (SELECT id FROM tmp_customers);

DELETE FROM identity.customer
WHERE id IN (SELECT id FROM tmp_customers);

-- 本地 baseline：physical=130, locked=2。其他环境请按实际值修改。
UPDATE commerce.stock
SET physical_stock = 130, locked_stock = 2
WHERE sku_id = 10012;

COMMIT;
