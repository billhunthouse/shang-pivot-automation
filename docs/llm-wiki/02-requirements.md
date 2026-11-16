# 需求目录（V1 + V2 + 扩展）

> ID 前缀 `V1-` / `V2-` 区分版本；页面和接口由实际路由/调用图反推。

## V1

| ID | 模块 | 功能 | 优先级 | 页面 | 接口数 |
|---|---|---|---|---|---:|
| V1-FR-001 | 登录 | 账密登录、失败锁定、登出 | P0 | page:admin:/login | 1 |
| V1-FR-002 | 用户管理 | 用户增删改查、启禁用、重置密码 | P0 | page:admin:/users | 8 |
| V1-FR-003 | 角色管理 | 角色、权限绑定、数据范围 | P0 | page:admin:/roles | 6 |
| V1-FR-004 | 菜单与权限 | 权限树维护、侧栏与按钮权限 | P0 | page:admin:/menus | 5 |
| V1-FR-005 | 部门管理 | 部门树增删改查 | P0 | page:admin:/depts | 5 |
| V1-FR-006 | 字典管理 | 字典类型与项 | P0 | page:admin:/dicts | 8 |
| V1-FR-007 | 操作日志 | 记录、查询、详情、导出 | P0 | page:admin:/logs | 3 |
| V1-FR-008 | 类目管理 | 类目树增删改查 | P0 | page:admin:/categories | 13 |
| V1-FR-009 | 品牌管理 | 品牌增删改查、归属类目 | P0 | page:admin:/categories | 13 |
| V1-FR-010 | 属性管理 | 属性、规格值维护 | P0 | page:admin:/categories | 13 |
| V1-FR-011 | 商品编辑 | SPU + 规格 + SKU 维护 | P0 | page:admin:/products/edit, page:admin:/products/edit/:id | 7 |
| V1-FR-012 | 商品列表 | 查询、聚合展示 | P0 | page:admin:/products | 7 |
| V1-FR-013 | 上下架 | 上架校验、单个/批量下架、删除草稿 | P0 | page:admin:/products | 7 |
| V1-FR-014 | 文件上传 | 图片上传与引用 | P0 | page:admin:/products/edit, page:admin:/products/edit/:id, page:admin:/site-brand | 9 |
| V1-FR-015 | 库存查询/调整 | 三态查询、手动调整 | P0 | page:admin:/inventory | 2 |
| V1-FR-016 | 库存预警 | 阈值、低库存/关注两档、筛选 | P1 | page:admin:/inventory | 2 |
| V1-FR-017 | 仓库 | 默认仓种子；无独立管理页 | P2 | page:admin:/inventory | 2 |
| V1-FR-018 | 订单列表 | 列表、详情 | P0 | page:admin:/orders | 4 |
| V1-FR-019 | 订单发货 | 承运商 + 运单号、状态流转 | P0 | page:admin:/orders | 4 |
| V1-FR-020 | 售后管理 | 列表、详情 | P0 | page:admin:/aftersales | 4 |
| V1-FR-021 | 售后审核 | 同意/拒绝 | P0 | page:admin:/aftersales | 4 |
| V1-FR-022 | 系统设置 | 配置 KV（分类 Tab、敏感脱敏） | P0 | page:admin:/settings | 2 |
| V1-FR-023 | 工作台 | 统计摘要、低库存入口 | P0 | page:admin:/dashboard | 2 |
| V1-FR-024 | 弹窗与提示 | 全站统一的确认/表单/拒绝/提示规范 | P0 | - | 0 |

## V2

