import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// @ts-ignore: Vite query import
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
maplibregl.setWorkerUrl(workerUrl);

type Aoi = { r0: number; r1: number; c0: number; c1: number };

type Props = {
  nlat: number;
  nlon: number;
  step: number;
  box: number[];
  cellTotals: number[];
  cellMax: number;
  aoi: Aoi;
  onAoi: (a: Aoi) => void;
  label: string;
};

// Viridis: perceptually uniform and colour-blind safe (same ramp as the calendar)
const STOPS = ["#440154", "#472d7b", "#3b528b", "#2c728e", "#21908d", "#27ad81", "#5cc863", "#aadc32", "#fde725"];

// Public vector style, no API key (OpenFreeMap, OpenStreetMap data).
const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";

// Smooth view: heatmap strength. If the smooth map looks washed out, raise it (e.g. 0.5);
// if most of it is saturated yellow, lower it (e.g. 0.2).
const HEAT_INTENSITY = 0.3;

// Offline fallback: plain background so the data layers always draw.
const FALLBACK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#dbe4ee" } }],
};

function rgb(h: string): [number, number, number] {
  return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
}

function ramp(t: number): string {
  const x = Math.min(1, Math.max(0, t)) * (STOPS.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const a = rgb(STOPS[i]);
  const b = rgb(STOPS[Math.min(i + 1, STOPS.length - 1)]);
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

function cellsGeoJson(box: number[], step: number, nlat: number, nlon: number, totals: number[], max: number) {
  const feats = [];
  for (let i = 0; i < nlat * nlon; i++) {
    const r = Math.floor(i / nlon);
    const c = i % nlon;
    const x0 = box[0] + c * step;
    const y0 = box[1] + r * step;
    const x1 = x0 + step;
    const y1 = y0 + step;
    const v = totals[i] ?? 0;
    feats.push({
      type: "Feature" as const,
      properties: { v, color: ramp(Math.sqrt(v / Math.max(1, max))) },
      geometry: { type: "Polygon" as const, coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] },
    });
  }
  return { type: "FeatureCollection" as const, features: feats };
}

function pointsGeoJson(box: number[], step: number, nlat: number, nlon: number, totals: number[], max: number) {
  const feats = [];
  for (let i = 0; i < nlat * nlon; i++) {
    const v = totals[i] ?? 0;
    if (v <= 0) continue;
    const r = Math.floor(i / nlon);
    const c = i % nlon;
    feats.push({
      type: "Feature" as const,
      properties: { w: Math.sqrt(v / Math.max(1, max)) },
      geometry: { type: "Point" as const, coordinates: [box[0] + (c + 0.5) * step, box[1] + (r + 0.5) * step] },
    });
  }
  return { type: "FeatureCollection" as const, features: feats };
}

function aoiGeoJson(box: number[], step: number, aoi: Aoi) {
  const x0 = box[0] + aoi.c0 * step;
  const x1 = box[0] + (aoi.c1 + 1) * step;
  const y0 = box[1] + aoi.r0 * step;
  const y1 = box[1] + (aoi.r1 + 1) * step;
  return {
    type: "FeatureCollection" as const,
    features: [{
      type: "Feature" as const,
      properties: {},
      geometry: { type: "Polygon" as const, coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] },
    }],
  };
}

function applyMode(map: maplibregl.Map, smooth: boolean) {
  if (!map.getLayer("heat") || !map.getLayer("cells-fill") || !map.getLayer("cells-line")) return;
  map.setLayoutProperty("heat", "visibility", smooth ? "visible" : "none");
  map.setLayoutProperty("cells-line", "visibility", smooth ? "none" : "visible");
  // keep the cells almost invisible in smooth mode so hover and tooltips still work
  map.setPaintProperty("cells-fill", "fill-opacity", ["case", [">", ["get", "v"], 0], smooth ? 0.02 : 0.72, 0]);
}

