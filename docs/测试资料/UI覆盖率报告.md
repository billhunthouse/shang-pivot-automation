# UI 自动化覆盖率报告

> 生成方式：`python3 scripts/ui_coverage.py`
> 结果目录：`artifacts/allure-ui-results`

## 1. 覆盖率总表

| 指标 | 结果 | 计算方式 |
|---|---:|---|
| 用例通过率 | 100.0%（58/58） | 通过用例数 ÷ 执行用例数 |
| 页面覆盖率 | 100.0%（41/41） | 被至少一条通过用例访问并断言的页面数 ÷ 41 |
| 需求触达率 | 96.2%（50/52） | 至少一个页面被覆盖的需求数 ÷ 52 |
| 需求行为覆盖率 | 37.5%（19.5/52） | Σ(需求行为状态权重) ÷ 52；full=1、partial=0.5 |
| 步骤证据覆盖率 | 100.0%（58/58） | 附件数 ≥ 步骤数的通过用例数 ÷ 通过用例数 |
| 角色覆盖率 | 100%（3/3） | 已执行角色数 ÷ guest/customer/admin |
| 视口覆盖率 | 100%（2/2） | 已执行视口档位数 ÷ 1440×900、390×844 |
| 浏览器覆盖率 | 33%（1/3） | 已执行浏览器数 ÷ Chromium/WebKit/Firefox |

## 2. 需求覆盖明细

