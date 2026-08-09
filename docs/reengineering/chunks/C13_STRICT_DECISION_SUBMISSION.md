# C13 — Strict Operational Decision Submission

Status: complete

## Purpose

Define the only terminal proposal path for predictive decision support. Provider output becomes a candidate only through the strict `submit_operational_decision` schema; free-form completion always abstains.

## Contracts

`DecisionCandidate` is a strict frozen Pydantic boundary carrying the C01 identity, scope, risk, action, optional quantity/unit, execute-by, reason, evidence, urgency, action risk, approval and considered-constraint fields. `NO_ACTION` and `ABSTAIN` are first-class actions and cannot carry quantities.

`run_operational_decision()` accepts an injected provider protocol, one C11 dossier, and a C12 toolbox scoped to that exact dossier. Invalid structured submissions receive at most the module-default repair count. Free-form output, provider failure, and exhausted validation return typed `AgentAbstention`; they never fall through to a decision.

All provider calls are injectable and fakeable. C13 performs no LLM arithmetic, policy guarding, persistence, network, or execution.

## Definition of done

C13 is complete when strict/frozen schema behavior, allowed enums, quantity/unit invariants, free-form rejection, provider failure, finite repairs, validation feedback, toolbox scoping, abstention and regression tests pass.
