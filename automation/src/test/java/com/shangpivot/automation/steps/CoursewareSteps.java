package com.shangpivot.automation.steps;

import com.fasterxml.jackson.databind.JsonNode;
import com.shangpivot.automation.context.ScenarioContext;
import com.shangpivot.automation.core.api.ApiResult;
import io.cucumber.datatable.DataTable;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import org.assertj.core.api.Assertions;

import java.util.Map;

/** 课件专用步骤：演示 DataTable 批量数据与断言，不影响生产用例。 */
public class CoursewareSteps {

    private final ScenarioContext ctx;

    public CoursewareSteps(ScenarioContext ctx) {
        this.ctx = ctx;
    }

    @When("我批量加入以下商品：")
    public void bulkAdd(DataTable table) {
        ctx.customerToken();
        for (Map<String, String> row : table.asMaps()) {
            ApiResult result = ctx.cart()
                    .add(row.get("skuId"), Integer.parseInt(row.get("quantity")))
                    .assertSuccess();
            ctx.registry().registerCartItem(result.data().path("cartItemId").asText());
        }
    }

    @Then("购物车应包含以下商品：")
    public void assertCartContains(DataTable table) {
        ApiResult cart = ctx.cart().getCart().assertSuccess();
        for (Map<String, String> row : table.asMaps()) {
            String skuId = row.get("skuId");
            int expected = Integer.parseInt(row.get("quantity"));
            int actual = 0;
            boolean found = false;
            for (JsonNode item : cart.data().path("items")) {
                if (skuId.equals(item.path("skuId").asText())) {
                    found = true;
                    actual = item.path("quantity").asInt();
                }
            }
            Assertions.assertThat(found).as("购物车应包含 SKU %s", skuId).isTrue();
            Assertions.assertThat(actual).as("SKU %s 数量", skuId).isEqualTo(expected);
        }
    }
}
