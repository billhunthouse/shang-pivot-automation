# CI/CD 面试题与实战解析

> 结合尚品汇电商项目（Java 21 + Cucumber + Allure + pytest-xdist + 腾讯云 + 飞书）整理。
> 用法：先看问题自己回答，再看“参考答法”；面试时优先讲**取舍**和**失败处理**，不要只背工具名。

---

## 一、基础概念

### Q1. CI、CD、持续交付、持续部署有什么区别？

**参考答法**

- **CI（持续集成）**：频繁合并代码，每次合并自动构建、跑测试，尽早发现集成问题。
- **CD（持续交付）**：在 CI 基础上，保证代码随时可发布，但**发布动作由人审批**。
- **持续部署**：审批也自动化，通过门禁就直接上生产。
- 很多团队说“CD”其实指持续交付，面试时要先确认语境。

**本项目实践**

- push/PR 触发 `e2e.yml`，自动构建后端、起前端、跑 Cucumber/Allure → CI。
- `deploy-tencent.yml` 用 `workflow_dispatch` + GitHub Environment 审批 → 持续交付，不是持续部署。
- 生产部署没有做成“合并即上线”，因为电商涉及资金/库存，必须保留人工放行。

---

### Q2. 一条合格的 CI 流水线应该有哪些阶段？

**参考答法**

```text
静态检查 → 构建 → 单元测试 → API 测试 → UI/E2E → 报告 → 质量门禁 → 制品归档
```

要求：

1. 每个阶段失败要快速失败（fail fast），不要把问题拖到 E2E；
2. 阶段之间产物可追溯（commit、构建号、报告、镜像 tag）；
3. 门禁可量化（覆盖率、P0/P1、flaky 率），不能只写“测试通过”。

**本项目实践**

- 测试流水线：`静态检查（可选）→ 构建后端 → 起 PG/Redis/MinIO → 起前端 → API/UI 测试 → Allure → 摘要 → 飞书`。
- 部署流水线：`构建 JAR/前端 → SSH 上传 → 切 release → 重启 → 健康检查 → 公网冒烟 → 飞书`。
- 失败时保留 Allure、日志、截图，部署失败自动回滚到上一个 release。

---

### Q3. 构建产物应该怎么管理？

**参考答法**

- 构建一次，多环境复用；不要在每个环境重新构建。
- 产物要有唯一版本：Git SHA、构建号、镜像 digest。
- 制品库保存：Nexus/Artifactory/Harbor/GitHub Packages。
- 产物不可变，配置通过环境变量/ConfigMap 注入。

**本项目实践**

- 后端：`shang-server-0.0.1-SNAPSHOT.jar`，用 Git SHA 作为 `--revision`。
- 前端：`shang-mall/dist`、`shang-admin-web/dist`。
- 服务器按 `releases/<revision>` 存放，`current` 符号链接切换；回滚就是切回上一个 release。
- 当前没有接 Harbor/Nexus，属于可改进点（P1）。

---

### Q4. 多环境配置怎么管？

**参考答法**

- 配置与代码分离：环境变量、配置中心、K8s ConfigMap/Secret。
- 环境分级：dev → staging → production；staging 尽量贴近生产。
- 禁止把生产密钥写进仓库；用 Secret 管理。
- 配置要有校验和默认值，启动时 fail fast。

**本项目实践**

- 本地/CI 用环境变量：`DB_URL`、`REDIS_HOST`、`JWT_SECRET`、`MINIO_*`。
- GitHub Actions 用 `secrets.*`；部署 workflow 用 `environment: staging/production`。
- 服务器用 systemd `EnvironmentFile` 和 drop-in。
- 不足：目前没有独立 staging 数据面，CI 用容器、部署用生产机，环境差异仍存在。

---

### Q5. 质量门禁应该怎么设计？

**参考答法**

- 门禁必须可量化、可执行、能阻断：
  - 单测通过率、覆盖率（行/分支/diff）；
  - API/UI 冒烟 100%；
  - P0/P1 缺陷 = 0；
  - 安全 Critical/High = 0；
  - flaky 率 ≤ 2%；
  - 部署健康检查通过。
- 门禁分阶段：PR 快、合并前全、发版前严。

**本项目实践**

