"""Vercel Python Function entrypoint."""
from __future__ import annotations
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))
sys.path.insert(0, str(ROOT / "packages" / "intelligence" / "src"))

from src.main import app as fastapi_app  # noqa: E402


class OriginalPathAdapter:
    """Restore the public path after Vercel's internal function rewrite."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            query = parse_qs(scope.get("query_string", b"").decode())
            original = query.pop("__path", [None])[0]
            if original:
                scope = dict(scope)
                scope["path"] = original
                scope["raw_path"] = original.encode()
                scope["query_string"] = urlencode(query, doseq=True).encode()
        await self.application(scope, receive, send)


app = OriginalPathAdapter(fastapi_app)
