import type { DailyLog, DailyLogEntry } from "../types";

/**
 * Driver's Daily Log sheet (SVG).
 *
 * Visual convention follows the FMCSA blank log and the reference video:
 *  - 4 status rows (Off Duty, Sleeper, Driving, On Duty not driving).
 *  - 24-hour grid with 15-minute ticks.
 *  - Horizontal line on the row of the current status.
 *  - Vertical connector when the status changes (with a red dot at each change).
 *  - Remarks under the grid with a vertical label "City, ST / activity".
 */

const ROWS = [
  { row: 1, label: "1. Off Duty" },
  { row: 2, label: "2. Sleeper Berth" },
  { row: 3, label: "3. Driving" },
  { row: 4, label: "4. On Duty (not driving)" },
];

const WIDTH = 960;
const LEFT = 160;
const RIGHT = 60;
const GRID_W = WIDTH - LEFT - RIGHT;
const TOP = 170;
const ROW_H = 34;
const GRID_H = ROW_H * 4;

const xForHour = (h: number) => LEFT + (h / 24) * GRID_W;
const yForRow = (row: number) => TOP + (row - 0.5) * ROW_H;

function hoursToHHMM(h: number): string {
  const hours = Math.floor(h);
  const minutes = Math.round((h - hours) * 60);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function buildPath(entries: DailyLogEntry[]): string {
  if (!entries.length) return "";
  const sorted = [...entries].sort((a, b) => a.start_hour - b.start_hour);
  let d = "";
  let prevY: number | null = null;
  for (const e of sorted) {
    const x1 = xForHour(e.start_hour);
    const x2 = xForHour(e.end_hour);
    const y = yForRow(e.status_row);
    if (prevY === null) {
      d += `M ${x1} ${y} `;
    } else if (prevY !== y) {
      d += `L ${x1} ${prevY} L ${x1} ${y} `;
    }
    d += `L ${x2} ${y} `;
    prevY = y;
  }
  return d;
}

function Remarks({ entries }: { entries: DailyLogEntry[] }) {
  const sorted = [...entries].sort((a, b) => a.start_hour - b.start_hour);
  return (
    <>
      {sorted.map((e, i) => {
        if (i === 0) return null;
        const x = xForHour(e.start_hour);
        const city = shortLocation(e.location_name);
        const top = TOP + GRID_H + 14;
        return (
          <g key={`r${i}`}>
            <line x1={x} y1={TOP + GRID_H} x2={x} y2={top} stroke="#111827" strokeWidth={1} />
            <text
              x={x + 3}
              y={top + 4}
              fontSize={10}
              fill="#1f2937"
              transform={`rotate(55 ${x + 3} ${top + 4})`}
            >
              {city ? `${city} / ` : ""}
              {e.note}
            </text>
          </g>
        );
      })}
    </>
  );
}

function shortLocation(loc: string): string {
  if (!loc) return "";
  // Nominatim returns long strings; shorten to city, state.
  const parts = loc.split(",").map((p) => p.trim());
  if (parts.length <= 2) return loc;
  // Heuristic: pick first non-numeric token + last state-like token.
  const city = parts.find((p) => !/^\d/.test(p)) ?? parts[0];
  const state = parts.length >= 3 ? parts[parts.length - 3] : parts[parts.length - 1];
  if (city === state) return city;
  return `${city}, ${state}`;
}

export default function LogSheet({ log }: { log: DailyLog }) {
  const pathD = buildPath(log.entries);
  const changePoints = [...log.entries]
    .sort((a, b) => a.start_hour - b.start_hour)
    .slice(1)
    .map((e) => ({ x: xForHour(e.start_hour), y: yForRow(e.status_row) }));
  const last = [...log.entries].sort((a, b) => a.end_hour - b.end_hour).pop();

  const totals = log.totals_hours;
  const totalOnDuty = (totals.driving ?? 0) + (totals.on_duty ?? 0);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 overflow-x-auto">
      <svg viewBox={`0 0 ${WIDTH} 520`} className="w-full min-w-[860px]">
        {/* Header */}
        <text x={20} y={30} fontSize={20} fontWeight={700} fill="#0f172a">
          Driver's Daily Log
        </text>
        <text x={20} y={48} fontSize={11} fill="#475569">
          (24 hours) — {log.date} — {log.timezone}
        </text>
        <text x={WIDTH - 300} y={30} fontSize={11} fill="#475569">
          Original — File at home terminal
        </text>
        <text x={WIDTH - 300} y={46} fontSize={11} fill="#475569">
          Duplicate — Driver retains for 8 days
        </text>

        {/* Info block */}
        <g fontSize={11} fill="#1f2937">
          <text x={20} y={78}>From: <tspan fontWeight={600}>{shortLocation(log.entries[0]?.location_name ?? "")}</tspan></text>
          <text x={20} y={96}>To: <tspan fontWeight={600}>{shortLocation(last?.location_name ?? "")}</tspan></text>
          <text x={20} y={114}>Driver: <tspan fontWeight={600}>{log.driver_name || "—"}</tspan></text>
          <text x={20} y={132}>Carrier: <tspan fontWeight={600}>{log.carrier_name || "—"}</tspan></text>
          <text x={20} y={150}>Home terminal: <tspan fontWeight={600}>{shortLocation(log.home_terminal)}</tspan></text>

          <text x={360} y={78}>Total miles driving today: <tspan fontWeight={600}>{log.total_miles_today}</tspan></text>
          <text x={360} y={96}>Total driving hours: <tspan fontWeight={600}>{(totals.driving ?? 0).toFixed(2)}</tspan></text>
          <text x={360} y={114}>Total on-duty hours: <tspan fontWeight={600}>{totalOnDuty.toFixed(2)}</tspan></text>
        </g>

        {/* Grid hour labels (top) */}
        {Array.from({ length: 25 }, (_, h) => (
          <text
            key={`h${h}`}
            x={xForHour(h)}
            y={TOP - 6}
            fontSize={10}
            fill="#475569"
            textAnchor="middle"
          >
            {h === 0 || h === 24 ? "Mid" : h === 12 ? "Noon" : h}
          </text>
        ))}

        {/* Row backgrounds + separators */}
        {ROWS.map((r, idx) => (
          <g key={r.row}>
            <rect
              x={LEFT}
              y={TOP + idx * ROW_H}
              width={GRID_W}
              height={ROW_H}
              fill={idx % 2 === 0 ? "#f8fafc" : "#ffffff"}
              stroke="#cbd5e1"
            />
            <text x={LEFT - 10} y={TOP + idx * ROW_H + ROW_H / 2 + 4} fontSize={11} fill="#1f2937" textAnchor="end">
              {r.label}
            </text>
          </g>
        ))}

        {/* Vertical hour grid + 15-min ticks */}
        {Array.from({ length: 25 }, (_, h) => (
          <line
            key={`v${h}`}
            x1={xForHour(h)}
            y1={TOP}
            x2={xForHour(h)}
            y2={TOP + GRID_H}
            stroke="#94a3b8"
            strokeWidth={1}
          />
        ))}
        {Array.from({ length: 24 * 4 + 1 }, (_, t) => {
          if (t % 4 === 0) return null;
          const x = LEFT + (t / (24 * 4)) * GRID_W;
          return ROWS.map((_, idx) => (
            <line
              key={`t${t}-${idx}`}
              x1={x}
              y1={TOP + idx * ROW_H}
              x2={x}
              y2={TOP + idx * ROW_H + (t % 2 === 0 ? 8 : 4)}
              stroke="#cbd5e1"
              strokeWidth={1}
            />
          ));
        })}

        {/* Totals column */}
        <g fontSize={10} fill="#1f2937">
          <rect x={LEFT + GRID_W} y={TOP} width={RIGHT - 8} height={GRID_H} fill="#f1f5f9" stroke="#cbd5e1" />
          <text x={LEFT + GRID_W + (RIGHT - 8) / 2} y={TOP - 6} fontSize={9} textAnchor="middle">Total hrs</text>
          {ROWS.map((r, idx) => (
            <text
              key={`tot${r.row}`}
              x={LEFT + GRID_W + (RIGHT - 8) / 2}
              y={TOP + idx * ROW_H + ROW_H / 2 + 4}
              textAnchor="middle"
              fontWeight={600}
            >
              {hoursToHHMM(totals[rowToStatus(r.row)] ?? 0)}
            </text>
          ))}
        </g>

        {/* Status line */}
        <path d={pathD} stroke="#0f172a" strokeWidth={2.2} fill="none" strokeLinejoin="miter" />
        {changePoints.map((p, i) => (
          <circle key={`dot${i}`} cx={p.x} cy={p.y} r={3} fill="#dc2626" stroke="#7f1d1d" strokeWidth={0.75} />
        ))}

        {/* Remarks */}
        <text x={20} y={TOP + GRID_H + 20} fontSize={12} fontWeight={700} fill="#0f172a">
          Remarks
        </text>
        <line
          x1={LEFT}
          y1={TOP + GRID_H}
          x2={LEFT + GRID_W}
          y2={TOP + GRID_H}
          stroke="#0f172a"
          strokeWidth={1}
        />
        <g transform={`translate(0, ${0})`}>
          <Remarks entries={log.entries} />
        </g>

        {/* Recap */}
        <g fontSize={10} fill="#1f2937" transform={`translate(20, ${TOP + GRID_H + 160})`}>
          <text fontWeight={700} fontSize={11}>Recap — 70 hr / 8 day</text>
          <text y={16}>On-duty today: {totalOnDuty.toFixed(2)}h</text>
          <text y={30}>Driving today: {(totals.driving ?? 0).toFixed(2)}h</text>
          <text y={44}>Off-duty today: {((totals.off_duty ?? 0) + (totals.sleeper ?? 0)).toFixed(2)}h</text>
        </g>
      </svg>
    </div>
  );
}

function rowToStatus(row: number): "off_duty" | "sleeper" | "driving" | "on_duty" {
  switch (row) {
    case 1: return "off_duty";
    case 2: return "sleeper";
    case 3: return "driving";
    default: return "on_duty";
  }
}
