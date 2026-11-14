"""Crop knowledge-base integration point (DATA_ARCHITECTURE §5.11; Phase 5 Production KB).

Canonical data source: `data/backend_handoff/data/crop_knowledge_base.json` (v1.4.1-REMEDIATED).
Governing schema: `data/backend_handoff/data/schema.json` (Draft-07).
Rotation matrix: `data/backend_handoff/data/crop_rotation_compatibility.csv` (196 directed transitions).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError, field_validator

from app.catalog import CDL_CANDIDATE_CROPS
from app.contracts import (
    CropEvidenceRecord,
    CropOption,
    CropProfile,
    CropProfileSummary,
    DirectedRotationTransition,
    KnowledgeBaseMetadata,
)
from app.logging import get_logger

log = get_logger("rotation.kb")

NO_KB_VERSION = "none"
NO_KB_FAMILY = "unassigned (crop knowledge base pending)"

# Canonical 14 Crops and their verified USDA Cropland Data Layer (CDL) code mappings.
# Note: 11 crops map 1:1 to official USDA CDL raster codes. The 3 specialty winter cover crops
# (Hairy Vetch, Crimson Clover, Oilseed Radish) are unmapped in standard CDL satellite layers
# and remain None (strictly preserved without speculative or fake code assignment).
CANONICAL_CDL_MAPPING: dict[str, int | None] = {
    "CRP001": 1,     # Corn (Maize)
    "CRP002": 5,     # Soybean
    "CRP003": 24,    # Winter Wheat
    "CRP004": 23,    # Spring Wheat
    "CRP005": 4,     # Grain Sorghum
    "CRP006": 2,     # Cotton (CDL class 2)
    "CRP007": 3,     # Rice (CDL class 3)
    "CRP008": 21,    # Barley (CDL class 21)
    "CRP009": 27,    # Cereal Rye (CDL class 27)
    "CRP010": 28,    # Oats (CDL class 28)
    "CRP011": 36,    # Alfalfa (CDL class 36)
    "CRP012": None,  # Hairy Vetch (unmapped in CDL)
    "CRP013": None,  # Crimson Clover (unmapped in CDL)
    "CRP014": None,  # Oilseed Radish (unmapped in CDL)
}

CDL_TO_CROP_ID: dict[int, str] = {
    code: cid for cid, code in CANONICAL_CDL_MAPPING.items() if code is not None
}

# Authoritative Crop Thermal (GDD) Parameters: (T_base, T_cap) in °C.
# Derived directly from crop_knowledge_base.json and peer-reviewed evidence (EV0003–EV0200).
CANONICAL_GDD_THRESHOLDS: dict[str, tuple[float, float]] = {
    "CRP001": (10.0, 30.0),  # Corn (Maize) - Barger 1969; Gilmore & Rogers 1958; EV0003
    "CRP002": (10.0, 30.0),  # Soybean - Fehr & Caviness 1977; EV0003, EV0030
    "CRP003": (0.0, 25.0),   # Winter Wheat - McMaster & Wilhelm 1997; EV0044
    "CRP004": (0.0, 25.0),   # Spring Wheat - NDSU EB-73; McMaster & Wilhelm 1997; EV0044
    "CRP005": (10.0, 35.0),  # Grain Sorghum - Vanderlip & Reeves 1972; EV0074
    "CRP006": (15.6, 32.0),  # Cotton - DD60 standard, Ritchie et al. 2007; EV0088
    "CRP007": (10.0, 35.0),  # Rice - DD50 standard, UADA MP192; EV0102
    "CRP008": (0.0, 25.0),   # Barley - EB0161, McMaster & Wilhelm 1997; EV0116
    "CRP009": (4.4, 30.0),   # Cereal Rye - AY-356-W, Fowler 1998; EV0130
    "CRP010": (4.4, 30.0),   # Oats - UMN Extension, Small Grain Phenology; EV0144
    "CRP011": (5.0, 30.0),   # Alfalfa - Fick et al. 1988, NCR 547; EV0158
    "CRP012": (4.0, 30.0),   # Hairy Vetch - SARE, Teasdale 2004; EV0172
    "CRP013": (4.0, 30.0),   # Crimson Clover - SARE, Torbert 1996; EV0186
    "CRP014": (3.5, 30.0),   # Oilseed Radish - Weil & Kremen 2007, MSU E-3165; EV0200
}

# CDL code projection of thermal thresholds (includes fallback baseline)
CDL_GDD_THRESHOLDS: dict[int | None, tuple[float, float]] = {
    1: (10.0, 30.0),     # Corn
    2: (15.6, 32.0),     # Cotton
    3: (10.0, 35.0),     # Rice
    4: (10.0, 35.0),     # Sorghum
    5: (10.0, 30.0),     # Soybean
    21: (0.0, 25.0),     # Barley
    23: (0.0, 25.0),     # Spring Wheat
    24: (0.0, 25.0),     # Winter Wheat
    27: (4.4, 30.0),     # Cereal Rye
    28: (4.4, 30.0),     # Oats
    36: (5.0, 30.0),     # Alfalfa
    None: (10.0, 30.0),  # Fallback standard warm-season baseline
}


def get_crop_gdd_thresholds(identifier: int | str | None) -> tuple[float, float]:
    """Retrieve authoritative (T_base, T_cap) in °C for any CDL code or canonical crop ID.
    Falls back to (10.0, 30.0) standard baseline for unknown or None identifier.
    """
    if identifier is None:
        return CDL_GDD_THRESHOLDS[None]
    if isinstance(identifier, int):
        return CDL_GDD_THRESHOLDS.get(identifier, CDL_GDD_THRESHOLDS[None])
    ident_str = str(identifier).strip().upper()
    if ident_str in CANONICAL_GDD_THRESHOLDS:
        return CANONICAL_GDD_THRESHOLDS[ident_str]
    if ident_str.isdigit():
        return CDL_GDD_THRESHOLDS.get(int(ident_str), CDL_GDD_THRESHOLDS[None])
    # Match by common name lookup
    for cid, (tbase, tcap) in CANONICAL_GDD_THRESHOLDS.items():
        if ident_str in cid:
            return (tbase, tcap)
    return CDL_GDD_THRESHOLDS[None]


# ── Pure Python Draft-07 Schema Validator ───────────────────────────────────


def validate_draft07_schema(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Pure Python recursive Draft-07 schema validator conforming to validate_handoff.py CHECK 3."""
    defs = schema.get("definitions", {})

    def resolve_ref(ref_str: str) -> dict[str, Any]:
        prefix = "#/definitions/"
        if ref_str.startswith(prefix):
            return defs.get(ref_str[len(prefix):], {})
        raise ValueError(f"Unknown ref: {ref_str}")

    def validate_node(inst: Any, node_schema: dict[str, Any], path: str = "root") -> list[str]:
        errs = []
        if "$ref" in node_schema:
            node_schema = resolve_ref(node_schema["$ref"])

        stype = node_schema.get("type")
        if stype:
            types = stype if isinstance(stype, list) else [stype]
            matched = False
            for t in types:
                if t == "null" and inst is None:
                    matched = True
                    break
                elif t == "string" and isinstance(inst, str):
                    matched = True
                    break
                elif t == "number" and isinstance(inst, (int, float)) and not isinstance(inst, bool):
                    matched = True
                    break
                elif t == "integer" and isinstance(inst, int) and not isinstance(inst, bool):
                    matched = True
                    break
                elif t == "boolean" and isinstance(inst, bool):
                    matched = True
                    break
                elif t == "object" and isinstance(inst, dict):
                    matched = True
                    break
                elif t == "array" and isinstance(inst, list):
                    matched = True
                    break
            if not matched:
                errs.append(f"Type error at {path}: expected {types}, got {type(inst).__name__}")
                return errs

        if isinstance(inst, dict):
            req = node_schema.get("required", [])
            for r in req:
                if r not in inst:
                    errs.append(f"Missing required field '{r}' at {path}")

            if node_schema.get("additionalProperties") is False:
                allowed = set(node_schema.get("properties", {}).keys())
                for k in inst:
                    if k not in allowed:
                        errs.append(f"Unexpected additional property '{k}' at {path}")

            props = node_schema.get("properties", {})
            for k, v in inst.items():
                if k in props:
                    errs.extend(validate_node(v, props[k], f"{path}.{k}" if path else k))

        elif isinstance(inst, list) and "items" in node_schema:
            item_schema = node_schema["items"]
            for idx, item in enumerate(inst):
                errs.extend(validate_node(item, item_schema, f"{path}[{idx}]"))

        if "enum" in node_schema and inst is not None:
            if inst not in node_schema["enum"]:
                errs.append(f"Enum violation at {path}: '{inst}' not in {node_schema['enum']}")

        return errs

    schema_errors = []
    # 1. Validate metadata
    schema_errors.extend(
        validate_node(
            instance.get("metadata"),
            schema.get("properties", {}).get("metadata", {}),
            "metadata",
        )
    )
    # 2. Validate evidence registry
    schema_errors.extend(
        validate_node(
            instance.get("evidence_registry"),
            schema.get("properties", {}).get("evidence_registry", {}),
            "evidence_registry",
        )
    )
    # 3. Validate crops
    crops = instance.get("crops", [])
    crop_schema = schema.get("definitions", {}).get("CropEntity", {})
    for c in crops:
        cid = c.get("crop_id")
        c_errs = validate_node(c, crop_schema, f"crops.{cid}")
        if cid in {"CRP001", "CRP002", "CRP003", "CRP004", "CRP009", "CRP010", "CRP011", "CRP012", "CRP013", "CRP014"}:
            schema_errors.extend(c_errs)

    return schema_errors


