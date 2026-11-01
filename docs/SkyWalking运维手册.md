# SkyWalking 全链路监控运维手册（尚品汇）

> 适用环境：腾讯云 `49.233.135.247`，SkyWalking OAP/UI 10.2.0，Java Agent 9.5.0  
> 关联文档：[部署实录](tencent-ops-stack.md) · [课堂课件](../courseware/03-SkyWalking全链路监控课件.md)

## 1. 系统定位

SkyWalking 在当前项目中承担 **APM（应用性能监控）**：

- 接口级：HTTP 入口、端点耗时、成功率、QPS；
- 链路级：一次请求经过的 Tomcat、HikariCP、JDBC、Redis 等 Span；
- SQL 级：`db.statement`、慢 SQL 阈值、数据库访问耗时；
- 实例级：JVM CPU、堆内存、线程、GC；
- 拓扑级：服务、数据库、缓存之间的依赖；
- 告警级：服务/端点/实例/数据库/CPU 规则 + Webhook。

它 **不是** 完整的基础设施监控：主机 CPU/磁盘、Nginx、PostgreSQL 服务端、Redis 服务端、RabbitMQ、集中日志、SLO/业务指标仍需补齐，见第 11 节。

## 2. 访问与凭证

| 项 | 值 |
|---|---|
| UI | http://49.233.135.247:60084/skywalking/ |
| 认证 | Nginx Basic Auth，用户名 `ops` |
| 密码文件 | `/opt/skywalking/ui-password`（600） |
| OAP GraphQL | `http://127.0.0.1:12800/graphql`（仅本机） |
| OAP gRPC | `127.0.0.1:11800`（Agent 上报） |
| Webhook | `http://172.17.0.1:18080/alarm`（Docker 网关，仅本机网络） |

读取密码：

```bash
ssh shangpivot-tencent 'cat /opt/skywalking/ui-password'
```

## 3. 组件与文件

| 组件 | 容器/服务 | 端口 | 关键文件 |
|---|---|---|---|
| OAP | `skywalking-oap` | 11800/12800/9411/4317/4318（均 127.0.0.1） | `/opt/skywalking/oap.env`（600） |
| UI | `skywalking-ui` | 60086 | `/opt/skywalking/ui-static/` |
| Agent | `shang-pivot` systemd drop-in | 上报 11800 | `/opt/skywalking/agent-95/` |
| 告警规则 | 挂载进 OAP | - | `/opt/skywalking/alarm-settings.yml` |
| 告警接收器 | `skywalking-alarm-webhook` | 172.17.0.1:18080 | `/opt/skywalking/alarm-webhook.py` |
| 告警日志 | - | - | `/var/log/skywalking-alarm/alarms.jsonl` |
| 存储 | PostgreSQL `skywalking` 库 | 5432 | 表按天分区 |

systemd drop-in：`/etc/systemd/system/shang-pivot.service.d/skywalking.conf`

```ini
[Service]
Environment="SW_AGENT_NAME=shang-pivot"
Environment="SW_AGENT_INSTANCE_NAME=shang-pivot-prod"
Environment="SW_AGENT_COLLECTOR_BACKEND_SERVICES=127.0.0.1:11800"
Environment="SW_LOGGING_OUTPUT=CONSOLE"
Environment="SW_LOGGING_LEVEL=INFO"
ExecStart=
ExecStart=/usr/bin/java -javaagent:/opt/skywalking/agent-95/skywalking-agent.jar -jar /opt/shang-pivot/current/app.jar
```

## 4. 日常巡检

### 4.1 五分钟巡检

```bash
# 1. 业务健康
curl -s http://127.0.0.1:8087/actuator/health

# 2. OAP 健康
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:12800/healthcheck

# 3. 容器
docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'skywalking|zentao'

# 4. 最近告警
tail -20 /var/log/skywalking-alarm/alarms.jsonl

# 5. 资源
free -h
df -h /
docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' | grep skywalking
```

期望：

- `actuator/health` 为 `UP`；
- OAP `/healthcheck` 为 `200`；
- OAP/UI 均为 `Up`；
- 无异常告警；
- 可用内存 > 1G，根分区使用率 < 80%。

### 4.2 日志入口

```bash
journalctl -u shang-pivot -n 200 --no-pager
journalctl -u skywalking-alarm-webhook -n 100 --no-pager
docker logs --tail 200 skywalking-oap
docker logs --tail 100 skywalking-ui
```

## 5. 指标字典

### 5.1 服务级（RED）

