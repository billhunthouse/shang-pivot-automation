---
id: L10
chapter: 实战
title: 真实 Bug 复盘：发货提示“订单不存在”
summary: 从访问日志和数据库差异定位 JS 雪花 ID 精度丢失，并建立防复发规范。
duration: 25
level: 实战
kind: lesson
---

# 真实 Bug 复盘：发货提示“订单不存在”

## 本节目标

- 用日志和数据库对比定位前后端契约问题；
- 理解 JS `Number` 的安全整数边界；
- 掌握 ID 全链路字符串化的修复方式；
- 设计能抓住这类问题的回归用例。

## 1. 现象

商家端订单管理，对订单 `O202611122012190001` 点击“发货”，提示“订单不存在”。

订单在列表中可见，状态“待发货”。

## 2. 证据链

### 访问日志

```text
GET  /admin/orders/2120852188811464700  code=40400  msg=订单不存在
POST /admin/orders/2120852188811464700/ship  code=40400
```

### 数据库

```text
id = 2120852188811464706
order_no = O202611122012190001
status = PENDING_SHIP
```

请求 ID `...4700` 与真实 ID `...4706` 只差末位。

### 前端代码

```ts
type OrderRow = { id: number }
id: Number(o.id)
```

## 3. 根因

JavaScript `Number` 的安全整数上限：

```text
Number.MAX_SAFE_INTEGER = 9007199254740991
2120852188811464706 > 9007199254740991
```

`Number("2120852188811464706")` 会变成 `2120852188811464700`，后续详情、发货都用错误 ID。

## 4. 修复

```ts
type OrderRow = { id: string }
id: String(o.id)
async function refreshDetail(rowId: string)
```

同类加固：

| 文件 | 修复 |
|---|---|
| `AftersalesView.vue` | 售后 ID 字符串化；关联订单 ID 不再 `Number()` |
| `UsersView.vue` | 用户 ID 字符串化；超管判断 `row.id === '1'` |

## 5. 验证

```text
GET  /admin/orders/2120852188811464706          200
POST /admin/orders/2120852188811464706/ship     200
页面提示：已确认发货
DB：status = PENDING_RECEIVE
```

## 6. 为什么测试没抓到

- 列表和详情只断言了“有数据”，没断言请求 URL 的完整 ID；
- 种子订单 ID 较小，`Number()` 不丢精度；
- 没有覆盖 19 位雪花 ID 的边界数据。

## 7. 防复发规范

1. 后端 `Long` ID 一律序列化为字符串；
2. 前端类型定义 ID 为 `string`；
3. 禁止 `Number()`、`parseInt()`、`+id`；
4. 路由参数、`v-for :key`、URL 拼接直接用字符串；
5. UI 回归断言真实请求 URL 含完整 ID；
6. 测试数据至少包含一个 19 位 ID。

## 8. 可复用的排查顺序

```text
页面提示
→ 浏览器 Network：请求 URL/参数
→ 后端访问日志：实际收到的 ID
→ 数据库：真实 ID
→ 前端代码：ID 是否被转换
→ 修复 + 回归
```

## 练习

1. 在代码库中搜索所有 `Number(...id)`，判断哪些有风险。
2. 写一条 Playwright 断言：发货请求 URL 必须匹配 `/admin/orders/\d{19}/ship`。
3. 解释为什么 `String(a) === String(b)` 比 `a === b` 更适合 ID 比较。
