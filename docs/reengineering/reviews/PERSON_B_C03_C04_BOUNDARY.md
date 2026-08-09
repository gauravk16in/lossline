# Person B — C03/C04 Boundary Expectations

Author: Person B (Product/Platform)

Date: 2026-08-09

Status: DRAFT — waiting for C02 and C03 contracts from Person A

## Purpose

This document describes what Person B needs from Person A's C03 (Synthetic Data) dataset contract before Person B can begin C04 (Feature Pipeline) implementation. It does **not** define domain models, SKU schemas, signal types, dataset structures or service-window models — those belong to Person A.

## Context

Per the coordination plan:
- Person A owns C03 specification, contracts and causal generator.
- Person B begins C04 only after C03's dataset contract is frozen.
- Person A can finish C03 testing while Person B begins C04 implementation.

## What Person B needs from C03

### 1. Grain identity schema

Person B needs the frozen typed contract for the canonical predictive grain: `outlet_id × sku_id × service_window × prediction_as_of`.

Questions for Person A:
- Is `sku_id` a string identifier or a structured type?
- Is `service_window` a string name (e.g., `"LUNCH"`) or a typed object with start/end times?
- Does the grain include a `window_date` or is it derived from `prediction_as_of` and the service window definition?

Person B will use this to design the PostgreSQL table schemas and API path parameters for C04/C19.

### 2. Ingestion path confirmation

C01 architecture and AGENTS.md require that the simulator calls `POST /events` — it never writes directly to the DB.

Person B needs to confirm:
- Does C03 synthetic data enter through the existing `POST /api/v1/events` endpoint?
- Are new event types needed? The current `EventEnvelope` supports `ORDER_PLACED`, `ORDER_CANCELLED`, `DELIVERY_COMPLETED`, `PREPARATION_STARTED`, `PREPARATION_COMPLETED`, `HANDOFF_STARTED`, `HANDOFF_COMPLETED`, `REVIEW_SUBMITTED` via the `EventType` enum.
- Does C03 introduce SKU-level events (e.g., `SKU_DEMAND_OBSERVED`, `INVENTORY_SNAPSHOT`, `CAPACITY_SNAPSHOT`)?
- Does C03 require new entity types in the event envelope?

If new event types are needed, Person B will extend the `EventEnvelope` schema and add corresponding persistence.

### 3. Normalization output contract

After raw events enter the system, C02's `NormalizedSignal` is the intermediate form. Person B needs to know:

- Does C04 read `NormalizedSignal` instances from PostgreSQL (i.e., Person B persists them first)?
- Or does C04 construct `NormalizedSignal` in-memory during the feature pipeline and persist the `FeatureSnapshot` downstream?
- What is the expected volume? One `NormalizedSignal` per event, or one per metric per window?

This determines whether Person B needs a `normalized_signals` table before C04 or only a `feature_snapshots` table.

### 4. Feature snapshot persistence contract

Person B needs the `FeatureSnapshot` Pydantic/dataclass definition from C03/C04 to design its persistence. At minimum:

- Snapshot ID format (deterministic hash or UUID).
- Grain fields (outlet, SKU, window, as-of).
- Registry version reference.
- Feature column names and types.
- Missing/imputed flag structure.
- Source signal IDs for provenance.
- Deterministic fingerprint computation method.

Person B will own the PostgreSQL table schema, but the column definitions must come from the frozen domain contract.

### 5. Censoring and stockout flags

C01 states: "Stockout-affected observations are censored. They must be flagged and may not silently serve as true-demand targets."

Person B needs:
- How are censored observations marked in the dataset? A boolean flag, a status enum, or a separate censoring table?
- Does the backend need to store and query censoring status?
- Does the API need to expose censoring information to the frontend?

### 6. Service window configuration

C01 freezes named service windows interpreted in outlet timezone. Person B needs:

- The configuration format: Is this a YAML file, a database table, or a Python dict?
- The minimum fields: window name, start time (local), end time (local), applicable days.
- Whether the backend stores this in PostgreSQL or reads from a configuration file.
- Whether the initial demo `LUNCH` window is hardcoded or configured.

Person B will design the storage and API exposure but will not invent the window model.

### 7. Dataset versioning

C01 requires: "Every model artifact stores training cutoff, dataset fingerprint, feature-registry version, code version, parameters, evaluation metrics and checksum."

Person B needs:
- Does the backend compute and store dataset fingerprints, or does `packages/intelligence/` compute them and the backend just persists?
- What is the fingerprint algorithm (SHA256 of sorted rows, etc.)?
- Does Person B need a `dataset_versions` table or is the fingerprint stored inline on the `FeatureSnapshot`?

## What Person B will NOT define

- SKU taxonomy or hierarchy.
- Signal type definitions or registry entries.
- Feature engineering formulas.
- Training target construction logic.
- Demand distribution parameters.
- Baseline/model comparison logic.
- Any `packages/intelligence/` domain model.

## Timeline expectations

1. Person A freezes C02 (Signal Registry) → Person B reviews contracts.
2. Person A freezes C03 dataset contract → Person B begins C04 persistence design.
3. Person A tests C03 generator → Person B implements C04 backend integration (in parallel).
4. Both agree on the `FeatureSnapshot` persistence contract before C04 is marked complete.