- 主回归 `mvn clean test` 默认排除 `@known-defect`，保持绿色；
- 已知缺陷专项单独跑，发布前必须全绿；
- 部署 workflow 要求 environment 审批 + 健康检查 + 公网冒烟；
- 不足：覆盖率门禁还未接入 deploy workflow（P1）。

---

## 二、GitHub Actions 核心

### Q6. workflow / job / step / runner / action 是什么关系？

**参考答法**

- workflow：一个 YAML 文件，一次完整流程。
- job：一组 step，默认并行；同一 job 内 step 串行。
- step：一个命令或一个 action。
- runner：执行 job 的机器（GitHub-hosted 或 self-hosted）。
- action：可复用的步骤包，如 `actions/checkout`、`actions/upload-artifact`。

**本项目实践**

- `e2e.yml` 有 `e2e` 和 `notify` 两个 job；`notify` 用 `needs: e2e` 依赖测试结果。
- 测试 job 内：checkout → setup-java → build → start backend → start frontend → Playwright → test → Allure → artifact。

---

### Q7. 常见触发方式有哪些？定时和手动怎么写？

**参考答法**

```yaml
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 17 * * *"   # UTC，对应北京时间 01:00
  workflow_dispatch:
    inputs:
      tags:
        default: "not @known-defect"
```

- `schedule` 只跑默认分支；cron 是 UTC。
- `workflow_dispatch` 可在 UI/API 手动触发。
- `repository_dispatch` 可被外部系统触发。

**本项目实践**

- `e2e.yml`：push/PR + 每日 01:00 + 手动 tag 输入。
- `nightly-pytest.yml`：每日 02:00 + 手动 `full/affected`。
- `deploy-tencent.yml`：只允许手动，避免误部署。

---

### Q8. matrix、cache、artifact 分别解决什么问题？

**参考答法**

- matrix：多版本/多浏览器/多 Node 版本并行。
- cache：缓存依赖（Maven `.m2`、npm、pip、Playwright 浏览器），缩短时长。
- artifact：保存构建/测试产物（报告、日志、截图），供下载和跨 job 使用。

**本项目实践**

- `setup-java` / `setup-node` / `setup-python` 开启 cache。
- Allure 报告、Cucumber HTML、`run-summary.json` 上传 artifact。
- 可改进：Playwright 浏览器和 Allure CLI 还没缓存，每次重装（P2）。

---

### Q9. GitHub Secrets 怎么管？为什么不能用明文？

**参考答法**

- 仓库/组织/Environment Secret 三层；最小权限。
- 日志会自动脱敏，但仍不能把密钥写进代码/命令回显。
- 生产密钥用 Environment Secret + required reviewers。
- 更高级：OIDC 联合云厂商，避免长期 AccessKey。

**本项目实践**

- `FEISHU_WEBHOOK`、`FEISHU_SECRET`、`TENCENT_SSH_KEY`、`TENCENT_KNOWN_HOSTS` 等都放 Secrets。
- 演示密码 `Admin@123` 做了 Secret 回退，但仍是公开仓库的隐患，建议轮换。
- 腾讯云长期密钥不是最佳实践，后续可接 OIDC/临时凭证。

---

### Q10. GitHub Environment 和审批怎么做？

**参考答法**

- Settings → Environments 建 `staging`、`production`。
- `production` 配 Required reviewers、Wait timer、Deployment branches。
- workflow job 写 `environment: production`，job 会等待审批。

**本项目实践**

- `deploy-tencent.yml` job 级 `environment: ${{ inputs.environment }}`。
- 需要你在 GitHub 里给 `production` 配审批人；否则不会阻塞。

---

### Q11. concurrency 和 permissions 为什么重要？

**参考答法**

- `concurrency` 防止同一分支/环境并发部署，避免互相覆盖。
- `permissions` 最小化 `GITHUB_TOKEN` 权限，默认只读。

**本项目实践**

```yaml
concurrency:
  group: deploy-tencent-${{ inputs.environment }}
  cancel-in-progress: false
permissions:
  contents: read
```

- 部署不取消进行中的任务，避免“部署到一半被取消”。
- 测试 job 只读代码，不需要写权限。

---

### Q12. reusable workflow 和 composite action 怎么选？

**参考答法**

