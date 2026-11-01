# 腾讯云部署 + GitHub Actions + 飞书通知

## 0. 2026-11-01 实际部署结果

- 服务器：腾讯云轻量 `lhins-0lfp6s8w`，Debian 13，4C8G，`49.233.135.247`
- 商城：http://49.233.135.247:60084/
- 管理端：http://49.233.135.247:60085/
- 后端：`/opt/shang-pivot/current/app.jar`，systemd `shang-pivot`
- 依赖：PostgreSQL 17、Redis 8、RabbitMQ、MinIO（商品图）
- 验证：商城/管理端 200，会员/管理员登录成功，商品图 200，Moodle 80 未受影响
- 详细记录：[`docs/tencent-deploy.md`](tencent-deploy.md)

## 1. 结论先说

代码侧已经补齐：GitHub Actions 定时/手动触发、测试摘要、飞书卡片通知、腾讯云部署工作流（含审批、健康检查、回滚）。

但有三项外部凭据目前本机没有，**因此还没有真正完成线上部署和真实飞书通知**：

| 阻塞项 | 现状 | 需要你提供 |
|--------|------|------------|
| 腾讯云服务器 | 已部署：`49.233.135.247:60084`（商城）、`:60085`（管理端），SSH root 密钥已配置；Moodle 80 未动 | ✅ 已完成，见 `docs/tencent-deploy.md` |
| GitHub 仓库 | PAT 属于 `billhunthouse`，读取正常，但创建分支/文件、触发 workflow、push 均 403（Token 无 Contents/Workflows/Actions 写权限）；HTTPS 经代理可通 | 换有 `Contents: Read and write` + `Workflows: Read and write` + `Actions: Read and write` 的 PAT，或把 SSH 公钥加到 GitHub |
| 飞书机器人 | 浏览器停在飞书登录页，无法读取你的会话 | 从飞书群机器人复制 Webhook（和 Secret） |

> 这三项不是代码能“猜”出来的。没有它们，工作流可以提交，但 `deploy-tencent` 和飞书通知不会真正执行。

---

## 2. 目标架构

```text
开发者 push / 定时 01:00
        │
        ▼
GitHub Actions
├─ e2e.yml             Java Cucumber + Allure，定时/手动/PR
├─ nightly-pytest.yml  pytest 全量/变更选测，每日 02:00
└─ deploy-tencent.yml  手动触发，environment 审批，部署/回滚
        │
        ├─ 测试结果 → ci-summary/summary.json
        ├─ 报告产物 → GitHub Artifact（Allure）
        └─ 通知 → scripts/ci/feishu_notify.py → 飞书群卡片
        │
        ▼
腾讯云服务器
/opt/shang-pivot/releases/<revision>
        ├─ app.jar（Java 17）
        ├─ mall/（商城静态文件）
        ├─ admin/（管理端静态文件）
        └─ current -> releases/<revision>
              │
              ▼
        systemd shang-pivot + nginx
```

---

## 3. 已实现的改动

| 文件 | 作用 |
|------|------|
| `.github/workflows/e2e.yml` | 增加每日定时、手动触发、Cucumber tag 输入、CI 摘要、飞书通知 |
| `.github/workflows/nightly-pytest.yml` | 增加 CI 摘要、飞书通知；演示密码改为 Secret 回退 |
| `.github/workflows/deploy-tencent.yml` | 新增腾讯云部署：手动触发、environment 审批、构建、SSH、健康检查、回滚、飞书 |
| `scripts/ci/feishu_notify.py` | 飞书交互卡片、签名、dry-run、结果摘要解析 |
| `scripts/deploy-release.sh` | 支持 `SHANG_SSH_USER`，其余沿用上传/切 release/健康检查/自动回滚 |
| `docs/ci-cd-tencent-feishu.md` | 本文档 |

---

## 4. GitHub Actions 必填 Secrets

在 GitHub 仓库 → Settings → Secrets and variables → Actions 中添加：

### 4.1 飞书

| Secret | 必填 | 说明 |
|--------|------|------|
| `FEISHU_WEBHOOK` | 是 | 飞书群机器人 Webhook，例如 `https://open.feishu.cn/open-apis/bot/v2/hook/...` |
| `FEISHU_SECRET` | 否 | 机器人开启“签名校验”时填写 |

### 4.2 腾讯云部署

| Secret | 必填 | 说明 |
|--------|------|------|
| `TENCENT_HOST` | 是 | 服务器公网 IP 或域名 |
| `TENCENT_PORT` | 否 | SSH 端口，默认 22 |
| `TENCENT_USER` | 否 | SSH 用户，默认 root；建议专用 deploy 用户 |
| `TENCENT_SSH_KEY` | 是 | 私钥完整内容（`-----BEGIN ...` 到 `-----END ...`） |
| `TENCENT_KNOWN_HOSTS` | 是 | `ssh-keyscan -p 22 <host>` 的输出，防 MITM |
| `PUBLIC_MALL_URL` | 否 | 部署后公网冒烟，如 `https://mall.example.com` |
| `PUBLIC_ADMIN_URL` | 否 | 管理端公网地址 |

