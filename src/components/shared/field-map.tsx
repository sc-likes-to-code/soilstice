"use client";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GeoJSONSource, Map as MlMap, MapMouseEvent, StyleSpecification } from "maplibre-gl";
import { Layers, MapPin, Satellite } from "lucide-react";
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

export type BasemapMode = "satellite" | "topo";

const ESRI_SATELLITE_TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const CARTO_VOYAGER_TILES = "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png";

const BASE_MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    satellite: {
      type: "raster",
      tiles: [ESRI_SATELLITE_TILES],
      tileSize: 256,
      attribution: "Esri, Maxar, Earthstar",
      maxzoom: 19,
    },
    topo: {
      type: "raster",
      tiles: [CARTO_VOYAGER_TILES],
      tileSize: 256,
      attribution: "OpenStreetMap, CARTO",
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: "topo-tiles",
      type: "raster",
      source: "topo",
      paint: { "raster-opacity": 1 },
      layout: { visibility: "none" },
    },
    {
      id: "satellite-tiles",
      type: "raster",
      source: "satellite",
      paint: { "raster-opacity": 1 },
      layout: { visibility: "visible" },
    },
  ],
};

function bboxPolygon([w, s, e, n]: Bbox): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: [
            [w, s],
            [e, s],
            [e, n],
            [w, n],
            [w, s],
          ],
        },
      },
    ],
  };
}

/**
 * Enhanced MapLibre field map with dual raster basemaps (Esri World Imagery satellite + Carto Topo)
 * and interactive layer switching.
 */