| 指标 | 含义 | 关注点 |
|---|---|---|
| `service_cpm` | 每分钟调用数 | 突增/突降 |
| `service_sla` | 成功率（10000=100%） | < 9500 告警 |
| `service_resp_time` | 平均响应时间 | 与基线比 |
| `service_percentile` | P50/P75/P90/P95/P99 | 平均值掩盖长尾 |
| `service_apdex` | Apdex 满意度 | < 0.9 需关注 |

### 5.2 端点级

- `endpoint_cpm`、`endpoint_sla`、`endpoint_resp_time`、`endpoint_percentile`；
- 先看 Top N 慢端点/错误端点，再下钻 Trace。

### 5.3 实例/JVM

| 指标 | 当前实测 |
|---|---:|
| `instance_jvm_cpu` | 1% |
| `instance_jvm_memory_heap` | ~212 MB |
| `instance_jvm_thread_live_count` | 67 |
| `instance_jvm_old_gc_count` | 0 |

查询示例：

```graphql
query($c: MetricsCondition!, $d: Duration!) {
  readMetricsValue(condition: $c, duration: $d)
}
```

```json
{
  "c": {
    "name": "instance_jvm_cpu",
    "entity": {
      "scope": "ServiceInstance",
      "serviceName": "shang-pivot",
      "serviceInstanceName": "shang-pivot-prod",
      "normal": true
    }
  },
  "d": {"start": "2026-11-01 0800", "end": "2026-11-01 0830", "step": "MINUTE"}
}
```

### 5.4 数据库/缓存

Agent 侧：

- `PostgreSQL/JDBC/PreparedStatement/executeWithFlags`：SQL 执行 Span；
- `db.statement`：SQL 文本；
- `HikariCP/Connection/getConnection`：连接池等待；
- `Lettuce/...`：Redis 调用。

注意：这是 **客户端视角**，不是 PostgreSQL/Redis 服务端指标。服务端连接数、慢查询、缓存命中率需要 exporter，见第 11 节。

## 6. 一步步排查方法

### 6.1 总流程

```text
告警/用户反馈
  → 服务 RED 指标（是不是全局变慢/报错）
  → 实例指标（是不是单实例/JVM/GC）
  → 端点 TopN（是哪个接口）
  → Trace（一次请求的完整 span）
  → Span 下钻（Tomcat → HikariCP → JDBC/Redis）
  → SQL/下游/日志确认
  → 止损 → 验证恢复 → 复盘
```

### 6.2 第一步：判断问题类型

| 现象 | 优先看 |
|---|---|
| 成功率下降 | `service_sla`、`endpoint_sla`、错误 Trace |
| 平均耗时上升 | `service_resp_time`、P95/P99 |
| 只有个别接口慢 | `endpoint_resp_time` TopN |
| 只有个别实例慢 | `service_instance_resp_time`、JVM |
| 数据库慢 | `database_access_resp_time`、SQL Span |
| 流量突增 | `service_cpm`、Nginx 访问日志 |

### 6.3 第二步：服务级

UI 路径：

```text
SkyWalking → General-Service → Services → shang-pivot
```

看四个卡片：Apdex、Success Rate、Avg Response Time、Load。  
如果平均值正常但 P95 很高，说明长尾请求；继续看端点。

### 6.4 第三步：实例级

```text
shang-pivot → Instance → shang-pivot-prod
```

看 JVM CPU、Heap、Thread、Old GC。若 Old GC 次数/时间持续上升，先怀疑内存压力，而不是 SQL。

### 6.5 第四步：端点级

在 Service 页面看 Endpoint 的 Success Rate / Avg Response Time / Load。  
优先选择“耗时长 × 流量高”的端点，例如 `/api/home`。

### 6.6 第五步：Trace

UI：`Trace` 页签 → 选择服务和端点 → 按耗时/错误过滤 → 点进 Trace。

读 Span 的顺序：

1. **Entry**：`Tomcat GET:/api/home`，确认 HTTP 状态和总耗时；
2. **Local**：`HikariCP/Connection/getConnection`，看是否在等连接；
3. **Exit**：`PostgreSQL/JDBC/PreparedStatement/executeWithFlags`，看 SQL 和耗时；
4. **Cache**：`Lettuce/...`，看 Redis；
5. **子 Span 数量**：一次 `/api/home` 出现 100+ span，通常意味着 N+1 查询或重复查询。

### 6.7 第六步：SQL 确认

在 Span 详情里看：

