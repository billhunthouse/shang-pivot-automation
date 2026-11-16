#!/usr/bin/env python3
"""Query Prometheus range data for the 100-VU local performance run."""
from __future__ import annotations

import argparse
import json
import statistics
import urllib.parse
import urllib.request
from pathlib import Path

QUERIES = {
    "k6_vus": 'max(k6_vus{app="shang-pivot"})',
    "k6_rps": 'sum(rate(k6_http_reqs_total{app="shang-pivot"}[1m]))',
    "k6_p95_ms": 'max(k6_http_req_duration_p95{app="shang-pivot"}) * 1000',
    "k6_p99_ms": 'max(k6_http_req_duration_p99{app="shang-pivot"}) * 1000',
    "k6_failure_rate": '(sum(rate(k6_http_reqs_total{app="shang-pivot",expected_response="false"}[1m])) or vector(0)) / clamp_min(sum(rate(k6_http_reqs_total{app="shang-pivot"}[1m])), 0.000001)',
    "app_qps": 'sum(rate(http_server_requests_seconds_count{job="shang-pivot",uri!~"/actuator.*"}[1m]))',
    "app_avg_ms": 'sum(rate(http_server_requests_seconds_sum{job="shang-pivot",uri!~"/actuator.*"}[1m])) / clamp_min(sum(rate(http_server_requests_seconds_count{job="shang-pivot",uri!~"/actuator.*"}[1m])), 0.000001) * 1000',
    "app_max_ms": 'max(http_server_requests_seconds_max{job="shang-pivot",uri!~"/actuator.*"}) * 1000',
    "hikari_active": 'max(hikaricp_connections_active{job="shang-pivot"})',
    "hikari_pending": 'max(hikaricp_connections_pending{job="shang-pivot"})',
    "hikari_max": 'max(hikaricp_connections_max{job="shang-pivot"})',
    "hikari_acquire_max_ms": 'max(hikaricp_connections_acquire_seconds_max{job="shang-pivot"}) * 1000',
    "tomcat_busy": 'max(tomcat_threads_busy_threads{job="shang-pivot"})',
    "tomcat_current": 'max(tomcat_threads_current_threads{job="shang-pivot"})',
    "jvm_heap_mb": 'sum(jvm_memory_used_bytes{job="shang-pivot",area="heap"}) / 1024 / 1024',
    "jvm_gc_pause_ms_per_s": 'max(rate(jvm_gc_pause_seconds_sum{job="shang-pivot"}[1m])) * 1000',
    "jvm_threads": 'max(jvm_threads_live_threads{job="shang-pivot"})',
    "app_cpu": 'max(process_cpu_usage{job="shang-pivot"})',
    "system_cpu": 'max(system_cpu_usage{job="shang-pivot"})',
    "pg_active": 'max(pg_activity_active{job="shang-pivot-local-exporter"})',
    "pg_lock_wait": 'max(pg_activity_lock_wait{job="shang-pivot-local-exporter"})',
    "pg_locks_waiting": 'max(pg_locks_waiting{job="shang-pivot-local-exporter"})',
    "pg_xact_commit_rate": 'max(rate(pg_stat_database_xact_commit{job="shang-pivot-local-exporter"}[1m]))',
    "pg_xact_rollback_rate": 'max(rate(pg_stat_database_xact_rollback{job="shang-pivot-local-exporter"}[1m]))',
    "pg_sku_seq_scan": 'max(pg_table_seq_scan{job="shang-pivot-local-exporter",relname="sku"})',
    "pg_sku_idx_scan": 'max(pg_table_idx_scan{job="shang-pivot-local-exporter",relname="sku"})',
    "pg_spu_seq_scan": 'max(pg_table_seq_scan{job="shang-pivot-local-exporter",relname="spu"})',
    "pg_stock_seq_scan": 'max(pg_table_seq_scan{job="shang-pivot-local-exporter",relname="stock"})',
    "pg_cart_seq_scan": 'max(pg_table_seq_scan{job="shang-pivot-local-exporter",relname="cart"})',
    "pg_order_seq_scan": 'max(pg_table_seq_scan{job="shang-pivot-local-exporter",relname="order"})',
    "pg_order_idx_scan": 'max(pg_table_idx_scan{job="shang-pivot-local-exporter",relname="order"})',
    "redis_ops": 'max(redis_ops_per_sec{job="shang-pivot-local-exporter"})',
    "redis_clients": 'max(redis_connected_clients{job="shang-pivot-local-exporter"})',
    "redis_memory_mb": 'max(redis_used_memory_bytes{job="shang-pivot-local-exporter"}) / 1024 / 1024',
}


def query_range(base_url: str, query: str, start: int, end: int, step: int) -> list[dict]:
    params = urllib.parse.urlencode({"query": query, "start": start, "end": end, "step": step})
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/v1/query_range?{params}", timeout=20) as response:
        payload = json.load(response)
    return payload.get("data", {}).get("result", [])


def summarize(series: list[dict]) -> list[dict]:
    rows = []
    for item in series:
        values = [float(value[1]) for value in item.get("values", [])]
        if not values:
            continue
        rows.append({
            "metric": item.get("metric", {}),
            "first": round(values[0], 4),
            "last": round(values[-1], 4),
            "delta": round(values[-1] - values[0], 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "avg": round(statistics.fmean(values), 4),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:19090")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--step", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, expr in QUERIES.items():
        series = query_range(args.url, expr, args.start, args.end, args.step)
        (args.out / f"prometheus-{name}.json").write_text(
            json.dumps({"query": expr, "series": series}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary[name] = {"query": expr, "series": summarize(series)}
    (args.out / "prometheus-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({name: item["series"] for name, item in summary.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
