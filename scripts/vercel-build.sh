#!/usr/bin/env bash
set -euo pipefail

echo "[vercel-build] validating deployment environment"
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${DIRECT_DATABASE_URL:?DIRECT_DATABASE_URL is required}"
: "${CLERK_ISSUER:?CLERK_ISSUER is required}"
: "${CLERK_JWKS_URL:?CLERK_JWKS_URL is required}"
: "${CREDENTIAL_PEPPER:?CREDENTIAL_PEPPER is required}"

if [[ "${VERCEL_ENV:-}" == "production" && "${DATABASE_URL:-}" == *"preview"* ]]; then
  echo "Production deployment received a preview database URL" >&2
  exit 1
fi
if [[ "${VERCEL_ENV:-}" == "preview" && "${DATABASE_URL:-}" == "${PRODUCTION_DATABASE_URL_SENTINEL:-__unset__}" ]]; then
  echo "Preview deployment received the production database URL" >&2
  exit 1
fi

echo "[vercel-build] running database migrations"
PGCONNECT_TIMEOUT=10 PYTHONPATH=apps/backend:packages/intelligence/src python apps/backend/migrate.py
echo "[vercel-build] verifying Python native dependencies and bundle size"
python -c 'import lightgbm, numpy, scipy; print("native intelligence dependencies imported")'
python scripts/check-function-bundle.py
npm --prefix apps/frontend ci
echo "[vercel-build] checking and building frontend"
npm --prefix apps/frontend run typecheck
npm --prefix apps/frontend run lint
npm --prefix apps/frontend run build

if rg -n "VITE_MANAGER_API_KEY|INGEST_API_KEY|CLERK_SECRET_KEY|DATABASE_URL|LLM_API_KEY" apps/frontend/dist; then
  echo "Forbidden credential identifier found in browser bundle" >&2
  exit 1
fi
