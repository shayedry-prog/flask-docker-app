#!/usr/bin/env bash
#
# smoke_test.sh - Hit the running Docker Compose stack and check the API works
# end to end against the real PostgreSQL database.
#
# Usage: ./scripts/smoke_test.sh [base_url]     (default http://localhost:8000)

set -euo pipefail

BASE="${1:-http://localhost:8000}"

fail() { echo "FAIL: $1" >&2; exit 1; }
pass() { echo "PASS: $1"; }

# Wait up to 60s for the app to come up
for _ in $(seq 1 30); do
  if curl -fsS "$BASE/health" > /dev/null 2>&1; then break; fi
  sleep 2
done

curl -fsS "$BASE/health" | grep -q '"database":"up"' || fail "health check (database not reachable)"
pass "health check reports database up"

created="$(curl -fsS -X POST "$BASE/tasks" -H 'Content-Type: application/json' -d '{"title":"smoke test"}')"
id="$(echo "$created" | sed -E 's/.*"id":([0-9]+).*/\1/')"
[[ "$id" =~ ^[0-9]+$ ]] || fail "create task (got: $created)"
pass "created task $id"

curl -fsS "$BASE/tasks" | grep -q '"title":"smoke test"' || fail "task not listed"
pass "task appears in list"

curl -fsS -X PATCH "$BASE/tasks/$id" -H 'Content-Type: application/json' -d '{"done":true}' \
  | grep -q '"done":true' || fail "mark task done"
pass "marked task done"

code="$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$BASE/tasks/$id")"
[[ "$code" == "204" ]] || fail "delete task (HTTP $code)"
pass "deleted task"

echo "All smoke tests passed"
