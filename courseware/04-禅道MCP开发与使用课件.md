# 禅道 MCP 开发与使用课件

> 本课件基于当前仓库里的 `zentao_mcp/` 真实代码和禅道 22.6 实测结果整理。  
> 目标不是只跑通一个脚本，而是让你理解：**MCP 协议怎么工作、禅道 API 怎么封装、工具怎么注册、ZCode 怎么拉起、日常怎么用。**

---

## 0. 学完你能做什么

学完这套内容，你应该能独立完成：

1. 用 Python MCP SDK 写一个 stdio MCP Server；
2. 把禅道 REST API 封装成可被 AI 调用的工具；
3. 在 ZCode 中注册 MCP Server；
4. 用自然语言查询产品、测试用例、Bug、测试单；
5. 创建带步骤和预期结果的测试用例；
6. 知道禅道 22.6 API 的边界，不会在“改用例状态/改步骤”上反复踩坑。

---

## 1. 先理解 MCP 是什么

MCP（Model Context Protocol）可以理解为：

```text
AI 客户端（Host）
   │  读取工具列表、发起工具调用
   ▼
MCP Server（本项目：zentao_mcp/server.py）
   │  HTTP + Token
   ▼
禅道 REST API（/api.php/v1/...）
   │
   ▼
禅道数据库
```

三个角色：

| 角色 | 在本项目里是谁 | 作用 |
|---|---|---|
| Host / Client | ZCode | 发现工具、把工具描述给模型、转发调用 |
| MCP Server | `zentao_mcp/server.py` | 暴露 `zentao_*` 工具 |
| 下游系统 | 禅道 22.6 | 提供产品、用例、Bug 数据 |

本项目使用 **stdio 传输**：

- ZCode 启动 `server.py` 子进程；
- 通过标准输入/标准输出交换 JSON-RPC 消息；
- 不需要额外开 HTTP 端口；
- **不要把调试 `print` 写到 stdout**，否则会污染协议消息。调试信息应写 stderr 或日志。

---

## 2. 项目结构

```text
zentao_mcp/
├── server.py            # MCP Server：定义工具、注册工具、启动 stdio
├── zentao_client.py     # 禅道 API 客户端：登录、请求、错误处理、业务封装
├── smoke_test.py        # 真实环境 smoke test：查询/创建/更新/删除
├── requirements.txt     # mcp>=1.0,<2
├── pyproject.toml       # Python 项目声明
├── .env.example         # 环境变量示例
└── README.md            # 快速使用说明
```

分层原则：

- `server.py` 只负责 **MCP 工具协议层**：参数、类型、docstring、返回值；
- `zentao_client.py` 只负责 **禅道 API 层**：URL、Token、表单、异常；
- 两层分开后，换 MCP 框架或换禅道版本时，不会互相牵连。

---

## 3. 开发准备

### 3.1 环境

```bash
cd zentao_mcp
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

依赖只有：

```text
mcp>=1.0,<2
```

### 3.2 凭证

不要把密码写进代码或仓库。推荐使用 600 权限文件：

```bash
mkdir -p ~/.zcode/secrets
chmod 700 ~/.zcode/secrets
# 从服务器读取或手动创建
ssh shangpivot-tencent 'cat /opt/zentao/admin-password' \
  > ~/.zcode/secrets/zentao-admin-password
chmod 600 ~/.zcode/secrets/zentao-admin-password
```

环境变量：

| 变量 | 必填 | 说明 |
|---|---|---|
| `ZENTAO_BASE_URL` | 是 | 例如 `http://49.233.135.247:60084` |
| `ZENTAO_ACCOUNT` | 否 | 默认 `admin` |
| `ZENTAO_PASSWORD_FILE` | 二选一 | 密码文件路径，推荐 |
| `ZENTAO_PASSWORD` | 二选一 | 直接传密码，不推荐 |
| `ZENTAO_TOKEN` | 否 | 已有 token 时跳过登录 |
| `ZENTAO_API_PREFIX` | 否 | 默认 `/api.php/v1` |
| `ZENTAO_TIMEOUT` | 否 | 默认 20 秒 |

---

## 4. 代码主线：一个 MCP Server 是怎么写出来的

