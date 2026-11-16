# 尚品汇自动化测试课件

四套可运行课件，全部基于当前电商项目真实接口与数据：

| 课件 | 文档 | 脚本 | 已验证结果 |
|---|---|---|---|
| Pytest | [01-Pytest自动化测试课件.md](01-Pytest自动化测试课件.md) | [`pytest/`](pytest/) | 22 passed |
| Java Cucumber + Allure | [02-Java-Cucumber课件.md](02-Java-Cucumber课件.md) | [`../automation/src/test/resources/features/courseware/`](../automation/src/test/resources/features/courseware/) | 11 passed |
| SkyWalking 全链路监控 | [03-SkyWalking全链路监控课件.md](03-SkyWalking全链路监控课件.md) | [`../observability/skywalking/`](../observability/skywalking/)、[`../scripts/observability/`](../scripts/observability/) | 服务/HTTP/SQL/JVM/告警通道已验证 |
| 禅道 MCP 开发与使用 | [04-禅道MCP开发与使用课件.md](04-禅道MCP开发与使用课件.md) | [`../zentao_mcp/`](../zentao_mcp/) | 连接/查询/创建/更新/删除 smoke test 通过 |

## 一、启动环境

课件依赖本地尚品汇后端、商城、管理端：

```bash
cd /Users/imac/Desktop/电商自动化测试/shang-pivot-master
bash automation/scripts/start-local.sh
```

确认：

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8086/api/home
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5174/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5173/
```

三个都应返回 `200`。

## 二、Pytest 课件

```bash
cd courseware/pytest
../../pytest_automation/.venv/bin/pip install -r requirements.txt
../../pytest_automation/.venv/bin/python -m pytest -q
# 22 passed
```

分层运行：

```bash
../../pytest_automation/.venv/bin/python -m pytest -m smoke -q
../../pytest_automation/.venv/bin/python -m pytest -m negative -q
../../pytest_automation/.venv/bin/python -m pytest -n 4 -q
```

课件覆盖：

1. 最小用例与业务码
2. fixture 登录复用
3. 参数化
4. 契约断言
5. marker 分层
6. xdist 并行
7. Allure
8. 数据工厂与清理
9. mock 外部依赖
10. API 端到端购买
11. 覆盖率

## 三、Java Cucumber 课件

```bash
cd automation
mvn test -Dcucumber.filter.tags="@courseware"
# 11 个课件场景通过，其余 74 个跳过
```

分层运行：

```bash
mvn test -Dcucumber.filter.tags="@courseware and @smoke"
mvn test -Dcucumber.filter.tags="@courseware and @negative"
mvn test -Dcucumber.filter.tags="@courseware and @e2e"
```

课件覆盖：

1. Feature/Scenario
2. Step Definition 与 Cucumber 表达式
3. Scenario Outline
4. DataTable
5. Background
6. Tags/Hooks
7. API Client 分层
8. Allure
9. 负向与安全
10. API E2E
11. 并行与 CI

## 四、与 CI/CD 的对应关系

| 课件知识点 | CI/CD 落点 |
|---|---|
| Pytest marker / xdist | `.github/workflows/nightly-pytest.yml` |
| Java Cucumber / Allure | `.github/workflows/e2e.yml` |
| 测试摘要 / 飞书 | `scripts/ci/feishu_notify.py` |
| 部署 / 回滚 | `.github/workflows/deploy-tencent.yml`、`scripts/deploy-release.sh` |
| 面试题 | [`../docs/CI-CD-面试题与实战解析.md`](../docs/CI-CD-面试题与实战解析.md) |

## 五、常见问题

| 现象 | 处理 |
|---|---|
| `ConnectException` / 环境预检失败 | 先执行 `automation/scripts/start-local.sh`，确认三个端口 200 |
| `pytest: error: unrecognized arguments: --reruns` | `pip install pytest-rerunfailures` |
| `--cov` 不识别 | `pip install pytest-cov` |
| Cucumber 找不到 Step | 确认 glue 包 `com.shangpivot.automation`，Step 文本完全一致 |
| 课件场景没跑 | 默认过滤了 `@courseware`，显式传 `-Dcucumber.filter.tags="@courseware"` |
| `total` 断言失败 | 后端 Long 序列化为字符串，先 `int()` |

## 六、建议的教学顺序

1. 先跑 Pytest 22 条，理解断言、fixture、参数化；
2. 再跑 Java Cucumber 11 条，理解 BDD 分层；
3. 对照 `docs/CI-CD-面试题与实战解析.md` 的流水线章节；
4. 最后把课件脚本接进自己的 GitHub Actions 练习。

## 七、SkyWalking 全链路监控课件

课件：[03-SkyWalking全链路监控课件.md](03-SkyWalking全链路监控课件.md)  
手册：[../docs/SkyWalking运维手册.md](../docs/SkyWalking运维手册.md)

不要求本地启动整套监控，直接在已部署的腾讯云环境练习：

```bash
# SkyWalking UI
open http://49.233.135.247:60084/skywalking/

# 链路查询（在服务器上执行）
python3 /opt/skywalking/skywalking-query.py \
  --service shang-pivot --minutes 30 --endpoint /api/home

# 告警接收器
curl -s http://172.17.0.1:18080/health
tail -f /var/log/skywalking-alarm/alarms.jsonl
```

课件覆盖：

1. Trace/Span/Segment/Endpoint/Instance 基础；
2. SkyWalking 架构与 Agent 接入；
3. 服务/实例/端点/JVM 指标；
4. 从告警到 SQL 的七步排查法；
5. 首页慢、登录慢、连接池、GC 四个案例；
6. 慢 SQL 阈值与 SQL 参数；
7. 告警规则/Webhook/Runbook；
8. 系统级监控缺口与补齐路线；
9. Lab 1–7 实验手册。

## 八、禅道 MCP 开发与使用课件

课件：[04-禅道MCP开发与使用课件.md](04-禅道MCP开发与使用课件.md)
代码：[../zentao_mcp/](../zentao_mcp/)

课件覆盖：

1. MCP Host / Server / 下游系统三层架构；
2. FastMCP、`@mcp.tool()`、类型注解与 docstring；
3. 禅道 Token 登录、401 重试、密码文件安全；
4. 产品查询、用例查询、用例详情、用例创建；
5. 禅道 22.6 的状态更新与步骤更新限制；
6. ZCode `mcp.servers.zentao` 注册与启动；
7. `smoke_test.py` 真实验证：创建、更新、查询、清理；
8. 产品查询、用例查询、创建用例的完整案例；
9. 常见故障排查与课堂练习。

验证命令：

```bash
cd zentao_mcp
ZENTAO_BASE_URL=http://49.233.135.247:60084 \
ZENTAO_ACCOUNT=admin \
ZENTAO_PASSWORD_FILE=$HOME/.zcode/secrets/zentao-admin-password \
.venv/bin/python smoke_test.py
```
