from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from lossline_intelligence.retrieval.models import ComparablePeriod, PolicyDocument, RetrievedItem

DEFAULT_RESULT_LIMIT = 5
DEFAULT_DOCUMENT_MIN_RELEVANCE = Decimal("0.2000")


@dataclass(frozen=True)
class DocumentRetrievalPolicy:
    enabled: bool = False
    corpus_admitted: bool = False
    min_relevance: Decimal = DEFAULT_DOCUMENT_MIN_RELEVANCE


@dataclass(frozen=True)
class RetrievalBundle:
    structured: tuple[RetrievedItem, ...]
    documents: tuple[RetrievedItem, ...]
    document_retrieval_used: bool


def _tokens(text: str) -> set[str]:
    return {token.strip(".,:;!?()[]").lower() for token in text.split() if token.strip(".,:;!?()[]")}


def retrieve_context(
    *, outlet_id: str, service_window: str, prediction_as_of: datetime,
    comparable_periods: tuple[ComparablePeriod, ...], sku_id: str | None = None,
    risk_type: str | None = None, query_text: str = "",
    documents: tuple[PolicyDocument, ...] = (),
    document_policy: DocumentRetrievalPolicy = DocumentRetrievalPolicy(),
    result_limit: int = DEFAULT_RESULT_LIMIT,
) -> RetrievalBundle:
    if prediction_as_of.tzinfo is None or prediction_as_of.utcoffset() is None:
        raise ValueError("prediction_as_of must be timezone-aware")
    if result_limit < 1: raise ValueError("result_limit must be positive")
    if not document_policy.min_relevance.is_finite() or not Decimal("0") <= document_policy.min_relevance <= Decimal("1"):
        raise ValueError("min_relevance must be finite and in [0, 1]")
    ranked: list[tuple[Decimal, ComparablePeriod]] = []
    for item in comparable_periods:
        if item.window_start.tzinfo is None or item.window_start.utcoffset() is None:
            raise ValueError("comparable windows must be timezone-aware")
        if item.window_start >= prediction_as_of: continue
        if item.outlet_id != outlet_id or item.service_window != service_window: continue
        score = Decimal("0.6000")
        if sku_id is not None and item.sku_id == sku_id: score += Decimal("0.2000")
        if risk_type is not None and item.risk_type == risk_type: score += Decimal("0.1500")
        if item.window_start.weekday() == prediction_as_of.weekday(): score += Decimal("0.0500")
        ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], -pair[1].window_start.timestamp(), pair[1].period_id))
    structured = tuple(RetrievedItem(item.period_id, "STRUCTURED_PERIOD", score, item.summary, item.evidence_ids)
        for score, item in ranked[:result_limit])

    use_documents = document_policy.enabled and document_policy.corpus_admitted
    document_results: list[tuple[Decimal, PolicyDocument]] = []
    if use_documents:
        query_tokens = _tokens(query_text)
        for item in documents:
            if item.effective_from.tzinfo is None or item.effective_from.utcoffset() is None:
                raise ValueError("document effective times must be timezone-aware")
            if item.effective_from > prediction_as_of or (item.effective_to is not None and item.effective_to <= prediction_as_of):
                continue
            tokens = _tokens(item.title + " " + item.text)
            score = Decimal("0") if not query_tokens else Decimal(len(query_tokens & tokens)) / Decimal(len(query_tokens | tokens))
            score = score.quantize(Decimal("0.0001"))
            if score >= document_policy.min_relevance:
                document_results.append((score, item))
        document_results.sort(key=lambda pair: (-pair[0], pair[1].document_id))
    document_items = tuple(RetrievedItem(item.document_id, "POLICY_DOCUMENT", score, item.title,
        (item.metadata_id,)) for score, item in document_results[:result_limit])
    return RetrievalBundle(structured, document_items, use_documents)