### 4.1 创建 FastMCP 实例

`server.py` 开头：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "zentao",
    instructions=(
        "禅道 MCP。先用 zentao_list_products 找 product_id，再查/建用例。"
        "写入类工具会直接修改禅道数据，调用前确认目标和字段。"
        "用例 status 在禅道 22.6 API 中不能直接改，请优先用 bug 生命周期动作或 UI。"
    ),
)
```

`instructions` 会告诉模型这个 Server 的边界和使用顺序，等于给 AI 一份“使用须知”。

### 4.2 用 `@mcp.tool()` 注册工具

```python
@mcp.tool()
def zentao_list_products(page: int = 1, limit: int = 20) -> dict[str, Any]:
    """列出禅道产品。product_id 是后续查/建用例的必填参数。"""
    return guarded(lambda: client().list_products(page=page, limit=limit))
```

三个关键点：

1. **函数名就是工具名**：`zentao_list_products`；
2. **类型注解就是参数 Schema**：`page: int`、`limit: int`；
3. **docstring 就是工具说明**：模型根据它决定什么时候调用。

### 4.3 统一返回格式

```python
def ok(data):
    return {"ok": True, "data": data}

def fail(exc):
    return {"ok": False, "error": str(exc), "type": type(exc).__name__}

def guarded(fn):
    try:
        return ok(fn())
    except ZenTaoError as exc:
        return fail(exc)
    except Exception as exc:
        return fail(exc)
```

这样即使禅道接口报错，MCP 也不会直接崩溃，而是返回可读的：

```json
{"ok": false, "error": "禅道登录失败: HTTP 401", "type": "ZenTaoError"}
```

### 4.4 单例客户端 + Token 缓存

```python
_client: ZenTaoClient | None = None

def client() -> ZenTaoClient:
    global _client
    if _client is None:
        _client = ZenTaoClient.from_env()
    return _client
```

`ZenTaoClient.login()` 第一次登录拿到 token 后会缓存：

```python
def login(self) -> str:
    if self._token:
        return self._token
    # POST /api.php/v1/tokens
    # 保存 self._token
```

请求遇到 401/403 时，`_request()` 会清空 token、重新登录，并只重试一次：

```python
if exc.code in (401, 403) and retry_auth:
    self._token = None
    self.login()
    return self._request(..., retry_auth=False)
```

这是对接企业系统时非常值得复用的模式。

---

## 5. 禅道 API 封装要点

### 5.1 产品查询

客户端方法：

```python
def list_products(self, page: int = 1, limit: int = 20) -> dict:
    return self._request(
        "GET", "/products", params={"page": page, "limit": limit}
    )
```

实际请求：

```http
GET /api.php/v1/products?page=1&limit=20
Token: <登录返回的 token>
```

### 5.2 测试用例查询

```python
def list_test_cases(
    self,
    product_id: int,
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
) -> dict:
    payload = self._request(
        "GET",
        f"/products/{product_id}/testcases",
        params={"page": page, "limit": limit},
    )
    if status:
        cases = payload.get("testcases") or []
        payload["testcases"] = [
            case for case in cases if case.get("status") == status
        ]
        payload["filteredByStatus"] = status
    return payload
```

注意：`status` 过滤是**客户端内存过滤**，不是禅道服务端查询参数。  
这样写简单，但数据量大时应改成服务端分页 + 服务端过滤，或至少明确返回 `filteredByStatus`。

### 5.3 用例 ID 兼容

列表接口可能返回：

```json
{"id": "case_1", "caseID": 1}
```

而详情接口要数字 `1`。因此客户端做了统一：

```python
@staticmethod
def normalize_case_id(case_id: int | str) -> int:
    value = str(case_id).strip()
    if value.startswith("case_"):
        value = value[5:]
    return int(value)