### 4.3 测试可选覆盖

| Secret | 默认 | 说明 |
|--------|------|------|
| `ADMIN_PASSWORD` | `Admin@123` | 仅 CI 演示环境；生产不要用默认值 |
| `CI_JWT_SECRET` | 内置 CI 值 | 仅 CI 临时使用，生产由服务器环境变量提供 |

> 生产环境不要把真实密码写进仓库或 workflow；用 GitHub Environment Secrets，并开启 required reviewers。

---

## 5. 飞书机器人创建

1. 飞书群 → 群设置 → 群机器人 → 添加机器人 → **自定义机器人**。
2. 复制 Webhook。
3. 安全设置建议勾选“签名校验”，复制 Secret。
4. 把 Webhook/Secret 分别写入 GitHub Secrets：`FEISHU_WEBHOOK` / `FEISHU_SECRET`。
5. 本地验证（不会真的发送）：

```bash
FEISHU_DRY_RUN=1 FEISHU_STATUS=success FEISHU_TITLE="尚品汇自动化测试" \
FEISHU_WORKFLOW=e2e FEISHU_BRANCH=main FEISHU_COMMIT=abc1234 \
python3 scripts/ci/feishu_notify.py
```

已验证：本地 mock HTTP 服务能收到 `msg_type=interactive` 卡片，签名 `timestamp/sign` 正常，HTTP 200。

---

## 6. 腾讯云服务器准备

部署脚本 `scripts/deploy-release.sh` 假设：

- Linux + systemd，服务名 `shang-pivot`
- 目录 `/opt/shang-pivot/{releases,current,.deploy-state}`
- 应用监听 `127.0.0.1:8086`，管理端口 `8087`
- nginx 反代商城/管理端（现有脚本会检查 8090/8091）
- 服务器 JVM 为 Java 17（CI 用 `-Djava.version=17` 构建）
- SSH 用户有权限写 `/opt/shang-pivot`、执行 `systemctl restart shang-pivot`

首次准备：

```bash
# 服务器上
sudo mkdir -p /opt/shang-pivot/{releases,.deploy-state}
sudo useradd -r -s /sbin/nologin shang-pivot 2>/dev/null || true
sudo chown -R shang-pivot:shang-pivot /opt/shang-pivot
```

部署用户建议只授予：

```sudoers
deploy ALL=(root) NOPASSWD: /bin/systemctl restart shang-pivot, /bin/systemctl status shang-pivot
```

> 当前脚本以 root 执行，若改用 deploy 用户，需要把 `systemctl` 与目录权限配好，或改成 sudo 调用。

---

## 7. 触发方式

| 工作流 | 定时 | 手动 | 其他 |
|--------|------|------|------|
| `e2e.yml` | 每日 01:00（Asia/Shanghai） | Actions → e2e → Run workflow，可填 Cucumber tag | push/PR 自动 |
| `nightly-pytest.yml` | 每日 02:00（Asia/Shanghai） | Actions → nightly-pytest → Run workflow，可选 full/affected、跳过 UI | 无 |
| `deploy-tencent.yml` | 无（部署不应定时） | Actions → deploy-tencent → Run workflow，选 staging/production、ref、是否回滚 | environment 审批 |

部署建议：

1. 先建 GitHub Environment：`staging`、`production`。
2. `production` 配置 Required reviewers（至少 1 人）。
3. 手动跑 `deploy-tencent`，`environment=staging` 验证。
4. 通过后再跑 `production`。
5. 回滚：同一工作流勾选 `rollback=true`。

---

## 8. 专家评审：当前不完善的点

### P0（阻塞上线）

| # | 问题 | 影响 | 处理 |
|---|------|------|------|
| 1 | 没有可用的腾讯云 SSH 凭据/主机确认 | 无法部署 | 需要你提供 IP、用户、私钥；当前 111.170.33.2 密钥被拒 |
| 2 | GitHub 仓库不可写 | 工作流无法上线 | 需要 PAT/SSH Key，或从 Gitee 导入公开仓库 |
| 3 | 没有飞书 Webhook | 通知不会发出 | 需要机器人 Webhook |
| 4 | 公开 Gitee 仓库仍含演示账号/服务器 IP | 账号与资产暴露 | 轮换 `Admin@123`、移除 `111.170.33.2` 或改私有 |

