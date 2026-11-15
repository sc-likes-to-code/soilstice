"""Frontend ↔ backend contract validation.

1. Every frontend mock-service response (SYNTHETIC fixtures exported by `npm run contract:fixtures`) must validate
   against the backend Pydantic models wrapped in ApiResponse (API_CONTRACTS §8 rule 7).
2. Every HTTP call in src/services/http/services.ts must map to an operation in the backend OpenAPI schema.
3. The committed backend/openapi.json must be current.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import app.contracts as C
from app.contracts import ApiResponse
from app.main import create_app

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
FIXTURES = BACKEND / "tests" / "fixtures" / "frontend_mock"
HTTP_SERVICES = REPO / "src" / "services" / "http" / "services.ts"

fixture_files = sorted(FIXTURES.glob("*.json"))


def test_fixtures_present():
    assert len(fixture_files) > 100, "run `npm run contract:fixtures` to export frontend mock fixtures"


@pytest.mark.parametrize("path", fixture_files, ids=lambda p: p.stem)
def test_frontend_fixture_validates(path):
    fx = json.loads(path.read_text(encoding="utf-8"))
    model = getattr(C, fx["model"])
    envelope = ApiResponse[list[model]] if fx["list"] else ApiResponse[model]
    parsed = envelope.model_validate(fx["payload"])
    assert parsed.meta.data_mode == "synthetic"  # mock data must stay self-identifying (rule R6)
    # round-trip: re-serialising produces the same JSON keys (nothing dropped or renamed)
    again = json.loads(parsed.model_dump_json())
    assert _keys(again) == _keys(fx["payload"])


def _keys(node, prefix=""):
    if isinstance(node, dict):
        out = set()
        for k, v in node.items():
            out.add(prefix + k)
            out |= _keys(v, prefix + k + ".")
        return out
    if isinstance(node, list):
        out = set()
        for v in node:
            out |= _keys(v, prefix + "[]")
        return out
    return set()


def test_frontend_http_calls_exist_in_openapi():
    src = HTTP_SERVICES.read_text(encoding="utf-8")
    calls = re.findall(r'request\(\s*"(GET|POST|PUT|PATCH|DELETE)",\s*[`"]([^`"]+)[`"]', src)
    assert len(calls) == 35  # E2–E27 plus 7 Phase 5 Crop KB endpoints plus 2 Phase 6 suitability endpoints
    ops = {(m.upper(), p.removeprefix("/api/v1")) for p, v in create_app().openapi()["paths"].items() for m in v}
    for method, path in calls:
        norm = re.sub(r"\$\{(\w+)\}", lambda m: "{" + {"id": "x", "farmId": "x", "scenarioId": "x", "jobId": "x", "cropId": "x"}
                      .get(m.group(1), m.group(1)) + "}", path)
        templ = {(m, re.sub(r"\{[^}]+\}", "{x}", p)) for m, p in ops}
        assert (method, re.sub(r"\{[^}]+\}", "{x}", norm)) in templ, f"{method} {path} missing from OpenAPI"


def test_committed_openapi_is_current():
    committed = json.loads((BACKEND / "openapi.json").read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(create_app().openapi(), sort_keys=True)), \
        "backend/openapi.json is stale: run `npm run contract:openapi`"
