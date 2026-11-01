#!/usr/bin/env python3
"""Receive SkyWalking alarm webhooks and append them as JSON lines.

This is intentionally dependency-free so it can run under systemd on the same
host as OAP. It binds to the Docker bridge gateway by default so containers can
reach `http://host.docker.internal:18080/alarm`, while the port is not exposed
by the cloud firewall.

Environment:
    ALARM_HOST  bind address (default 172.17.0.1)
    ALARM_PORT  bind port (default 18080)
    ALARM_LOG   JSONL output path (default /var/log/skywalking-alarm/alarms.jsonl)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("ALARM_HOST", "172.17.0.1")
PORT = int(os.environ.get("ALARM_PORT", "18080"))
LOG_PATH = os.environ.get("ALARM_LOG", "/var/log/skywalking-alarm/alarms.jsonl")


class AlarmHandler(BaseHTTPRequestHandler):
    server_version = "SkyWalkingAlarmWebhook/1.0"

    def _write(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/health":
            self._write(200, {"status": "UP"})
        else:
            self._write(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/alarm":
            self._write(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError as exc:
            self._write(400, {"error": f"invalid json: {exc}"})
            return

        record = {
            "receivedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
            "remote": self.client_address[0],
            "payload": payload,
        }
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(
            f"alarm received from {self.client_address[0]}: "
            f"{payload.get('alarmMessage', payload)[:300]}",
            flush=True,
        )
        self._write(200, {"status": "accepted"})


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), AlarmHandler)
    print(f"SkyWalking alarm webhook listening on {HOST}:{PORT}, log={LOG_PATH}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as exc:
        print(f"failed to start alarm webhook: {exc}", file=sys.stderr)
        raise SystemExit(1)
