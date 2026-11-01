# SkyWalking 配置与告警

本目录保存 SkyWalking 的可复用配置，部署位置见 [运维手册](../../docs/SkyWalking运维手册.md)。

| 文件 | 用途 |
|---|---|
| `alarm-settings.yml` | 正式告警规则 + Webhook |
| `alarm-settings.test.yml` | 课堂/联调用的临时告警规则 |
| `alarm-webhook.py` | 零依赖告警接收器，写 JSONL |
| `skywalking-alarm-webhook.service` | systemd 单元 |

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
