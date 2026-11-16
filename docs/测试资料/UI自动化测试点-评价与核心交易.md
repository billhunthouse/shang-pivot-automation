# UI 自动化测试点：评价商家回复 + 核心交易链路

> 依据：`PRD-V2.1-评价商家回复`、`PRD-V2.0-购物网站`  
> 规范：`docs/测试资料/UI自动化用例设计规范.md`  
> 日期：2026-11-15

## 1. 范围

| 域 | 覆盖 |
|---|---|
| 管理端评价管理 | 列表、回复弹窗、空校验、500 字边界、覆盖回复、隐藏评价、权限、XSS |
| 商城 C 端 | 商品详情有/无商家回复、隐藏评价不可见、已完成订单已评价状态 |
| 核心交易链路 | 立即购买 → 提交订单 → 沙箱支付 → 管理端发货 → 确认收货 → 评价 → 商家回复 |
| 全站页面 | 41 个页面路由可达、关键内容渲染、无页面级错误（39 条页面冒烟 + checkout/pay 由核心链路覆盖） |
| 业务冒烟 | 搜索、加购/删除、商品查询、库存筛选、售后详情、H5 视口 |

不覆盖：支付失败重试、库存不足、售后审核写操作、优惠券（这些由 API/其他专项覆盖）。

## 2. UI 测试点矩阵

### 2.1 评价商家回复

| ID | 测试点 | 前置条件 | 操作 | 预期 | 优先级 | 自动化 |
|---|---|---|---|---|---|---|
| UI-REVIEW-001 | 评价列表展示回复列与操作 | 管理员登录，评价 8503 有回复 | 打开评价管理 | 表头含“商家回复”；行内显示回复摘要和“修改回复” | P1 | 是 |
| UI-REVIEW-002 | 回复弹窗信息完整 | 同上 | 点击“修改回复” | 弹窗显示商品/评价摘要、原回复、`n / 500` 计数 | P1 | 是 |
| UI-REVIEW-003 | 空回复内联校验 | 同上 | 清空后保存 | `.error-text` 显示“回复内容不能为空”，弹窗不关闭 | P1 | 是 |
| UI-REVIEW-004 | 500 字边界 | 同上 | 输入 500 字保存 | 计数 `500 / 500`；保存成功；列表刷新 | P2 | 是 |
| UI-REVIEW-005 | 重复回复覆盖 | 同上 | 连续保存两次 | 第二次覆盖第一次；再次打开回填第二次 | P1 | 是 |
| UI-REVIEW-006 | C 端有回复展示 | 评价 8503 有回复 | 打开 `/product/127` | `.merchant-reply` 显示当前回复 | P0 | 是 |
| UI-REVIEW-006b | C 端无回复不展示空块 | 评价 8501 无回复 | 打开 `/product/162` | 评价区存在，但 `.merchant-reply` 数量为 0 | P1 | 是 |
| UI-REVIEW-007 | 隐藏评价不公开 | 评价 8504 为 HIDDEN | 管理端筛选已隐藏；C 端打开 `/product/101` | 管理端可见；C 端评价区不渲染、回复不可见 | P2 | 是 |
| UI-REVIEW-008 | 未登录访问评价管理 | 无登录态 | 直接访问 `/reviews` | 重定向 `/login`，显示登录表单 | P1 | 是 |
| UI-REVIEW-009 | 回复 HTML 转义 | 管理员登录 | 回复 `<img onerror>` 内容 | C 端按文本展示，不生成 img，不执行脚本 | P2 | 是 |
| UI-REVIEW-010 | 已完成订单已评价状态 | 顾客 13800000001，订单 104 | 打开 `/orders/104` | 显示“已评价 · 提交后不可修改”，无“评价”按钮 | P1 | 是 |

### 2.2 核心交易链路

| ID | 测试点 | 前置条件 | 操作 | 预期 | 优先级 | 自动化 |
|---|---|---|---|---|---|---|
| UI-CORE-001 | 商品详情与库存 | 顾客登录，商品 111 有货 | 打开 `/product/111` | 商品名、价格、库存、按钮可见 | P0 | 是 |
| UI-CORE-002 | 立即购买与规格层 | 同上 | 点击“立即购买” | 规格层出现，可确认购买 | P0 | 是 |
| UI-CORE-003 | 确认订单信息 | 已选规格 | 点击“去确认订单” | 进入结算页，地址/商品/金额正确 | P0 | 是 |
| UI-CORE-004 | 提交订单 | 结算页 | 提交并确认 | 生成待付款订单，跳转收银台 | P0 | 是 |
| UI-CORE-005 | 沙箱支付 | 待付款订单 | 等待支付结果 | 支付成功，订单进入待发货 | P0 | 是 |
| UI-CORE-006 | 管理端发货 | 管理员登录，待发货订单 | 查询订单 → 发货 → 填运单号 | 提示已确认发货，订单待收货 | P0 | 是 |
| UI-CORE-007 | 顾客确认收货 | 订单待收货 | 点击确认收货 | 订单已完成 | P0 | 是 |
| UI-CORE-008 | 订单评价 | 订单已完成 | 5 星 + 内容 → 提交 | 提示评价成功，商品详情出现评价 | P0 | 是 |
| UI-CORE-009 | 商家回复闭环 | 新评价存在 | 管理端回复 → C 端查看 | 商品详情显示商家回复 | P0 | 是 |