```

所以 `zentao_get_test_case` 同时接受 `1` 和 `case_1`。

### 5.4 创建用例：为什么用表单而不是 JSON

禅道 22.6 创建用例时，步骤字段不是普通 JSON 数组，而是嵌套表单字段：

```text
product=1
module=0
type=feature
stage[]=test
title=API-003 购物车并发加购
pri=1
precondition=...
keywords=...
steps[1]=打开购物车
expects[1]=页面正常
stepType[1]=step
steps[2]=并发加购同一 SKU
expects[2]=不超卖
stepType[2]=step
```

代码：

```python
pairs = [
    ("product", str(product_id)),
    ("module", str(module_id)),
    ("type", case_type),
    ("stage[]", stage),
    ("title", title),
    ("pri", str(priority)),
    ("precondition", precondition or ""),
    ("keywords", keywords or ""),
]
for index, step in enumerate(steps or [], start=1):
    pairs.extend([
        (f"steps[{index}]", step_text),
        (f"expects[{index}]", expect_text),
        (f"stepType[{index}]", step_type),
    ])
return self._request("POST", f"/products/{product_id}/testcases", form_pairs=pairs)
```

**教学重点**：不要凭直觉用 `json={"steps": [...]}`；先用 curl/Postman 验证接口实际接受什么格式，再封装。

### 5.5 更新用例与限制

更新只支持基础字段：

```python
body = {}
if title is not None:
    body["title"] = title
if precondition is not None:
    body["precondition"] = precondition
if keywords is not None:
    body["keywords"] = keywords
if priority is not None:
    body["pri"] = priority
return self._request("PUT", f"/testcases/{case_id}", json_body=body)
```

两个明确限制：

1. **不能直接替换步骤**：`PUT /testcases/{id}` 不会改 steps，客户端会主动抛错，提示用 UI 编辑或新建用例；
2. **不能直接改 status**：`zentao_update_test_case_status` 会先改、再读回验证，如果状态没变就返回明确错误。

---

## 6. MCP 注册：让 ZCode 找到它

### 6.1 配置文件

在 `~/.zcode/cli/config.json` 的 `mcp.servers` 下增加 `zentao`：

```json
{
  "mcp": {
    "servers": {
      "zentao": {
        "command": "/Users/imac/Desktop/电商自动化测试/shang-pivot-master/zentao_mcp/.venv/bin/python",
        "args": [
          "/Users/imac/Desktop/电商自动化测试/shang-pivot-master/zentao_mcp/server.py"
        ],
        "env": {
          "ZENTAO_BASE_URL": "http://49.233.135.247:60084",
          "ZENTAO_ACCOUNT": "admin",
          "ZENTAO_PASSWORD_FILE": "/Users/imac/.zcode/secrets/zentao-admin-password"
        }
      }
    }
  }
}
```

说明：

- `command` 必须是 **MCP 专用 venv 的 Python 绝对路径**；
- `args` 必须是 `server.py` 的绝对路径；
- 密码文件不要写进仓库，只写路径；
- 当前 ZCode 配置可以省略 `"type": "stdio"`；其他 MCP 客户端通常需要写明 `type: stdio`。

### 6.2 重新加载

保存配置后：

1. 重启 ZCode，或重新加载 MCP；
2. 在工具列表里确认出现 `zentao_ping`、`zentao_list_products`、`zentao_list_test_cases` 等；
3. 先调用 `zentao_ping`，不要一上来就创建用例。

### 6.3 启动方式

MCP Server 不需要你手动常驻启动：

```text
ZCode 启动 → 读取 config.json → 拉起 server.py → 通过 stdio 通信
```

`server.py` 最后一行：

```python
if __name__ == "__main__":
    main()
