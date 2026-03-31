#!/usr/bin/env bash
set -euo pipefail

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-$(whoami)}"
PGPASSWORD="${PGPASSWORD:-}"
APP_DB="${RAG_DB_NAME:-agentic_rag_dev}"
TEST_DB="${RAG_TEST_DB_NAME:-agentic_rag_test}"

create_db_sql() {
  local db_name="$1"
  cat <<SQL
SELECT 'CREATE DATABASE "${db_name}"'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${db_name}');
\gexec
SQL
}

psql_cmd=(psql -v ON_ERROR_STOP=1)
if [[ -n "${PGHOST}" ]]; then
  psql_cmd+=(-h "${PGHOST}")
fi
if [[ -n "${PGPORT}" ]]; then
  psql_cmd+=(-p "${PGPORT}")
fi
if [[ -n "${PGUSER}" ]]; then
  psql_cmd+=(-U "${PGUSER}")
fi

if [[ -n "${PGPASSWORD}" ]]; then
  export PGPASSWORD
fi

"${psql_cmd[@]}" -d postgres <<<"$(create_db_sql "${APP_DB}")"
"${psql_cmd[@]}" -d postgres <<<"$(create_db_sql "${TEST_DB}")"
"${psql_cmd[@]}" -d "${APP_DB}" -c "CREATE EXTENSION IF NOT EXISTS vector;"
"${psql_cmd[@]}" -d "${TEST_DB}" -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "Initialized local databases: ${APP_DB}, ${TEST_DB} on ${PGHOST}:${PGPORT}"
