const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export type City = "new_york" | "chicago";
export const CITY_LABELS: Record<City, string> = { new_york: "New York", chicago: "Chicago" };

export type CityStat = {
  city: City;
  trip_count: number;
  station_count: number;
};

export type Station = {
  station_id: string;
  name: string;
  lat: number;
  lon: number;
};

export type StationDemandHour = {
  hour_of_day: number;
  avg_trips_per_day: number;
};

export type StationDemand = {
  station_id: string;
  name: string;
  range_days: number;
  total_trips: number;
  by_hour: StationDemandHour[];
};

export type NetworkDemandHour = {
  hour_of_day: number;
  trip_count: number;
};

export type StationImbalance = {
  station_id: string;
  name: string;
  hour_of_day: number;
  avg_net_balance: number;
};

export type WeekdayVsWeekend = {
  weekday_mean_trips_per_day: number;
  weekend_mean_trips_per_day: number;
  weekday_days: number;
  weekend_days: number;
  holidays_excluded: number;
  pct_difference: number;
  test_used: string;
  statistic: number;
  p_value: number;
};

export type RebalancingCandidate = {
  station_id: string;
  name: string;
  stockout_episodes: number;
  estimated_lost_trips: number;
  truck_hours_needed: number;
  lost_trips_per_truck_hour: number;
};

export type ForecastDay = {
  date: string;
  trip_count: number;
  is_forecast: boolean;
};

export type StationForecast = {
  station_id: string;
  name: string;
  method: string;
  history_days_used: number;
  forecast: ForecastDay[];
};

export const api = {
  cities: () => get<CityStat[]>("/cities"),
  stations: (city: City = "new_york", limit = 3000) =>
    get<Station[]>(`/stations?city=${city}&limit=${limit}`),
  stationDemand: (id: string, range?: number) =>
    get<StationDemand>(`/stations/${encodeURIComponent(id)}/demand${range ? `?range=${range}` : ""}`),
  stationForecast: (id: string, days = 7) =>
    get<StationForecast>(`/stations/${encodeURIComponent(id)}/forecast?days=${days}`),
  networkDemand: (city: City = "new_york") => get<NetworkDemandHour[]>(`/network/demand?city=${city}`),
  networkImbalance: (hour: number, city: City = "new_york") =>
    get<StationImbalance[]>(`/network/imbalance?hour=${hour}&city=${city}`),
  weekdayVsWeekend: (city: City = "new_york") =>
    get<WeekdayVsWeekend>(`/insights/weekday-vs-weekend?city=${city}`),
  rebalancingCandidates: (city: City = "new_york", limit = 20) =>
    get<RebalancingCandidate[]>(`/insights/rebalancing-candidates?city=${city}&limit=${limit}`),
};
