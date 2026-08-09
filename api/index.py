"""Vercel Python Function entrypoint."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))
sys.path.insert(0, str(ROOT / "packages" / "intelligence" / "src"))

from src.main import app  # noqa: E402,F401
