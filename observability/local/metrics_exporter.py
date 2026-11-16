#!/usr/bin/env python3
"""本地压测指标导出器：PostgreSQL + Redis。

只用于本地性能测试，监听 127.0.0.1:19187，输出 Prometheus text format。
不写入业务库、不修改数据，只读 pg_stat_* / Redis INFO。
"""
from __future__ import annotations

import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import psycopg

PG_DSN = os.getenv("PERF_PG_DSN", "")
REDIS_CONTAINER = os.getenv("PERF_REDIS_CONTAINER", "shang-redis")
PORT = int(os.getenv("PERF_EXPORTER_PORT", "19187"))
TABLES = ("sku", "spu", "stock", "cart", "order")


def pg_metrics() -> list[str]:
    lines: list[str] = []
    started = time.perf_counter()
    if not PG_DSN:
        return ["pg_up 0", "pg_exporter_error{reason=\"missing_dsn\"} 1"]
    try:
        with psycopg.connect(PG_DSN, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT datname, numbackends, xact_commit, xact_rollback,
                           blks_read, blks_hit, tup_returned, tup_fetched,
                           deadlocks, temp_files, temp_bytes
                    FROM pg_stat_database
                    WHERE datname = current_database()
                    """
                )
                row = cur.fetchone()
                if row:
                    datname = row[0]
                    values = {
                        "numbackends": row[1],
                        "xact_commit": row[2],
                        "xact_rollback": row[3],
                        "blks_read": row[4],
                        "blks_hit": row[5],
                        "tup_returned": row[6],
                        "tup_fetched": row[7],
                        "deadlocks": row[8],
                        "temp_files": row[9],
                        "temp_bytes": row[10],
                    }
                    for name, value in values.items():
                        lines.append(f'pg_stat_database_{name}{{datname="{datname}"}} {value}')

                cur.execute(
                    """
                    SELECT
                      count(*) FILTER (WHERE state = 'active'),
                      count(*) FILTER (WHERE wait_event_type = 'Lock'),
                      count(*)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    """
                )
                active, lock_wait, total = cur.fetchone()
                lines.extend([
                    f"pg_activity_active {active}",
                    f"pg_activity_lock_wait {lock_wait}",
                    f"pg_activity_total {total}",
                ])

                cur.execute("SELECT count(*) FROM pg_locks WHERE NOT granted")
                lines.append(f"pg_locks_waiting {cur.fetchone()[0]}")

                cur.execute("SELECT setting::int FROM pg_settings WHERE name = 'max_connections'")
                lines.append(f"pg_settings_max_connections {cur.fetchone()[0]}")

                cur.execute(
                    """
                    SELECT relname, seq_scan, idx_scan, n_live_tup, n_dead_tup
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'commerce' AND relname = ANY(%s)
                    """,
                    (list(TABLES),),
                )
                for relname, seq_scan, idx_scan, live_tup, dead_tup in cur.fetchall():
                    labels = f'{{relname="{relname}"}}'
                    lines.extend([
                        f"pg_table_seq_scan{labels} {seq_scan}",
                        f"pg_table_idx_scan{labels} {idx_scan}",
                        f"pg_table_live_tup{labels} {live_tup}",
                        f"pg_table_dead_tup{labels} {dead_tup}",
                    ])
        lines.append("pg_up 1")
    except Exception as exc:  # noqa: BLE001 - exporter must stay alive
        lines.append("pg_up 0")
        lines.append(f'pg_exporter_error{{reason="{type(exc).__name__}"}} 1')
    lines.append(f"pg_exporter_scrape_duration_seconds {time.perf_counter() - started:.6f}")
    return lines


def redis_info() -> dict[str, str]:
    try:
        result = subprocess.run(
            ["docker", "exec", REDIS_CONTAINER, "redis-cli", "INFO"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode != 0:
            return {}
        info: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if ":" in line and not line.startswith("#"):
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()
        return info
    except Exception:  # noqa: BLE001 - Redis metrics are best effort
        return {}


def redis_metrics() -> list[str]:
    info = redis_info()
    if not info:
        return ["redis_up 0"]
    fields = {
        "connected_clients": "redis_connected_clients",
        "used_memory": "redis_used_memory_bytes",
        "instantaneous_ops_per_sec": "redis_ops_per_sec",
        "keyspace_hits": "redis_keyspace_hits_total",
        "keyspace_misses": "redis_keyspace_misses_total",
        "evicted_keys": "redis_evicted_keys_total",
        "total_commands_processed": "redis_commands_processed_total",
        "uptime_in_seconds": "redis_uptime_seconds",
    }
    lines = ["redis_up 1"]
    for source, target in fields.items():
        value = info.get(source)
        if value is not None:
            try:
                lines.append(f"{target} {float(value)}")
            except ValueError:
                pass
    return lines


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path not in ("/metrics", "/"):
            self.send_response(404)
            self.end_headers()
            return
        body = "\n".join(pg_metrics() + redis_metrics()) + "\n"
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"perf exporter listening on http://127.0.0.1:{PORT}/metrics", flush=True)
    server.serve_forever()
