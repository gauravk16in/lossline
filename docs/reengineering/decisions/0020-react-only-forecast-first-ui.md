# ADR 0020 — React-Only Forecast-First UI

Status: accepted — 2026-08-09

## Decision

Use the Vite/React application as the sole canonical UI. Add a Predictive Today view backed only by C19 APIs, delete disconnected synthetic dashboard data/components, and retire backend-served HTML after build/API parity. Retain reactive pages during coexistence.

## Consequences

The browser no longer presents hardcoded intelligence as live capability. Predictive and reactive pages coexist in React until later product migration. The initial bundle emits a size warning; optimization requires measured evidence and does not block functional acceptance.

## Verification

ESLint, TypeScript and Vite builds pass; source scan finds no mock imports/constants; backend integration verifies the aggregate payload and confirms root HTML is gone.