## 3. 自动化映射

| 文件 | 用例 |
|---|---|
| `api_testcases/tests/ui/test_page_smoke.py` + `page_catalog.py` | 39 条页面冒烟，覆盖 41 页中的 39 页 |
| `api_testcases/tests/ui/test_business_smoke.py` | 搜索、购物车、商品查询、库存筛选、售后详情、H5 |
| `api_testcases/tests/ui/test_review_ui.py` | UI-REVIEW-001 ~ 010 |
| `api_testcases/tests/ui/test_core_flow_ui.py` | UI-CORE-001 ~ 009（一条长链路，步骤内断言） |
| `api_testcases/tests/ui/ui_support.py` | 浏览器、登录、截图、API 数据恢复 |
| `api_testcases/tests/ui/conftest.py` | `ui`、`smoke_pages`、`review_target` fixture |

## 4. 测试数据

| 数据 | 值 | 用途 |
|---|---|---|
| 管理员 | `admin / Admin@123`（本地） | 管理端 |
| 顾客 | `13800000001 / 123456` | C 端 |
| 评价 8503 | spu 127，VISIBLE，有回复 | 回复/覆盖/跨端 |
| 评价 8501 | spu 162，VISIBLE，无回复 | 无回复空块 |
| 评价 8504 | spu 101，HIDDEN | 隐藏评价 |
| 订单 104 | 顾客 9001，COMPLETED，item 105 已评价 | 已评价状态 |
| 商品 111 | vivo X100，库存充足 | 核心链路 |

数据恢复：

- `review_target` fixture 记录 8503 原始回复，模块结束后恢复；
- 核心链路每轮生成唯一订单号、评价内容、回复内容，使用时间戳避免重复；
- 本地演示库允许保留新订单/评价，便于报告回查。

## 5. 截图点

每条用例的 `step` 都会自动截图。核心链路至少包含：

```text
商品详情 → 规格层 → 确认下单信息 → 结算页 → 确认提交
→ 支付成功 → 支付结果 → 订单详情 → 管理端订单 → 发货弹窗
→ 发货成功 → 待收货 → 确认收货 → 已完成 → 发表评价
→ 评价成功 → 商品详情新评价 → 管理端回复 → C 端商家回复
```

## 6. 执行结果

执行时间：2026-11-15  
环境：本地 5173 / 5174 / 8086  
结果：

```text
collected 58 items
58 passed in 43.90s
通过率 100%
```

Allure 3 报告：

```text
api_testcases/artifacts/allure3-ui-report/index.html
http://127.0.0.1:9093/
```

报告统计：

```text
Allure Report 3.33.0
Total 58 / Passed 58 / 100%
测试体步骤 140 / 附件 141 / 证据覆盖率 100%
```

执行中发现并修复的产品问题：

- 订单详情页刷新后不显示“已评价”状态，仍展示“评价”按钮；
- 修复：`GET /api/orders/{id}` 返回 `reviewedItemIds`，前端 `OrderDetailView` 回填 `reviewedItems`；
- 回归：`UI-REVIEW-010` 通过。

## 7. 执行命令

```bash
cd api_testcases

RUN_UI=1 \
ADMIN_UI_URL=http://127.0.0.1:5173 \
MALL_UI_URL=http://127.0.0.1:5174 \
ADMIN_BASE_URL=http://127.0.0.1:8086/admin \
MALL_BASE_URL=http://127.0.0.1:8086 \
ADMIN_TEST_ACCOUNT=admin \
ADMIN_TEST_PASSWORD='Admin@123' \
MALL_TEST_PHONE=13800000001 \
MALL_TEST_CODE=123456 \
UI_HEADLESS=true \
python3 -m pytest tests/ui \
  -q --alluredir=artifacts/allure-ui-results --clean-alluredir
```

生成 Allure 3：

```bash
/Users/imac/.local/opt/allure3/node_modules/.bin/allure generate \
  artifacts/allure-ui-results \
  --output artifacts/allure3-ui-report \
  --report-name "尚品汇 UI 自动化"
```

## 8. 通过标准

- 58 条用例全部通过；
- 每条用例每个步骤有截图；
- 报告按 feature/story/severity 可筛选；
- 失败时有失败现场截图和 URL；
- 评价 8503 的回复在结束后恢复原值。
