#!/usr/bin/env python3
"""Query SkyWalking traces for the ShangPivot service and print SQL spans.

Run this on the server (OAP GraphQL binds to 127.0.0.1:12800):

    python3 scripts/observability/skywalking-query.py --service shang-pivot
    python3 scripts/observability/skywalking-query.py --endpoint /api/home --limit 50

Only the Python standard library is required.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.error
import urllib.request


def gql(endpoint: str, query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        return {"http": exc.code, "body": exc.read().decode(errors="replace")}
    except urllib.error.URLError as exc:
        return {"error": str(exc)}


def duration(minutes: int) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(minutes=minutes)
    # SkyWalking uses UTC and a compact HHmm format for the MINUTE step.
    fmt = "%Y-%m-%d %H%M"
    return {"start": start.strftime(fmt), "end": now.strftime(fmt), "step": "MINUTE"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oap", default="http://127.0.0.1:12800/graphql")
    parser.add_argument("--service", default="shang-pivot")
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--endpoint", default="/api/home")
    args = parser.parse_args()

    window = duration(args.minutes)
    services = gql(
        args.oap,
        "query($d: Duration!) { getAllServices(duration: $d) { id name } }",
        {"d": window},
    )
    rows = ((services.get("data") or {}).get("getAllServices") or [])
    service = next((row for row in rows if row["name"] == args.service), None)
    if service is None:
        print(f"service {args.service!r} not found; services={[r['name'] for r in rows]}")
        return 1

    query = """query($c: TraceQueryCondition) {
      queryBasicTraces(condition: $c) {
        traces { segmentId endpointNames duration start isError traceIds }
      }
    }"""
    condition = {
        "serviceId": service["id"],
        "queryDuration": window,
        "traceState": "ALL",
        "queryOrder": "BY_START_TIME",
        "paging": {"pageNum": 1, "pageSize": args.limit},
    }
    result = gql(args.oap, query, {"c": condition})
    traces = ((result.get("data") or {}).get("queryBasicTraces") or {}).get("traces") or []
    print(f"service={args.service} window={window['start']}..{window['end']} traces={len(traces)}")
    for trace in traces:
        print(f"  {trace['start']}  {trace['duration']:>5}ms  {'/'.join(trace['endpointNames'])}")

    target = next(
        (trace for trace in traces if any(args.endpoint in name for name in trace["endpointNames"])),
        traces[0] if traces else None,
    )
    if target is None:
        return 0

    trace_id = target["traceIds"][0]
    detail = gql(
        args.oap,
        """query($id: ID!) {
          queryTrace(traceId: $id) {
            spans {
              spanId parentSpanId serviceCode endpointName type peer component isError
              tags { key value }
            }
          }
        }""",
        {"id": trace_id},
    )
    spans = ((detail.get("data") or {}).get("queryTrace") or {}).get("spans") or []
    print(f"\ntrace={trace_id} spans={len(spans)}")
    sql_count = 0
    for span in spans:
        tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])}
        statement = tags.get("db.statement")
        if statement:
            sql_count += 1
        print(
            f"  {span['spanId']:>3} parent={span['parentSpanId']:>3} "
            f"{span['type']:<5} {span['component']:<26} {span['endpointName']}"
        )
        if statement:
            print(f"       SQL: {statement[:180]}")
    print(f"\nSQL spans: {sql_count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Allow piping into `head` without a traceback.
        raise SystemExit(0) from None
