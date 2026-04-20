import { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import * as L from "leaflet";
import type { Stop } from "../types";

const KIND_COLORS: Record<Stop["kind"], string> = {
  start: "#0ea5e9",    // sky
  pickup: "#22c55e",   // green
  dropoff: "#ef4444",  // red
  fuel: "#f59e0b",     // amber
  break: "#8b5cf6",    // violet
  rest: "#6366f1",     // indigo
};

const KIND_GLYPHS: Record<Stop["kind"], string> = {
  start: "S",
  pickup: "P",
  dropoff: "D",
  fuel: "⛽",
  break: "☕",
  rest: "💤",
};

const LARGE_KINDS = new Set<Stop["kind"]>(["start", "pickup", "dropoff"]);

function stopIcon(kind: Stop["kind"]) {
  const color = KIND_COLORS[kind];
  const glyph = KIND_GLYPHS[kind];
  const big = LARGE_KINDS.has(kind);
  const size = big ? 28 : 20;
  const font = big ? 13 : 11;
  return L.divIcon({
    className: "",
    html: `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:${font}px;font-family:Inter,sans-serif">${glyph}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

const LEGEND_ENTRIES: { kind: Stop["kind"]; label: string }[] = [
  { kind: "start", label: "Start" },
  { kind: "pickup", label: "Pickup" },
  { kind: "dropoff", label: "Drop-off" },
  { kind: "fuel", label: "Fuel" },
  { kind: "break", label: "Break" },
  { kind: "rest", label: "Rest" },
];

function MapLegend() {
  return (
    <div className="absolute top-3 right-3 z-[400] bg-white/95 backdrop-blur rounded-lg border border-slate-200 shadow-md px-3 py-2 text-xs">
      <div className="font-semibold text-slate-500 uppercase tracking-wide mb-1.5 text-[10px]">
        Legend
      </div>
      <ul className="space-y-1">
        {LEGEND_ENTRIES.map(({ kind, label }) => (
          <li key={kind} className="flex items-center gap-2">
            <span
              className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0"
              style={{ background: KIND_COLORS[kind] }}
              aria-hidden
            >
              {KIND_GLYPHS[kind]}
            </span>
            <span className="text-slate-700">{label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const bounds = L.latLngBounds(points.map((p) => L.latLng(p[0], p[1])));
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [points, map]);
  return null;
}

interface Props {
  geometry: [number, number][];
  stops: Stop[];
}

export default function RouteMap({ geometry, stops }: Props) {
  const center: [number, number] = geometry.length
    ? geometry[Math.floor(geometry.length / 2)]
    : [39.8283, -98.5795];

  return (
    <div className="relative h-[520px] rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
      <MapLegend />
      <MapContainer center={center} zoom={5} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{y}/{x}.png"
        />
        {geometry.length > 1 && (
          <Polyline positions={geometry} pathOptions={{ color: "#2563eb", weight: 4 }} />
        )}
        {stops.map((s, i) => (
          <Marker
            key={i}
            position={[s.lat, s.lon]}
            icon={stopIcon(s.kind)}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-semibold capitalize">{s.kind}</div>
                <div className="text-slate-600">{s.label}</div>
                {s.location_name && <div className="text-xs text-slate-500 mt-1">{s.location_name}</div>}
              </div>
            </Popup>
          </Marker>
        ))}
        <FitBounds points={geometry.length ? geometry : stops.map((s) => [s.lat, s.lon])} />
      </MapContainer>
    </div>
  );
}