| 需求 | 优先级 | 标题 | 页面触达 | 行为覆盖 | 用例 |
|---|---|---|---|---|---|
| EXT-AI-001 | P1 | 商城 C 端 AI 助手浮窗（商品/知识/订单） | 是 | partial | UI-PAGE-MALL-018 |
| EXT-REVIEW-REPLY-001 | P1 | 商品评价商家回复（管理端回复、C 端展示） | 是 | full | UI-REVIEW-001, UI-REVIEW-002, UI-REVIEW-003… |
| V1-FR-001 | P0 | 账密登录、失败锁定、登出 | 是 | full | UI-PAGE-ADMIN-001 |
| V1-FR-002 | P0 | 用户增删改查、启禁用、重置密码 | 是 | none | — |
| V1-FR-003 | P0 | 角色、权限绑定、数据范围 | 是 | none | — |
| V1-FR-004 | P0 | 权限树维护、侧栏与按钮权限 | 是 | none | — |
| V1-FR-005 | P0 | 部门树增删改查 | 是 | none | — |
| V1-FR-006 | P0 | 字典类型与项 | 是 | none | — |
| V1-FR-007 | P0 | 记录、查询、详情、导出 | 是 | none | — |
| V1-FR-008 | P0 | 类目树增删改查 | 是 | none | — |
| V1-FR-009 | P0 | 品牌增删改查、归属类目 | 是 | none | — |
| V1-FR-010 | P0 | 属性、规格值维护 | 是 | none | — |
| V1-FR-011 | P0 | SPU + 规格 + SKU 维护 | 是 | none | — |
| V1-FR-012 | P0 | 查询、聚合展示 | 是 | full | UI-ADMIN-001 |
| V1-FR-013 | P0 | 上架校验、单个/批量下架、删除草稿 | 是 | none | — |
| V1-FR-014 | P0 | 图片上传与引用 | 是 | none | — |
| V1-FR-015 | P0 | 三态查询、手动调整 | 是 | full | UI-ADMIN-002 |
| V1-FR-016 | P1 | 阈值、低库存/关注两档、筛选 | 是 | full | UI-ADMIN-002 |
| V1-FR-017 | P2 | 默认仓种子；无独立管理页 | 是 | none | — |
| V1-FR-018 | P0 | 列表、详情 | 是 | full | UI-CORE-001 |
| V1-FR-019 | P0 | 承运商 + 运单号、状态流转 | 是 | full | UI-CORE-001 |
| V1-FR-020 | P0 | 列表、详情 | 是 | full | UI-ADMIN-003 |
| V1-FR-021 | P0 | 同意/拒绝 | 是 | none | — |
| V1-FR-022 | P0 | 配置 KV（分类 Tab、敏感脱敏） | 是 | none | — |
| V1-FR-023 | P0 | 统计摘要、低库存入口 | 是 | none | — |
| V1-FR-024 | P0 | 全站统一的确认/表单/拒绝/提示规范 | 否 | partial | UI-MALL-002, UI-REVIEW-003 |
| V2-FR-001 | P0 | 手机号登录、游客浏览、登录引导、退出 | 是 | full | UI-CORE-001 |
| V2-FR-002 | P1 | 个人资料 | 是 | none | — |
| V2-FR-003 | P0 | 站点品牌、运营位、推荐流 | 是 | none | — |
| V2-FR-004 | P0 | 分类导航与商品列表 | 是 | partial | UI-MALL-001 |
| V2-FR-005 | P0 | 搜索 | 是 | full | UI-MALL-001 |
| V2-FR-006 | P0 | 商品详情与加购/购买 | 是 | full | UI-CORE-001, UI-MALL-002 |
| V2-FR-007 | P0 | 增删改、勾选、失效、角标 | 是 | partial | UI-MALL-002 |
| V2-FR-008 | P0 | 确认订单 | 是 | full | UI-CORE-001 |
| V2-FR-009 | P0 | 提交订单与待付款倒计时 | 是 | full | UI-CORE-001 |
| V2-FR-010 | P0 | 模拟支付与结果页 | 是 | full | UI-CORE-001 |
| V2-FR-011 | P0 | 列表、详情、取消、收货、物流 | 是 | partial | UI-CORE-001 |
| V2-FR-012 | P0 | 申请、列表、详情、凭证上传 | 是 | none | — |
| V2-FR-013 | P0/P1 | 首页、收藏、足迹、设置 | 是 | none | — |
| V2-FR-014 | P0 | 地址管理 | 是 | none | — |
| V2-FR-015 | P1 | 发表评价与详情页展示 | 是 | full | UI-CORE-001, UI-REVIEW-001, UI-REVIEW-002… |
| V2-FR-016 | P0 | Web/H5 双布局 | 是 | partial | UI-MOBILE-001 |
| V2-FR-017 | P0 | 会员管理 | 是 | none | — |
| V2-FR-018 | P0 | 站点品牌 | 是 | none | — |
| V2-FR-019 | P0 | 首页运营位 | 是 | none | — |
| V2-FR-020 | P0 | 交易配置 | 是 | none | — |
| V2-FR-021 | P0 | 超时关单与销量回写 | 是 | none | — |
| V2-FR-022 | P1 | 订单增强与导出 | 是 | none | — |
| V2-FR-023 | P1 | 定时上架 | 是 | none | — |
| V2-FR-024 | P1 | 出入库单 | 是 | none | — |
| V2-FR-025 | P1 | 评价管理 | 是 | full | UI-REVIEW-001, UI-REVIEW-002, UI-REVIEW-003… |
| V2-FR-026 | P0 | 弹窗与提示规范（C 端） | 否 | partial | UI-MALL-002, UI-REVIEW-003 |

## 3. 页面覆盖明细

