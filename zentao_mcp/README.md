# ZenTao MCP Server

一个基于 Python MCP SDK 的禅道 MCP Server，面向测试工程师：

- 查看产品、测试用例、Bug、测试单；
- 上传/创建测试用例（含步骤、预期结果）；
- 更新用例标题、前置条件、关键词、优先级；
- 执行 Bug 生命周期动作：resolve / close / assign / confirm / active；
- 查询用例状态，并对“禅道 22.6 不支持直接改状态”给出明确提示。

## 工具列表

| 工具 | 作用 | 写操作 |
|---|---|---|
| `zentao_ping` | 检查地址、账号、token | 否 |
| `zentao_list_products` | 列出产品 | 否 |
| `zentao_list_test_cases` | 按产品查用例 | 否 |
| `zentao_get_test_case` | 查看用例详情，`case_id` 支持 1 或 `case_1` | 否 |
| `zentao_create_test_case` | 创建用例，支持多步骤 | 是 |
| `zentao_update_test_case` | 改标题/前置/关键词/优先级 | 是 |
| `zentao_update_test_case_status` | 尝试改状态并读回验证 | 是（通常会被禅道 API 拒绝） |
| `zentao_list_bugs` | 查 Bug | 否 |
| `zentao_get_bug` | 查看 Bug | 否 |
| `zentao_bug_action` | resolve/close/assign/confirm/active | 是 |
| `zentao_list_test_tasks` | 查测试单 | 否 |

## 安装

```bash
cd zentao_mcp
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

## 凭证

不要把密码写进仓库。推荐把禅道管理员密码放在本地 600 权限文件：

```bash
mkdir -p ~/.zcode/secrets
chmod 700 ~/.zcode/secrets
# 从服务器读取，或手动创建
ssh shangpivot-tencent 'cat /opt/zentao/admin-password' > ~/.zcode/secrets/zentao-admin-password
chmod 600 ~/.zcode/secrets/zentao-admin-password
```

## MCP 配置

在 `~/.zcode/cli/config.json` 的 `mcp.servers` 中增加：

```json
{
  "zentao": {
    "type": "stdio",
    "command": "/path/to/shang-pivot-master/zentao_mcp/.venv/bin/python",
    "args": [
      "/path/to/shang-pivot-master/zentao_mcp/server.py"
    ],
    "env": {
      "ZENTAO_BASE_URL": "http://49.233.135.247:60084",
      "ZENTAO_ACCOUNT": "admin",
      "ZENTAO_PASSWORD_FILE": "/path/to/zentao-admin-password"
    }
  }
}
```

支持的环境变量：

| 变量 | 必填 | 说明 |
|---|---|---|
| `ZENTAO_BASE_URL` | 是 | 如 `http://49.233.135.247:60084` |
| `ZENTAO_ACCOUNT` | 否 | 默认 `admin` |
| `ZENTAO_PASSWORD_FILE` | 二选一 | 密码文件路径 |
| `ZENTAO_PASSWORD` | 二选一 | 直接传密码（不推荐写进配置） |
| `ZENTAO_TOKEN` | 否 | 已有 token 时跳过登录 |
| `ZENTAO_API_PREFIX` | 否 | 默认 `/api.php/v1` |
| `ZENTAO_TIMEOUT` | 否 | 默认 20 秒 |

改完配置后重启 ZCode，让 MCP 重新加载。列表接口返回的用例 ID 可能是 `case_1`，`zentao_get_test_case` / `zentao_update_test_case` 同时接受 `1` 和 `case_1`。

## 使用示例

```text
列出禅道里的产品
```

```text
查一下产品 1 下的测试用例，只看 blocked
```

```text
在产品 1 下创建用例：
标题：API-003 购物车并发加购
步骤：1. 并发加购同一 SKU；2. 检查库存和购物车数量
预期：1. 不超卖；2. 数量正确
优先级：1
```

```text
把用例 1 的关键词改成 smoke，优先级改成 2
```

```text
把 Bug 1 标记为已解决，resolution=fixed
```

## 已知限制

### 1. 用例状态不能直接改

禅道 22.6 的 API 没有直接修改用例 `status` 的入口。`zentao_update_test_case_status` 会：

1. 调用 `PUT /testcases/{id}`；
2. 重新 `GET` 用例；
3. 如果状态没变，返回明确错误。

状态值：`wait`、`normal`、`blocked`、`investigate`。  
生产建议用评审/执行动作，或在禅道 UI 修改。

### 2. 步骤更新不支持

`PUT /testcases/{id}` 不会替换 `steps`。当前支持：

- 创建时写入步骤（`steps[N]` + `expects[N]` + `stepType[N]`）；
- 更新标题/前置条件/关键词/优先级。

步骤修改请用 UI。

### 3. Bug 动作字段

`zentao_bug_action` 透传禅道 API 字段，例如：

```json
{"resolution": "fixed", "resolvedBuild": "trunk"}
```

不同禅道版本字段可能不同，先 `zentao_get_bug` 看当前数据。

## 安全建议

- 使用独立测试账号，不要长期用 `admin`；
- 密码文件 600，不提交 Git；
- 生产环境给 MCP 账号最小权限；
- 写操作前先查询确认 ID，避免误改；
- 不要把 token/密码打印到日志或聊天。

## 本地验证

```bash
cd zentao_mcp
ZENTAO_BASE_URL=http://49.233.135.247:60084 \
ZENTAO_PASSWORD_FILE=$HOME/.zcode/secrets/zentao-admin-password \
.venv/bin/python - <<'PY'
from zentao_client import ZenTaoClient
c = ZenTaoClient.from_env()
print(c.list_products(limit=5)["total"])
print(c.list_test_cases(1, limit=5)["total"])
PY
```
