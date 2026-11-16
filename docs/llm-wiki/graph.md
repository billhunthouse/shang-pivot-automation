# LLM-wiki 知识图谱

> 生成时间：2026-11-12  
> 数据源：`data/graph.json` + `apis.json` + `pages.json` + `requirements.json`  
> 规模：**309 节点 / 964 关系 / 6 类节点**

## 1. 直接打开

```bash
open /Users/imac/Desktop/电商自动化测试/shang-pivot-master/docs/llm-wiki/graph.html
```

或双击 `docs/llm-wiki/graph.html`。

页面支持：

- 左侧按类型筛选（需求 / 页面 / 接口 / 控制器 / 服务 / 数据表）
- 顶部搜索标题、ID、路径
- 点击节点查看属性、度数、关联关系
- 点击邻居继续跳转
- 中间图谱可横向滚动；节点多时纵向滚动

## 2. 节点与关系

| 节点类型 | 数量 | 含义 |
|---|---:|---|
| `requirement` | 52 | V1/V2/EXT 需求 |
| `page` | 41 | C 端/管理端页面路由 |
| `api` | 137 | HTTP 端点 |
| `controller` | 24 | Spring Controller |
| `service` | 24 | 应用 Service |
| `table` | 31 | PostgreSQL 表 |

| 关系类型 | 数量 | 含义 |
|---|---:|---|
| `requirement_has_page` | 79 | 需求包含页面 |
| `requirement_has_api` | 259 | 需求涉及接口 |
| `page_calls_api` | 147 | 页面调用接口 |
| `handled_by` | 137 | 接口由 Controller 处理 |
| `calls_service` | 86 | Controller 调用 Service |
| `accesses_table` | 256 | 链路访问数据表 |

## 3. 导出格式

| 文件 | 用途 |
|---|---|
| `data/knowledge-graph.json` | 带节点属性/关系标签的完整 JSON |
| `data/graph.graphml` | Gephi / yEd / Neo4j GraphML 导入 |
| `data/graph.cypher` | Neo4j `MERGE` 脚本 |
| `graph.html` | 自包含交互式可视化（无外部 CDN） |

### Neo4j 导入

```bash
# 1. 启动 Neo4j 后执行
cat docs/llm-wiki/data/graph.cypher | cypher-shell -u neo4j -p '<password>'
```

常用查询：

```cypher
// 某需求涉及的接口
MATCH (r:Requirement {id:'V2-FR-007'})-[:REQUIREMENT_HAS_API]->(a:Api)
RETURN r.label, a.label;

// 某页面调用的接口及落表
MATCH (p:Page {id:'page:mall:/product/:spuId'})-[:PAGE_CALLS_API]->(a:Api)
OPTIONAL MATCH (a)-[:ACCESSES_TABLE]->(t:Table)
RETURN p.label, a.label, collect(t.label);

// 某接口的完整下钻
MATCH path=(a:Api {id:'api:GET:/api/products/{spuId}'})-[*1..3]->(n)
RETURN path LIMIT 20;
```

### Gephi

1. 打开 Gephi → File → Open → `data/graph.graphml`
2. 按 `type` 着色（节点属性 `type`）
3. 用 ForceAtlas2 布局
4. 按 `degree` 调整节点大小

## 4. 维护

图谱由脚本生成，不手工编辑：

```bash
# 1) 若接口/页面/需求数据有变化，先重建 wiki 索引
python3 docs/llm-wiki/scripts/build_wiki.py

# 2) 重建知识图谱（JSON/GraphML/Cypher/HTML）
python3 docs/llm-wiki/scripts/build_graph_view.py
```

`build_graph_view.py` 会：

- 从 `graph.json` 读取节点/边
- 从 `apis/pages/requirements` 补属性
- 统计节点/关系类型
- 生成可交互 HTML 和 Neo4j/GraphML 导出

## 5. 限制

- 页面→接口映射来自 Vue import 启发式，间接调用可能漏；当前已对登录/设置/AI 浮窗做手工补充。
- 需求→页面/接口按模块/页面映射，跨模块需求可能不完整。
- 图谱中的“关系”是静态结构关系，不是运行时调用次数；运行时链路请看 `docs/06-baseline/05-调用链路.md` 或 SkyWalking/Tempo。
- 新增 API/页面/需求后必须重跑生成器，否则图谱会落后于代码。
