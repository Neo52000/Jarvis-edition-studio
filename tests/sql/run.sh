#!/usr/bin/env bash
# Usage: tests/sql/run.sh <postgres-url>   (an EMPTY throw-away database only!)
set -euo pipefail
url="${1:?postgres url of an empty scratch database}"
d="$(cd "$(dirname "$0")" && pwd)"
root="$d/../.."
psql "$url" -v ON_ERROR_STOP=1 -q -f "$d/00_stub_supabase.sql"
for f in "$root"/supabase/migrations/*.sql; do psql "$url" -v ON_ERROR_STOP=1 -q -f "$f"; done
psql "$url" -v ON_ERROR_STOP=1 -q -t -f "$d/rls_test.sql" | grep -q 'ALL SQL TESTS PASSED'
echo "SQL tests OK"
