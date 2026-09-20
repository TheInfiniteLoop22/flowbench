import type { Metadata } from "next";
import { api } from "@/lib/api";
import { Card, StatTile } from "@/components/Card";
import { CityShapeChart } from "@/components/CityShapeChart";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Compare cities" };
export const maxDuration = 60;

export default async function ComparePage() {
  const [cityStats, nycDemand, chiDemand, nycWvw, chiWvw] = await Promise.all([
    api.cities(),
    api.networkDemand("new_york"),
    api.networkDemand("chicago"),
    api.weekdayVsWeekend("new_york"),
    api.weekdayVsWeekend("chicago"),
  ]);

  const nyc = cityStats.find((c) => c.city === "new_york");
  const chi = cityStats.find((c) => c.city === "chicago");

  const nycTotal = nycDemand.reduce((s, d) => s + d.trip_count, 0);
  const chiTotal = chiDemand.reduce((s, d) => s + d.trip_count, 0);
  const chiByHour = new Map(chiDemand.map((d) => [d.hour_of_day, d.trip_count]));
  const shapeData = nycDemand.map((d) => ({
    hour_of_day: d.hour_of_day,
    new_york: d.trip_count / nycTotal,
    chicago: (chiByHour.get(d.hour_of_day) ?? 0) / chiTotal,
  }));

  const nycPeak = nycDemand.reduce((a, b) => (b.trip_count > a.trip_count ? b : a));
  const chiPeak = chiDemand.reduce((a, b) => (b.trip_count > a.trip_count ? b : a));

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-lg font-semibold">Compare cities</h1>
        <p className="mt-1 text-sm text-muted">
          NYC (Citi Bike) vs. Chicago (Divvy) &mdash; same 12-month window (2025-09 &ndash; 2026-08), same
          warehouse schema, same query logic. See{" "}
          <code className="text-[11px]">analysis/q10_cross_city.py</code> for the full comparison script.
        </p>
      </div>

      <Card title="Scale">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="NYC trips" value={(nyc?.trip_count ?? 0).toLocaleString()} tone="accent" />
          <StatTile label="NYC stations" value={(nyc?.station_count ?? 0).toLocaleString()} />
          <StatTile label="Chicago trips" value={(chi?.trip_count ?? 0).toLocaleString()} />
          <StatTile label="Chicago stations" value={(chi?.station_count ?? 0).toLocaleString()} />
        </div>
        <p className="mt-3 text-xs text-muted">
          NYC&apos;s network moves {nyc && chi ? (nyc.trip_count / chi.trip_count).toFixed(1) : "…"}x
          Chicago&apos;s trip volume on {nyc && chi ? (nyc.station_count / chi.station_count).toFixed(1) : "…"}x
          the station count.
        </p>
      </Card>

      <Card
        title="Demand shape by hour of day"
        subtitle="Share of each city's own daily total — normalized so the two cities' very different absolute volumes don't hide whether the *rhythm* of demand is similar"
      >
        <CityShapeChart data={shapeData} />
        <p className="mt-3 text-xs text-muted">
          NYC peaks at {String(nycPeak.hour_of_day).padStart(2, "0")}:00, Chicago at{" "}
          {String(chiPeak.hour_of_day).padStart(2, "0")}:00.
        </p>
      </Card>

      <Card title="Weekday vs. weekend, both cities">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted">New York</div>
            <div className="mt-2 text-2xl font-semibold text-accent">
              {nycWvw.pct_difference >= 0 ? "+" : ""}
              {(nycWvw.pct_difference * 100).toFixed(1)}%
            </div>
            <p className="mt-1 text-xs text-muted">
              weekday vs. weekend, {nycWvw.test_used},{" "}
              {nycWvw.p_value < 0.001 ? "p < 0.001" : `p = ${nycWvw.p_value.toFixed(4)}`}
            </p>
          </div>
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted">Chicago</div>
            <div className="mt-2 text-2xl font-semibold text-accent">
              {chiWvw.pct_difference >= 0 ? "+" : ""}
              {(chiWvw.pct_difference * 100).toFixed(1)}%
            </div>
            <p className="mt-1 text-xs text-muted">
              weekday vs. weekend, {chiWvw.test_used},{" "}
              {chiWvw.p_value < 0.001 ? "p < 0.001" : `p = ${chiWvw.p_value.toFixed(4)}`}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
