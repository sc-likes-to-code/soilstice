"""Geometry utilities. Storage CRS EPSG:4326; areas and buffers computed in EPSG:5070 (PHASE_0 T3)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from app.catalog import AOIS, MAX_FIELD_HA, AoiDef
from app.contracts import GeoJSONMultiPolygon
from app.errors import FieldTooLarge, GeometryInvalid, OutsideAoi


@lru_cache(maxsize=16)
def transformer(src: str, dst: str) -> Transformer:
    return Transformer.from_crs(src, dst, always_xy=True)


def reproject(geom: BaseGeometry, src: str, dst: str) -> BaseGeometry:
    if src == dst:
        return geom
    return transform(transformer(src, dst).transform, geom)


def to_shapely(gj: GeoJSONMultiPolygon) -> MultiPolygon:
    return shape({"type": "MultiPolygon", "coordinates": gj.coordinates})


def to_geojson(geom: BaseGeometry) -> GeoJSONMultiPolygon:
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    m = mapping(geom)
    coords = [[[[float(x), float(y)] for x, y, *_ in ring] for ring in poly] for poly in m["coordinates"]]
    return GeoJSONMultiPolygon(type="MultiPolygon", coordinates=coords)


def area_ha(geom_4326: BaseGeometry) -> float:
    return reproject(geom_4326, "EPSG:4326", "EPSG:5070").area / 10_000.0


@dataclass(frozen=True)
class ValidatedGeometry:
    geom: MultiPolygon
    aoi: AoiDef
    area_ha: float
    centroid: tuple[float, float]


def validate_field_geometry(gj: GeoJSONMultiPolygon, aoi_id: str) -> ValidatedGeometry:
    """E8 validation: valid closed rings, lon/lat ranges, inside the farm AOI, <= 260 ha (T20)."""
    if not gj.coordinates:
        raise GeometryInvalid("Geometry has no polygons.")
    for poly in gj.coordinates:
        if not poly:
            raise GeometryInvalid("Polygon has no rings.")
        for ring in poly:
            if len(ring) < 4:
                raise GeometryInvalid("Each ring needs at least 4 positions (closed).")
            if any(len(p) < 2 for p in ring):
                raise GeometryInvalid("Positions must be [lon, lat].")
            if ring[0][:2] != ring[-1][:2]:
                raise GeometryInvalid("Rings must be closed (first position equals last).")
            for lon, lat, *_ in ring:
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise GeometryInvalid("Coordinates must be EPSG:4326 [lon, lat].")
    try:
        geom = to_shapely(gj)
    except Exception as exc:  # shapely raises various errors on degenerate input
        raise GeometryInvalid(f"Geometry could not be parsed: {exc}") from exc
    if not geom.is_valid:
        raise GeometryInvalid("Geometry is not valid (self-intersection or bad ring orientation).",
                              details={"reason": _invalid_reason(geom)})
    a = area_ha(geom)
    if a <= 0:
        raise GeometryInvalid("Geometry has zero area.")
    aoi = AOIS[aoi_id]
    if not box(*aoi.bbox).contains(geom):
        raise OutsideAoi(f"Field must lie inside {aoi.label}.", details={"aoi_id": aoi_id, "aoi_bbox": list(aoi.bbox)})
    if a > MAX_FIELD_HA:
        raise FieldTooLarge(f"Field area {a:.1f} ha exceeds the {MAX_FIELD_HA:.0f} ha limit.",
                            details={"area_ha": round(a, 2), "max_ha": MAX_FIELD_HA})
    c = geom.centroid
    return ValidatedGeometry(geom=geom, aoi=aoi, area_ha=a, centroid=(round(c.x, 6), round(c.y, 6)))


def _invalid_reason(geom: BaseGeometry) -> str:
    from shapely.validation import explain_validity

    return explain_validity(geom)


def inward_buffer_5070(geom_4326: BaseGeometry, metres: float) -> tuple[BaseGeometry, bool]:
    """15 m inward buffer in EPSG:5070 (DATA_ARCHITECTURE §5.2 step 4).
    Returns (geometry in EPSG:5070, buffer_applied). If < 50% of the area remains, the unbuffered polygon is used."""
    g = reproject(geom_4326, "EPSG:4326", "EPSG:5070")
    b = make_valid(g.buffer(-metres))
    if b.is_empty or b.area < 0.5 * g.area:
        return g, False
    return b, True
