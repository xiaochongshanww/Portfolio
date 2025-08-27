#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting backend container..."
python -c "import platform,sys;print(f'Python {platform.python_version()} - {sys.executable}')"

if [ "${AUTO_MIGRATE:-1}" = "1" ]; then
  echo "[entrypoint] Running database migrations..."
  flask db upgrade || { echo "[entrypoint] Migration failed"; exit 1; }
else
  echo "[entrypoint] AUTO_MIGRATE disabled. Skipping migrations."
fi

if [ "${REINDEX_ON_START:-false}" = "true" ]; then
  echo "[entrypoint] Rebuilding search index..."
  python -m scripts.reindex_search || echo "[entrypoint] Reindex failed (non-fatal)"
fi

echo "[entrypoint] Launching: $@"
exec "$@"
