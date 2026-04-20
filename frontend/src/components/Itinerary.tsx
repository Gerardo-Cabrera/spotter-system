import type { Stop } from "../types";

/**
 * Chronological list of every stop of the trip.
 *
 * Surfaces the same information the map exposes through pin pop-ups, but as
 * a scannable vertical timeline — so the "information regarding stops and
 * rests" required by the assessment is readable without having to click
 * every marker.
 */

interface Props {
  stops: Stop[];
  timezone: string;
}

const KIND_META: Record<Stop["kind"], { label: string; color: string; glyph: string }> = {
  start: { label: "Start", color: "#0ea5e9", glyph: "S" },
  pickup: { label: "Pickup", color: "#22c55e", glyph: "P" },
  dropoff: { label: "Drop-off", color: "#ef4444", glyph: "D" },
  fuel: { label: "Fueling", color: "#f59e0b", glyph: "⛽" },
  break: { label: "30-min break", color: "#8b5cf6", glyph: "☕" },
  rest: { label: "10-h rest", color: "#6366f1", glyph: "💤" },
};

function formatTime(iso: string | undefined, timezone: string): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: timezone,
      weekday: "short",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function Itinerary({ stops, timezone }: Props) {
  if (!stops.length) return null;

  // The backend already sorts chronologically (see `_extract_stops` in
  // trips/views.py), but we re-sort here as a defense-in-depth pass:
  // - A stable sort keeps deterministic order on `at` ties.
  // - Stops without `at` sink to the tail.
  // - Using the original index as tie-breaker prevents render reshuffles.
  const ordered = stops
    .map((s, idx) => ({ s, idx, t: s.at ? Date.parse(s.at) : Number.POSITIVE_INFINITY }))
    .sort((a, b) => a.t - b.t || a.idx - b.idx)
    .map(({ s }) => s);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
      <div className="flex items-baseline justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
          Itinerary
        </h3>
        <span className="text-xs text-slate-400">Times in {timezone}</span>
      </div>

      <ol className="relative space-y-3 before:absolute before:left-[13px] before:top-2 before:bottom-2 before:w-px before:bg-slate-200">
        {ordered.map((s, i) => {
          const meta = KIND_META[s.kind];
          return (
            <li key={`${s.kind}-${i}`} className="relative flex gap-3 items-start">
              <div
                className="relative z-10 w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold text-white shadow ring-2 ring-white shrink-0"
                style={{ background: meta.color }}
                aria-label={meta.label}
              >
                {meta.glyph}
              </div>
              <div className="flex-1 min-w-0 pt-0.5">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-900">
                    {meta.label}
                  </span>
                  <span className="text-xs text-slate-400">·</span>
                  <span className="text-xs text-slate-500 tabular-nums">
                    {formatTime(s.at, timezone)}
                  </span>
                </div>
                {(s.location_name || s.label) && (
                  <div className="text-xs text-slate-500 truncate" title={s.location_name || s.label}>
                    {s.location_name || s.label}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