export default function MapView({ nlat, nlon, step, box, cellTotals, cellMax, aoi, onAoi, label }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const latest = useRef({ nlat, nlon, step, box, cellTotals, cellMax, aoi, onAoi });
  const smoothRef = useRef(false);
  const [smooth, setSmooth] = useState(false);
  const [status, setStatus] = useState("Starting map…");
  const [err, setErr] = useState("");

  useEffect(() => {
    latest.current = { nlat, nlon, step, box, cellTotals, cellMax, aoi, onAoi };
  });

  useEffect(() => {
    smoothRef.current = smooth;
    const map = mapRef.current;
    if (map && readyRef.current) applyMode(map, smooth);
  }, [smooth]);

  useEffect(() => {
    if (!containerRef.current) return;
    const p0 = latest.current;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      bounds: [[p0.box[0], p0.box[1]], [p0.box[2], p0.box[3]]],
      fitBoundsOptions: { padding: 24 },
      boxZoom: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

    const addOverlay = () => {
      if (map.getSource("cells")) return;
      try {
        const p = latest.current;
        map.addSource("cells", { type: "geojson", data: cellsGeoJson(p.box, p.step, p.nlat, p.nlon, p.cellTotals, p.cellMax) });
        map.addSource("points", { type: "geojson", data: pointsGeoJson(p.box, p.step, p.nlat, p.nlon, p.cellTotals, p.cellMax) });
        map.addSource("aoi", { type: "geojson", data: aoiGeoJson(p.box, p.step, p.aoi) });
        const firstSymbol = map.getStyle().layers?.find((l) => l.type === "symbol")?.id;
        map.addLayer({
          id: "heat", type: "heatmap", source: "points", layout: { visibility: "none" },
          paint: {
            "heatmap-weight": ["get", "w"],
            "heatmap-intensity": HEAT_INTENSITY,
            "heatmap-radius": ["interpolate", ["exponential", 2], ["zoom"], 4, 10, 6, 40, 8, 160, 10, 640],
            "heatmap-opacity": 0.85,
            "heatmap-color": [
              "interpolate", ["linear"], ["heatmap-density"],
              0, "rgba(68,1,84,0)",
              0.08, "rgba(68,1,84,0.35)",
              0.2, "#3b528b",
              0.4, "#21908d",
              0.6, "#5cc863",
              0.8, "#aadc32",
              1, "#fde725",
            ],
          },
        }, firstSymbol);
        map.addLayer({
          id: "cells-fill", type: "fill", source: "cells",
          paint: { "fill-color": ["get", "color"], "fill-opacity": ["case", [">", ["get", "v"], 0], 0.72, 0] },
        }, firstSymbol);
        map.addLayer({
          id: "cells-line", type: "line", source: "cells", filter: [">", ["get", "v"], 0],
          paint: { "line-color": "#ffffff", "line-opacity": 0.3, "line-width": 0.5 },
        }, firstSymbol);
        map.addLayer({
          id: "aoi-line", type: "line", source: "aoi",
          paint: { "line-color": "#ef4444", "line-width": 3 },
        });
        readyRef.current = true;
        applyMode(map, smoothRef.current);
        const n = p.cellTotals.filter((v) => v > 0).length;
        setStatus(`Map ready: ${n} cells with data drawn.`);
      } catch (e) {
        console.error("MapView: could not add overlay layers", e);
        setErr(`Overlay error: ${e instanceof Error ? e.message : String(e)}`);
      }
    };

    map.on("style.load", () => {
      setStatus("Style loaded; adding data cells…");
      addOverlay();
    });
    map.on("error", (e) => {
      const msg = String(e?.error?.message ?? "map error");
      console.error("MapView: map error", e?.error ?? e);
      setErr(msg);
    });

    const timer = window.setTimeout(() => {
      if (!readyRef.current) {
        setStatus("Basemap did not load in time: using a plain background.");
        map.setStyle(FALLBACK_STYLE);
      }
    }, 6000);

    map.on("mousemove", "cells-fill", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const v = Math.round(Number(f.properties?.v ?? 0));
      popup.setLngLat(e.lngLat).setHTML(`${v.toLocaleString("en-IN")} hotspots in this 0.25° cell`).addTo(map);
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "cells-fill", () => {
      popup.remove();
      map.getCanvas().style.cursor = "";
    });

    map.on("click", (e) => {
      const p = latest.current;
      const c = Math.floor((e.lngLat.lng - p.box[0]) / p.step);
      const r = Math.floor((e.lngLat.lat - p.box[1]) / p.step);
      if (r < 0 || r >= p.nlat || c < 0 || c >= p.nlon) return;
      if (e.originalEvent.shiftKey) {
        const a = p.aoi;
        p.onAoi({ r0: Math.min(a.r0, r), r1: Math.max(a.r1, r), c0: Math.min(a.c0, c), c1: Math.max(a.c1, c) });
      } else {
        p.onAoi({ r0: r, r1: r, c0: c, c1: c });
      }
    });

    mapRef.current = map;
    return () => {
      window.clearTimeout(timer);
      readyRef.current = false;
      popup.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    (map.getSource("cells") as maplibregl.GeoJSONSource | undefined)
      ?.setData(cellsGeoJson(box, step, nlat, nlon, cellTotals, cellMax));
    (map.getSource("points") as maplibregl.GeoJSONSource | undefined)
      ?.setData(pointsGeoJson(box, step, nlat, nlon, cellTotals, cellMax));
  }, [box, step, nlat, nlon, cellTotals, cellMax]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    (map.getSource("aoi") as maplibregl.GeoJSONSource | undefined)?.setData(aoiGeoJson(box, step, aoi));
  }, [box, step, aoi]);

  const btn = "rounded border px-2 py-1 text-sm";

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">Map: {label}</h2>
        <div className="flex gap-2" role="group" aria-label="Map display">
          <button
            onClick={() => setSmooth(false)}
            aria-pressed={!smooth}
            className={`${btn} ${!smooth ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 bg-white"}`}
          >
            Cells (exact)
          </button>
          <button
            onClick={() => setSmooth(true)}
            aria-pressed={smooth}
            className={`${btn} ${smooth ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 bg-white"}`}
          >
            Smooth
          </button>
        </div>
      </div>
      <p className="mb-2 text-xs text-slate-600">
        Hotspots per 0.25° cell in the chosen years. Click a cell to select it, Shift+click to extend the selection;
        the red outline is your area. The calendar below follows it.
        {smooth && " Smooth view is a visual interpolation of the 0.25° cells, not finer-resolution data."}
      </p>
      <div ref={containerRef} className="h-[28rem] w-full overflow-hidden rounded border border-slate-300" />
      <div className="mt-2 flex items-center gap-2 text-xs">
        <span>{smooth ? "low" : "0"}</span>
        <div className="h-3 w-48 rounded" style={{ background: `linear-gradient(to right, ${STOPS.join(",")})` }} />
        <span>{smooth ? "high (relative density)" : `${Math.round(cellMax).toLocaleString("en-IN")} (max cell)`}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">Map status: {status}</p>
      {err && <p className="mt-1 text-xs text-red-700">Last map message: {err}</p>}
    </div>
  );
}
