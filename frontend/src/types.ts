export type Status = "off_duty" | "sleeper" | "driving" | "on_duty";

export interface GeocodedPoint {
  query: string;
  display_name: string;
  lat: number;
  lon: number;
}

export interface Stop {
  kind: "start" | "pickup" | "dropoff" | "fuel" | "break" | "rest";
  label: string;
  lat: number;
  lon: number;
  location_name?: string;
  at?: string;
}

export interface Segment {
  status: Status;
  start: string;
  end: string;
  hours: number;
  miles: number;
  note: string;
  location_name: string;
  lat: number;
  lon: number;
}

export interface DailyLogEntry {
  status: Status;
  status_row: 1 | 2 | 3 | 4;
  start_hour: number;
  end_hour: number;
  start: string;
  end: string;
  note: string;
  location_name: string;
  miles: number;
}

export interface DailyLog {
  date: string;
  timezone: string;
  driver_name: string;
  carrier_name: string;
  home_terminal: string;
  entries: DailyLogEntry[];
  totals_hours: Record<Status, number>;
  total_miles_today: number;
}

export interface TripSummary {
  total_miles: number;
  total_driving_hours: number;
  total_on_duty_hours: number;
  average_speed_mph: number;
  total_days: number;
  cycle_used_hours_end: number;
  needs_restart: boolean;
}

export interface TripPlan {
  inputs: {
    current_location: string;
    pickup_location: string;
    dropoff_location: string;
    current_cycle_used_hours: number;
    departure_time: string;
  };
  geocoded: {
    current: GeocodedPoint;
    pickup: GeocodedPoint;
    dropoff: GeocodedPoint;
  };
  timezone: string;
  summary: TripSummary;
  route_geometry: [number, number][];
  stops: Stop[];
  segments: Segment[];
  daily_logs: DailyLog[];
  trip_id?: string;
}

export interface TripInput {
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  current_cycle_used_hours: number;
  departure_time?: string;
  driver_name?: string;
  carrier_name?: string;
  save?: boolean;
}