export function FieldMap({
  fields,
  selectedId,
  onSelect,
  colorBy = "band",
  height = 420,
  className,
  aoiBbox,
  draft,
  onMapClick,
  drawing,
  focusId,
  caption,
  initialBasemap = "satellite",
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
  initialBasemap?: BasemapMode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const lastFit = useRef<{ b: [[number, number], [number, number]]; padding: number; maxZoom: number } | null>(null);
  const [ready, setReady] = useState(false);
  const [hover, setHover] = useState<{ name: string; x: number; y: number } | null>(null);
  const [failed, setFailed] = useState(false);
  const [basemap, setBasemap] = useState<BasemapMode>(initialBasemap);

  const handlers = useRef({ onSelect, onMapClick, drawing });
  useEffect(() => {
    handlers.current = { onSelect, onMapClick, drawing };
  }, [onSelect, onMapClick, drawing]);

  const fc = useMemo<GeoJSON.FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: fields.map((f) => ({
        type: "Feature",
        id: f.field_id,
        properties: {
          id: f.field_id,
          name: f.name,
          color:
            colorBy === "crop"
              ? cropColor(f.crop)
              : colorBy === "band"
                ? BAND_STYLE[f.band ?? "unknown"].fill
                : "#34d399",
          selected: f.field_id === selectedId ? 1 : 0,
          muted: f.muted ? 1 : 0,
        },
        geometry: f.geometry,
      })),
    }),
    [fields, colorBy, selectedId],
  );

  const extent = useMemo<Bbox | null>(() => (fields.length ? bboxOf(fields.map((f) => f.geometry)) : aoiBbox ?? null), [fields, aoiBbox]);

  // Switch basemap layer visibility
  const toggleBasemap = (mode: BasemapMode) => {
    setBasemap(mode);
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setLayoutProperty("satellite-tiles", "visibility", mode === "satellite" ? "visible" : "none");
    map.setLayoutProperty("topo-tiles", "visibility", mode === "topo" ? "visible" : "none");
  };

  // Create map once
  useEffect(() => {
    let cancelled = false;
    let map: MlMap | null = null;

    (async () => {
      try {
        const ml = (await import("maplibre-gl")).default;
        if (cancelled || !ref.current) return;

        map = new ml.Map({
          container: ref.current,
          style: BASE_MAP_STYLE,
          center: [-98.06, 37.95],
          zoom: 11,
          attributionControl: false,
          dragRotate: false,
          pitchWithRotate: false,
        });

        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        map.addControl(new ml.AttributionControl({ compact: true }), "bottom-right");
        mapRef.current = map;

        map.on("load", () => {
          if (!map) return;

          // Sources
          map.addSource("aoi", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addSource("fields", { type: "geojson", data: { type: "FeatureCollection", features: [] }, promoteId: "id" });
          map.addSource("draft", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

          // AOI dashed boundary
          map.addLayer({
            id: "aoi",
            type: "line",
            source: "aoi",
            paint: {
              "line-color": "#f59e0b",
              "line-width": 2,
              "line-dasharray": [3, 2],
            },
          });

          // Field Fill
          map.addLayer({
            id: "fields-fill",
            type: "fill",
            source: "fields",
            paint: {
              "fill-color": ["get", "color"],
              "fill-opacity": [
                "case",
                ["==", ["get", "selected"], 1],
                0.68,
                ["boolean", ["feature-state", "hover"], false],
                0.58,
                ["==", ["get", "muted"], 1],
                0.18,
                0.46,
              ],
            },
          });

          // Field Outline
          map.addLayer({
            id: "fields-line",
            type: "line",
            source: "fields",
            paint: {
              "line-color": [
                "case",
                ["==", ["get", "selected"], 1],
                "#ffffff",
                ["boolean", ["feature-state", "hover"], false],
                "#fbbf24",
                "#10b981",
              ],
              "line-width": [
                "case",
                ["==", ["get", "selected"], 1],
                3.2,
                ["boolean", ["feature-state", "hover"], false],
                2.6,
                1.6,
              ],
            },
          });

          // Draft polygon styling
          map.addLayer({
            id: "draft-fill",
            type: "fill",
            source: "draft",
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: { "fill-color": "#eab308", "fill-opacity": 0.35 },
          });
          map.addLayer({
            id: "draft-line",
            type: "line",
            source: "draft",
            filter: ["!=", ["geometry-type"], "Point"],
            paint: { "line-color": "#facc15", "line-width": 2.5, "line-dasharray": [2, 1.5] },
          });
          map.addLayer({
            id: "draft-pts",
            type: "circle",
            source: "draft",
            filter: ["==", ["geometry-type"], "Point"],
            paint: {
              "circle-radius": 5.5,
              "circle-color": "#ffffff",
              "circle-stroke-color": "#d97706",
              "circle-stroke-width": 2.5,
            },
          });

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
          if (lastFit.current) {
            map.fitBounds(lastFit.current.b, {
              padding: lastFit.current.padding,
              maxZoom: lastFit.current.maxZoom,
              duration: 0,
            });
          }
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

  // Update GeoJSON data
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("fields") as GeoJSONSource)?.setData(fc);
    (map.getSource("aoi") as GeoJSONSource)?.setData(aoiBbox ? bboxPolygon(aoiBbox) : { type: "FeatureCollection", features: [] });
  }, [ready, fc, aoiBbox]);

  // Fit bounds when fields or focus change
  const fitKey = `${fields.map((f) => f.field_id).join(",")}|${focusId ?? ""}`;
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const focus = focusId ? fields.find((f) => f.field_id === focusId) : null;
    const b = focus ? bboxOf(focus.geometry) : extent;
    if (!b) return;
    const fit = {
      b: [
        [b[0], b[1]],
        [b[2], b[3]],
      ] as [[number, number], [number, number]],
      padding: focus ? 80 : 44,
      maxZoom: focus ? 14.5 : 14,
    };
    lastFit.current = fit;
    map.resize();
    map.fitBounds(fit.b, { padding: fit.padding, maxZoom: fit.maxZoom, duration: 400 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, fitKey]);

  // Draft polygon updates
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const pts = draft ?? [];
    const features: GeoJSON.Feature[] = pts.map((p) => ({
      type: "Feature",
      properties: {},
      geometry: { type: "Point", coordinates: p },
    }));
    if (pts.length >= 3) {
      features.push({
        type: "Feature",
        properties: {},
        geometry: { type: "Polygon", coordinates: [[...pts, pts[0]]] },
      });
    } else if (pts.length === 2) {
      features.push({
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: pts },
      });
    }
    (map.getSource("draft") as GeoJSONSource)?.setData({ type: "FeatureCollection", features });
    map.getCanvas().style.cursor = drawing ? "crosshair" : "";
    if (drawing) map.doubleClickZoom.disable();
    else map.doubleClickZoom.enable();
  }, [ready, draft, drawing]);

  return (
    <div className={cn("relative overflow-hidden rounded-xl border border-line bg-forest-950 shadow-inner", className)} style={{ height }}>
      <div ref={ref} className="h-full w-full" role="application" aria-label="Geospatial field map" />

      {/* Layer switcher */}
      <div className="absolute left-2.5 top-2.5 z-10 flex items-center gap-1 rounded-lg border border-line/80 bg-paper/95 p-0.5 shadow-md backdrop-blur-md">
        <button
          type="button"
          onClick={() => toggleBasemap("satellite")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11.5px] font-semibold transition-colors",
            basemap === "satellite"
              ? "bg-forest-800 text-white shadow-sm"
              : "text-ink-soft hover:bg-parchment hover:text-ink",
          )}
          title="Satellite imagery (Esri World Imagery)"
        >
          <Satellite className="h-3.5 w-3.5" />
          <span>Satellite</span>
        </button>
        <button
          type="button"
          onClick={() => toggleBasemap("topo")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11.5px] font-semibold transition-colors",
            basemap === "topo"
              ? "bg-forest-800 text-white shadow-sm"
              : "text-ink-soft hover:bg-parchment hover:text-ink",
          )}
          title="Topographic / street basemap (Carto)"
        >
          <Layers className="h-3.5 w-3.5" />
          <span>Topo</span>
        </button>
      </div>

      {!ready && !failed && <div className="skeleton absolute inset-0 rounded-none bg-forest-900/60" aria-hidden />}
      {failed && (
        <div className="absolute inset-0 grid place-items-center bg-paper/90 p-4 text-center text-[13px] text-ink-soft">
          Map could not be initialised (WebGL unavailable).
        </div>
      )}

      {hover && (
        <div
          className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[135%] rounded-md border border-line/50 bg-forest-950/95 px-2.5 py-1 text-[11.5px] font-semibold text-white shadow-xl backdrop-blur-sm"
          style={{ left: hover.x, top: hover.y }}
        >
          <div className="flex items-center gap-1">
            <MapPin className="h-3 w-3 text-emerald-400" />
            <span>{hover.name}</span>
          </div>
        </div>
      )}

      {caption && (
        <div className="pointer-events-none absolute bottom-2 left-2 z-10 rounded-md border border-line/60 bg-paper/90 px-2 py-1 text-[10.5px] font-medium text-stone-700 shadow-sm backdrop-blur">
          {caption}
        </div>
      )}
    </div>
  );
}
