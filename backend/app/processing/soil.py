"""SSURGO aggregation to a field SoilProfile — DATA_ARCHITECTURE §5.3.1 (method `ssurgo_area_comppct_weighting` v1).

Implemented as written in §5.3.1:
 1. area_fraction per mukey from locally measured EPSG:5070 areas of SDA clipped geometries;
 2. major components only, component weight w = area_fraction * comppct_r / 100;
 3. fixed depth intervals 0–30, 30–100, 100–150 cm; overlap-thickness weighting; a component interval value exists
    only if horizons with a non-null value cover >= 80 % of the interval thickness;
 4. continuous properties = Σ(w·v) / Σ(w over non-null); _l/_h aggregated the same way -> uncertainty "range";
    pH averaged arithmetically (documented simplification);
 5. texture class from the aggregated sand/silt/clay (USDA triangle);
 6. categorical (drainage, hydrologic group): class with largest summed w, with its weight_share;
 7. AWS 0–100 / 0–150 from muaggatt aws0100wta / aws0150wta, area-weighted across map units;
 8. quality: null_weight_fraction > 0.2 -> partial; > 0.5 -> missing with INSUFFICIENT_COVERAGE.

PROVISIONAL (requires team approval; handover §3.3 / D1): §5.3.1 does not define the denominator of
null_weight_fraction. This module uses: nominal weight = w; a major component with null comppct_r gets nominal
weight area_fraction / n_major_in_mapunit; map units without major components count their whole area_fraction as
null; null weight = nominal weight of null-comppct components + components with no 0–30 cm value for any core
property. The rule is surfaced in the MethodRef and as a quality flag on every profile.
Also PROVISIONAL: AWS / SSURGO slope are null (INSUFFICIENT_COVERAGE) when map units with a value cover < 50 % of
the field area (mirrors the §5.3.1 > 0.5 threshold; not stated in §5.3.1).
"""

from __future__ import annotations

from uuid import UUID

from app.catalog import SPATIAL, source_ref
from app.contracts import (
    ClassValue,
    MethodRef,
    QualityFlag,
    QualityInfo,
    Quantity,
    SoilComponentRef,
    SoilLayer,
    SoilMapUnitShare,
    SoilProfile,
    SurveyRef,
    Uncertainty,
)
from app.providers.ssurgo import SsurgoRaw

from .texture import usda_texture_class

INTERVALS: list[tuple[float, float]] = [(0, 30), (30, 100), (100, 150)]
COVERAGE_MIN = 0.8
# contract field -> (SSURGO horizon property, unit)
LAYER_PROPS = {
    "sand_pct": ("sandtotal", "percent"),
    "silt_pct": ("silttotal", "percent"),
    "clay_pct": ("claytotal", "percent"),
    "ph_h2o": ("ph1to1h2o", "pH"),
    "om_pct": ("om", "percent"),
    "awc": ("awc", "cm_cm-1"),
}

METHOD = MethodRef(
    method_id="ssurgo_area_comppct_weighting",
    name="SSURGO area × component-percent weighting",
    version="1",
    description=(
        "DATA_ARCHITECTURE §5.3.1: major components weighted by map-unit area fraction × comppct_r; fixed depth "
        "intervals 0–30/30–100/100–150 cm with an 80% horizon-coverage rule; _l/_h as ranges; texture from aggregated "
        "fractions (USDA triangle); categorical classes by largest weight; AWS from muaggatt. PROVISIONAL, pending "
        "team approval: the null_weight_fraction denominator (null-comppct components weighted area_fraction/n_major) "
        "and the 50%-area rule for AWS/slope."
    ),
    reference_url=None,
)

PROVISIONAL_FLAG = QualityFlag(
    code="PROVISIONAL_NULL_WEIGHT_RULE", severity="info",
    message="null_weight_fraction uses a provisional denominator rule that is not yet approved by the team "
            "(see method description).",
)
REPRESENTATIVE_VALUES_FLAG = QualityFlag(
    code="SSURGO_REPRESENTATIVE_VALUES", severity="info",
    message="SSURGO values are representative (_r) values for map-unit components, often estimated, not samples "
            "taken in this field. Ranges come from the _l/_h columns.",
)


def interval_value(horizons: list[dict], top: float, bottom: float, col: str) -> float | None:
    thickness = bottom - top
    covered = 0.0
    acc = 0.0
    for h in horizons:
        ht, hb, v = h.get("top"), h.get("bottom"), h.get(col)
        if ht is None or hb is None or v is None:
            continue
        overlap = max(0.0, min(hb, bottom) - max(ht, top))
        if overlap > 0:
            covered += overlap
            acc += overlap * v
    if covered < COVERAGE_MIN * thickness or covered == 0:
        return None
    return acc / covered


def _wmean(pairs: list[tuple[float, float | None]]) -> float | None:
    num = sum(w * v for w, v in pairs if v is not None and w > 0)
    den = sum(w for w, v in pairs if v is not None and w > 0)
    return num / den if den > 0 else None


