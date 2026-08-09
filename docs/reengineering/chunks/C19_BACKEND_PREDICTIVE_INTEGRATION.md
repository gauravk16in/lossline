# C19 — Backend Predictive Integration and Coexistence

Status: complete

## Purpose

Persist and expose the C04–C18 predictive artifacts additively while the reactive incident path remains operational. C19 freezes backend storage/API/scheduling contracts; it does not remove reactive tables or endpoints.

## Persistence

The Alembic revision `b91c19predictive` adds queryable identity/scope columns plus complete validated JSON contracts for feature snapshots, forecasts, inventory/capacity projections, risks, drivers, dossiers, guarded decisions, guard results, decision traces and forecast-model artifact metadata. New predictive tables use canonical `outlet_id`; reactive tables retain `restaurant_id` during coexistence.

Persistence adapters are immutable and idempotent: repeating the same ID/payload returns the row, while the same ID with a different payload fails. Forecast strategy selects the newest accepted ML artifact and otherwise explicitly falls back to the baseline.

## APIs

- forecast list by outlet and named service window;
- inventory/capacity projection reads;
- dossier and guarded-decision reads;
- idempotent manager approve/reject review;
- selected model strategy and predictive analytics summary.

Manager review accepts no arbitrary action edits and only transitions decisions already awaiting review. Reactive APIs remain available and are tested alongside predictive analytics.

## Scheduling

Timezone-aware named-window schedule entries produce deterministic daily run keys inside a configurable tolerance. Completed keys suppress duplicates. The callback boundary is async and injected; C22 supplies the integrated predictive cycle.

## Additional correction

Inline event ingestion now passes its injected SQLAlchemy session into the reactive pipeline. This removes the prior split-session test/runtime hazard while preserving the Redis-consumer path's owned session.

## Definition of done

C19 is complete when migration upgrade/downgrade, immutable persistence/collision behavior, read APIs/404s, manager idempotency/conflict, baseline fallback/accepted artifact, scheduler timezone/replay, predictive/reactive coexistence, full backend, intelligence and simulator suites pass.
