# 尚品汇 LLM-wiki

> 面向 LLM / RAG / 新需求分析 / 用例生成 / 代码影响分析的项目知识库  
> 生成日期：2026-11-11  
> 代码基线：当前工作区（含 V1 后台、V2 C 端、C 端 AI 助手扩展）

## 这套 wiki 解决什么问题

传统文档按“版本/章节”组织，适合人读；LLM 需要的是：

1. 需求、页面、接口、Controller/Service/表之间有明确 ID 和边；
2. 能按主题召回小块，而不是整篇 PRD；
3. 能区分“需求意图”和“实现真值/已知缺口”；
4. 能从页面/接口反向定位代码和数据库表。

因此本目录同时提供两种形态：

```text
docs/llm-wiki/
├── README.md                    # 使用说明（本文件）
├── index.md                     # 导航与典型问题
├── 00-glossary.md               # 术语表
├── 01-overview.md               # 系统全景、模块、角色、端口
├── 02-requirements.md           # V1/V2/EXT 需求目录
├── 03-api-catalog.md            # 136 个端点目录（按 tag）
├── 04-page-map.md               # C 端/管理端页面 ↔ API
├── 05-traceability-matrix.md    # 需求 → 页面 → 接口
├── 06-business-rules.md         # 状态机、库存、鉴权、负面清单
├── 07-code-map.md               # Controller → Service → 表
├── 08-llm-playbooks.md          # 需求分析/用例生成/代码分析提示词
├── 09-critical-call-chains.md    # 关键调用链
├── 10-test-assets.md             # 现有测试资产与复用
├── graph.html                    # 交互式知识图谱
├── graph.md                      # 图谱说明/Neo4j/Gephi
├── course/                       # 学习课件与笔记（13 节课 + 6 篇笔记）
├── data/
│   ├── apis.json                # 机器可读接口目录
│   ├── pages.json               # 机器可读页面目录
│   ├── requirements.json        # 机器可读需求目录
│   ├── graph.json               # 需求/页面/接口/服务/表图
│   ├── knowledge-graph.json     # 带节点属性的知识图谱
│   ├── graph.graphml            # Gephi/yEd/Neo4j GraphML
│   ├── graph.cypher             # Neo4j MERGE 脚本
│   └── chunks.jsonl             # RAG 切片（242 chunks）
└── scripts/build_wiki.py        # 可再生生成器
```

## 数据规模

| 对象 | 数量 |
|---|---:|
| API 端点 | **137**（135 个源码/调用图端点 + C 端 AI 聊天 + 评价商家回复） |
| 页面路由 | **41**（C 端 20 个，含 AI 浮窗；管理端 21 个） |
| 需求条目 | **52**（V1 24 + V2 26 + EXT 2） |
| RAG chunks | **242** |
| 数据表 | 36（identity 12 + commerce 24），详见 `docs/06-baseline/01-数据字典.md` |

## 三种使用方式

### 1. 人读：从 index 进入

```text
index.md
  → 00-glossary.md
  → 01-overview.md
  → 02-requirements.md
  → 04-page-map.md
  → 03-api-catalog.md
  → 06-business-rules.md
  → 07-code-map.md
  → 09-critical-call-chains.md
  → 10-test-assets.md
```

### 2. RAG：直接摄入 `data/chunks.jsonl`

每行结构：

```json
{
  "id": "api:GET:/api/home",
  "type": "api|page|requirement|rule",
  "title": "GET /api/home",
  "text": "可读正文",
  "source": "源文件/生成物",
  "links": ["tag:C端商城"],
  "tags": ["C端商城", "api"]
}
```

建议：

- embedding 文本 = `title + "\n" + text`；
- metadata 保留 `type/source/tags`；
- `api` 查询 top-k 8，`requirement`/`rule` 查询 top-k 5；
- 使用 `links` 做第二跳扩展：接口 → Controller/Service/表，需求 → 页面/接口；
- 不要把 03/04 的整篇 Markdown 再切片，避免与 chunks 重复。

### 3. 代码/需求分析：先图后文

- 需求影响：`requirements.json` → `pages` / `api_ids` → `graph.json` 找 Controller/Service/表；
- 页面问题：`pages.json` → `api_ids` → `apis.json`；
- 接口问题：`apis.json` → `controller/services/tables`；
- 规则问题：`06-business-rules.md` + `chunks` 中 `type=rule`。

## 生成与维护

```bash
# 重新生成 data/*.json、chunks.jsonl、02/03/04/05/07 Markdown
python3 docs/llm-wiki/scripts/build_wiki.py
```

数据来源：

| 来源 | 用途 |
|---|---|
| `docs/openapi-v3-api-docs.json` | 参数、tag、operationId |
| `api_testcases/artifacts/call-graph.json` | 端点 → Controller/Service/表、前端 API 文件 |
| `api_testcases/artifacts/endpoint-model.json` | 端点摘要、DTO 字段、错误码 |
| `docs/01-requirements/PRD-V1.0-后台管理.md` | V1 需求 |
| `docs/01-requirements/PRD-V2.0-购物网站.md` | V2 需求 |
| `shang-mall/src/router/index.ts` + `views/*.vue` | C 端页面/API import |
| `shang-admin-web/src/router/index.ts` + `views/*.vue` | 管理端页面/API import |
| `docs/06-baseline/02-业务规则与状态机.md` | 实现真值/状态机/负面清单 |

> `call-graph.json` 和 OpenAPI 是 2026-10-09/10 生成的快照；本轮生成器已补入 2026-11 的 C 端 AI 聊天端点。**如果后端新增/修改接口，先重新生成 call graph/endpoint model，再运行本生成器。**

## 可信度与限制

**可信度顺序（从高到低）：**

1. 运行中的代码：Controller / Service / SecurityConfig / Mapper / SQL
2. `docs/06-baseline/02-业务规则与状态机.md`（As-built，但基线为 `810986c`）
3. `api_testcases/artifacts/call-graph.json`、`endpoint-model.json`、OpenAPI
4. PRD / 设计文档（需求意图，不保证实现）
5. 本 wiki 的自动映射（页面 import 启发式、需求模块映射）

**已知限制：**

- 页面 → API 通过 Vue import 解析，间接调用（组件/store/父组件）可能漏；AI 浮窗已手工加入。
- 需求 → 页面按模块映射，V2“后台”需求已手工指定管理端页面；跨模块需求可能不完整。
- `03-api-catalog.md` 的 auth 来自 call graph；公开白名单以 `SecurityConfig` 为准。
- `06-business-rules.md` 以基线 `810986c` 为准；当前工作区新增的 C 端 AI 助手属于 EXT，不在旧基线。
- 本 wiki 不保存真实密码、token、密钥。

## 推荐问答

- 新增“优惠券”会影响哪些页面、接口、表？
- 订单从待付款到已完成有哪些合法/非法转移？
- 商品详情页调用了哪些接口？各接口落到哪个 Service/表？
- 管理端订单导出需要什么权限？有无审计？
- 退货/换货/退款当前实现有什么缺口？
- 为“地址管理”生成正向、边界、越权、并发用例。
- 修改 `OrderSubmitService.submit` 会影响哪些接口和测试？