| ID | 模块 | 功能 | 优先级 | 页面 | 接口数 |
|---|---|---|---|---|---:|
| V2-FR-001 | 账号 | 手机号登录、游客浏览、登录引导、退出 | P0 | page:mall:/login, page:mall:/me, page:mall:/settings | 5 |
| V2-FR-002 | 账号 | 个人资料 | P1 | page:mall:/login, page:mall:/me, page:mall:/settings | 5 |
| V2-FR-003 | 首页 | 站点品牌、运营位、推荐流 | P0 | page:mall:/, page:mall:/promo/:code | 3 |
| V2-FR-004 | 浏览 | 分类导航与商品列表 | P0 | page:mall:/category, page:mall:/product/:spuId, page:mall:/search | 8 |
| V2-FR-005 | 浏览 | 搜索 | P0 | page:mall:/category, page:mall:/product/:spuId, page:mall:/search | 8 |
| V2-FR-006 | 详情 | 商品详情与加购/购买 | P0 | page:mall:/product/:spuId | 4 |
| V2-FR-007 | 购物车 | 增删改、勾选、失效、角标 | P0 | page:mall:/cart | 3 |
| V2-FR-008 | 交易 | 确认订单 | P0 | page:mall:/checkout, page:mall:/pay/:orderId | 5 |
| V2-FR-009 | 交易 | 提交订单与待付款倒计时 | P0 | page:mall:/checkout, page:mall:/pay/:orderId | 5 |
| V2-FR-010 | 交易 | 模拟支付与结果页 | P0 | page:mall:/checkout, page:mall:/pay/:orderId | 5 |
| V2-FR-011 | 订单 | 列表、详情、取消、收货、物流 | P0 | page:mall:/orders, page:mall:/orders/:id | 7 |
| V2-FR-012 | 售后 | 申请、列表、详情、凭证上传 | P0 | page:mall:/after-sales, page:mall:/after-sales/apply, page:mall:/after-sales/:id | 5 |
| V2-FR-013 | 个人中心 | 首页、收藏、足迹、设置 | P0/P1 | page:mall:/me, page:mall:/addresses, page:mall:/favorites, page:mall:/history | 9 |
| V2-FR-014 | 个人中心 | 地址管理 | P0 | page:mall:/me, page:mall:/addresses, page:mall:/favorites, page:mall:/history | 9 |
| V2-FR-015 | 评价 | 发表评价与详情页展示 | P1 | page:mall:/product/:spuId | 4 |
| V2-FR-016 | 多端 | Web/H5 双布局 | P0 | page:mall:/, page:mall:/category, page:mall:/cart, page:mall:/me | 7 |
| V2-FR-017 | 后台 | 会员管理 | P0 | page:admin:/customers | 2 |
| V2-FR-018 | 后台 | 站点品牌 | P0 | page:admin:/site-brand | 3 |
| V2-FR-019 | 后台 | 首页运营位 | P0 | page:admin:/home-slots | 4 |
| V2-FR-020 | 后台 | 交易配置 | P0 | page:admin:/settings | 2 |
| V2-FR-021 | 后台 | 超时关单与销量回写 | P0 | page:admin:/orders | 4 |
| V2-FR-022 | 后台 | 订单增强与导出 | P1 | page:admin:/orders | 4 |
| V2-FR-023 | 后台 | 定时上架 | P1 | page:admin:/products/edit, page:admin:/products/edit/:id | 7 |
| V2-FR-024 | 后台 | 出入库单 | P1 | page:admin:/in-out | 3 |
| V2-FR-025 | 后台 | 评价管理 | P1 | page:admin:/reviews | 3 |
| V2-FR-026 | 全局 | 弹窗与提示规范（C 端） | P0 | - | 0 |

## EXT

| ID | 模块 | 功能 | 优先级 | 页面 | 接口数 |
|---|---|---|---|---|---:|
| EXT-AI-001 | AI助手 | 商城 C 端 AI 助手浮窗（商品/知识/订单） | P1 | page:mall:ai-assistant | 1 |
| EXT-REVIEW-REPLY-001 | 评价管理 | 商品评价商家回复（管理端回复、C 端展示） | P1 | page:admin:/reviews, page:mall:/product/:spuId | 3 |
