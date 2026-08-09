from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.db.models import Event, Incident, Outcome, Restaurant
from src.intelligence.langgraph_workflow import run_investigation
from src.intelligence.explanations import ExplanationResult
from src.intelligence.outcomes import verify_incident_outcome


def investigation_data(confidence: float = 0.81) -> dict:
    return {
        "candidate_id": "inc_candidate_1",
        "outlet_id": "outlet_1",
        "incident_type": "OPERATIONAL_OVERLOAD",
        "signals": [
            {
                "signal_type": "ORDER_VOLUME_SPIKE",
                "current_value": "20",
                "baseline_value": "5",
                "unit": "orders",
            },
            {
                "signal_type": "PREP_TIME_SPIKE",
                "current_value": "45",
                "baseline_value": "12",
                "unit": "minutes",
            },
            {
                "signal_type": "CANCELLATION_SPIKE",
                "current_value": "0.20",
                "baseline_value": "0.07",
                "unit": "ratio",
            },
        ],
        "confidence": confidence,
        "confidence_components": {"coverage_component": 0.75},
        "revenue_risk": {"status": "OK", "estimated_amount": "1200.00"},
        "recommendation": {"action_code": "REDUCE_DELIVERY_LOAD"},
    }


class FakeProvider:
    model_name = "fake-grounded-model"

    def __init__(self, result: ExplanationResult | Exception) -> None:
        self.result = result

    async def generate(self, evidence):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def grounded_result() -> ExplanationResult:
    return ExplanationResult(
        headline="Lunch-rush operational overload",
        probable_cause="The evidence suggests a capacity mismatch.",
        evidence_summary="Order volume, preparation time, and cancellations rose.",
        uncertainty_note="This is evidence-supported, not proof of causation.",
    )


@pytest.mark.asyncio
async def test_langgraph_runs_only_bounded_post_detection_stages() -> None:
    result = await run_investigation(
        **investigation_data(), provider=FakeProvider(grounded_result())
    )
    assert result["status"] == "AWAITING_APPROVAL"
    assert result["stages"] == [
        "load_context",
        "assess_confidence",
        "explain",
        "recommend",
        "finalize",
    ]
    assert result["explanation_source"] == "LLM"
    assert result["explanation"]["headline"] == "Lunch-rush operational overload"


@pytest.mark.asyncio
async def test_langgraph_abstains_without_enough_confidence() -> None:
    result = await run_investigation(
        **investigation_data(confidence=0.49),
        provider=FakeProvider(grounded_result()),
    )
    assert result["status"] == "MONITOR_ONLY"
    assert result["retry_count"] == 1
    assert result["stages"] == [
        "load_context",
        "assess_confidence",
        "widen_context",
        "reassess_confidence",
        "explain",
        "recommend",
        "finalize",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,reason",
    [
        (None, "LLM provider is not configured"),
        (FakeProvider(TimeoutError("provider timeout")), "TimeoutError"),
        (FakeProvider(ValueError("malformed structured output")), "ValueError"),
        (
            FakeProvider(
                grounded_result().model_copy(
                    update={"evidence_summary": "Confidence is 91%."}
                )
            ),
            "ValueError",
        ),
    ],
)
async def test_explanation_failures_use_grounded_template(provider, reason) -> None:
    result = await run_investigation(**investigation_data(), provider=provider)
    assert result["status"] == "AWAITING_APPROVAL"
    assert result["explanation_source"] == "TEMPLATE"
    assert result["explanation_fallback_reason"] == reason
    assert "91" not in " ".join(result["explanation"].values())


@pytest.mark.asyncio
async def test_recovery_events_resolve_incident_idempotently(db_session) -> None:
    window_end = datetime(2026, 8, 8, 13, 0, tzinfo=timezone.utc)
    db_session.add(Restaurant(id="outlet_1", name="Outlet 1", synthetic=True))
    incident = Incident(
        restaurant_id="outlet_1",
        incident_type="OPERATIONAL_OVERLOAD",
        status="ACTION_APPROVED",
        severity=0.8,
        confidence=0.82,
        confidence_components={},
        probable_cause="CAPACITY_MISMATCH",
        explanation="Grounded deterministic explanation",
        revenue_at_risk=1200,
        currency="INR",
        window_start=window_end - timedelta(minutes=30),
        window_end=window_end,
        correlation_rule_version="v1",
        config_version="v1",
    )
    db_session.add(incident)
    await db_session.flush()
    for index in range(3):
        db_session.add(
            Event(
                event_id=f"recovery_{index}",
                restaurant_id="outlet_1",
                source="pos",
                event_type="order.created",
                occurred_at=window_end + timedelta(minutes=index + 1),
                entity={"type": "order", "id": f"ord_{index}"},
                data={"channel": "delivery", "amount": 300, "currency": "INR"},
                metadata_json={"synthetic": True},
                schema_version="1.0",
                payload_hash=f"hash_{index}",
                published_to_stream=True,
            )
        )
    await db_session.flush()

    first = await verify_incident_outcome(db_session, incident)
    second = await verify_incident_outcome(db_session, incident)
    assert first.id == second.id
    assert first.status == "IMPROVED"
    assert incident.status == "RESOLVED"
    assert len((await db_session.execute(select(type(first)))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_insufficient_outcome_is_rechecked_after_recovery_events(db_session) -> None:
    window_end = datetime(2026, 8, 8, 13, 0, tzinfo=timezone.utc)
    db_session.add(Restaurant(id="outlet_retry", name="Retry Outlet", synthetic=True))
    incident = Incident(
        restaurant_id="outlet_retry",
        incident_type="OPERATIONAL_OVERLOAD",
        status="ACTION_APPROVED",
        severity=0.8,
        confidence=0.82,
        confidence_components={},
        probable_cause="CAPACITY_MISMATCH",
        explanation="Grounded deterministic explanation",
        revenue_at_risk=1200,
        currency="INR",
        window_start=window_end - timedelta(minutes=30),
        window_end=window_end,
        correlation_rule_version="v1",
        config_version="v1",
    )
    db_session.add(incident)
    await db_session.flush()

    first = await verify_incident_outcome(db_session, incident)
    assert first.status == "INSUFFICIENT_DATA"
    assert incident.status == "VERIFYING"

    for index in range(3):
        db_session.add(
            Event(
                event_id=f"retry_recovery_{index}",
                restaurant_id="outlet_retry",
                source="pos",
                event_type="order.created",
                occurred_at=window_end + timedelta(minutes=index + 1),
                entity={"type": "order", "id": f"retry_order_{index}"},
                data={"channel": "delivery", "amount": 300, "currency": "INR"},
                metadata_json={"synthetic": True},
                schema_version="1.0",
                payload_hash=f"retry_hash_{index}",
                published_to_stream=True,
            )
        )
    await db_session.flush()

    second = await verify_incident_outcome(db_session, incident)
    assert second.id == first.id
    assert second.status == "IMPROVED"
    assert incident.status == "RESOLVED"
    assert len((await db_session.execute(select(Outcome))).scalars().all()) == 1
