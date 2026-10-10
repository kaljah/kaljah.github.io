#!/usr/bin/env bash
# Smoke test of a running Neocarbon stack, through nginx over HTTPS.
#   deploy/smoke-test.sh https://neocarbon.example:443 admin@example.com 'password' [compose args...]
# The compose arguments (e.g. -f deploy/compose.yml --env-file .env) enable the backup / restore
# check; without them it is skipped. Uses curl -k: the certificate may be self-signed in a test.
set -euo pipefail

BASE="${1:?usage: smoke-test.sh <base url> <admin email> <admin password> [compose args]}"
EMAIL="${2:?admin email}"
PASSWORD="${3:?admin password}"
shift 3
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT
fail=0
c() { curl -sk --noproxy '*' -c "$JAR" -b "$JAR" "$@"; }
check() {  # name, expected, actual
  if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1 (expected $2, got $3)"; fail=1; fi
}
token() { c "$BASE/api/csrf-token" | python3 -c 'import json,sys; print(json.load(sys.stdin)["csrf_token"])'; }

check "API ready" "ready" "$(c "$BASE/api/health/ready" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"
check "SPA deep link /reports" "200" "$(c -o /dev/null -w '%{http_code}' "$BASE/reports")"
headers="$(c -I "$BASE/")"
for h in strict-transport-security content-security-policy x-frame-options referrer-policy; do
  check "header $h" "1" "$(grep -ci "^$h:" <<<"$headers" || true)"
done
check "unknown API route" "404" "$(c -o /dev/null -w '%{http_code}' "$BASE/api/satellite/sentinel5p/layer-config")"

check "sign-in without CSRF token refused" "400" "$(c -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" "$BASE/api/auth/login")"
check "sign-in" "200" "$(c -o /dev/null -w '%{http_code}' -H "X-CSRFToken: $(token)" -H "Referer: $BASE/login" \
  -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" "$BASE/api/auth/login")"
T="$(token)"
check "write from another site refused" "400" "$(c -o /dev/null -w '%{http_code}' -H "X-CSRFToken: $T" -H 'Referer: https://other.example/' \
  -H 'Content-Type: application/json' -d '{"theme":"light"}' -X PUT "$BASE/api/auth/settings")"
check "write from the application" "200" "$(c -o /dev/null -w '%{http_code}' -H "X-CSRFToken: $T" -H "Referer: $BASE/settings" \
  -H 'Content-Type: application/json' -d '{"theme":"light"}' -X PUT "$BASE/api/auth/settings")"
check "audit chain verified" "verified" "$(c "$BASE/api/audit/verify-chain" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"

if [ "$#" -gt 0 ]; then
  check "backup" "0" "$(docker compose "$@" exec -T app neocarbon-entrypoint backup >/dev/null 2>&1; echo $?)"
  latest="$(docker compose "$@" exec -T app sh -c 'ls -t /data/backups/*.sql.gz | head -1' | tr -d '\r')"
  check "restore" "0" "$(docker compose "$@" exec -T app neocarbon-entrypoint restore "$latest" --apply >/dev/null 2>&1; echo $?)"
  check "API ready after restore" "ready" "$(c "$BASE/api/health/ready" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"
fi

[ "$fail" = 0 ] && echo "All checks passed." || { echo "Some checks failed."; exit 1; }
