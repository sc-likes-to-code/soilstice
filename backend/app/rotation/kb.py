"""Crop knowledge-base integration point (DATA_ARCHITECTURE §5.11; PHASE_0 T19).

The KB is a teammate deliverable. When SOILSTICE_CROP_KB_DIR points at a directory containing `kb.json`, it is
loaded and validated: every threshold MUST carry a citation, otherwise the whole KB is rejected (entries without
citations are blocked from the live KB). Expected `kb.json` shape (proposed; to be agreed with the KB author):

    {"kb_version": "2026.1", "crops": [
        {"crop_code": 24, "name": "Winter Wheat", "family": "...", "is_double_crop": false,
         "thresholds": [{"factor": "ph", "rule": "...", "citation": "K-State ... (year)", "url": "..."}]}]}

Without a valid KB, E20 serves the CDL candidate list (names only, no thresholds) with kb_version "none".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator

from app.catalog import CDL_CANDIDATE_CROPS
from app.contracts import CropOption
from app.logging import get_logger

log = get_logger("rotation.kb")
NO_KB_VERSION = "none"
NO_KB_FAMILY = "unassigned (crop knowledge base pending)"


class KbThreshold(BaseModel):
    factor: str
    rule: str
    citation: str
    url: str | None = None

    @field_validator("citation")
    @classmethod
    def _cited(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("every KB threshold requires a citation")
        return v


class KbCrop(BaseModel):
    crop_code: int
    name: str
    family: str
    is_double_crop: bool
    thresholds: list[KbThreshold] = []


class KbFile(BaseModel):
    kb_version: str
    crops: list[KbCrop]


@dataclass
class CropKnowledgeBase:
    available: bool
    kb_version: str
    crops: list[CropOption]
    status_message: str
    entries: dict[int, KbCrop] = field(default_factory=dict)

    def crop_name(self, code: int) -> str | None:
        return next((c.name for c in self.crops if c.crop_code == code), None)


def fallback_kb(message: str) -> CropKnowledgeBase:
    return CropKnowledgeBase(
        available=False, kb_version=NO_KB_VERSION, status_message=message,
        crops=[CropOption(crop_code=c, name=n, family=NO_KB_FAMILY, is_double_crop=d, kb_version=NO_KB_VERSION)
               for c, n, d in CDL_CANDIDATE_CROPS],
    )


def load_kb(kb_dir: Path | None) -> CropKnowledgeBase:
    if kb_dir is None:
        return fallback_kb("No crop knowledge base configured (SOILSTICE_CROP_KB_DIR unset).")
    path = Path(kb_dir) / "kb.json"
    if not path.exists():
        return fallback_kb(f"Crop knowledge base file not found at {path}.")
    try:
        kb = KbFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (ValidationError, ValueError) as exc:
        log.warning("crop KB rejected", extra={"path": str(path), "error": str(exc)[:500]})
        return fallback_kb("Crop knowledge base rejected: every threshold must be cited and well-formed.")
    return CropKnowledgeBase(
        available=True, kb_version=kb.kb_version, status_message="Crop knowledge base loaded.",
        crops=[CropOption(crop_code=c.crop_code, name=c.name, family=c.family, is_double_crop=c.is_double_crop,
                          kb_version=kb.kb_version) for c in kb.crops],
        entries={c.crop_code: c for c in kb.crops},
    )
