# shang-mall

尚品汇 C 端（Web / H5 自适应）。技术栈：Vue 3 · Vite · Pinia · Vue Router · TypeScript · Vant 4。

## 启动

```bash
# 需先启动 backend（shang-server，默认 8086）
cd shang-mall
npm install
npm run dev
```

本地地址：http://127.0.0.1:5174  
`/api` 代理到 `http://localhost:8086`。

## 目录

```
src/
  api/           # /api/** 契约封装（对齐 V2 接口设计）
  components/    # ProductCard 等
  composables/   # useClientType（web|h5）
  layouts/       # MallLayout（Web 顶栏 / H5 TabBar）
  router/        # 路由与登录守卫
  stores/        # auth / brand / cart
  views/         # 首页、分类、详情、购物车、结算、支付、订单、我的…
  utils/         # request、format
```

## AI 助手

商城 Web/H5 共用 `src/components/AiAssistant.vue` 浮窗，入口位于右下角（H5 在底部 Tab 上方）。

- 调用 `POST /api/customer-service/chat`，由 `shang-customerservice` 代理到 Agent 服务。
- 支持商品推荐、知识问答、订单查询；登录态由商城 `http` 封装自动透传。
- 未登录查订单会返回 `need_auth`，前端提供「去登录查订单」按钮。
- 会话 ID 保存在浏览器 `localStorage`，用于多轮上下文。

## 说明

- 站点名 / Logo / Slogan **运行时**读 `GET /api/site/brand`，禁止写死安装包；失败时用「尚品汇 / 选好物，享生活」兜底。
- 登录 JWT：`clientType` 按视口自动取 `web` 或 `h5`。
- 商品图走 `/api/files/view` 或已有 `/admin/files/view`（开发代理已转发）。
- 数据全部来自后端 `/api/**`，无前端 mock 商品。