| 页面 | 区域 | 路由 | 覆盖 | 用例 |
|---|---|---|---|---|
| 登录 | mall | `/login` | ✓ | UI-PAGE-MALL-001 |
| 首页 | mall | `/` | ✓ | UI-MALL-001, UI-MOBILE-001, UI-PAGE-MALL-000 |
| 活动专区 | mall | `/promo/:code` | ✓ | UI-PAGE-MALL-003 |
| 分类 | mall | `/category` | ✓ | UI-PAGE-MALL-004 |
| 商品详情 | mall | `/product/:spuId` | ✓ | UI-CORE-001, UI-MALL-001, UI-MALL-002 |
| 搜索 | mall | `/search` | ✓ | UI-MALL-001, UI-PAGE-MALL-006 |
| 购物车 | mall | `/cart` | ✓ | UI-MALL-002, UI-MOBILE-001, UI-PAGE-MALL-007 |
| 确认订单 | mall | `/checkout` | ✓ | UI-CORE-001 |
| 我的订单 | mall | `/orders` | ✓ | UI-MOBILE-001, UI-PAGE-MALL-008 |
| 订单详情 | mall | `/orders/:id` | ✓ | UI-CORE-001, UI-PAGE-MALL-009, UI-REVIEW-001 |
| 支付 | mall | `/pay/:orderId` | ✓ | UI-CORE-001 |
| 个人中心 | mall | `/me` | ✓ | UI-PAGE-MALL-010 |
| 个人设置 | mall | `/settings` | ✓ | UI-PAGE-MALL-011 |
| 收货地址 | mall | `/addresses` | ✓ | UI-PAGE-MALL-012 |
| 我的收藏 | mall | `/favorites` | ✓ | UI-PAGE-MALL-013 |
| 浏览足迹 | mall | `/history` | ✓ | UI-PAGE-MALL-014 |
| 我的售后 | mall | `/after-sales` | ✓ | UI-PAGE-MALL-015 |
| 申请售后 | mall | `/after-sales/apply` | ✓ | UI-PAGE-MALL-016 |
| 售后详情 | mall | `/after-sales/:id` | ✓ | UI-PAGE-MALL-017 |
| 登录 | admin | `/login` | ✓ | UI-PAGE-ADMIN-001 |
| 工作台 | admin | `/dashboard` | ✓ | UI-PAGE-ADMIN-002 |
| 商品列表 | admin | `/products` | ✓ | UI-ADMIN-001, UI-PAGE-ADMIN-003 |
| 新增商品 | admin | `/products/edit` | ✓ | UI-PAGE-ADMIN-004 |
| 编辑商品 | admin | `/products/edit/:id` | ✓ | UI-PAGE-ADMIN-005 |
| 类目与品牌 | admin | `/categories` | ✓ | UI-PAGE-ADMIN-006 |
| 库存管理 | admin | `/inventory` | ✓ | UI-ADMIN-002, UI-PAGE-ADMIN-007 |
| 出入库单 | admin | `/in-out` | ✓ | UI-PAGE-ADMIN-008 |
| 订单列表 | admin | `/orders` | ✓ | UI-ADMIN-003, UI-CORE-001, UI-PAGE-ADMIN-009 |
| 售后管理 | admin | `/aftersales` | ✓ | UI-ADMIN-003, UI-PAGE-ADMIN-010 |
| 评价管理 | admin | `/reviews` | ✓ | UI-CORE-001, UI-PAGE-ADMIN-011, UI-REVIEW-001 |
| 会员管理 | admin | `/customers` | ✓ | UI-PAGE-ADMIN-012 |
| 站点品牌 | admin | `/site-brand` | ✓ | UI-PAGE-ADMIN-013 |
| 首页运营位 | admin | `/home-slots` | ✓ | UI-PAGE-ADMIN-014 |
| 用户管理 | admin | `/users` | ✓ | UI-PAGE-ADMIN-015 |
| 角色管理 | admin | `/roles` | ✓ | UI-PAGE-ADMIN-016 |
| 菜单与权限 | admin | `/menus` | ✓ | UI-PAGE-ADMIN-017 |
| 部门管理 | admin | `/depts` | ✓ | UI-PAGE-ADMIN-018 |
| 字典管理 | admin | `/dicts` | ✓ | UI-PAGE-ADMIN-019 |
| 操作日志 | admin | `/logs` | ✓ | UI-PAGE-ADMIN-020 |
| 系统设置 | admin | `/settings` | ✓ | UI-PAGE-ADMIN-021 |
| AI 助手浮窗 | mall | `(global)` | ✓ | UI-PAGE-MALL-018 |

## 4. 未完全覆盖的需求

共 36 条（partial 或 none）：

