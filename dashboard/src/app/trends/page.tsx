import type { Metadata } from "next";
import { api, CITY_LABELS, type City } from "@/lib/api";
import { Card, StatTile } from "@/components/Card";
import { DemandCurveChart } from "@/components/DemandCurveChart";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Trends" };
export const maxDuration = 60;

export default async function TrendsPage({ searchParams }: PageProps<"/trends">) {
  const { city: cityParam } = await searchParams;
  const city = (cityParam === "chicago" ? "chicago" : "new_york") as City;

  const [demand, wvw] = await Promise.all([api.networkDemand(city), api.weekdayVsWeekend(city)]);

  const totalTrips = demand.reduce((sum, d) => sum + d.trip_count, 0);
  const peak = demand.reduce((a, b) => (b.trip_count > a.trip_count ? b : a));
  const trough = demand.reduce((a, b) => (b.trip_count < a.trip_count ? b : a));
  const chartData = demand.map((d) => ({ hour_of_day: d.hour_of_day, trips: d.trip_count }));

  const barData = [
    { label: "Weekday", value: wvw.weekday_mean_trips_per_day },
    { label: "Weekend", value: wvw.weekend_mean_trips_per_day },
  ];
  const maxBar = Math.max(...barData.map((b) => b.value));

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-lg font-semibold">City-wide trends &mdash; {CITY_LABELS[city]}</h1>
        <p className="mt-1 text-sm text-muted">
          {totalTrips.toLocaleString()} trips, 12-month window (2025-09 &ndash; 2026-08).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatTile label="Total trips" value={totalTrips.toLocaleString()} />
        <StatTile
          label="Peak hour"
          value={`${String(peak.hour_of_day).padStart(2, "0")}:00`}
          hint={`${((peak.trip_count / totalTrips) * 100).toFixed(1)}% of daily demand`}
          tone="accent"
        />
        <StatTile
          label="Trough hour"
          value={`${String(trough.hour_of_day).padStart(2, "0")}:00`}
          hint={`${((trough.trip_count / totalTrips) * 100).toFixed(2)}% of daily demand`}
        />
        <StatTile
          label="Peak / trough ratio"
          value={`${(peak.trip_count / trough.trip_count).toFixed(1)}x`}
        />
      </div>

      <Card title="Demand by hour of day" subtitle="System-wide trip count, summed across every day in the window">
        <DemandCurveChart data={chartData} valueKey="trips" format="millions" />
      </Card>

      <Card
        title="Weekday vs. weekend"
        subtitle={`${wvw.test_used}, p = ${wvw.p_value < 0.001 ? "< 0.001" : wvw.p_value.toFixed(4)} (n=${wvw.weekday_days} weekday / ${wvw.weekend_days} weekend days, ${wvw.holidays_excluded} holidays excluded)`}
      >
        <div className="space-y-3">
          {barData.map((b) => (
            <div key={b.label} className="flex items-center gap-3">
              <div className="w-20 shrink-0 text-sm text-muted">{b.label}</div>
              <div className="h-6 flex-1 overflow-hidden rounded-md bg-surface-2">
                <div
                  className="h-full rounded-md bg-accent"
                  style={{ width: `${(b.value / maxBar) * 100}%` }}
                />
              </div>
              <div className="w-24 shrink-0 text-right text-sm tabular-nums text-foreground">
                {Math.round(b.value).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted">
          Weekdays average{" "}
          <span className="font-medium text-accent">{(wvw.pct_difference * 100).toFixed(1)}% more</span>{" "}
          trips/day than weekends, a statistically significant difference.
        </p>
      </Card>
    </div>
  );
}