- reusable workflow：跨仓库/跨 workflow 复用整条流水线（`workflow_call`）。
- composite action：复用一组 step，适合“安装+登录+通知”这种小动作。
- 多个项目都要发飞书，应该把通知做成 composite action/reusable workflow。

**本项目实践**

- 目前飞书通知是 `scripts/ci/feishu_notify.py`，三个 workflow 重复调用。
- 可改进：封装成 `.github/actions/feishu-notify/action.yml`，减少重复（P2）。

---

## 三、测试流水线设计

### Q13. 测试分层怎么落到 CI？

**参考答法建议**

```text
单元测试（秒级）→ API 契约/业务（分钟级）→ UI 冒烟（分钟级）→ E2E（少量）
```

- PR：单元 + API 关键 + UI 冒烟；
- 夜间：全量 API/UI + 安全 + 覆盖率；
- 发版前：全量 + 部署后冒烟。

**本项目实践**

- Java：`automation` 21 API + 12 UI + 已知缺陷隔离；
- pytest：778 条（API/UI/E2E/security/idempotency/validation）；
- PR 适合 `@smoke`，夜间 `nightly-pytest` 全量。

---

### Q14. pytest-xdist 并行怎么保证结果正确？

**参考答法**

- 按接口/资源分组，避免共享库存、共享账号竞争；
- `--dist loadgroup` + `xdist_group`；
- 串行 lane 放库存批量、登录限流等不安全用例；
- 每 worker 独立数据，结束后合并产物。

**本项目实践**

- 分支 `ls_v2_withxdist` 提供两阶段并行：库存分片 + serial lane + 产物合并；
- `make api-parallel` 推荐；`make api-fast` 只用于快速反馈；
- 实测 701 API：271s → 84s（3.23x）；47 UI：174s → 83s（2.10x）。

---

### Q15. Flaky 测试怎么治理？

**参考答法**

- 先复现，定位是产品、环境、测试代码还是数据竞争；
- 加自动等待，禁止固定 sleep；
- 隔离共享数据、唯一账号/订单；
- 失败留证：截图、DOM、trace、请求响应；
- 对已知 flaky 打标签隔离，统计 flaky 率，不能长期靠重试。

**本项目实践**

- 已知缺陷用 `@known-defect` 隔离，主回归保持绿色；
- 失败附 Allure 截图/DOM/控制台/trace；
- 唯一手机号 + 清理注册表，避免数据污染；
- 重试只作为兜底，不掩盖缺陷。

---

### Q16. 测试数据怎么隔离和清理？

**参考答法**

- 每场景唯一标识（手机号/租户/订单号）；
- 数据工厂造数，登记资源 ID；
- 结束后 API/DB 精确清理；
- 清理失败让场景失败，不静默。

**本项目实践**

- `TestData.uniquePhone()` 自动注册新会员；
- `TestDataRegistry` 登记购物车/地址/订单；
- `ScenarioContext.cleanup()` 取消待支付订单、删地址/购物车；
- 管理端写操作使用独立订单，避免污染演示数据。

---

### Q17. 覆盖率应该看哪些指标？

**参考答法**

- 行覆盖率：基础；
- 分支覆盖率：异常/条件分支；
- diff 覆盖率：PR 新增代码；
- 模块覆盖率：核心模块单独阈值；
- 变异得分：断言是否有效。

不要盲目追求 100%，要防止“高覆盖低断言”。

**本项目实践**

- 设计文档要求：核心模块行覆盖 ≥80%、diff ≥80%、分支 ≥60%、变异得分 ≥50%；
- 当前部署 workflow 尚未接覆盖率门禁，建议下一步接入 JaCoCo + diff-cover。

---

### Q18. 测试报告怎么进 CI？

**参考答法**

- 生成 Allure/JUnit HTML/JSON；
- 上传 artifact；
- PR 评论摘要；
- 失败时把关键附件（截图/trace）放进 artifact；
- 报告链接要能被通知工具打开（注意权限）。

**本项目实践**

- `automation/target/allure-results` → `allure generate` → artifact；
- pytest 侧 `artifacts/allure-report`；
- 飞书通知里发摘要 + GitHub run 链接；artifact 需要登录，外部查看不便（P1）。

---

## 四、部署与发布

### Q19. 常见部署策略有哪些？

**参考答法**

