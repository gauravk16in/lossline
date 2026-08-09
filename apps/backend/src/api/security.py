"""Protected-demo API-key authentication dependencies."""

from __future__ import annotations

import secrets
from typing import Annotated, Literal

from fastapi import Header, HTTPException

from src.config import settings


def _expected(role: Literal["ingest", "manager", "admin"]) -> str | None:
    return {
        "ingest": settings.INGEST_API_KEY,
        "manager": settings.MANAGER_API_KEY,
        "admin": settings.ADMIN_API_KEY,
    }[role]


def require_role(role: Literal["ingest", "manager", "admin"]):
    async def authenticate(
        supplied: Annotated[str | None, Header(alias="X-LOSSLine-Key")] = None,
    ) -> None:
        expected = _expected(role)
        if not expected:
            raise HTTPException(status_code=503, detail=f"{role} API key is not configured")
        if supplied is None or not secrets.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail=f"Valid {role} API key required")

    return authenticate


require_ingest_key = require_role("ingest")
require_manager_key = require_role("manager")
require_admin_key = require_role("admin")