def aggregate_soil(field_id: UUID, raw: SsurgoRaw) -> SoilProfile:
    total_area = sum(raw.mapunit_area_m2.values())
    af = {mk: a / total_area for mk, a in raw.mapunit_area_m2.items()}
    comps_by_mu: dict[str, list[dict]] = {}
    for c in raw.components:
        if c["mukey"] in af:
            comps_by_mu.setdefault(c["mukey"], []).append(c)

    weights: dict[str, float] = {}  # cokey -> w (0 for null comppct)
    nominal_total = 0.0
    null_weight = 0.0
    for mk, frac in af.items():
        majors = comps_by_mu.get(mk, [])
        if not majors:
            nominal_total += frac
            null_weight += frac
            continue
        for c in majors:
            if c["comppct_r"] is None:
                nominal = frac / len(majors)
                weights[c["cokey"]] = 0.0
                null_weight += nominal
            else:
                nominal = frac * c["comppct_r"] / 100.0
                weights[c["cokey"]] = nominal
                hz = raw.horizons.get(c["cokey"], [])
                has_any = any(interval_value(hz, 0, 30, f"{p}_r") is not None for p, _ in LAYER_PROPS.values())
                if not has_any:
                    null_weight += nominal
            nominal_total += nominal
    nwf = null_weight / nominal_total if nominal_total > 0 else 1.0
    insufficient = nwf > 0.5

    layers: list[SoilLayer] = []
    for top, bottom in INTERVALS:
        vals: dict[str, Quantity] = {}
        agg_r: dict[str, float | None] = {}
        for fld, (prop, unit) in LAYER_PROPS.items():
            per = {s: _wmean([(weights.get(c["cokey"], 0.0),
                               interval_value(raw.horizons.get(c["cokey"], []), top, bottom, f"{prop}_{s}"))
                              for c in raw.components if c["mukey"] in af]) for s in ("l", "r", "h")}
            v = None if insufficient else per["r"]
            agg_r[fld] = v
            if v is None:
                vals[fld] = Quantity(value=None, unit=unit, missing_reason="INSUFFICIENT_COVERAGE")
            else:
                unc = (Uncertainty(kind="range", low=round(per["l"], 4), high=round(per["h"], 4),
                                   note="SSURGO _l/_h aggregated with the same weights")
                       if per["l"] is not None and per["h"] is not None else None)
                vals[fld] = Quantity(value=round(v, 4), unit=unit, uncertainty=unc)
        layers.append(SoilLayer(
            top_cm=top, bottom_cm=bottom, texture_class=usda_texture_class(agg_r["sand_pct"], agg_r["silt_pct"],
                                                                           agg_r["clay_pct"]),
            **vals,
        ))

    def categorical(key: str) -> ClassValue:
        sums: dict[str, float] = {}
        for c in raw.components:
            w = weights.get(c["cokey"], 0.0)
            v = c.get(key)
            if v and w > 0 and c["mukey"] in af:
                sums[str(v)] = sums.get(str(v), 0.0) + w
        if not sums:
            return ClassValue(value=None, weight_share=None, missing_reason="INSUFFICIENT_COVERAGE")
        best = max(sums, key=sums.get)
        return ClassValue(value=best, weight_share=round(sums[best] / sum(sums.values()), 4), missing_reason=None)

    def mu_weighted(col: str, unit: str) -> Quantity:
        pairs = [(frac, (raw.muaggatt.get(mk) or {}).get(col)) for mk, frac in af.items()]
        covered = sum(f for f, v in pairs if v is not None)
        v = _wmean(pairs)
        if v is None or covered < 0.5:
            return Quantity(value=None, unit=unit, missing_reason="INSUFFICIENT_COVERAGE")
        return Quantity(value=round(v, 3), unit=unit)

    flags = [REPRESENTATIVE_VALUES_FLAG, PROVISIONAL_FLAG]
    if insufficient:
        status, reason = "missing", "INSUFFICIENT_COVERAGE"
        flags.append(QualityFlag(code="NULL_WEIGHT_HIGH", severity="critical",
                                 message=f"{nwf:.0%} of component weight has no usable horizon data (> 50%)."))
    elif nwf > 0.2:
        status, reason = "partial", None
        flags.append(QualityFlag(code="NULL_WEIGHT_ELEVATED", severity="warning",
                                 message=f"{nwf:.0%} of component weight has no usable horizon data (> 20%)."))
    else:
        status, reason = "valid", None

    survey_txt = "; ".join(f"{a} saverest {d.isoformat() if d else 'unknown'}" for a, d in raw.surveys) or "unknown"
    version_str = f"SDA live database ({survey_txt})"
    seen_sources = set()
    sources = []
    for a in raw.acquisitions:
        key = (DATASET_ID_SSURGO, version_str)
        if key not in seen_sources:
            seen_sources.add(key)
            sources.append(source_ref(DATASET_ID_SSURGO, product="SSURGO via Soil Data Access",
                                      version=version_str, acquisition_id=a.acquisition_id,
                                      retrieved_at=a.retrieved_at))
    map_units = [
        SoilMapUnitShare(
            mukey=mk, muname=raw.mapunit_names.get(mk, ""), area_fraction=round(frac, 6),
            major_components=[SoilComponentRef(cokey=c["cokey"], compname=c["compname"], comppct_r=c["comppct_r"])
                              for c in comps_by_mu.get(mk, [])],
        )
        for mk, frac in sorted(af.items(), key=lambda kv: -kv[1])
    ]
    return SoilProfile(
        field_id=field_id, layers=layers,
        aws_0_100=mu_weighted("aws0100wta", "cm"), aws_0_150=mu_weighted("aws0150wta", "cm"),
        drainage_class=categorical("drainagecl"), hydrologic_group=categorical("hydgrp"),
        slope_pct_ssurgo=mu_weighted("slopegradwta", "percent"),
        map_units=map_units, survey=[SurveyRef(areasymbol=a, saverest=d) for a, d in raw.surveys],
        method=METHOD, null_weight_fraction=round(nwf, 4), spatial=SPATIAL[DATASET_ID_SSURGO], sources=sources,
        quality=QualityInfo(status=status, flags=flags, completeness=round(1 - nwf, 4), missing_reason=reason),
    )


DATASET_ID_SSURGO = "usda_nrcs_ssurgo_sda"