| 需求 | 优先级 | 当前级别 | 建议补充 |
|---|---|---|---|
| EXT-AI-001 | P1 | partial | 补关键交互/异常路径 |
| V1-FR-002 | P0 | none | 补页面级功能用例 |
| V1-FR-003 | P0 | none | 补页面级功能用例 |
| V1-FR-004 | P0 | none | 补页面级功能用例 |
| V1-FR-005 | P0 | none | 补页面级功能用例 |
| V1-FR-006 | P0 | none | 补页面级功能用例 |
| V1-FR-007 | P0 | none | 补页面级功能用例 |
| V1-FR-008 | P0 | none | 补页面级功能用例 |
| V1-FR-009 | P0 | none | 补页面级功能用例 |
| V1-FR-010 | P0 | none | 补页面级功能用例 |
| V1-FR-011 | P0 | none | 补页面级功能用例 |
| V1-FR-013 | P0 | none | 补页面级功能用例 |
| V1-FR-014 | P0 | none | 补页面级功能用例 |
| V1-FR-017 | P2 | none | 补页面级功能用例 |
| V1-FR-021 | P0 | none | 补页面级功能用例 |
| V1-FR-022 | P0 | none | 补页面级功能用例 |
| V1-FR-023 | P0 | none | 补页面级功能用例 |
| V1-FR-024 | P0 | partial | 补关键交互/异常路径 |
| V2-FR-002 | P1 | none | 补页面级功能用例 |
| V2-FR-003 | P0 | none | 补页面级功能用例 |
| V2-FR-004 | P0 | partial | 补关键交互/异常路径 |
| V2-FR-007 | P0 | partial | 补关键交互/异常路径 |
| V2-FR-011 | P0 | partial | 补关键交互/异常路径 |
| V2-FR-012 | P0 | none | 补页面级功能用例 |
| V2-FR-013 | P0/P1 | none | 补页面级功能用例 |
| V2-FR-014 | P0 | none | 补页面级功能用例 |
| V2-FR-016 | P0 | partial | 补关键交互/异常路径 |
| V2-FR-017 | P0 | none | 补页面级功能用例 |
| V2-FR-018 | P0 | none | 补页面级功能用例 |
| V2-FR-019 | P0 | none | 补页面级功能用例 |
| V2-FR-020 | P0 | none | 补页面级功能用例 |
| V2-FR-021 | P0 | none | 补页面级功能用例 |
| V2-FR-022 | P1 | none | 补页面级功能用例 |
| V2-FR-023 | P1 | none | 补页面级功能用例 |
| V2-FR-024 | P1 | none | 补页面级功能用例 |
| V2-FR-026 | P0 | partial | 补关键交互/异常路径 |

## 5. 计算口径

```text
页面覆盖率 = |{page_id | 存在 passed 用例且 case_pages 包含该 page_id}| / 41
需求触达率 = |{requirement | requirement.pages ∩ covered_pages ≠ ∅}| / 52
需求行为覆盖率 = Σ(level_weight) / 52
  full = 1.0   需求的核心行为有明确断言
  partial = 0.5 只覆盖部分行为/页面渲染
  none = 0
步骤证据覆盖率 = |{passed case | attachments >= steps 且 steps > 0}| / passed
```

说明：

- 页面覆盖只代表“访问并断言关键内容”，不代表该页面所有交互都已验证；
- 需求行为覆盖是人工映射到用例后的加权结果，映射表在 `scripts/ui_coverage.py` 的 `FUNCTIONAL` 中维护；
- 2 条无页面需求（V1-FR-024、V2-FR-026）是跨页面规范，无法通过单页覆盖，按 partial/none 计入；
- 浏览器只跑了 Chromium，所以浏览器覆盖率为 1/3；视口覆盖桌面 + H5 两档。

## 6. 结论

- 执行 58 条 UI 用例，通过 58 条；
- 页面覆盖 41/41；
- 需求触达 50/52，行为覆盖 19.5/52（37.5%）；
- 下一阶段优先补：管理端 CRUD 写操作、售后审核、地址管理、订单取消/物流、WebKit/Firefox。
