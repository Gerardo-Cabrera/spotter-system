import type { TripInput, TripPlan } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function planTrip(input: TripInput): Promise<TripPlan> {
  const res = await fetch(`${API_BASE}/api/trips/plan/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? "Failed to plan trip");
  }
  return res.json();
}

export async function autocompleteAddress(q: string): Promise<{ display_name: string; lat: number; lon: number }[]> {
  if (q.trim().length < 3) return [];
  const res = await fetch(`${API_BASE}/api/geocode/?q=${encodeURIComponent(q)}&limit=5`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.results ?? [];
}
