"""Export the OpenAPI schema to backend/openapi.json (deterministic, sorted keys).

Usage (from backend/):  .venv/Scripts/python scripts/export_openapi.py [--check]
--check exits 1 if the committed file differs from the generated schema (for CI).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import create_app  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "openapi.json"


def main() -> int:
    schema = create_app().openapi()
    text = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("openapi.json is out of date; run scripts/export_openapi.py", file=sys.stderr)
            return 1
        print("openapi.json is up to date")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(schema['paths'])} paths, {len(schema['components']['schemas'])} schemas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