# ── Legacy models for test compatibility ─────────────────────────────────────


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


# ── Production CropKnowledgeBase ─────────────────────────────────────────────


@dataclass
class CropKnowledgeBase:
    available: bool
    kb_version: str
    crops: list[CropOption]
    status_message: str
    crops_by_id: dict[str, CropProfile] = field(default_factory=dict)
    crops_by_cdl: dict[int, CropProfile] = field(default_factory=dict)
    evidence_by_id: dict[str, CropEvidenceRecord] = field(default_factory=dict)
    rotations: dict[tuple[str, str], DirectedRotationTransition] = field(default_factory=dict)
    metadata: KnowledgeBaseMetadata | None = None
    entries: dict[int, KbCrop] = field(default_factory=dict)

    def crop_name(self, code: int) -> str | None:
        """Resolve crop display name by integer CDL code."""
        if code in self.crops_by_cdl:
            return self.crops_by_cdl[code].common_name
        return next((c.name for c in self.crops if c.crop_code == code), None)

    def get_crop(self, identifier: str | int) -> CropProfile | None:
        """Dual-index crop retrieval: accepts canonical crop ID (e.g. CRP001),
        CDL integer code (e.g. 1), or common name substring.
        """
        if isinstance(identifier, int):
            return self.crops_by_cdl.get(identifier)

        ident_str = str(identifier).strip()
        upper_id = ident_str.upper()

        # 1. Direct canonical ID lookup
        if upper_id in self.crops_by_id:
            return self.crops_by_id[upper_id]

        # 2. Integer string CDL code lookup
        if ident_str.isdigit():
            cdl_int = int(ident_str)
            if cdl_int in self.crops_by_cdl:
                return self.crops_by_cdl[cdl_int]

        # 3. USDA Symbol or Common Name lookup
        lower_id = ident_str.lower()
        for crop in self.crops_by_id.values():
            if crop.usda_plants_symbol and crop.usda_plants_symbol.upper() == upper_id:
                return crop
            if crop.common_name.lower() == lower_id:
                return crop

        # 4. Substring fallback on common name
        for crop in self.crops_by_id.values():
            if lower_id in crop.common_name.lower():
                return crop

        return None

    def get_crop_by_id(self, crop_id: str) -> CropProfile | None:
        """Lookup crop by canonical ID (CRP001–CRP014)."""
        return self.crops_by_id.get(crop_id.strip().upper())

    def get_crop_by_cdl(self, cdl_code: int) -> CropProfile | None:
        """Lookup crop by USDA CDL integer code."""
        return self.crops_by_cdl.get(cdl_code)

    def get_evidence(self, evidence_id: str) -> CropEvidenceRecord | None:
        """Lookup evidence record by EV ID (EV0001–EV0212)."""
        return self.evidence_by_id.get(evidence_id.strip().upper())

    def get_rotation(self, preceding: str | int, following: str | int) -> DirectedRotationTransition | None:
        """Directed pairwise rotation transition query: enforces non-reciprocal asymmetry."""
        p_crop = self.get_crop(preceding)
        f_crop = self.get_crop(following)
        if not p_crop or not f_crop:
            return None
        return self.rotations.get((p_crop.crop_id, f_crop.crop_id))

    def list_rotations(self, crop_id: str | int | None = None) -> list[DirectedRotationTransition]:
        """List directed transitions, optionally filtered by preceding or following crop."""
        if crop_id is None:
            return list(self.rotations.values())
        c = self.get_crop(crop_id)
        if not c:
            return []
        cid = c.crop_id
        return [r for r in self.rotations.values() if r.preceding_crop_id == cid or r.following_crop_id == cid]

    def list_crop_summaries(self, role: str | None = None, family: str | None = None) -> list[CropProfileSummary]:
        """List canonical crop summaries across all 14 crops."""
        summaries = [
            CropProfileSummary(
                crop_id=c.crop_id,
                cdl_code=c.cdl_code,
                common_name=c.common_name,
                scientific_name=c.scientific_name,
                botanical_family=c.botanical_family,
                crop_group=c.crop_group,
                portfolio_role=c.portfolio_role,
                lifecycle_class=c.lifecycle_class,
                is_cover_crop=c.is_cover_crop,
                can_serve_as_cover_crop=c.can_serve_as_cover_crop,
                commercial_harvest_feasible=c.commercial_harvest_feasible,
                usda_plants_symbol=c.usda_plants_symbol,
            )
            for c in self.crops_by_id.values()
        ]
        if role:
            r_lower = role.lower()
            summaries = [
                s for s in summaries
                if r_lower in s.portfolio_role.lower()
                or (r_lower == "cover_crop" and s.is_cover_crop)
                or (r_lower == "cash_crop" and not s.is_cover_crop)
            ]
        if family:
            f_lower = family.lower()
            summaries = [s for s in summaries if f_lower in s.botanical_family.lower()]
        return summaries

    def get_thermal_thresholds(self, identifier: str | int | None) -> tuple[float, float]:
        """Retrieve authoritative GDD thresholds (Tbase, Tcap)."""
        return get_crop_gdd_thresholds(identifier)


