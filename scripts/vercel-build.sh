#!/usr/bin/env bash
set -euo pipefail

if [[ "${VERCEL_ENV:-}" == "production" && "${DATABASE_URL:-}" == *"preview"* ]]; then
  echo "Production deployment received a preview database URL" >&2
  exit 1
fi
if [[ "${VERCEL_ENV:-}" == "preview" && "${DATABASE_URL:-}" == "${PRODUCTION_DATABASE_URL_SENTINEL:-__unset__}" ]]; then
  echo "Preview deployment received the production database URL" >&2
  exit 1
fi

PYTHONPATH=apps/backend:packages/intelligence/src python apps/backend/migrate.py
python -c 'import lightgbm, numpy, scipy; print("native intelligence dependencies imported")'
npm --prefix apps/frontend ci
npm --prefix apps/frontend run typecheck
npm --prefix apps/frontend run lint
npm --prefix apps/frontend run build

if rg -n "VITE_MANAGER_API_KEY|INGEST_API_KEY|CLERK_SECRET_KEY|DATABASE_URL|LLM_API_KEY" apps/frontend/dist; then
  echo "Forbidden credential identifier found in browser bundle" >&2
  exit 1
fi
