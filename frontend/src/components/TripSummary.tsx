import type { TripPlan } from "../types";
import { Clock, Gauge, Route, CalendarDays, AlertTriangle } from "lucide-react";

interface Props {
  plan: TripPlan;
}

export default function TripSummary({ plan }: Props) {
  const s = plan.summary;
  const cards = [
    { icon: Route, label: "Distance", value: `${s.total_miles.toLocaleString()} mi` },
    { icon: Clock, label: "Driving time", value: `${s.total_driving_hours.toFixed(1)} h` },
    { icon: Gauge, label: "On-duty time", value: `${s.total_on_duty_hours.toFixed(1)} h` },
    { icon: CalendarDays, label: "Days", value: `${s.total_days}` },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {cards.map(({ icon: Icon, label, value }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-slate-500 text-xs uppercase font-semibold tracking-wide">
              <Icon className="w-3.5 h-3.5" />
              {label}
            </div>
            <div className="mt-1 text-xl font-bold text-slate-900">{value}</div>
          </div>
        ))}
      </div>
      {s.needs_restart && (
        <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-900 rounded-xl px-4 py-3 text-sm">
          <AlertTriangle className="w-4 h-4" />
          This trip reaches the 70-hour cycle limit. A 34-hour restart has been inserted.
        </div>
      )}
    </div>
  );
}