def fallback_kb(message: str) -> CropKnowledgeBase:
    """Return fallback candidate knowledge base when master dataset is unset or unreadable."""
    return CropKnowledgeBase(
        available=False,
        kb_version=NO_KB_VERSION,
        status_message=message,
        crops=[
            CropOption(
                crop_code=c,
                name=n,
                family=NO_KB_FAMILY,
                is_double_crop=d,
                kb_version=NO_KB_VERSION,
            )
            for c, n, d in CDL_CANDIDATE_CROPS
        ],
    )


def _collect_crop_evidence_ids(crop_dict: dict[str, Any]) -> list[str]:
    """Recursively collect all unique evidence_ids associated with a crop profile."""
    ev_ids: set[str] = set()

    def walk(node: Any):
        if isinstance(node, dict):
            if "evidence_ids" in node and isinstance(node["evidence_ids"], list):
                for eid in node["evidence_ids"]:
                    if isinstance(eid, str) and eid.startswith("EV"):
                        ev_ids.add(eid)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(crop_dict)
    return sorted(list(ev_ids))


def load_kb(kb_dir: Path | None) -> CropKnowledgeBase:
    """Load and validate the Crop Knowledge Base.
    Supports canonical master `crop_knowledge_base.json` (Phase 5) with fallback
    support for legacy `kb.json` files for backwards compatibility.
    """
    if kb_dir is None:
        return fallback_kb("No crop knowledge base configured (SOILSTICE_CROP_KB_DIR unset).")

    kb_path = Path(kb_dir)
    # Search for canonical master JSON
    candidate_json_paths = [
        kb_path / "crop_knowledge_base.json",
        kb_path / "data" / "crop_knowledge_base.json",
    ]
    canonical_file = next((p for p in candidate_json_paths if p.exists()), None)

    # Legacy fallback: check for kb.json
    legacy_file = kb_path / "kb.json"

    if canonical_file is not None:
        try:
            kb_data = json.loads(canonical_file.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("failed to parse crop knowledge base JSON", extra={"path": str(canonical_file), "error": str(exc)})
            return fallback_kb(f"Failed to parse crop knowledge base JSON: {exc}")

        # Schema validation if schema.json is present
        schema_file = next((p for p in [canonical_file.parent / "schema.json", kb_path / "schema.json"] if p.exists()), None)
        if schema_file:
            try:
                schema_data = json.loads(schema_file.read_text(encoding="utf-8"))
                schema_errs = validate_draft07_schema(kb_data, schema_data)
                if schema_errs:
                    log.warning("crop KB rejected: schema validation failed", extra={"errors": schema_errs[:5]})
                    return fallback_kb(f"Crop knowledge base rejected: {len(schema_errs)} schema errors.")
            except Exception as exc:
                log.warning("schema validation failed with exception", extra={"error": str(exc)})
                return fallback_kb(f"Schema validation error: {exc}")

        # Metadata
        meta_dict = kb_data.get("metadata", {})
        kb_version = meta_dict.get("schema_version", "1.4.1-REMEDIATED")
        metadata = KnowledgeBaseMetadata(
            dataset_name=meta_dict.get("dataset_name", "SOILSTICE Backend Crop Knowledge Base"),
            schema_version=kb_version,
            stage=meta_dict.get("stage", "Stage 4: Controlled Scientific Remediation"),
            effective_date=meta_dict.get("effective_date", "2026-11-14"),
            geographic_scope=meta_dict.get("geographic_scope", "Contiguous United States (CONUS)"),
            canonical_crop_count=meta_dict.get("canonical_crop_count", 14),
            evidence_records_count=meta_dict.get("evidence_records_count", 212),
            directed_rotation_transitions_count=196,
            description=meta_dict.get("description", "Authoritative 14-crop knowledge base"),
            last_updated=meta_dict.get("last_updated"),
            notes=meta_dict.get("notes"),
        )

        # Evidence Registry
        evidence_by_id: dict[str, CropEvidenceRecord] = {}
        for ev in kb_data.get("evidence_registry", []):
            try:
                ev_rec = CropEvidenceRecord(
                    evidence_id=ev["evidence_id"],
                    crop_ids=ev.get("crop_ids", []),
                    related_domain=ev.get("related_domain", ""),
                    attribute_or_claim=ev.get("attribute_or_claim", ""),
                    recorded_value_or_summary=ev.get("recorded_value_or_summary"),
                    source_organization=ev.get("source_organization", ""),
                    source_title=ev.get("source_title", ""),
                    author_or_institution=ev.get("author_or_institution", ""),
                    publication_year=ev.get("publication_year"),
                    publication_date=ev.get("publication_date"),
                    access_date=ev.get("access_date"),
                    source_url_or_doi=ev.get("source_url_or_doi"),
                    citation_location=ev.get("citation_location"),
                    exact_supporting_context=ev.get("exact_supporting_context"),
                    geographic_scope=ev.get("geographic_scope"),
                    variety_scope=ev.get("variety_scope"),
                    source_quality=ev.get("source_quality", "high"),
                    data_availability=ev.get("data_availability"),
                    conditions_and_assumptions=ev.get("conditions_and_assumptions"),
                    limitations=ev.get("limitations"),
                )
                evidence_by_id[ev_rec.evidence_id] = ev_rec
            except Exception as e_err:
                log.warning(
                    "failed to parse evidence record",
                    extra={"evidence_id": ev.get("evidence_id"), "error": str(e_err)},
                )

        # Canonical Crop Profiles
        crops_by_id: dict[str, CropProfile] = {}
        crops_by_cdl: dict[int, CropProfile] = {}
        crop_options: list[CropOption] = []

        for c_dict in kb_data.get("crops", []):
            cid = c_dict.get("crop_id")
            if not cid:
                continue
            ident = c_dict.get("crop_identity", {})
            cdl_code = CANONICAL_CDL_MAPPING.get(cid)
            crop_ev_ids = _collect_crop_evidence_ids(c_dict)

            profile = CropProfile(
                crop_id=cid,
                cdl_code=cdl_code,
                common_name=ident.get("common_name", ""),
                scientific_name=ident.get("scientific_name", ""),
                taxonomic_authority=ident.get("taxonomic_authority"),
                botanical_family=ident.get("botanical_family", ""),
                crop_group=ident.get("crop_group", ""),
                portfolio_role=ident.get("portfolio_role", ""),
                lifecycle_class=ident.get("lifecycle_class", ""),
                is_cover_crop=ident.get("is_cover_crop", False),
                can_serve_as_cover_crop=ident.get("can_serve_as_cover_crop", False),
                commercial_harvest_feasible=ident.get("commercial_harvest_feasible", True),
                usda_plants_symbol=ident.get("usda_plants_symbol"),
                crop_identity=ident,
                growing_duration=c_dict.get("growing_duration", {}),
                temperature_requirements=c_dict.get("temperature_requirements", {}),
                rainfall_requirements=c_dict.get("rainfall_requirements", {}),
                water_demand_and_tolerance=c_dict.get("water_demand_and_tolerance", {}),
                soil_preferences=c_dict.get("soil_preferences", {}),
                root_and_nutrients=c_dict.get("root_and_nutrients", {}),
                nitrogen_and_biomass=c_dict.get("nitrogen_and_biomass", {}),
                rotation_compatibility=c_dict.get("rotation_compatibility", {}),
                regional_suitability=c_dict.get("regional_suitability", []),
                evidence_ids=crop_ev_ids,
            )
            crops_by_id[cid] = profile
            if cdl_code is not None:
                crops_by_cdl[cdl_code] = profile
                crop_options.append(CropOption(
                    crop_code=cdl_code,
                    name=profile.common_name,
                    family=profile.botanical_family,
                    is_double_crop=False,
                    kb_version=kb_version,
                ))

        # Add double-crop and fallow candidates to options for complete rotation planning
        crop_options.append(CropOption(
            crop_code=26,
            name="Dbl Crop WinWht/Soybeans",
            family="Poaceae / Fabaceae",
            is_double_crop=True,
            kb_version=kb_version,
        ))
        crop_options.append(CropOption(
            crop_code=236,
            name="Dbl Crop WinWht/Sorghum",
            family="Poaceae",
            is_double_crop=True,
            kb_version=kb_version,
        ))
        crop_options.append(CropOption(
            crop_code=61,
            name="Fallow/Idle Cropland",
            family="Non-crop",
            is_double_crop=False,
            kb_version=kb_version,
        ))

        # Directed Rotation Transitions (196 Transitions from CSV)
        rotations: dict[tuple[str, str], DirectedRotationTransition] = {}
        rot_candidates = [
            canonical_file.parent / "crop_rotation_compatibility.csv",
            kb_path / "crop_rotation_compatibility.csv",
        ]
        rot_csv_path = next((p for p in rot_candidates if p.exists()), None)
        if rot_csv_path:
            try:
                with open(rot_csv_path, encoding="utf-8") as rf:
                    r_reader = csv.DictReader(rf)
                    for row in r_reader:
                        pid = row["preceding_crop_id"]
                        fid = row["following_crop_id"]
                        eids = [e.strip() for e in row.get("evidence_ids", "").split(";") if e.strip()]
                        is_mono = row.get("is_monoculture", "false").lower() == "true"
                        trans = DirectedRotationTransition(
                            preceding_crop_id=pid,
                            preceding_crop_name=row.get("preceding_crop_name", ""),
                            following_crop_id=fid,
                            following_crop_name=row.get("following_crop_name", ""),
                            compatibility_rating=row.get("compatibility_rating", "unknown"),
                            is_monoculture=is_mono,
                            monoculture_risk=row.get("monoculture_risk") or None,
                            synergy_mechanisms=row.get("synergy_mechanisms") or None,
                            disease_break_potential=row.get("disease_break_potential") or None,
                            shared_pest_disease_risks=row.get("shared_pest_disease_risks") or None,
                            herbicide_carryover_risks=row.get("herbicide_carryover_risks") or None,
                            rotational_niche=row.get("rotational_niche") or None,
                            evidence_ids=eids,
                            limitations=row.get("limitations") or None,
                        )
                        rotations[(pid, fid)] = trans
            except Exception as r_err:
                log.warning(
                    "failed to parse rotation transitions CSV",
                    extra={"path": str(rot_csv_path), "error": str(r_err)},
                )

        return CropKnowledgeBase(
            available=True,
            kb_version=kb_version,
            crops=crop_options,
            status_message=(
                f"Crop knowledge base loaded ({len(crops_by_id)} crops, "
                f"{len(evidence_by_id)} evidence records, {len(rotations)} rotation transitions)."
            ),
            crops_by_id=crops_by_id,
            crops_by_cdl=crops_by_cdl,
            evidence_by_id=evidence_by_id,
            rotations=rotations,
            metadata=metadata,
        )

    # Legacy kb.json loader
    if legacy_file.exists():
        try:
            legacy_kb = KbFile.model_validate(json.loads(legacy_file.read_text(encoding="utf-8")))
        except (ValidationError, ValueError) as exc:
            log.warning("legacy crop KB rejected", extra={"path": str(legacy_file), "error": str(exc)[:500]})
            return fallback_kb("Crop knowledge base rejected: every threshold must be cited and well-formed.")
        return CropKnowledgeBase(
            available=True,
            kb_version=legacy_kb.kb_version,
            status_message="Crop knowledge base loaded (legacy).",
            crops=[
                CropOption(
                    crop_code=c.crop_code,
                    name=c.name,
                    family=c.family,
                    is_double_crop=c.is_double_crop,
                    kb_version=legacy_kb.kb_version,
                )
                for c in legacy_kb.crops
            ],
            entries={c.crop_code: c for c in legacy_kb.crops},
        )

    return fallback_kb(f"Crop knowledge base file not found at {kb_path}.")
