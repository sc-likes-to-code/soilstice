"use client";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GeoJSONSource, Map as MlMap, MapMouseEvent, StyleSpecification } from "maplibre-gl";
import type { GeoJSONMultiPolygon, ScoreBand, CropCode } from "@/types/contracts";
import { BAND_STYLE, cropColor } from "@/lib/vocab";
import { bboxOf, type Bbox, type LngLat } from "@/lib/geo";
import { cn } from "@/lib/cn";

export interface MapField {
  field_id: string;
  name: string;
  geometry: GeoJSONMultiPolygon;
  band?: ScoreBand;
  crop?: CropCode | null;
  muted?: boolean;
}

const BLANK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#efe8da" } }],
};

const MILE_DEG_LAT = 1609.34 / 110540;

function sectionGrid(b: Bbox) {
  const [w, s, e, n] = b;
  const lat = (s + n) / 2;
  const dLon = 1609.34 / (111320 * Math.cos((lat * Math.PI) / 180));
  const lines: GeoJSON.Feature<GeoJSON.LineString>[] = [];
  const pad = 14;
  for (let x = w - pad * dLon; x <= e + pad * dLon; x += dLon) lines.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[x, s - pad * MILE_DEG_LAT], [x, n + pad * MILE_DEG_LAT]] } });
  for (let y = s - pad * MILE_DEG_LAT; y <= n + pad * MILE_DEG_LAT; y += MILE_DEG_LAT) lines.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[w - pad * dLon, y], [e + pad * dLon, y]] } });
  return { type: "FeatureCollection" as const, features: lines };
}

function bboxPolygon([w, s, e, n]: Bbox): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[w, s], [e, s], [e, n], [w, n], [w, s]] } }] };
}

/**
 * MapLibre field map. No basemap tiles in Phase 1 (U-UI-1): a schematic 1-mile section grid stands in.
 * Geometry shown in mock mode is synthetic.
 */