- 重建（Recreate）：简单，有停机；
- 滚动（Rolling）：逐步替换，K8s 常用；
- 蓝绿：两套环境切换，回滚快；
- 金丝雀：小流量验证，逐步放量。

**本项目实践**

- 当前是“新 release 目录 + symlink 切换 + 重启 systemd”，接近重建，存在秒级停机；
- `deploy-release.sh` 已保留上一 release，回滚就是切回 symlink；
- 后续可改蓝绿/滚动（P1）。

---

### Q20. 部署后健康检查怎么做？

**参考答法**

- 进程/端口检查；
- 健康接口（`/actuator/health`）；
- 关键业务接口（`/api/home`）；
- 公网入口（域名/端口）；
- 失败自动回滚。

**本项目实践**

- 服务器内检查 `8087/actuator/health` + `8086/api/home code=0`；
- 可选公网 `PUBLIC_MALL_URL/api/home` + 管理端首页；
- 失败自动切回上一个 release 并重启。

---

### Q21. 回滚怎么设计？

**参考答法**

- 制品不可变，保留 N 个版本；
- 回滚只切版本，不重新构建；
- 数据库迁移要向前兼容，避免回滚后 schema 不兼容；
- 回滚后同样跑健康检查。

**本项目实践**

- `releases/<revision>` + `current` symlink + `.deploy-state/previous-release`；
- `deploy-release.sh --rollback` 切回上一个 release；
- 不足：数据库备份/迁移回滚未自动化（P1）。

---

### Q22. 数据库迁移怎么进 CI/CD？

**参考答法**

- 迁移脚本版本化（Flyway/Liquibase）；
- 部署前备份；
- 先 staging 跑，再生产；
- 迁移向后兼容（先加列、再双写、再删旧列）；
- 失败有回滚/前滚方案。

**本项目实践**

- 后端使用 Flyway，启动自动迁移；
- 当前部署脚本没有 `pg_dump` 和迁移门禁，属于 P1 缺口；
- 建议部署前 `pg_dump` + staging 预跑。

---

### Q23. 零停机部署难在哪？

**参考答法**

- 需要多实例 + 负载均衡；
- 新版本先启动、健康后再切流量；
- 会话/缓存/定时任务要兼容；
- 数据库迁移要兼容双版本。

**本项目实践**

- 当前单机 systemd，重启期间可能 502；
- 改进方向：nginx 上游双端口/双实例，或容器化 + 滚动。

---

### Q24. 多环境发布怎么防止误操作？

**参考答法**

- 环境隔离（账号/网络/DB）；
- production 必须审批；
- 部署 workflow 只允许手动；
- 变更窗口、冻结期；
- 回滚演练。

**本项目实践**

- `deploy-tencent` 仅 `workflow_dispatch`；
- `environment: staging/production`；
- 需在 GitHub 给 production 配 required reviewers。

---

## 五、通知、安全与可观测

### Q25. 飞书通知应该发什么？怎么保证安全？

**参考答法**

- 发结论、关键数字、失败原因、运行链接；
- 成功可汇总，失败必发；
- 不发明文密钥/手机号/地址；
- 自定义机器人用签名校验；
- 通知失败不能影响主流程。

**本项目实践**

- `feishu_notify.py` 发 interactive 卡片：状态、分支、提交、通过/失败/通过率、Run ID、按钮。
- 支持 `FEISHU_SECRET` 签名；`continue-on-error` 避免通知失败拖垮流水线。
- 本地 mock 验证 HTTP 200；真实 Webhook 待提供。

---

### Q26. CI 里应该做哪些安全扫描？

**参考答法**

- Secrets 扫描：Gitleaks；
- 依赖漏洞：Dependency-Check/Trivy；
- SAST：Semgrep/CodeQL；
- DAST：ZAP baseline/API scan；
- 镜像扫描：Trivy；
- 供应链：锁定依赖、校验 checksum。

**本项目实践**

- 设计文档已列 P1；当前 workflow 还没接这些扫描。
- 建议先加 Gitleaks + Trivy（误报低、接入快）。

---

### Q27. 权限最小化怎么做？

**参考答法**

- `permissions: contents: read`；
- 部署用 Environment Secret + 专用 deploy 用户；
- SSH key 只授权必要命令；
- 不在 PR from fork 里跑需要 secrets 的部署；
- 定期轮换密钥。