### P1（上线前应补）

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 5 | 无 staging→production 数据隔离 | 部署验证可能污染生产 | 两套 DB/Redis/MinIO；CI 用容器，staging 独立 |
| 6 | 部署不是零停机 | 重启期间 502 | 后续改蓝绿/滚动；至少 nginx 维护页 + 健康检查 |
| 7 | 无数据库备份/迁移门禁 | 迁移失败难回滚 | 部署前 `pg_dump`；Flyway 迁移先在 staging 跑 |
| 8 | CI 测试跑本地服务，未跑腾讯云环境 | 线上配置差异测不到 | 部署后跑一组 `@smoke` 指向公网 URL |
| 9 | Allure 报告只在 GitHub Artifact | 飞书链接需登录，外部看不了 | 部署到 GitHub Pages/对象存储，或飞书发摘要+运行链接 |
| 10 | 无依赖/密钥扫描 | 供应链与泄密风险 | 加 Trivy/Dependency-Check、Gitleaks、Semgrep |
| 11 | 每次运行都通知 | 飞书噪音 | 失败必发；成功可每日汇总或仅发 release |
| 12 | 服务器防火墙/端口未知 | 公网暴露面不清 | 仅开 22/80/443；60084/60085 走反代或内网 |

### P2（持续改进）

- 增加 GitHub Release/Tag 与变更记录。
- 部署后自动附上服务端 `journalctl` 最近错误摘要。
- 失败通知附失败用例 Top 5 与 traceId。
- 对 `production` 部署加双人审批与变更窗口。
- 增加 Playwright/Allure 缓存，缩短 CI 时长。
- 为 Feishu 通知加去重/静默时段。

---

## 9. 已验证 / 未验证

已验证：

- `scripts/ci/feishu_notify.py` dry-run 输出正确卡片。
- 本地 mock Webhook 收到 POST，HTTP 200，签名字段存在。
- 三个 workflow YAML 可被 PyYAML 解析，jobs 为 `e2e/notify`、`regression/notify`、`deploy/notify`。
- `scripts/deploy-release.sh` 语法通过，支持 `SHANG_SSH_USER`。
- 新分支 pytest 收集 778 条通过（依赖已补装）。

未验证（缺凭据）：

- 腾讯云真实部署。
- GitHub Actions 真实运行。
- 飞书真实群消息。
- 生产环境健康检查与回滚。

---

## 10. 下一步操作清单

### 10.1 已生成的部署公钥（加到对应平台即可）

腾讯云服务器（加到 `~/.ssh/authorized_keys`，用户可为 root 或 deploy）：

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICESpz7Jq0PRmGLAluCZCUAAW1qmnqXTGpbttPgBZHZh shang-pivot-tencent-deploy
```

GitHub（Settings → SSH and GPG keys → New SSH key）：

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL5ZCcS7s7nRWP8e8aTavAD2KgsOsZRjDpdTBSq0Q0UY shang-pivot-ci
```

> 私钥只在本地 `~/.ssh/` 与 GitHub Secrets 中使用，不要发到聊天里。

### 10.2 本次实测记录（2026-10-31）

- GitHub API 读取 `simon6wu-sys/shang-pivot` 成功；`permissions.push=true`。
- 创建 `automation-ci` 分支、写入 workflow：`403 Resource not accessible by personal access token`。
- 触发 `workflow_dispatch`：`403 Resource not accessible by personal access token`。
- Git push：`Permission to simon6wu-sys/shang-pivot.git denied to billhunthouse`（HTTP 403）。
- 代理 `127.0.0.1:7890` 可用，`git ls-remote` 成功，说明网络不是阻塞点，**是 Token 权限不足**。
- `49.233.135.247:22` 开放，root/ubuntu 使用现有密钥均 `Permission denied (publickey)`；80 开放、443 关闭。
- 飞书网页跳转到登录页，无法读取你已登录的会话。

### 10.3 操作顺序

1. 腾讯云已完成部署；SSH 已用 `/root/.ssh/authorized_keys` + 本地 `~/.ssh/tencent_deploy` 打通。
2. 把 GitHub 公钥加到 GitHub，或用 “Import repository” 导入 `https://gitee.com/simon6wu/shang-pivot-automation`（该镜像包含 `3eb03b6` 的 CI）。
3. 飞书群 → 群机器人 → 自定义机器人 → 复制 Webhook/Secret。
4. 在 GitHub 添加第 4 节 Secrets。
5. 先手动跑 `e2e`，确认飞书卡片。
6. 再手动跑 `deploy-tencent` 的 `staging`，确认健康检查。
7. 最后跑 `production`，验收后把 `nightly-pytest` 定时打开。

> 当前 GitHub PAT 已在聊天中暴露，完成配置后请立即 revoke/rotate。