- `db.statement`；
- `peer`（如 `127.0.0.1:5432`）；
- `component`（`postgresql-jdbc-driver`）；
- 是否超过 `SW_SLOW_DB_THRESHOLD`（当前 200ms）。

如果 SQL 本身很快，但 `HikariCP/getConnection` 很慢，问题在连接池/数据库连接数，不是 SQL。

### 6.8 第七步：日志与业务确认

当前系统没有把应用日志和 TraceId 集中关联，先用：

```bash
journalctl -u shang-pivot --since '10 min ago' --no-pager
```

确认异常堆栈、业务错误码。后续建议在 Logback 中输出 `traceId`，接 Loki/ELK/OTel Logs。

## 7. 告警配置与处理

### 7.1 当前规则

文件：`/opt/skywalking/alarm-settings.yml`，挂载到 OAP `/skywalking/config/alarm-settings.yml`（只读）。

已配置：

| 规则 | 条件 |
|---|---|
| `service_resp_time_rule` | 服务 10 分钟内 3 次 > 1000ms |
| `service_sla_rule` | 服务 10 分钟内 2 次成功率 < 95% |
| `service_resp_time_percentile_rule` | P95 > 1000ms，3 次 |
| `service_instance_resp_time_rule` | 实例 2 次 > 1000ms |
| `database_access_resp_time_rule` | 数据库访问 2 次 > 200ms |
| `endpoint_resp_time_rule` | 端点 2 次 > 1000ms |
| `endpoint_sla_rule` | 端点 2 次成功率 < 95% |
| `instance_jvm_cpu_rule` | JVM CPU > 80%，3 次 |

Webhook：`http://host.docker.internal:18080/alarm`

### 7.2 告警接收器

```bash
systemctl status skywalking-alarm-webhook
curl -s http://172.17.0.1:18080/health
tail -f /var/log/skywalking-alarm/alarms.jsonl
```

手动验证接收器：

```bash
curl -s -X POST http://172.17.0.1:18080/alarm \
  -H 'Content-Type: application/json' \
  -d '{"scope":"SERVICE","name":"shang-pivot","alarmMessage":"manual test","ruleName":"manual-test"}'
```

### 7.3 修改规则的步骤

```bash
# 1. 备份
cp /opt/skywalking/alarm-settings.yml /opt/skywalking/alarm-settings.yml.bak

# 2. 编辑（仓库源文件：observability/skywalking/alarm-settings.yml）
vi /opt/skywalking/alarm-settings.yml

# 3. 重启 OAP 使规则生效
docker restart skywalking-oap

# 4. 等健康检查
for i in $(seq 1 40); do
  curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:12800/healthcheck | grep -q 200 && break
  sleep 3
done

# 5. 看 OAP 是否加载 alarm module
docker logs --tail 100 skywalking-oap | grep -i alarm

# 6. 失败回滚
cp /opt/skywalking/alarm-settings.yml.bak /opt/skywalking/alarm-settings.yml
docker restart skywalking-oap
```

### 7.4 告警响应 Runbook

1. **确认告警**：看 `alarms.jsonl` 的 `ruleName`、`name`、`alarmMessage`；
2. **定位服务/端点**：UI 对应时间窗看 RED 与 TopN；
3. **找 Trace**：按端点、耗时、错误过滤；
4. **判断根因**：SQL / 连接池 / Redis / JVM GC / 下游；
5. **止损**：回滚、扩容、限流、加缓存、加索引、调连接池；
6. **验证**：SLA 恢复、P95 回落、告警 silence 周期结束；
7. **复盘**：记录时间线、根因、动作、后续任务。

### 7.5 测试规则

仓库提供 `observability/skywalking/alarm-settings.test.yml`，用于课堂/联调验证 Webhook 通道：

```bash
cp /opt/skywalking/alarm-settings.yml /opt/skywalking/alarm-settings.yml.bak
cp /opt/skywalking/alarm-settings.test.yml /opt/skywalking/alarm-settings.yml
docker restart skywalking-oap
# 等待 1-3 分钟，观察 alarms.jsonl
tail -f /var/log/skywalking-alarm/alarms.jsonl
# 恢复
cp /opt/skywalking/alarm-settings.yml.bak /opt/skywalking/alarm-settings.yml
docker restart skywalking-oap
```

> 当前已验证：Webhook 接收器可用、OAP 容器可访问 Webhook、正式规则已加载。业务阈值尚未触发过真实告警，故障演练时再验证完整链路。

## 8. 慢 SQL 配置

OAP 环境变量：

```ini
SW_SLOW_DB_THRESHOLD=default:200,mongodb:100
```