**本项目实践**

- workflow 已加 `permissions: contents: read`；
- 部署用 `TENCENT_SSH_KEY`，建议专用 deploy 用户 + sudoers 限制；
- Token 已在聊天中暴露，建议立即 revoke/rotate。

---

### Q28. 可观测性怎么和 CI/CD 结合？

**参考答法**

- 构建/部署注入版本号、commit、构建号；
- 日志/指标/追踪带版本标签；
- 部署后在平台上对比错误率/延迟；
- 失败通知附 traceId/日志链接。

**本项目实践**

- 后端有 OTel/Tempo/Prometheus/Grafana；
- 部署 manifest 写 revision；
- 可改进：部署通知附 Grafana/Tempo 链接和 `journalctl` 错误摘要。

---

### Q29. GitHub-hosted runner 和 self-hosted 怎么选？

**参考答法**

- GitHub-hosted：免运维、干净环境、按分钟计费；适合开源/中小项目。
- self-hosted：可访问内网、性能可控、成本可控；但要自己打补丁、隔离、清理。
- 部署到内网/腾讯云，self-hosted 更顺；公开仓库慎用 self-hosted（fork PR 风险）。

**本项目实践**

- 测试用 GitHub-hosted，服务用 services 容器；
- 部署通过 SSH 到腾讯云，不需要 self-hosted；
- 若测试要直连腾讯云内网，再考虑 self-hosted。

---

## 六、场景题：给尚品汇设计一套 CI/CD

**题目**：一个电商项目，Java 后端 + 两个 Vue 前端 + PostgreSQL/Redis/MinIO，要求 PR 快速反馈、每日全量回归、可手动部署到腾讯云、失败飞书通知。

**回答框架**

1. **触发**
   - PR：`@smoke` + API 关键 + 前端构建；
   - push main：全量 API + UI；
   - 每日 02:00：全量 + 安全 + 覆盖率；
   - 手动：部署 staging/production。
2. **流水线**
   - 静态检查：lint、Gitleaks、依赖扫描；
   - 构建：Java 17 兼容 JAR、前端 dist；
   - 测试：PG/Redis/MinIO services，起后端/前端，跑 API/UI；
   - 报告：Allure + JUnit + 摘要；
   - 门禁：P0/P1=0、冒烟 100%、覆盖率阈值；
   - 通知：飞书卡片。
3. **部署**
   - 构建一次，产物按 revision 存放；
   - SSH 上传 → 解包 → 切 symlink → 重启 → 健康检查 → 公网冒烟；
   - 失败自动回滚；
   - production 审批。
4. **可观测**
   - 版本号注入日志/指标/追踪；
   - 部署后看错误率/延迟；
   - 失败通知附 run URL + 日志。
5. **取舍**
   - 单机先做重建部署，后续再蓝绿；
   - 先做关键路径冒烟，不做全量 E2E；
   - 通知成功可降噪，失败必发。

**本项目落地文件**

```text
.github/workflows/e2e.yml
.github/workflows/nightly-pytest.yml
.github/workflows/deploy-tencent.yml
scripts/ci/feishu_notify.py
scripts/deploy-release.sh
docs/ci-cd-tencent-feishu.md
```

---

## 七、本项目落地清单

### 7.1 触发矩阵

| 工作流 | 触发 | 用途 |
|---|---|---|
| `e2e.yml` | push/PR + 每日 01:00 + 手动 | Java Cucumber + Allure |
| `nightly-pytest.yml` | 每日 02:00 + 手动 | 778 条 pytest 全量/选测 |
| `deploy-tencent.yml` | 手动 | 腾讯云部署/回滚 |

### 7.2 必填 Secrets

```text
FEISHU_WEBHOOK
FEISHU_SECRET（可选）
TENCENT_HOST
TENCENT_PORT（默认 22）
TENCENT_USER（默认 root）
TENCENT_SSH_KEY
TENCENT_KNOWN_HOSTS
PUBLIC_MALL_URL（可选）
PUBLIC_ADMIN_URL（可选）
ADMIN_PASSWORD（可选，CI 演示）
CI_JWT_SECRET（可选）
```

### 7.3 关键命令

