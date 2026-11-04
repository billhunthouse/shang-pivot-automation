# SkyWalking 配置与告警

本目录保存 SkyWalking 的可复用配置，部署位置见 [运维手册](../../docs/SkyWalking运维手册.md)。

| 文件 | 用途 |
|---|---|
| `alarm-settings.yml` | 正式告警规则 + Webhook |
| `alarm-settings.test.yml` | 课堂/联调用的临时告警规则 |
| `alarm-webhook.py` | 零依赖告警接收器，写 JSONL |
| `skywalking-alarm-webhook.service` | systemd 单元 |
| `customize_enhance.xml` | 业务方法级追踪规则（customize-enhance） |

## 函数级追踪（customize-enhance）

Agent 默认只在 HTTP、JDBC、Redis 等边界生成 Span，不会自动追踪业务方法。
`customize_enhance.xml` 用官方 optional plugin 指定要追踪的类和方法，不需要改业务代码。

规则当前覆盖 C 端主链路：

```text
StorefrontController.home
  → CatalogReadService.home
     → SiteBrandService.get
     → HomeSlotService.listForStorefront
     → CatalogReadService.productPage
        → CatalogReadService.toCard
```

启用步骤。

先在开发机上传规则文件：

```bash
scp observability/skywalking/customize_enhance.xml \
  shangpivot-tencent:/opt/skywalking/customize_enhance.xml
```

再在服务器执行：

```bash
# 1. 备份 agent 配置
cp /opt/skywalking/agent-95/config/agent.config \
   /opt/skywalking/agent-95/config/agent.config.bak-$(date +%F-%H%M%S)

# 2. 启用 optional plugin
cp /opt/skywalking/agent-95/optional-plugins/apm-customize-enhance-plugin-9.5.0.jar \
   /opt/skywalking/agent-95/plugins/

# 3. 安装规则文件
chmod 644 /opt/skywalking/customize_enhance.xml

# 4. 让 agent 读取规则
grep -q '^plugin.customize.enhance_file=' /opt/skywalking/agent-95/config/agent.config || \
  echo 'plugin.customize.enhance_file=/opt/skywalking/customize_enhance.xml' \
  >> /opt/skywalking/agent-95/config/agent.config

# 5. 重启应用
systemctl restart shang-pivot
curl -fsS http://127.0.0.1:8087/actuator/health
```

验证：

```bash
curl -sS http://127.0.0.1:8086/api/home -o /dev/null
sleep 15
python3 /opt/skywalking/skywalking-query.py \
  --service shang-pivot --minutes 5 --limit 100 --endpoint /api/home
```

Trace 里应出现 `StorefrontController.home`、`CatalogReadService.home`、
`CatalogReadService.productPage`、`CatalogReadService.toCard` 等 Local Span。
方法签名变更后要同步改 `customize_enhance.xml`。

回滚：

```bash
rm -f /opt/skywalking/agent-95/plugins/apm-customize-enhance-plugin-9.5.0.jar
# 恢复最近一次备份的 agent.config（或删除 plugin.customize.enhance_file 行）
systemctl restart shang-pivot
```

## 部署

```bash
# 1. 告警规则挂载到 OAP
scp alarm-settings.yml root@server:/opt/skywalking/alarm-settings.yml
chmod 644 /opt/skywalking/alarm-settings.yml

# 2. 告警接收器
scp alarm-webhook.py root@server:/opt/skywalking/alarm-webhook.py
scp skywalking-alarm-webhook.service root@server:/etc/systemd/system/
ssh root@server '
  install -d -o nobody -g nogroup -m 750 /var/log/skywalking-alarm
  systemctl daemon-reload
  systemctl enable --now skywalking-alarm-webhook
'
```

OAP 需要挂载规则文件（重建容器时加）：

```bash
-v /opt/skywalking/alarm-settings.yml:/skywalking/config/alarm-settings.yml:ro
```

并确保 OAP 能访问 Webhook：

```bash
docker exec skywalking-oap curl -s http://host.docker.internal:18080/health
```

## 验证

```bash
curl -s http://172.17.0.1:18080/health
curl -s -X POST http://172.17.0.1:18080/alarm \
  -H 'Content-Type: application/json' \
  -d '{"scope":"SERVICE","name":"shang-pivot","alarmMessage":"manual test"}'
tail -1 /var/log/skywalking-alarm/alarms.jsonl
```

## 临时规则

```bash
cp /opt/skywalking/alarm-settings.yml /opt/skywalking/alarm-settings.yml.bak
cp /opt/skywalking/alarm-settings.test.yml /opt/skywalking/alarm-settings.yml
docker restart skywalking-oap
# 观察 alarms.jsonl
cp /opt/skywalking/alarm-settings.yml.bak /opt/skywalking/alarm-settings.yml
docker restart skywalking-oap
```