含义：数据库访问超过 200ms 标记为慢，单位 ms。

Agent 是否记录 SQL 参数：

```ini
SW_JDBC_TRACE_SQL_PARAMETERS=false
```

默认关闭。打开后能看到 `?` 的实际参数，但可能泄露手机号、地址等敏感信息；只在测试环境或脱敏环境开启。

修改 OAP 环境变量后：

```bash
docker restart skywalking-oap
```

## 9. 链路查询脚本

仓库脚本：`scripts/observability/skywalking-query.py`  
服务器已部署：`/opt/skywalking/skywalking-query.py`

```bash
# 在服务器上执行
python3 /opt/skywalking/skywalking-query.py \
  --service shang-pivot --minutes 30 --endpoint /api/home
```

输出：Trace 列表、Span 树摘要、`db.statement`、SQL Span 数量。

如果脚本放在本机，可先 scp 到服务器，或通过 SSH 管道执行。

## 10. 常见故障

| 现象 | 排查 | 处理 |
|---|---|---|
| UI 显示 404 | 静态资源路由 base 不对 | 重跑 `fetch-skywalking-ui-static.py`，检查 Nginx alias |
| UI 401 | Basic Auth | 读取 `/opt/skywalking/ui-password` |
| UI 提示 OAP 不健康 | `/healthcheck` 404 | 确认 `SW_HEALTH_CHECKER=default` |
| OAP 启动报 `no provider found for module storage` | `SW_STORAGE` 值错误 | 用 `postgresql`，不是 `jdbc` |
| OAP 连不上 PostgreSQL | 监听地址/ pg_hba | `listen_addresses` 含 172.17.0.1，放行 172.17.0.0/16 |
| Agent 无数据 | 11800 不通/服务名 | `ss -ltn | grep 11800`，看 `SW_AGENT_COLLECTOR_BACKEND_SERVICES` |
| Trace 列表为空 | 时间窗/时区 | UI 用本地时间；GraphQL 用 UTC，格式 `yyyy-MM-dd HHmm` |
| 告警不触发 | 阈值/时间窗 | 看 OAP alarm 日志；用 test 规则验证通道 |
| 磁盘增长 | OAP 数据/日志 | 监控 `df -h`，配置 TTL/清理，PostgreSQL 备份 |
| OOM | OAP/容器内存 | `JAVA_OPTS` 控制堆，增加 swap，拆分 OAP |

## 11. 当前监控缺口与补齐路线

### 11.1 已有

- HTTP/Trace/SQL/Redis Span；
- 服务、实例、端点 RED 指标；
- JVM CPU/Heap/Thread/GC；
- 服务拓扑；
- 告警规则 + 本地 Webhook；
- 慢 SQL 阈值；
- 链路查询脚本。

### 11.2 缺口

| 缺口 | 影响 | 建议 |
|---|---|---|
| 主机指标 | CPU/内存/磁盘/网络异常发现晚 | `node_exporter` + Prometheus/Grafana，或接入 SkyWalking fetcher |
| PostgreSQL 服务端 | 连接数、慢查询、锁等待看不到 | `postgres_exporter` + 慢查询日志 |
| Redis 服务端 | 命中率、内存、evict 看不到 | `redis_exporter` |
| RabbitMQ | 队列积压、消费延迟看不到 | `rabbitmq_exporter` |
| Nginx | 4xx/5xx、上游耗时、QPS | `nginx-prometheus-exporter` + 访问日志 |
| 日志 | 无法按 TraceId 关联 | Logback 输出 traceId + Loki/ELK/OTel Logs |
| SLO/业务 | 不知道“下单成功率/支付成功率” | 自定义 Micrometer 指标 + SLO 看板 |
| 外部探测 | 域名/DNS/TLS/CDN 故障发现晚 | blackbox_exporter / 飞书告警 |
| 告警路由 | 只有本地 JSONL | 飞书/钉钉/Alertmanager + 升级策略 |
| 采样 | 100% 采样，流量大时成本高 | 自适应采样/尾部采样 |
| 持续剖析 | 只有瞬时 JVM 指标 | SkyWalking profiling / async-profiler |
| 高可用 | OAP/PostgreSQL 单点 | 多 OAP + PostgreSQL 主备/备份 |
| 安全 | Basic Auth 走 HTTP | 域名 + TLS + SSO/RBAC |

### 11.3 优先级

