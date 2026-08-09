"""C15 deterministic structured-first retrieval."""

from lossline_intelligence.retrieval.engine import (
    DEFAULT_RESULT_LIMIT, DocumentRetrievalPolicy, RetrievalBundle,
    retrieve_context,
)
from lossline_intelligence.retrieval.models import ComparablePeriod, PolicyDocument, RetrievedItem

__all__ = ["DEFAULT_RESULT_LIMIT", "ComparablePeriod", "DocumentRetrievalPolicy",
    "PolicyDocument", "RetrievedItem", "RetrievalBundle", "retrieve_context"]