```

`main()` 里：

```python
mcp.run(transport="stdio")
```

手动运行 `python server.py` 会看起来“卡住”，因为它正在等待 stdin 的 JSON-RPC 消息，这是正常的。

如果要单独验证禅道 HTTP 客户端，而不是 MCP 协议，可以运行：

```bash
cd zentao_mcp
ZENTAO_BASE_URL=http://49.233.135.247:60084 \
ZENTAO_ACCOUNT=admin \
ZENTAO_PASSWORD_FILE=$HOME/.zcode/secrets/zentao-admin-password \
.venv/bin/python smoke_test.py
```

---

## 7. 实测验证

### 7.1 `zentao_ping`

调用：

```text
zentao_ping
```

返回（节选）：

```json
{
  "ok": true,
  "data": {
    "baseUrl": "http://49.233.135.247:60084",
    "products": {
      "page": 1,
      "total": 1,
      "products": [
        {
          "id": 1,
          "name": "尚品汇电商平台",
          "totalBugs": 4
        }
      ]
    }
  }
}
```

说明登录、token、产品接口都通了。

### 7.2 产品查询

调用：

```text
zentao_list_products(page=1, limit=20)
```

关键返回字段：

| 字段 | 含义 |
|---|---|
| `id` | 产品 ID，后续查用例/Bug 的入口 |
| `name` | 产品名称 |
| `totalBugs` | Bug 总数 |
| `testCaseCoverage` | 用例覆盖率（当前为 0） |

实际数据：

```text
1 个产品：尚品汇电商平台（id=1）
```

### 7.3 用例查询

调用：

```text
zentao_list_test_cases(product_id=1, page=1, limit=20)
```

实际返回 3 条：

| 用例 ID | 标题 | 优先级 | 类型 | 状态 |
|---|---|---:|---|---|
| `case_3` | SEC-001 JWT alg=none 必须拒绝 | 1 | security | normal |
| `case_2` | API-002 登录-地址-下单-支付主链路 | 1 | feature | normal |
| `case_1` | API-001 首页健康检查与运营位契约 | 3 | feature | normal |

查询 `blocked`：

```text
zentao_list_test_cases(product_id=1, status="blocked")
```

返回：

```json
{
  "ok": true,
  "data": {
    "testcases": [],
    "filteredByStatus": "blocked"
  }
}
```

注意：这是客户端过滤，分页外的数据不会被扫描；真实项目应改成服务端过滤或全量拉取后过滤。

### 7.4 用例详情

调用：

```text
zentao_get_test_case(case_id="case_1")
```

返回（节选）：

```json
{
  "ok": true,
  "data": {
    "id": 1,
    "title": "API-001 首页健康检查与运营位契约",
    "precondition": "服务已启动",
    "pri": 3,
    "type": "feature",
    "status": "normal",
    "steps": [],
    "caseID": 1
  }
}
```

这条用例当前 `steps` 为空。创建用例时如果传了步骤，详情里会返回步骤数组。

### 7.5 创建用例 smoke test

`smoke_test.py` 会真实执行一遍：

```text
products: 1
test cases: 3
created: 19 steps: 2
title: MCP smoke test（可删除）
updated keywords: ok
status update limitation: 禅道 22.6 的 API 没有直接修改用例 status 的入口；当前仍为 normal。请用评审/执行动作，或在 UI 中修改。
cleanup: ok
```

它验证了：

1. 产品查询；
2. 用例查询；
3. 创建带 2 个步骤的用例；
4. 查询刚创建的用例；
5. 更新关键词；
6. 状态修改限制；
7. 删除清理（清理接口只在 smoke test 内部使用，没有暴露成 MCP 工具，避免误删）。

### 7.6 Bug 与测试单

```text
zentao_list_bugs(product_id=1)
```

实际 4 条：

- DEF-001 并发下单发货单号冲突
- DEF-002 畸形 JSON 返回 500
- DEF-003 JWT alg=none 触发 500 与默认错误体
- DEF-004 购物车数量 1.5/abc 返回 500

```text
zentao_list_test_tasks(project_id=1)
```

当前返回 0 条，接口正常。

---

## 8. 日常使用案例

### 案例 1：先找产品，再查用例

自然语言：

```text
帮我查一下禅道里有哪些产品，然后查产品 1 下的测试用例。
```

模型应调用：

```text
zentao_list_products()
zentao_list_test_cases(product_id=1)
```

为什么要先查产品？因为 `product_id` 是后续接口的必填参数，不要凭猜测传 1。

### 案例 2：按状态筛选

```text
查产品 1 下所有 blocked 的用例。
```

调用：

```text
zentao_list_test_cases(product_id=1, status="blocked")
```

如果没有结果，返回空数组是正常业务结果，不是接口失败。

### 案例 3：查看某条用例的步骤

```text
把 case_3 的详情打开，重点看前置条件和步骤。
```

调用：

```text
zentao_get_test_case(case_id="case_3")
```

### 案例 4：创建一条带步骤的用例

自然语言：

```text
在产品 1 下创建用例：
标题：API-003 购物车并发加购
前置条件：已登录
步骤 1：并发加购同一 SKU
预期 1：不超卖
步骤 2：查询购物车数量
预期 2：数量正确
优先级：1
```

对应工具调用参数：

```json
{
  "product_id": 1,
  "title": "API-003 购物车并发加购",
  "precondition": "已登录",
  "priority": 1,
  "steps": [
    {"step": "并发加购同一 SKU", "expect": "不超卖"},
    {"step": "查询购物车数量", "expect": "数量正确"}
  ]
}
```

### 案例 5：查询 Bug 并做生命周期动作

```text
查产品 1 下的 Bug，然后把 Bug 1 标记为已解决，resolution=fixed。
```

调用：

```text
zentao_list_bugs(product_id=1)
zentao_bug_action(bug_id=1, action="resolve",
                  fields={"resolution": "fixed", "resolvedBuild": "trunk"})