```bash
# Java/Cucumber
cd automation && mvn clean test

# pytest 收集
cd pytest_automation && ./.venv/bin/python -m pytest --collect-only -q

# 夜间回归
cd pytest_automation && bash scripts/ci/nightly.sh

# 部署
bash scripts/deploy-release.sh \
  --jar backend/shang-server/target/shang-server-0.0.1-SNAPSHOT.jar \
  --mall-dist shang-mall/dist \
  --admin-dist shang-admin-web/dist \
  --revision <sha>

# 回滚
bash scripts/deploy-release.sh --rollback

# 飞书本地预览
FEISHU_DRY_RUN=1 FEISHU_STATUS=success FEISHU_WORKFLOW=e2e \
FEISHU_SUMMARY_FILE=/tmp/summary.json python3 scripts/ci/feishu_notify.py
```

### 7.4 当前阻塞

- 腾讯云：49.233.135.247:22 开放但现有密钥被拒，需要部署公钥/正确用户。
- GitHub：Token 可写 `simon6wu-sys/shang-pivot`，但不能新建仓库；HTTPS 443 被本机网络阻断，需要 SSH key 或新仓库。
- 飞书：浏览器未登录，需你从群机器人复制 Webhook。

---

## 八、常见坑与排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `Permission denied (publickey)` | 服务器/GitHub 没加公钥 | 把 `.pub` 加到 `authorized_keys` / GitHub SSH keys |
| `could not read Username` | CI 没有凭据 | 用 Secret + `GIT_ASKPASS`，不要把 Token 写 URL |
| `port 443 timeout` | 网络/代理阻断 | 用 SSH 22 或配置代理 |
| Java `UnsupportedClassVersionError` | 服务器 Java 17，jar 用 21 编译 | `-Djava.version=17` |
| Flyway 迁移失败 | 脚本改过已应用版本 | `repair-on-migrate` / 新版本前向修复 |
| Playwright 浏览器缺失 | 未安装 | `python -m playwright install --with-deps chromium` |
| pytest `--reruns` 不识别 | 缺 `pytest-rerunfailures` | 装插件 |
| xdist 结果不稳定 | 共享库存/账号 | 分组 + serial lane + 唯一数据 |
| 飞书 403/sign 错误 | Webhook/Secret 不对 | 检查签名算法 `timestamp+"\n"+secret` |
| 部署后 502 | 应用未起/端口/权限 | 看 `journalctl -u shang-pivot`，脚本会自动回滚 |

---

## 九、面试速答卡

**30 秒介绍本项目的 CI/CD**

> 我们用 GitHub Actions 做三层流水线：PR 跑冒烟和 API 关键用例，push main 跑全量 Java/Cucumber + Allure，夜间跑 778 条 pytest + xdist；部署是手动触发、Environment 审批，构建 JAR 和前端 dist 后 SSH 到腾讯云，按 revision 切 symlink、重启、健康检查，失败自动回滚；结果用飞书机器人卡片通知，失败带运行链接和摘要。当前还在补 staging 隔离、覆盖率门禁和零停机。

**高频追问**

1. 为什么不用 Jenkins？——GitHub 托管、维护成本低；内网/大规模再考虑 self-hosted。
2. 为什么部署不自动？——电商资金/库存风险，保留人工审批。
3. 怎么保证测试稳定？——唯一数据、自动等待、失败留证、已知缺陷隔离。
4. 怎么保证可回滚？——不可变 release + symlink + 上一版本记录。
5. 怎么防止密钥泄露？——Secrets + 最小权限 + 定期轮换 + 扫描。
6. 怎么降低 CI 成本？——缓存、路径过滤、分层触发、只跑受影响用例。

---

## 十、练习题

1. 把 `e2e.yml` 拆成 PR 冒烟和 nightly 全量两个 workflow，说明触发和门禁差异。
2. 给 `deploy-tencent` 加“部署前 pg_dump + 迁移检查”，画出失败回滚流程。
3. 设计一个“只跑受影响用例”的选测方案，说明如何避免漏测。
4. 把飞书通知封装成 composite action，支持成功降噪、失败必发。
5. 设计 staging → production 的审批与数据隔离方案。
6. 给核心模块加 JaCoCo diff 覆盖率门禁，阈值怎么定、如何避免误伤。
