import type { TripInput, TripPlan } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function planTrip(input: TripInput): Promise<TripPlan> {
  const res = await fetch(`${API_BASE}/api/trips/plan/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(extractErrorMessage(body, res.statusText));
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

/**
 * Produce a human-readable error from a DRF response body.
 *
 * DRF returns two shapes depending on the failure mode:
 *   - exception-style:   { "detail": "Upstream routing provider failed..." }
 *   - validation-style:  { "current_location": ["This field may not be blank."] }
 *
 * The previous implementation only honoured the first shape, so validation
 * errors degraded to a generic "Failed to plan trip". Now we surface the
 * first field-level message whenever `detail` is absent.
 */
function extractErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback || "Failed to plan trip";
  const obj = body as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  for (const [field, value] of Object.entries(obj)) {
    if (Array.isArray(value) && value.length && typeof value[0] === "string") {
      return `${field}: ${value[0]}`;
    }
    if (typeof value === "string") return `${field}: ${value}`;
  }
  return fallback || "Failed to plan trip";
}
