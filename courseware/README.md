# 尚品汇自动化测试课件

两套可运行课件，全部基于当前电商项目真实接口与数据：

| 课件 | 文档 | 脚本 | 已验证结果 |
|---|---|---|---|
| Pytest | [01-Pytest自动化测试课件.md](01-Pytest自动化测试课件.md) | [`pytest/`](pytest/) | 22 passed |
| Java Cucumber + Allure | [02-Java-Cucumber课件.md](02-Java-Cucumber课件.md) | [`../automation/src/test/resources/features/courseware/`](../automation/src/test/resources/features/courseware/) | 11 passed |

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
