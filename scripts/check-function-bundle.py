"""Conservative uncompressed-size guard for the Vercel Python function."""
from __future__ import annotations
import importlib.util
from pathlib import Path

LIMIT = 500 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT / "api", ROOT / "apps" / "backend", ROOT / "packages" / "intelligence"]
for package in ("lightgbm", "numpy", "scipy"):
    spec = importlib.util.find_spec(package)
    if spec and spec.origin:
        paths.append(Path(spec.origin).parent)
seen: set[Path] = set(); total = 0
for base in paths:
    for path in base.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved); total += path.stat().st_size
print(f"Estimated uncompressed Python function payload: {total / 1024 / 1024:.1f} MB")
if total >= LIMIT:
    raise SystemExit("Estimated Vercel function payload exceeds 500 MB")
