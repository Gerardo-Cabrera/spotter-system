import { useState } from "react";
import { Truck, Github } from "lucide-react";
import TripForm from "./components/TripForm";
import RouteMap from "./components/RouteMap";
import LogSheet from "./components/LogSheet";
import TripSummary from "./components/TripSummary";
import { planTrip } from "./api";
import type { TripInput, TripPlan } from "./types";

export default function App() {
  const [plan, setPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (input: TripInput) => {
    setLoading(true);
    setError(null);
    try {
      const result = await planTrip(input);
      setPlan(result);
    } catch (e: any) {
      setError(e?.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-full bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-600 text-white flex items-center justify-center">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900 leading-none">Spotter</h1>
              <p className="text-xs text-slate-500 leading-none mt-1">HOS-compliant trip planner</p>
            </div>
          </div>
          {import.meta.env.VITE_GITHUB_URL && (
            <a
              href={import.meta.env.VITE_GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="text-slate-500 hover:text-slate-900"
              aria-label="Source on GitHub"
            >
              <Github className="w-5 h-5" />
            </a>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        <aside>
          <TripForm loading={loading} onSubmit={handleSubmit} />
          {error && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 text-red-800 px-4 py-3 text-sm">
              {error}
            </div>
          )}
        </aside>

        <section className="space-y-6">
          {!plan && !loading && <EmptyState />}
          {loading && <SkeletonState />}
          {plan && (
            <>
              <TripSummary plan={plan} />
              <RouteMap geometry={plan.route_geometry} stops={plan.stops} />
              <div>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Daily log sheets ({plan.daily_logs.length})
                </h3>
                <div className="space-y-6">
                  {plan.daily_logs.map((log) => (
                    <LogSheet key={log.date} log={log} />
                  ))}
                </div>
              </div>
            </>
          )}
        </section>
      </main>

      <footer className="max-w-7xl mx-auto px-6 py-10 text-center text-xs text-slate-400">
        Built with Django + React · Map data © OpenStreetMap · Routing by OSRM
      </footer>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-12 text-center">
      <Truck className="w-10 h-10 text-slate-300 mx-auto" />
      <h3 className="mt-4 text-lg font-semibold text-slate-800">Plan a new trip</h3>
      <p className="text-sm text-slate-500 mt-1">
        Enter your current location, pickup and drop-off, and current cycle hours.
        We'll compute the route, required HOS stops and draw your daily log sheets.
      </p>
    </div>
  );
}

function SkeletonState() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 bg-white rounded-xl border border-slate-200 animate-pulse" />
        ))}
      </div>
      <div className="h-[520px] bg-white rounded-2xl border border-slate-200 animate-pulse" />
      <div className="h-80 bg-white rounded-2xl border border-slate-200 animate-pulse" />
    </div>
  );
}
