#!/usr/bin/env bash
# 生成 Allure 3 报告（结果兼容 allure-pytest 输出的 Allure 2 JSON）。
#
# 用法：
#   bash scripts/allure3_report.sh
#   bash scripts/allure3_report.sh --results artifacts/allure-ui-results --report artifacts/allure3-ui-report
#   bash scripts/allure3_report.sh --serve --port 9093
set -euo pipefail

cd "$(dirname "$0")/.."
RESULTS="artifacts/allure-ui-results"
REPORT="artifacts/allure3-ui-report"
SERVE=0
PORT=9093

while [ $# -gt 0 ]; do
  case "$1" in
    --results) RESULTS="${2:?--results 需要目录}"; shift 2 ;;
    --report) REPORT="${2:?--report 需要目录}"; shift 2 ;;
    --serve) SERVE=1; shift ;;
    --port) PORT="${2:?--port 需要端口}"; shift 2 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done

ALLURE="${ALLURE3_BIN:-}"
if [ -z "$ALLURE" ] && [ -x "/Users/imac/.local/opt/allure3/node_modules/.bin/allure" ]; then
  ALLURE="/Users/imac/.local/opt/allure3/node_modules/.bin/allure"
fi
if [ -z "$ALLURE" ] && command -v allure >/dev/null 2>&1; then
  ALLURE="allure"
fi
if [ -z "$ALLURE" ]; then
  cat >&2 <<'EOF'
未找到 Allure 3 CLI。安装：
  npm install -g allure
或：
  npm install --prefix ~/.local/opt/allure3 allure@3
EOF
  exit 3
fi

if [ ! -d "$RESULTS" ] || [ -z "$(ls -A "$RESULTS" 2>/dev/null)" ]; then
  echo "结果目录为空：$RESULTS" >&2
  exit 4
fi

if [ "$SERVE" = "1" ]; then
  exec "$ALLURE" serve "$RESULTS" --port "$PORT" --host 127.0.0.1
fi

"$ALLURE" generate "$RESULTS" --output "$REPORT" --report-name "尚品汇 UI 自动化" --clean
echo "✅ Allure 3 报告：$REPORT/index.html"
echo "   本地预览：python3 -m http.server 9093 --bind 127.0.0.1 --directory $REPORT"