export function FieldMap({
  fields, selectedId, onSelect, colorBy = "band", height = 420, className, aoiBbox, draft, onMapClick, drawing, focusId, caption,
}: {
  fields: MapField[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  colorBy?: "band" | "crop" | "none";
  height?: number | string;
  className?: string;
  aoiBbox?: Bbox;
  draft?: LngLat[];
  onMapClick?: (p: LngLat) => void;
  drawing?: boolean;
  focusId?: string | null;
  caption?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const lastFit = useRef<{ b: [[number, number], [number, number]]; padding: number; maxZoom: number } | null>(null);
  const [ready, setReady] = useState(false);
  const [hover, setHover] = useState<{ name: string; x: number; y: number } | null>(null);
  const [failed, setFailed] = useState(false);
  const handlers = useRef({ onSelect, onMapClick, drawing });
  useEffect(() => {
    handlers.current = { onSelect, onMapClick, drawing };
  }, [onSelect, onMapClick, drawing]);

  const fc = useMemo<GeoJSON.FeatureCollection>(() => ({
    type: "FeatureCollection",
    features: fields.map((f) => ({
      type: "Feature",
      id: f.field_id,
      properties: {
        id: f.field_id,
        name: f.name,
        color: colorBy === "crop" ? cropColor(f.crop) : colorBy === "band" ? BAND_STYLE[f.band ?? "unknown"].fill : "#74a07a",
        selected: f.field_id === selectedId ? 1 : 0,
        muted: f.muted ? 1 : 0,
      },
      geometry: f.geometry,
    })),
  }), [fields, colorBy, selectedId]);

  const extent = useMemo<Bbox | null>(() => (fields.length ? bboxOf(fields.map((f) => f.geometry)) : aoiBbox ?? null), [fields, aoiBbox]);

  // create map once
  useEffect(() => {
    let cancelled = false;
    let map: MlMap | null = null;
    (async () => {
      try {
        const ml = (await import("maplibre-gl")).default;
        if (cancelled || !ref.current) return;
        map = new ml.Map({ container: ref.current, style: BLANK_STYLE, center: [-98.06, 37.95], zoom: 11, attributionControl: false, dragRotate: false, pitchWithRotate: false });
        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        map.addControl(new ml.AttributionControl({ compact: true }));
        mapRef.current = map;
        map.on("load", () => {
          if (!map) return;
          map.addSource("grid", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addSource("aoi", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addSource("fields", { type: "geojson", data: { type: "FeatureCollection", features: [] }, promoteId: "id" });
          map.addSource("draft", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addLayer({ id: "grid", type: "line", source: "grid", paint: { "line-color": "#d6ccb6", "line-width": 1 } });
          map.addLayer({ id: "aoi", type: "line", source: "aoi", paint: { "line-color": "#6f5141", "line-width": 1.4, "line-dasharray": [3, 3] } });
          map.addLayer({
            id: "fields-fill", type: "fill", source: "fields",
            paint: {
              "fill-color": ["get", "color"],
              "fill-opacity": ["case", ["==", ["get", "selected"], 1], 0.78, ["boolean", ["feature-state", "hover"], false], 0.66, ["==", ["get", "muted"], 1], 0.22, 0.62],
            },
          });
          map.addLayer({
            id: "fields-line", type: "line", source: "fields",
            paint: { "line-color": ["case", ["==", ["get", "selected"], 1], "#0e1d15", "#284e36"], "line-width": ["case", ["==", ["get", "selected"], 1], 2.6, 1.1] },
          });
          map.addLayer({ id: "draft-fill", type: "fill", source: "draft", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#c99a3e", "fill-opacity": 0.25 } });
          map.addLayer({ id: "draft-line", type: "line", source: "draft", filter: ["!=", ["geometry-type"], "Point"], paint: { "line-color": "#a87a24", "line-width": 2, "line-dasharray": [2, 1.5] } });
          map.addLayer({ id: "draft-pts", type: "circle", source: "draft", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 4.5, "circle-color": "#fbf8f2", "circle-stroke-color": "#a87a24", "circle-stroke-width": 2 } });

          let hoveredId: string | number | undefined;
          map.on("mousemove", "fields-fill", (e) => {
            const f = e.features?.[0];
            if (!f || !map) return;
            if (hoveredId !== undefined) map.setFeatureState({ source: "fields", id: hoveredId }, { hover: false });
            hoveredId = f.id;
            if (hoveredId !== undefined) map.setFeatureState({ source: "fields", id: hoveredId }, { hover: true });
            map.getCanvas().style.cursor = handlers.current.drawing ? "crosshair" : "pointer";
            setHover({ name: String(f.properties?.name ?? ""), x: e.point.x, y: e.point.y });
          });
          map.on("mouseleave", "fields-fill", () => {
            if (hoveredId !== undefined) map?.setFeatureState({ source: "fields", id: hoveredId }, { hover: false });
            hoveredId = undefined;
            if (map) map.getCanvas().style.cursor = handlers.current.drawing ? "crosshair" : "";
            setHover(null);
          });
          map.on("click", (e: MapMouseEvent) => {
            if (!map) return;
            if (handlers.current.drawing) {
              handlers.current.onMapClick?.([e.lngLat.lng, e.lngLat.lat]);
              return;
            }
            const hit = map.queryRenderedFeatures(e.point, { layers: ["fields-fill"] })[0];
            if (hit?.properties?.id) handlers.current.onSelect?.(String(hit.properties.id));
          });
          setReady(true);
        });
        const ro = new ResizeObserver(() => {
          if (!map) return;
          map.resize();
          // Re-apply the last fit once the container has its real size.
          if (lastFit.current) map.fitBounds(lastFit.current.b, { padding: lastFit.current.padding, maxZoom: lastFit.current.maxZoom, duration: 0 });
        });
        ro.observe(ref.current);
        map.once("remove", () => ro.disconnect());
      } catch {
        setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  // data updates
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("fields") as GeoJSONSource).setData(fc);
    if (extent) (map.getSource("grid") as GeoJSONSource).setData(sectionGrid(aoiBbox && fields.length === 0 ? aoiBbox : extent));
    (map.getSource("aoi") as GeoJSONSource).setData(aoiBbox ? bboxPolygon(aoiBbox) : { type: "FeatureCollection", features: [] });
  }, [ready, fc, extent, aoiBbox, fields.length]);

  // fit bounds when the field set or focus changes
  const fitKey = `${fields.map((f) => f.field_id).join(",")}|${focusId ?? ""}`;
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const focus = focusId ? fields.find((f) => f.field_id === focusId) : null;
    const b = focus ? bboxOf(focus.geometry) : extent;
    if (!b) return;
    const fit = { b: [[b[0], b[1]], [b[2], b[3]]] as [[number, number], [number, number]], padding: focus ? 90 : 48, maxZoom: focus ? 13.6 : 14 };
    lastFit.current = fit;
    map.resize();
    map.fitBounds(fit.b, { padding: fit.padding, maxZoom: fit.maxZoom, duration: 500 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, fitKey]);

  // draft polygon
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const pts = draft ?? [];
    const features: GeoJSON.Feature[] = pts.map((p) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: p } }));
    if (pts.length >= 3) features.push({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[...pts, pts[0]]] } });
    else if (pts.length === 2) features.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: pts } });
    (map.getSource("draft") as GeoJSONSource).setData({ type: "FeatureCollection", features });
    map.getCanvas().style.cursor = drawing ? "crosshair" : "";
    // Successive vertex clicks must not be read as a double-click zoom.
    if (drawing) map.doubleClickZoom.disable();
    else map.doubleClickZoom.enable();
  }, [ready, draft, drawing]);

  return (
    <div className={cn("relative overflow-hidden rounded-xl border border-line bg-parchment", className)} style={{ height }}>
      {/* maplibre's own CSS sets position:relative on the container, so size it explicitly */}
      <div ref={ref} className="h-full w-full" role="application" aria-label="Field map" />
      {!ready && !failed && <div className="skeleton absolute inset-0 rounded-none" aria-hidden />}
      {failed && <div className="absolute inset-0 grid place-items-center text-[13px] text-ink-soft">Map could not be initialised (WebGL unavailable).</div>}
      {hover && (
        <div className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[130%] rounded-md bg-forest-950 px-2 py-1 text-[11.5px] font-semibold text-forest-50 shadow-lg" style={{ left: hover.x, top: hover.y }}>
          {hover.name}
        </div>
      )}
      {caption && <div className="pointer-events-none absolute bottom-2 left-2 rounded-md bg-paper/85 px-2 py-1 text-[10.5px] font-medium text-stone-600 backdrop-blur">{caption}</div>}
    </div>
  );
}
