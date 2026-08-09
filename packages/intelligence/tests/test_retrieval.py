from datetime import datetime, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.retrieval import (
    ComparablePeriod, DocumentRetrievalPolicy, PolicyDocument, retrieve_context,
)

AS_OF = datetime(2026, 1, 9, 10, tzinfo=timezone.utc)


def period(identifier, day, *, outlet="out1", window="DINNER", sku="sku1", risk="SHORTAGE"):
    return ComparablePeriod(identifier, outlet, window, datetime(2026, 1, day, 10, tzinfo=timezone.utc),
        sku, risk, f"summary {identifier}", (f"e-{identifier}",))


def document(identifier, text, *, start=datetime(2025, 1, 1, tzinfo=timezone.utc), end=None):
    return PolicyDocument(identifier, f"Policy {identifier}", text, start, end, f"meta-{identifier}")


def test_structured_exact_scope_first_and_deterministic() -> None:
    items = (period("older", 2), period("newer", 8), period("other", 8, outlet="out2"))
    result = retrieve_context(outlet_id="out1", service_window="DINNER", prediction_as_of=AS_OF,
        comparable_periods=items, sku_id="sku1", risk_type="SHORTAGE")
    assert tuple(item.item_id for item in result.structured) == ("older", "newer")
    assert result == retrieve_context(outlet_id="out1", service_window="DINNER", prediction_as_of=AS_OF,
        comparable_periods=items, sku_id="sku1", risk_type="SHORTAGE")


def test_future_and_wrong_scope_are_excluded() -> None:
    future = ComparablePeriod("future", "out1", "DINNER", AS_OF, "sku1", "SHORTAGE", "future", ("e",))
    result = retrieve_context(outlet_id="out1", service_window="DINNER", prediction_as_of=AS_OF,
        comparable_periods=(future, period("wrong-window", 8, window="LUNCH")))
    assert result.structured == ()


def test_limit_and_sparse_result() -> None:
    items = tuple(period(str(day), day) for day in range(1, 9))
    assert len(retrieve_context(outlet_id="out1", service_window="DINNER", prediction_as_of=AS_OF,
        comparable_periods=items, result_limit=3).structured) == 3
    assert retrieve_context(outlet_id="missing", service_window="DINNER", prediction_as_of=AS_OF,
        comparable_periods=items).structured == ()


def test_documents_disabled_by_default_and_require_admission() -> None:
    docs = (document("p1", "inventory shortage preparation policy"),)
    base = dict(outlet_id="out1", service_window="DINNER", prediction_as_of=AS_OF,
        comparable_periods=(), documents=docs, query_text="inventory shortage")
    assert not retrieve_context(**base).document_retrieval_used
    assert not retrieve_context(**base, document_policy=DocumentRetrievalPolicy(enabled=True)).document_retrieval_used
    admitted = retrieve_context(**base, document_policy=DocumentRetrievalPolicy(enabled=True, corpus_admitted=True))
    assert admitted.document_retrieval_used and admitted.documents[0].item_id == "p1"


def test_document_relevance_and_effective_time() -> None:
    docs = (document("relevant", "inventory shortage response"), document("irrelevant", "uniform policy"),
        document("expired", "inventory shortage", end=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    result = retrieve_context(outlet_id="out1", service_window="DINNER", prediction_as_of=AS_OF,
        comparable_periods=(), documents=docs, query_text="inventory shortage",
        document_policy=DocumentRetrievalPolicy(enabled=True, corpus_admitted=True, min_relevance=Decimal("0.2")))
    assert tuple(item.item_id for item in result.documents) == ("relevant",)


def test_invalid_time_limit_and_relevance_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        retrieve_context(outlet_id="o", service_window="w", prediction_as_of=datetime(2026, 1, 1), comparable_periods=())
    with pytest.raises(ValueError, match="positive"):
        retrieve_context(outlet_id="o", service_window="w", prediction_as_of=AS_OF, comparable_periods=(), result_limit=0)
    with pytest.raises(ValueError, match="min_relevance"):
        retrieve_context(outlet_id="o", service_window="w", prediction_as_of=AS_OF, comparable_periods=(),
            document_policy=DocumentRetrievalPolicy(min_relevance=Decimal("NaN")))


def test_no_vector_or_raw_query_surface() -> None:
    from lossline_intelligence.retrieval import engine
    names = set(dir(engine))
    assert not names.intersection({"vector_search", "raw_sql", "query_database"})
