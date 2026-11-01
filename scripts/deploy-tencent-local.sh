#!/usr/bin/env bash
# 本地一键发布到腾讯云轻量服务器。--rollback 只回滚，不重新构建。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export JAVA_HOME="${JAVA_HOME:-$(/usr/libexec/java_home -v 21 2>/dev/null || true)}"
MVN="${MVN:-$(command -v mvn || true)}"
[ -n "$MVN" ] || MVN="/Users/imac/.m2/wrapper/dists/apache-maven-3.9.12/57e1dc81/bin/mvn"
NPM="${NPM:-$(command -v npm || true)}"
[ -n "$NPM" ] || NPM="/Users/imac/.local/bin/npm"

export SHANG_SSH_HOST="${SHANG_SSH_HOST:-49.233.135.247}"
export SHANG_SSH_PORT="${SHANG_SSH_PORT:-22}"
export SHANG_SSH_USER="${SHANG_SSH_USER:-root}"
export SHANG_SSH_KEY="${SHANG_SSH_KEY:-$HOME/.ssh/tencent_deploy}"

if [ "${1:-}" = "--rollback" ]; then
  exec bash scripts/deploy-release.sh --rollback
fi

echo "== 构建后端（Java 17 兼容）=="
"$MVN" -q -DskipTests -Djava.version=17 -f backend/pom.xml -pl shang-server -am clean package

echo "== 构建前端 =="
(cd shang-mall && "$NPM" run build)
(cd shang-admin-web && "$NPM" run build)

echo "== 发布 =="
exec bash scripts/deploy-release.sh \
  --jar backend/shang-server/target/shang-server-0.0.1-SNAPSHOT.jar \
  --mall-dist shang-mall/dist \
  --admin-dist shang-admin-web/dist \
  --revision "${REVISION:-local-$(date +%Y%m%d-%H%M)}"
