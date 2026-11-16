---
id: L08
chapter: 图谱与 RAG
title: RAG 切片与召回：242 条 chunk 怎么建、怎么评
summary: 切片粒度、元数据、检索参数、评测指标和常见失败模式。
duration: 30
level: 进阶
kind: lesson
---

# RAG 切片与召回：242 条 chunk 怎么建、怎么评

## 本节目标

- 理解 chunk 的字段和类型；
- 会为不同问题选择 top-k 和过滤条件；
- 能设计一套最小召回评测；
- 知道 RAG 答错的四类原因。

## 1. 为什么需要 RAG

LLM 直接读整个 wiki 有三个问题：

1. 上下文窗口有限；
2. 无关内容稀释注意力；
3. 无法给出可点击的证据。

RAG 的做法：

```text
问题 → 检索 top-k chunk → 拼进 prompt → 生成答案 + 引用
```

## 2. chunk 的结构

`data/chunks.jsonl` 共 242 条，每行一个 JSON：

```json
{
  "id": "api:GET:/api/products/{spuId}",
  "type": "api",
  "title": "查询商品详情",
  "text": "GET /api/products/{spuId} ...",
  "links": ["page:mall:/product/:spuId", "commerce.spu"]
}
```

类型分布：

| type | 内容 |
|---|---|
| `requirement` | 需求条目 |
| `page` | 页面与调用接口 |
| `api` | 端点、鉴权、服务、表 |
| `rule` | 状态机、库存、鉴权、负面清单 |
| `code` | Controller/Service 映射 |
| `test` | 测试资产 |

## 3. 切片原则

一条 chunk 只回答一类问题：

- 一个 API 一条；
- 一个页面一条；
- 一条规则一条；
- 不要把一个 Controller 的所有方法塞进一条。

必须带元数据：

- `id`：稳定、可引用；
- `type`：用于过滤；
- `links`：支持二跳；
- `source`：文件/行号，方便回查。

## 4. 检索参数

| 场景 | top-k | 过滤 |
|---|---:|---|
| 需求影响 | 6 | `type in (requirement, rule)` |
| 接口定位 | 8 | `type=api` |
| 页面定位 | 5 | `type=page` |
| 用例生成 | 10 | requirement + page + api + rule |
| 代码分析 | 8 | api + rule |

推荐查询词：

```text
"订单 状态 支付 发货 取消 库存"
"售后 退款 换货 REFUNDING 审核"
"商品详情 SKU 库存 评价"
"管理端 订单 导出 权限 审计"
```

## 5. 最小评测集

准备 20 个问题，每个标注：

```json
{
  "query": "订单状态怎么流转？",
  "expected_ids": ["rule:order-state"],
  "must_contain": ["PENDING_PAY", "PENDING_SHIP"]
}
```

指标：

| 指标 | 含义 |
|---|---|
| Hit@k | 正确 chunk 是否在前 k |
| MRR | 正确 chunk 排名倒数的均值 |
| 引用准确率 | 答案引用是否真的支持结论 |
| 拒答率 | 无证据时是否承认不知道 |

## 6. 四类失败模式

| 失败 | 原因 | 修复 |
|---|---|---|
| 召回不到 | 切片太大/太小、同义词缺失 | 调整粒度、加关键词 |
| 召回错 | 元数据缺失、过滤条件不对 | 加 type/模块过滤 |
| 答非所问 | prompt 没约束“只基于证据” | 强约束 + 引用 |
| 编造 | 无证据仍回答 | 要求“无证据则拒答” |

## 7. 在 AI_Studio 里验证

```text
知识库 → 召回测试
查询：订单状态怎么流转
Top K：5
```

检查返回的 chunk 是否包含 `PENDING_PAY`、`PENDING_SHIP`、`CLOSED`，以及来源文档是否为课件 L05/L06。

## 练习

1. 为“评价商家回复”设计 5 条评测问题。
2. 比较 top-k=3 和 top-k=8 的召回差异。
3. 找一条你认为切得太粗的 chunk，说明如何拆。
