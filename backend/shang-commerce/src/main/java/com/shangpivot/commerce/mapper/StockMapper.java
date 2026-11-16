package com.shangpivot.commerce.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.shangpivot.commerce.entity.Stock;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface StockMapper extends BaseMapper<Stock> {

    /**
     * 原子锁定库存：把「检查可售 + 加锁定量」合并为一条 UPDATE，
     * 避免先 SELECT ... FOR UPDATE 再 updateById 的两次往返和更长持锁时间。
     * 返回 warehouse_id；返回 null 表示库存不足/记录不存在。
     */
    @Select("""
            WITH updated AS (
                UPDATE commerce.stock
                SET locked_stock = COALESCE(locked_stock, 0) + #{qty},
                    updated_at = NOW()
                WHERE id = (
                    SELECT id FROM commerce.stock
                    WHERE sku_id = #{skuId} AND deleted = FALSE
                    ORDER BY id
                    LIMIT 1
                )
                  AND deleted = FALSE
                  AND COALESCE(physical_stock, 0) - COALESCE(locked_stock, 0) >= #{qty}
                RETURNING warehouse_id
            )
            SELECT warehouse_id FROM updated
            """)
    Long lockStock(@Param("skuId") Long skuId, @Param("qty") int qty);
}
