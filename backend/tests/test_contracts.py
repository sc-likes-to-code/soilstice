"""Contract model invariants (API_CONTRACTS §1 rules R3/R5, §3)."""

import pytest
from pydantic import ValidationError

from app.contracts import ApiResponse, Farm, Quantity, SourceRef, UpsertScenarioRequest
from app.main import create_app


def test_quantity_missing_iff_null():
    assert Quantity(value=1.0, unit="mm").missing_reason is None
    assert Quantity(value=None, unit="mm", missing_reason="FILL_VALUE").value is None
    with pytest.raises(ValidationError):
        Quantity(value=None, unit="mm")  # missing without reason
    with pytest.raises(ValidationError):
        Quantity(value=0.0, unit="mm", missing_reason="FILL_VALUE")  # value with reason


def test_zero_is_a_value_not_missing():
    q = Quantity(value=0.0, unit="mm")
    assert q.value == 0.0 and q.missing_reason is None


def test_extra_keys_rejected_including_example_marker():
    with pytest.raises(ValidationError):
        Quantity.model_validate({"value": 1, "unit": "mm", "_example": True})


def test_unknown_vocab_rejected():
    with pytest.raises(ValidationError):
        Quantity(value=1.0, unit="inches")
    with pytest.raises(ValidationError):
        SourceRef(dataset_id="not_a_dataset", product="x", product_version="1")


def test_scenario_length_bounds():
    with pytest.raises(ValidationError):
        UpsertScenarioRequest(name="x", start_year=2026, sequence=[{"year": 2026, "crop_code": 1}])


def test_serialization_never_omits_nullable_fields():
    dumped = Quantity(value=1.0, unit="mm").model_dump(mode="json")
    assert set(dumped) == {"value", "unit", "uncertainty", "missing_reason"}


def test_openapi_output_schemas_mark_defaulted_fields_required():
    schema = create_app().openapi()["components"]["schemas"]
    assert set(schema["Quantity"]["required"]) == {"value", "unit", "uncertainty", "missing_reason"}
    assert "flags" in schema["QualityInfo"]["required"]
    # No separate -Input/-Output variants: one schema per contract type, as in contracts.ts
    assert not [k for k in schema if k.endswith("-Input") or k.endswith("-Output")]
    assert "ApiResponse_Farm_" in schema and Farm.__name__ in schema
    assert ApiResponse[Farm]
