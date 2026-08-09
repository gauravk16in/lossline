"""Grounded natural-language explanations for deterministic incident evidence."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Annotated, Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from lossline_intelligence.models.signal import SignalType

from src.config import settings

logger = logging.getLogger(__name__)

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ExplanationSource = Literal["LLM", "TEMPLATE"]
_NUMBER = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?%?")


class SignalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_type: SignalType
    current_value: Annotated[Decimal, Field(allow_inf_nan=False)]
    baseline_value: Annotated[Decimal, Field(allow_inf_nan=False)]
    unit: Identifier


class ExplanationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    incident_type: Identifier
    outlet_id: Identifier
    confidence: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    confidence_components: dict[str, float] = Field(default_factory=dict)
    signals: tuple[SignalEvidence, ...] = Field(min_length=1)
    revenue_risk: dict[str, Any] = Field(default_factory=dict)
    recommendation: dict[str, Any] | None = None


class ExplanationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    headline: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    probable_cause: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]
    evidence_summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]
    uncertainty_note: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]


class GeneratedExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    result: ExplanationResult
    source: ExplanationSource
    provider_model: str
    fallback_reason: str | None = None


class ExplanationProvider(Protocol):
    model_name: str

    async def generate(self, evidence: ExplanationEvidence) -> ExplanationResult: ...


class OpenAICompatibleExplanationProvider:
    """Small HTTP adapter; all business reasoning remains outside the provider."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str,
        timeout_seconds: float,
        post: Callable[..., Awaitable[httpx.Response]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._post = post

    async def generate(self, evidence: ExplanationEvidence) -> ExplanationResult:
        prompt = (
            "Explain this restaurant incident for a manager. Use only supplied facts. "
            "Do not calculate, infer new numbers, or claim causation. If using a "
            "number, copy its exact JSON representation. Return JSON matching the "
            "schema.\nEVIDENCE:\n"
            + evidence.model_dump_json()
        )
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You produce concise grounded incident prose.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "incident_explanation",
                    "strict": True,
                    "schema": ExplanationResult.model_json_schema(),
                },
            },
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self._post is not None:
            response = await self._post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return ExplanationResult.model_validate_json(content)


def build_fallback_explanation(evidence: ExplanationEvidence) -> ExplanationResult:
    present = {signal.signal_type for signal in evidence.signals}
    observations: list[str] = []
    if SignalType.ORDER_VOLUME_SPIKE in present:
        observations.append("order volume rose above its baseline")
    if SignalType.PREP_TIME_SPIKE in present:
        observations.append("preparation time increased")
    if SignalType.CANCELLATION_SPIKE in present:
        observations.append("cancellations increased")
    if SignalType.HANDOFF_DELAY_SPIKE in present:
        observations.append("handoff delays increased")
    if SignalType.DELAY_REVIEW_SPIKE in present:
        observations.append("delay-related reviews increased")
    summary = _join_observations(observations)
    return ExplanationResult(
        headline="Operational overload requires attention",
        probable_cause=(
            "The evidence suggests a capacity mismatch during the current "
            "service window."
        ),
        evidence_summary=f"{summary.capitalize()}.",
        uncertainty_note=(
            "This explanation is supported by correlated evidence, not proof "
            "of causation."
        ),
    )


def _join_observations(values: list[str]) -> str:
    if not values:
        return "multiple operating metrics changed from baseline"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def validate_grounding(
    result: ExplanationResult, evidence: ExplanationEvidence
) -> None:
    """Reject numeric or signal claims that are absent from deterministic evidence."""
    text = " ".join(
        (
            result.headline,
            result.probable_cause,
            result.evidence_summary,
            result.uncertainty_note,
        )
    )
    supplied = json.dumps(evidence.model_dump(mode="json"), sort_keys=True)
    allowed_numbers = {_normalize_number(value) for value in _NUMBER.findall(supplied)}
    unsupported_numbers = {
        value
        for value in _NUMBER.findall(text)
        if _normalize_number(value) not in allowed_numbers
    }
    if unsupported_numbers:
        raise ValueError(f"unsupported numeric claims: {sorted(unsupported_numbers)}")

    supplied_types = {signal.signal_type.value for signal in evidence.signals}
    mentioned_types = {kind.value for kind in SignalType if kind.value in text.upper()}
    unsupported_types = mentioned_types - supplied_types
    if unsupported_types:
        raise ValueError(f"unsupported signal claims: {sorted(unsupported_types)}")


def _normalize_number(value: str) -> Decimal:
    raw = value.removesuffix("%")
    number = Decimal(raw)
    return number / Decimal("100") if value.endswith("%") else number


async def generate_explanation(
    evidence: ExplanationEvidence,
    provider: ExplanationProvider | None = None,
) -> GeneratedExplanation:
    selected = provider or default_provider()
    if selected is None:
        return GeneratedExplanation(
            result=build_fallback_explanation(evidence),
            source="TEMPLATE",
            provider_model="TEMPLATE",
            fallback_reason="LLM provider is not configured",
        )
    try:
        result = await selected.generate(evidence)
        validate_grounding(result, evidence)
        return GeneratedExplanation(
            result=result,
            source="LLM",
            provider_model=selected.model_name,
        )
    except Exception as exc:
        logger.warning("LLM explanation rejected; using template: %s", exc)
        return GeneratedExplanation(
            result=build_fallback_explanation(evidence),
            source="TEMPLATE",
            provider_model="TEMPLATE",
            fallback_reason=type(exc).__name__,
        )


def default_provider() -> ExplanationProvider | None:
    if not settings.LLM_API_KEY:
        return None
    return OpenAICompatibleExplanationProvider(
        api_key=settings.LLM_API_KEY,
        model_name=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )
