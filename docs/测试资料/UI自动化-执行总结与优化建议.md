# UI 自动化执行总结与优化建议

> 日期：2026-11-15  
> 范围：全站 41 页 + 评价商家回复 + 核心交易链路  
> 结果：58 passed / 100%  
> 报告：`api_testcases/artifacts/allure3-ui-report/index.html`  
> 覆盖率：`docs/测试资料/UI覆盖率报告.md`

## 1. 本次交付

| 交付物 | 路径 |
|---|---|
| UI 用例设计规范 | `docs/测试资料/UI自动化用例设计规范.md` |
| UI 测试点矩阵 | `docs/测试资料/UI自动化测试点-评价与核心交易.md` |
| 覆盖率报告 | `docs/测试资料/UI覆盖率报告.md` |
| 覆盖率计算脚本 | `api_testcases/scripts/ui_coverage.py` |
| 41 页页面目录 | `api_testcases/tests/ui/page_catalog.py` |
| 全站页面冒烟 | `api_testcases/tests/ui/test_page_smoke.py` |
| 业务冒烟 | `api_testcases/tests/ui/test_business_smoke.py` |
| 评价 UI 用例 | `api_testcases/tests/ui/test_review_ui.py` |
| 核心链路用例 | `api_testcases/tests/ui/test_core_flow_ui.py` |
| Playwright/Allure 基础设施 | `api_testcases/tests/ui/ui_support.py` |
| Allure 3 生成脚本 | `api_testcases/scripts/allure3_report.sh` |

## 2. 执行结果

```text
collected 58 items
58 passed in 43.90s
通过率 100%
```

报告：

```text
Allure Report 3.33.0
Total 58 / Passed 58 / 100%
测试体步骤 140 / 附件 141 / 证据覆盖率 100%
```

## 3. 覆盖率

| 指标 | 结果 | 计算方式 |
|---|---:|---|
| 用例通过率 | 100%（58/58） | 通过用例 ÷ 执行用例 |
| 页面覆盖率 | 100%（41/41） | 被通过用例访问并断言的页面 ÷ 41 |
| 需求触达率 | 96.2%（50/52） | 至少一个页面被覆盖的需求 ÷ 52 |
| 需求行为覆盖率 | 37.5%（19.5/52） | Σ(full=1, partial=0.5) ÷ 52 |
| 步骤证据覆盖率 | 100%（58/58） | 附件数 ≥ 步骤数的通过用例 ÷ 通过用例 |
| 角色覆盖率 | 100%（3/3） | guest / customer / admin |
| 视口覆盖率 | 100%（2/2） | 1440×900 + 390×844 |
| 浏览器覆盖率 | 33%（1/3） | Chromium / WebKit / Firefox |

解释：

- 页面覆盖率 100%，代表所有页面都能打开并渲染关键内容；
- 需求行为覆盖率 37.5%，代表只有一部分需求做到了“具体行为断言”，大量管理端 CRUD、售后审核、地址管理仍是缺口；
- 两条无页面需求（V1-FR-024、V2-FR-026）是跨页面规范，按 partial 计入；
- 浏览器只跑了 Chromium。

## 4. 本次发现的问题

### 4.1 订单详情不显示“已评价”（已修复）

- 现象：订单已完成且已有评价，刷新详情仍显示“评价”按钮；
- 根因：`OrderDetailView.vue` 的 `reviewedItems` 只存在页面内存，刷新即丢失；
- 修复：
  - `GET /api/orders/{id}` 新增 `reviewedItemIds`；
  - 前端 `load()` 回填 `reviewedItems`；
- 回归：`UI-REVIEW-010` 通过。

### 4.2 评价管理搜索框文案与实际过滤不一致（待修复）

- 页面 placeholder：`商品名 / 会员手机尾号`；
- 后端实际：`ReviewAdminService.page` 对 `Review::getContent` 做 LIKE；
- 影响：用户按商品名/手机号搜不到，按评价内容反而能搜到；
- 测试应对：用例改为按评价内容“打工人”过滤；
- 建议：要么改后端支持商品名/手机号，要么把 placeholder 改为“评价内容”。

### 4.3 评价列表分页导致固定数据漂移（测试数据问题）

- 核心链路每跑一次新增评价，8503 被挤到第二页；
- 处理：评价用例先按内容过滤再定位；
- 根因：缺少专用测试数据和清理机制。

## 5. 优化点（按优先级）

### P0：稳定性与数据隔离

| # | 优化 | 说明 |
|---|---|---|
| 1 | 专用测试数据工厂 | 每次创建专属评价/订单，替代固定 8503 |
| 2 | 清理新增订单/评价 | 核心链路每跑一次新增一条订单和评价 |
| 3 | function 级 fixture | 当前 `review_target` 是 module 级，xdist 并行会冲突 |
| 4 | `data-testid` | 评价行、回复按钮、弹窗、运单号输入等 |
| 5 | 失败收集 console/network/trace | 目前只有截图和 URL |
| 6 | 修复评价搜索框 | 文案与后端过滤字段对齐 |

### P1：覆盖深化

| # | 优化 | 说明 |
|---|---|---|
| 7 | 管理端 CRUD 写操作 | 用户/角色/菜单/部门/字典/类目/品牌 |
| 8 | 售后审核 | 同意/拒绝、状态守卫、退款金额边界 |
| 9 | 地址管理 | 新增/编辑/默认/删除、下单引用 |
| 10 | 订单取消/物流 | 待付款取消、物流查看 |
| 11 | 收藏/足迹/设置 | 收藏切换、清空足迹、资料保存 |
| 12 | 商品上架/下架/库存调整 | 写操作与校验 |
| 13 | AI 助手对话 | 真实发消息、引用、订单查询 |
| 14 | 异常/弱网 | 接口 4xx/5xx、超时、重复提交 |
| 15 | WebKit/Firefox | 浏览器覆盖率 1/3 → 3/3 |
| 16 | axe-core 可访问性 | 关键页面扫描 |
| 17 | 视觉回归 | 关键页面截图基线 |

### P2：工程化

| # | 优化 | 说明 |
|---|---|---|
| 18 | Page Object Model | 抽 AdminReviewsPage、MallProductPage、CheckoutPage |
| 19 | Allure 3 趋势 | 固定 history 目录 |
| 20 | Allure 3 Quality Gate | 通过率/严重用例门槛 |
| 21 | CI 集成 | Docker 起服务 → UI → 报告 artifact |
| 22 | 截图压缩 | 141 张图使报告 ~14MB |
| 23 | 状态文案统一 | 订单详情显示英文枚举，列表显示中文 |
| 24 | 数据清理脚本 | 清理 E2E 产生的订单/评价 |

## 6. 建议下一轮

```text
第 1 周：数据工厂 + data-testid + 失败 trace
第 2 周：管理端 CRUD + 售后审核 + 地址管理
第 3 周：订单取消/物流 + AI 助手 + 异常
第 4 周：WebKit/Firefox + axe + CI + Allure 3 趋势
```

## 7. 结论

本次已经做到：

- 用知识图谱/需求文档生成 41 页页面目录和 58 条 UI 用例；
- 页面覆盖 41/41，需求触达 50/52；
- 每步截图，证据覆盖率 100%；
- Allure 3 报告可筛选、可下钻；
- 发现并修复订单详情“已评价”状态缺失。

下一阶段的核心不是继续堆页面冒烟，而是**补行为断言、做数据隔离、提高失败可诊断性**。
