"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type StationDemand, type StationForecast } from "@/lib/api";
import { Card, StatTile } from "@/components/Card";
import { DemandCurveChart } from "@/components/DemandCurveChart";
import { ForecastChart } from "@/components/ForecastChart";

const RANGES: Array<{ label: string; days?: number }> = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "All 12mo" },
];

export function StationDetail({ stationId }: { stationId: string }) {
  const [range, setRange] = useState<{ label: string; days?: number }>(RANGES[3]);
  const [data, setData] = useState<StationDemand | null>(null);
  const [forecast, setForecast] = useState<StationForecast | null>(null);
  const [error, setError] = useState(false);
  const [settledKey, setSettledKey] = useState("");
  const requestKey = `${stationId}|${range.label}`;
  const loading = settledKey !== requestKey;

  useEffect(() => {
    let stale = false;
    api
      .stationDemand(stationId, range.days)
      .then((d) => {
        if (stale) return;
        setData(d);
        setSettledKey(requestKey);
      })
      .catch(() => {
        if (stale) return;
        setError(true);
        setSettledKey(requestKey);
      });
    return () => {
      stale = true;
    };
  }, [stationId, range, requestKey]);

  useEffect(() => {
    api.stationForecast(stationId, 7).then(setForecast).catch(() => setForecast(null));
  }, [stationId]);

  if (error) {
    return (
      <div className="p-6">
        <Link href="/" className="text-sm text-accent hover:underline">
          &larr; back to map
        </Link>
        <p className="mt-4 text-sm text-danger">Station {stationId} not found.</p>
      </div>
    );
  }

  const peak = data?.by_hour.reduce((a, b) => (b.avg_trips_per_day > a.avg_trips_per_day ? b : a), data.by_hour[0]);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <Link href="/" className="text-sm text-accent hover:underline">
          &larr; back to map
        </Link>
        <h1 className="mt-2 text-lg font-semibold">{data?.name ?? "Loading…"}</h1>
        <p className="mt-1 text-xs text-muted">station_id: {stationId}</p>
      </div>

      <div className="flex gap-1 rounded-lg border border-border bg-surface-2 p-1 w-fit">
        {RANGES.map((r) => (
          <button
            key={r.label}
            onClick={() => setRange(r)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              range.label === r.label ? "bg-accent-soft text-accent" : "text-muted hover:text-foreground"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <StatTile
          label={`Trips (${range.label})`}
          value={loading ? "…" : (data?.total_trips ?? 0).toLocaleString()}
        />
        <StatTile
          label="Busiest hour"
          value={loading || !peak ? "…" : `${String(peak.hour_of_day).padStart(2, "0")}:00`}
          tone="accent"
        />
        <StatTile
          label="Peak avg trips/day"
          value={loading || !peak ? "…" : peak.avg_trips_per_day.toFixed(1)}
        />
      </div>

      <Card title="Demand by hour of day" subtitle="Average trips started per day, by hour">
        {data && (
          <DemandCurveChart
            data={data.by_hour.map((h) => ({ hour_of_day: h.hour_of_day, avg: h.avg_trips_per_day }))}
            valueKey="avg"
            format="raw"
          />
        )}
      </Card>

      {forecast && (
        <Card
          title="7-day forecast"
          subtitle={`${forecast.method}, based on ${forecast.history_days_used} days of history — a stretch baseline, not independently validated per station`}
        >
          <ForecastChart data={forecast.forecast} />
        </Card>
      )}
    </div>
  );
}
