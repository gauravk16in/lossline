"""LangGraph workflow placeholder.

LangGraph starts ONLY after deterministic correlation creates an
IncidentCandidate. It must not run per routine event.

Required future nodes (FINAL_IMPLEMENTATION_PLAN):
  load_evidence → specialist_* → correlate → score → widen_once →
  estimate_impact → explain → recommend → persist → await_approval →
  schedule_verification

This module is intentionally empty until Phase 2 detection → recommend
is proven end-to-end. Do not import LangGraph dependencies yet.
"""

# Phase 3 — deferred. Wire from pipeline.py after IncidentCandidate persist.
