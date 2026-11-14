"""SSURGO via Soil Data Access provider (INTEGRATION_GUIDE §2; DATA_ARCHITECTURE §5.3.1). Acquisition + parsing.

Endpoint: POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest, body {"format": "JSON+COLUMNNAME",
"query": <T-SQL>}. No auth. Response {"Table": [[col names], [row], ...]}; a missing "Table" key means no rows.
Verified 2026-11-14 [LIVE]: every value is returned as a STRING (or null); `sacatalog.saverest` is formatted
"M/D/YYYY h:mm:ss AM/PM". Area fractions come from `~GetClippedMapunits~`; the returned WKT is reprojected to
EPSG:5070 and measured locally (STArea() is in degree^2 and is not used).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from shapely import wkt as shapely_wkt
from shapely.geometry.base import BaseGeometry

from app.processing.geometry import reproject
from app.repositories.records import AcquisitionRecord

from .http import HttpAcquirer, ProviderError

SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
DATASET_ID = "usda_nrcs_ssurgo_sda"
SDA_TIMEOUT_S = 120.0

HORIZON_PROPS = ["sandtotal", "silttotal", "claytotal", "om", "ph1to1h2o", "awc"]


@dataclass
class SsurgoRaw:
    mapunit_area_m2: dict[str, float]
    mapunit_names: dict[str, str]
    components: list[dict]  # major components only
    horizons: dict[str, list[dict]]  # cokey -> horizons
    muaggatt: dict[str, dict]
    surveys: list[tuple[str, date | None]]
    acquisitions: list[AcquisitionRecord] = field(default_factory=list)


def parse_table(doc: dict) -> list[dict]:
    """JSON+COLUMNNAME -> list of row dicts. Missing 'Table' => no rows."""
    table = doc.get("Table") if isinstance(doc, dict) else None
    if not table:
        return []
    cols = table[0]
    return [dict(zip(cols, row, strict=False)) for row in table[1:]]


def to_float(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_saverest(v) -> date | None:
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _mukey_list(mukeys: list[str]) -> str:
    safe = [m for m in mukeys if re.fullmatch(r"\d+", m)]
    if not safe:
        raise ProviderError("No valid mukeys to query.", "NO_DATA_SOURCE")
    return ",".join(f"'{m}'" for m in safe)


def clip_query(field_wkt: str) -> str:
    return (
        "~DeclareGeometry(@aoi)~\n"
        f"SELECT @aoi = geometry::STPolyFromText('{field_wkt}', 4326);\n"
        "~DeclareIdGeomTable(@int)~\n"
        "~GetClippedMapunits(@aoi,polygon,geo,@int)~\n"
        "SELECT id AS mukey, geom.STAsText() AS wkt FROM @int"
    )


def component_query(mukeys: list[str]) -> str:
    hcols = ", ".join(f"h.{p}_{s}" for p in HORIZON_PROPS for s in ("l", "r", "h"))
    return (
        "SELECT mu.mukey, mu.muname, c.cokey, c.compname, c.comppct_r, c.majcompflag, c.drainagecl, c.hydgrp, "
        f"h.chkey, h.hzdept_r, h.hzdepb_r, {hcols} "
        "FROM mapunit mu "
        "LEFT JOIN component c ON c.mukey = mu.mukey AND c.majcompflag = 'Yes' "
        "LEFT JOIN chorizon h ON h.cokey = c.cokey "
        f"WHERE mu.mukey IN ({_mukey_list(mukeys)}) "
        "ORDER BY mu.mukey, c.comppct_r DESC, h.hzdept_r"
    )


def muaggatt_query(mukeys: list[str]) -> str:
    return ("SELECT mukey, aws0100wta, aws0150wta, drclassdcd, hydgrpdcd, slopegradwta FROM muaggatt "
            f"WHERE mukey IN ({_mukey_list(mukeys)})")


def survey_query(mukeys: list[str]) -> str:
    return ("SELECT DISTINCT l.areasymbol, sc.saverest FROM mapunit mu JOIN legend l ON l.lkey = mu.lkey "
            f"JOIN sacatalog sc ON sc.areasymbol = l.areasymbol WHERE mu.mukey IN ({_mukey_list(mukeys)})")


def mapunit_areas_from_clip(rows: list[dict]) -> dict[str, float]:
    """Sum clipped geometry areas per mukey in EPSG:5070 (several rows may share one mukey)."""
    areas: dict[str, float] = {}
    for r in rows:
        mk, w = str(r.get("mukey") or ""), r.get("wkt")
        if not mk or not w:
            continue
        g: BaseGeometry = shapely_wkt.loads(w)
        areas[mk] = areas.get(mk, 0.0) + reproject(g, "EPSG:4326", "EPSG:5070").area
    return {k: v for k, v in areas.items() if v > 0}


class SsurgoClient:
    dataset_id = DATASET_ID

    def __init__(self, http: HttpAcquirer):
        self.http = http

    def _query(self, sql: str):
        fetched = self.http.fetch(DATASET_ID, "POST", SDA_URL, json_body={"format": "JSON+COLUMNNAME", "query": sql},
                                  timeout=SDA_TIMEOUT_S, retry_on_5xx=False)
        try:
            doc = fetched.json()
        except ValueError as exc:
            raise ProviderError(f"SDA returned a non-JSON response: {fetched.text[:200]}") from exc
        return parse_table(doc), fetched.acquisition

    def fetch_for_polygon(self, geom_4326: BaseGeometry) -> SsurgoRaw:
        from shapely.geometry import MultiPolygon

        # The clip macro takes a POLYGON; process each part of a multipolygon and merge areas.
        parts = list(geom_4326.geoms) if isinstance(geom_4326, MultiPolygon) else [geom_4326]
        acqs: list[AcquisitionRecord] = []
        clip_rows: list[dict] = []
        for part in parts:
            rows, acq = self._query(clip_query(shapely_wkt.dumps(part, rounding_precision=6)))
            clip_rows.extend(rows)
            acqs.append(acq)
        areas = mapunit_areas_from_clip(clip_rows)
        if not areas:
            raise ProviderError("No SSURGO map units intersect the field polygon.", "NO_DATA_SOURCE")
        mukeys = sorted(areas)
        comp_rows, a2 = self._query(component_query(mukeys))
        agg_rows, a3 = self._query(muaggatt_query(mukeys))
        sv_rows, a4 = self._query(survey_query(mukeys))
        acqs += [a2, a3, a4]

        names: dict[str, str] = {}
        comps: dict[str, dict] = {}
        horizons: dict[str, list[dict]] = {}
        for r in comp_rows:
            mk = str(r["mukey"])
            names[mk] = r.get("muname") or ""
            ck = r.get("cokey")
            if not ck:
                continue  # map unit without major components (e.g. water)
            ck = str(ck)
            if ck not in comps:
                comps[ck] = {
                    "mukey": mk, "cokey": ck, "compname": r.get("compname") or "",
                    "comppct_r": to_float(r.get("comppct_r")), "drainagecl": r.get("drainagecl"),
                    "hydgrp": r.get("hydgrp"),
                }
            if r.get("chkey"):
                h = {"top": to_float(r.get("hzdept_r")), "bottom": to_float(r.get("hzdepb_r"))}
                for p in HORIZON_PROPS:
                    for s in ("l", "r", "h"):
                        h[f"{p}_{s}"] = to_float(r.get(f"{p}_{s}"))
                horizons.setdefault(ck, []).append(h)
        muagg = {str(r["mukey"]): {k: (to_float(v) if k in ("aws0100wta", "aws0150wta", "slopegradwta") else v)
                                   for k, v in r.items()} for r in agg_rows}
        surveys = sorted({(str(r["areasymbol"]), parse_saverest(r.get("saverest"))) for r in sv_rows},
                         key=lambda x: x[0])
        return SsurgoRaw(mapunit_area_m2=areas, mapunit_names=names, components=list(comps.values()),
                         horizons=horizons, muaggatt=muagg, surveys=surveys, acquisitions=acqs)
