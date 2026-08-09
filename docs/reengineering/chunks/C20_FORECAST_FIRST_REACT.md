# C20 — Forecast-First React Migration

Status: complete

## Purpose

Make `apps/frontend/` the sole application UI and render predictive backend facts without frontend business calculations or disconnected mock intelligence.

## Delivered view

`/predictive` provides outlet and named-window selection, loading/error/empty states, a visible synthetic-data label, SKU lower/point/upper forecasts, inventory ending/shortage risk, shared capacity range/tier, top structured non-causal driver, and guarded-decision status. Typed API contracts mirror C19 and the view calls the aggregated predictive-today endpoint.

The unused mock data tree and its disconnected dashboard/activity/context components were removed. The backend `GET /` HTML route and legacy template were retired after React build and API integration passed; backend root now returns 404 while nginx/Vite owns the SPA.

## Verification tooling

The stale Next.js ESLint configuration was replaced with pinned TypeScript/React ESLint plugins appropriate for Vite. Existing dead imports were removed. Lockfile installation, lint, strict TypeScript checking and production build pass. The remaining bundle-size notice is a build warning, not a correctness failure; code splitting is deferred until measured load performance requires it.

## Definition of done

C20 is complete when typed predictive API integration, forecast/projection/driver/decision rendering, all UI states, mock removal scan, backend HTML retirement test, lint, typecheck, production build and backend regression pass.