| 优先级 | 动作 | 理由 |
|---|---|---|
| P0 | TLS + 告警接飞书/钉钉 | 当前公网 HTTP 和本地 JSONL 不可用于生产 |
| P0 | 日志 TraceId 关联 | 排障最后一步必须看日志 |
| P1 | node/postgres/redis/nginx exporter | 补系统级可观测性 |
| P1 | SLO/业务指标 | 从“技术指标”走到“业务结果” |
| P2 | 采样、持续剖析、HA、RUM | 规模化后再做 |

## 12. 备份、升级与回滚

### 12.1 PostgreSQL 备份

```bash
sudo -u postgres pg_dump -Fc skywalking > /var/backups/skywalking-$(date +%F).dump
```

建议每日备份到异地/对象存储，并定期恢复演练。

告警日志已配置 logrotate：`/etc/logrotate.d/skywalking-alarm`，保留 14 天并压缩。

### 12.2 Agent 升级

1. 备份 `/opt/skywalking/agent-95`；
2. 解压新 Agent；
3. 更新 systemd drop-in 的 `-javaagent` 路径；
4. `systemctl daemon-reload && systemctl restart shang-pivot`；
5. 验证 `actuator/health`、UI 服务列表、Trace；
6. 失败回滚旧 Agent 路径。

### 12.3 OAP/UI 升级

- OAP 升级前备份 PostgreSQL；
- UI 升级后必须重跑 `fetch-skywalking-ui-static.py` 并检查 `/static` alias；
- 先看 [SkyWalking Release Notes](https://github.com/apache/skywalking/releases) 的存储/配置变更；
- 回滚：切回旧镜像，恢复数据库备份。

## 13. 安全

- SkyWalking UI 已加 Basic Auth；密码在 `/opt/skywalking/ui-password`，不要写入仓库。
- OAP 的 11800/12800/9411 只绑定 `127.0.0.1`。
- Webhook 只绑定 Docker 网关 `172.17.0.1:18080`，不对公网开放。
- 禅道管理员密码已轮换；`install.php` 已禁用。
- 仍然建议：域名 + HTTPS、限制 60084 来源 IP、SSO/RBAC、审计日志。

## 14. 相关链接

- SkyWalking 官网：https://skywalking.apache.org/
- 文档：https://skywalking.apache.org/docs/
- 告警配置：https://skywalking.apache.org/docs/main/latest/en/setup/backend/backend-alarm/
- Java Agent：https://skywalking.apache.org/docs/skywalking-java/latest/readme/
- 本项目部署实录：[tencent-ops-stack.md](tencent-ops-stack.md)
- 课堂课件：[03-SkyWalking全链路监控课件.md](../courseware/03-SkyWalking全链路监控课件.md)

## 15. 附录：一次真实请求的排查记录

时间：2026-11-01 16:48:42 CST。

```bash
BASE=http://49.233.135.247:60084
curl -sS -m 10 -w '\nHTTP %{http_code} time=%{time_total}s\n' \
  "$BASE/api/home" -o /tmp/home.json
```

也可以直接运行 `/opt/skywalking/demo-request.sh`（仓库源文件 `scripts/observability/demo-request.sh`）。

```text
HTTP 200 time=0.077574s
```

响应：

```json
{
  "code": 0,
  "msg": "success",
  "traceId": "899bc6269ffd468eab46ee506c56b6b1",
  "feed": 20,
  "slots": 6
}
```

SkyWalking 查询：

```bash
python3 /opt/skywalking/skywalking-query.py \
  --service shang-pivot --minutes 5 --limit 100 --endpoint /api/home
```

```text
1793522922191   48ms   GET:/api/home
trace=6f80125963884371a7e165db927af64e.56.17935229221910007 spans=116
SQL spans: 39
```

对比：

| 指标 | 值 |
|---|---:|
| 客户端耗时（含 Nginx/网络） | 77.6ms |
| 应用 Trace 耗时 | 48ms |
| Span 数 | 116 |
| SQL Span 数 | 39 |

结论：

- 服务端 48ms，客户端 77.6ms，约 29.6ms 在接入层/网络/序列化；
- 39 条 SQL 集中在家首页品牌、运营位、SPU、SKU、配置；
- `home_slot_item`、`sku` 存在重复查询/N+1 风险；
- 优化优先级：缓存首页基础数据 → 批量查 SKU → 限制 feed 数量 → 加索引；
- 验证指标：P95、SQL Span 数、数据库 QPS。

完整课堂版见 [03-SkyWalking全链路监控课件.md](../courseware/03-SkyWalking全链路监控课件.md) 的 5.9 节。
