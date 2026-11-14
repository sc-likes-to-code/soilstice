"""Crop KB integration point: uncited thresholds must block the KB."""

import json

from app.rotation.kb import load_kb


def test_no_kb_falls_back_to_cdl_names(tmp_path):
    kb = load_kb(None)
    assert not kb.available and kb.kb_version == "none" and kb.crop_name(24) == "Winter Wheat"
    assert not load_kb(tmp_path).available  # dir without kb.json


def test_uncited_threshold_rejects_kb(tmp_path):
    (tmp_path / "kb.json").write_text(json.dumps({"kb_version": "t1", "crops": [
        {"crop_code": 24, "name": "Winter Wheat", "family": "Cereal", "is_double_crop": False,
         "thresholds": [{"factor": "ph", "rule": "test rule", "citation": " "}]}]}))
    kb = load_kb(tmp_path)
    assert not kb.available and "rejected" in kb.status_message


def test_cited_kb_loads(tmp_path):
    (tmp_path / "kb.json").write_text(json.dumps({"kb_version": "t2", "crops": [
        {"crop_code": 24, "name": "Winter Wheat", "family": "Cereal", "is_double_crop": False,
         "thresholds": [{"factor": "ph", "rule": "test rule", "citation": "Test citation (synthetic)"}]}]}))
    kb = load_kb(tmp_path)
    assert kb.available and kb.kb_version == "t2" and [c.kb_version for c in kb.crops] == ["t2"]
