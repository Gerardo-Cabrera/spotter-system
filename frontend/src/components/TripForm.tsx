import { useState } from "react";
import { Loader2, Navigation } from "lucide-react";
import AddressInput from "./AddressInput";
import DateTimePicker from "./DateTimePicker";
import type { TripInput } from "../types";

interface Props {
  loading: boolean;
  onSubmit: (input: TripInput) => void;
}

const EXAMPLE: TripInput = {
  current_location: "Green Bay, WI",
  pickup_location: "Chicago, IL",
  dropoff_location: "Dallas, TX",
  current_cycle_used_hours: 10,
};

export default function TripForm({ loading, onSubmit }: Props) {
  const [form, setForm] = useState<TripInput>(EXAMPLE);
  // `DateTimePicker` uses the same `YYYY-MM-DDTHH:mm` format the native
  // input does, so we keep the raw local string in state and convert to an
  // ISO-8601 UTC string only at submit time.
  const [departureLocal, setDepartureLocal] = useState<string>("");

  const update = <K extends keyof TripInput>(k: K, v: TripInput[K]) =>
    setForm((p) => ({ ...p, [k]: v }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.current_location || !form.pickup_location || !form.dropoff_location) return;
    onSubmit({
      ...form,
      departure_time: departureLocal ? new Date(departureLocal).toISOString() : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-10 h-10 rounded-xl bg-brand-600 text-white flex items-center justify-center">
          <Navigation className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900">Trip details</h2>
          <p className="text-sm text-slate-500">Plan your route with HOS-compliant stops.</p>
        </div>
      </div>

      <AddressInput
        label="Current location"
        value={form.current_location}
        onChange={(v) => update("current_location", v)}
        placeholder="City, State or full address"
      />
      <AddressInput
        label="Pickup location"
        value={form.pickup_location}
        onChange={(v) => update("pickup_location", v)}
        placeholder="City, State or full address"
      />
      <AddressInput
        label="Dropoff location"
        value={form.dropoff_location}
        onChange={(v) => update("dropoff_location", v)}
        placeholder="City, State or full address"
      />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1 uppercase tracking-wide">
            Cycle used (hrs)
          </label>
          <input
            type="number"
            min={0}
            max={70}
            step="0.25"
            value={form.current_cycle_used_hours}
            onChange={(e) => update("current_cycle_used_hours", Number(e.target.value))}
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1 uppercase tracking-wide">
            Departure (optional)
          </label>
          <DateTimePicker
            value={departureLocal}
            onChange={setDepartureLocal}
            placeholder="Pick a date and time"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1 uppercase tracking-wide">
            Driver name
          </label>
          <input
            type="text"
            value={form.driver_name ?? ""}
            onChange={(e) => update("driver_name", e.target.value)}
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none text-sm"
            placeholder="Optional"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1 uppercase tracking-wide">
            Carrier
          </label>
          <input
            type="text"
            value={form.carrier_name ?? ""}
            onChange={(e) => update("carrier_name", e.target.value)}
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none text-sm"
            placeholder="Optional"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-brand-600 hover:bg-brand-700 disabled:bg-brand-600/50 text-white font-semibold py-2.5 rounded-lg transition flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Planning...
          </>
        ) : (
          <>Plan trip</>
        )}
      </button>

      <p className="text-xs text-slate-400 leading-relaxed">
        Assumes property-carrying driver on a 70h / 8-day cycle, fueling every 1000 mi, 1h for pickup
        and 1h for dropoff.
      </p>
    </form>
  );
}
