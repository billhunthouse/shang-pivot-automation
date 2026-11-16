# 本地性能监控（100 并发）

启动顺序：

```bash
# 1. 指标导出器（PostgreSQL + Redis）
cd /Users/imac/Desktop/电商自动化测试/shang-pivot-master
export PERF_PG_DSN='postgresql://shang:<password>@127.0.0.1:55434/shang'
agent_service/.venv/bin/python observability/local/metrics_exporter.py

# 2. Prometheus + Grafana
export GRAFANA_ADMIN_PASSWORD='<local-only-password>'
docker compose -f observability/local/docker-compose.yml up -d
```

访问：

- Prometheus：http://127.0.0.1:19090
- Grafana：http://127.0.0.1:13000
- 本地压测仪表板：http://127.0.0.1:13000/d/shang-pivot-local-perf
- 原服务端仪表板：http://127.0.0.1:13000/d/shang-pivot-perf-overview

k6 写入 Prometheus：

```bash
cd observability
K6_PROMETHEUS_RW_SERVER_URL=http://127.0.0.1:19090/api/v1/write \
K6_PROMETHEUS_RW_TREND_STATS='p(95),p(99),avg,min,max' \
k6 run -o experimental-prometheus-rw \
  --tag app=shang-pivot --tag env=local-perf \
  -e BASE_URL=http://127.0.0.1:8086/api \
  -e PHONE=13900000009 \
  -e STAGES='30s:20,1m:60,2m:100,2m:100,30s:0' \
  k6/browse-load.js
```

导出压测区间指标：

```bash
START=$(cat artifacts/perf-100u/load-start-epoch.txt)
END=$(cat artifacts/perf-100u/load-end-epoch.txt)
agent_service/.venv/bin/python observability/local/query_metrics.py \
  --start "$START" --end "$END" --out artifacts/perf-100u
```

注意：应用 Actuator 暴露的是 summary，不是 histogram；服务端 P95/P99 不能直接由 `histogram_quantile` 得到。详见 `docs/性能监控链路-k6-100并发.md`。