```

写操作前必须先查详情，确认 Bug ID 和当前状态。

---

## 9. 工具与 API 对照表

| MCP 工具 | HTTP 方法与路径 | 说明 |
|---|---|---|
| `zentao_ping` | `GET /products?limit=1` | 验证登录与产品接口 |
| `zentao_list_products` | `GET /products` | 产品列表 |
| `zentao_list_test_cases` | `GET /products/{id}/testcases` | 用例列表；status 客户端过滤 |
| `zentao_get_test_case` | `GET /testcases/{id}` | 用例详情 |
| `zentao_create_test_case` | `POST /products/{id}/testcases` | 表单提交，步骤用 `steps[N]` |
| `zentao_update_test_case` | `PUT /testcases/{id}` | 基础字段更新 |
| `zentao_update_test_case_status` | `PUT /testcases/{id}` + 读回 | 22.6 通常不生效 |
| `zentao_list_bugs` | `GET /products/{id}/bugs` | Bug 列表 |
| `zentao_get_bug` | `GET /bugs/{id}` | Bug 详情 |
| `zentao_bug_action` | `POST /bugs/{id}/{action}` | resolve/close/assign/confirm/active |
| `zentao_list_test_tasks` | `GET /projects/{id}/testtasks` | 测试单列表 |

---

## 10. 常见问题与排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `缺少环境变量 ZENTAO_BASE_URL` | 配置没有注入 env | 检查 `config.json` 的 `env` |
| `读取密码文件失败` | 路径错误/权限不足 | 用绝对路径，`chmod 600` |
| `禅道登录失败: HTTP 401` | 账号密码错误或 token 过期 | 检查密码文件；重启 MCP |
| 工具列表里没有 `zentao_*` | MCP 未加载 | 重启 ZCode，检查 JSON 语法 |
| 运行 `server.py` 像卡住 | stdio 正常等待输入 | 不要手动当 HTTP 服务用 |
| 创建用例步骤丢失 | 没用 `steps[N]` 表单格式 | 按第 5.4 节组装 |
| 改状态失败 | 禅道 22.6 API 限制 | 用评审/执行动作或 UI |
| 更新步骤失败 | API 不支持替换 | 新建用例或在 UI 编辑 |
| 查询 blocked 为空 | 客户端只过滤当前页 | 改服务端过滤或全量拉取 |

---

## 11. 课堂练习

1. 调用 `zentao_ping`，确认返回 `ok: true`；
2. 调用 `zentao_list_products`，记录产品 ID 和名称；
3. 调用 `zentao_list_test_cases(product_id=1)`，统计 `normal/blocked` 数量；
4. 调用 `zentao_get_test_case(case_id="case_1")`，找出前置条件；
5. 创建一条带 2 个步骤的临时用例；
6. 查询详情确认步骤数量；
7. 更新关键词；
8. 用 `smoke_test.py` 的清理逻辑删除临时用例；
9. 解释为什么 `server.py` 不能手动当 HTTP 服务启动。

---

## 12. 一句话总结

**MCP Server 的本质不是“写一个聊天机器人”，而是把下游系统的能力，用清晰的工具名、参数 Schema 和错误边界，稳定地暴露给 AI 客户端。**  
`zentao_mcp` 的价值在于：把禅道的产品、用例、Bug 查询和用例创建，变成了 ZCode 里可以直接调用的 `zentao_*` 工具。
