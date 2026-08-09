"""C22 public-API runner for the seeded predictive golden demo."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from .scenarios.predictive_demo import generate_predictive_demo_events


async def run_predictive_demo(*, api_url: str, seed: int,
    target_window_start: datetime, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Post every input/actual through `/events`, approve, and collect evidence."""
    history, scheduled, actual = generate_predictive_demo_events(seed=seed,
        target_window_start=target_window_start)
    owns_client = client is None
    active = client or httpx.AsyncClient(base_url=api_url, timeout=30)
    try:
        for event in history:
            response = await active.post(f"{api_url}/api/v1/events", json=event)
            response.raise_for_status()
        scheduled_response = await active.post(f"{api_url}/api/v1/events", json=scheduled)
        scheduled_response.raise_for_status()
        cycle = scheduled_response.json()["predictive"]
        review = await active.post(f"{api_url}/api/v1/predictive/decisions/{cycle['decision_id']}/review",
            json={"decision": "APPROVE", "manager_id": "demo_manager",
                "idempotency_key": f"pred-review-{seed}", "manager_note": "Seeded C22 demo"})
        review.raise_for_status()
        actual_response = await active.post(f"{api_url}/api/v1/events", json=actual)
        actual_response.raise_for_status()
        today = await active.get(f"{api_url}/api/v1/predictive/today/{scheduled['restaurant_id']}/{scheduled['data']['service_window']}")
        today.raise_for_status()
        evaluations: list[dict[str, Any]] = []
        for forecast_id in cycle["forecast_ids"]:
            response = await active.get(f"{api_url}/api/v1/predictive/evaluations/forecast/{forecast_id}")
            response.raise_for_status(); evaluations.extend(response.json())
        return {"seed": seed, "history_event_count": len(history), "cycle": cycle,
            "review": review.json(), "outcome_ids": actual_response.json()["predictive"]["outcome_ids"],
            "today": today.json(), "evaluations": evaluations}
    finally:
        if owns_client: await active.aclose()
