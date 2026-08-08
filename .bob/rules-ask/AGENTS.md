# Project Documentation Context (Non-Obvious Only)

- **`FINAL_IMPLEMENTATION_PLAN.md` is the implementation authority** — `IMPLEMENTATION_PLAN.md` is the superseded candidate; do not cite it.
- **Most directories are empty stubs**: `apps/backend/`, `apps/frontend/`, `services/intelligence/`, `simulator/`, `docs/`, `scripts/` all contain only placeholder files (`.md`, `.txt`). The only real code is in `packages/intelligence/`.
- **`app/` (with `x.txt`/`y.txt`) is not the same as `apps/`** — `apps/` is the target per the plan; `app/` is a placeholder that should not receive code.
- **Two `lossline_intelligence` source trees exist** in `packages/intelligence/`: `src/lossline_intelligence/` (installed, authoritative) and `lossline_intelligence/` (stray, not on the package path). Questions about "where is X implemented" must check `src/` first.
- **`claude.md` at the root is just `@AGENTS.md`** — it redirects to AGENTS.md, not a separate rules source.
- **The root `.venv` is shared** — it already has `lossline-intelligence` installed in editable mode. No setup step is needed before running tests.
- **All numeric values in the plan labeled `CONFIG_DEFAULT`** (thresholds, weights, window sizes, confidence cutoffs) are explicitly not business facts — never present them as authoritative.
