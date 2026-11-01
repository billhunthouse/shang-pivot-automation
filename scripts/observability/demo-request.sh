#!/usr/bin/env bash
# Send the three read-only requests used in the SkyWalking courseware.
# Usage: BASE_URL=http://49.233.135.247:60084 bash demo-request.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://49.233.135.247:60084}"

request() {
  local path="$1"
  local out
  out="$(mktemp /tmp/skywalking-demo.XXXXXX)"
  local result
  result="$(curl -sS -m 10 -w 'HTTP %{http_code} time=%{time_total}s' "$BASE_URL$path" -o "$out")"
  printf '%-42s %s\n' "$path" "$result"
  if command -v jq >/dev/null 2>&1; then
    jq -c '{code,msg,traceId,feed:(.data.feed|length),total:.data.total}' "$out" 2>/dev/null || head -c 200 "$out"
    echo
  fi
}

request "/api/home"
request "/api/products/101"
request "/api/search?q=iPhone&page=1&size=10"

cat <<'EOF'

Next:
1. Wait 10-15 seconds for the agent to export and OAP to aggregate.
2. Run:
   python3 /opt/skywalking/skywalking-query.py \
     --service shang-pivot --minutes 5 --limit 100 --endpoint /api/home
3. Compare client time (curl) with server Trace time.
EOF
