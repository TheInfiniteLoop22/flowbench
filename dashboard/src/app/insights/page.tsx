import type { Metadata } from "next";
import Link from "next/link";
import { api, CITY_LABELS, type City } from "@/lib/api";
import { Card, StatTile } from "@/components/Card";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Insights" };
export const maxDuration = 60;

const NYC_FINDINGS = [
  {
    title: "Casual riders take much longer trips than members",
    stat: "19.8 min vs. 11.6 min avg",
    detail:
      "Casual: mean 19.8 min (median 12.7 min, n=7,938,556). Member: mean 11.6 min (median 8.4 min, n=37,749,147) — casual trips run ~70% longer, consistent with leisure vs. commute usage.",
  },
  {
    title: "Temperature is a strong driver of system-wide demand",
    stat: "Spearman r = 0.833, p = 8.3×10⁻⁹⁶",
    detail:
      "n=367 days, via Open-Meteo's free historical archive. Precipitation has a smaller but still significant effect (r=-0.149, p=0.0042); days with >1mm precipitation average 11.8% fewer trips than dry days.",
  },
  {
    title: "An estimated 302,565 trips were lost to stockouts",
    stat: "0.66% of observed demand, 12 months",
    detail:
      "Stations running structurally low relative to their own typical range (a stated-assumption relative-inventory model, not a measured stockout count) — see the rebalancing ranking below for where to act on it.",
  },
] as const;

export default async function InsightsPage({ searchParams }: PageProps<"/insights">) {
  const { city: cityParam } = await searchParams;
  const city = (cityParam === "chicago" ? "chicago" : "new_york") as City;

  const [rebalancing, wvw] = await Promise.all([
    api.rebalancingCandidates(city, 20),
    api.weekdayVsWeekend(city),
  ]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-lg font-semibold">Insight report &mdash; {CITY_LABELS[city]}</h1>
        <p className="mt-1 text-sm text-muted">
          Numbers with a live badge are computed on request from the current warehouse for the
          selected city; the rest are recorded NYC-specific findings from{" "}
          <code className="text-[11px]">docs/RESULTS.md</code> (Chicago equivalents not yet computed
          — see <code className="text-[11px]">analysis/q10_cross_city.py</code>).
        </p>
      </div>

      <Card
        title="Rebalancing candidates"
        subtitle="Top 20 stations by estimated lost trips recovered per truck-hour of rebalancing effort (assumption: 1 truck moves 20 bikes/hour)"
      >
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" /> live
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase tracking-wide text-muted">
                <th className="py-2 pr-4 font-medium">Station</th>
                <th className="hidden py-2 pr-4 font-medium text-right sm:table-cell">Stockout episodes</th>
                <th className="py-2 pr-4 font-medium text-right">Est. lost trips</th>
                <th className="hidden py-2 pr-4 font-medium text-right sm:table-cell">Truck-hours</th>
                <th className="py-2 pl-4 font-medium text-right">Trips / truck-hour</th>
              </tr>
            </thead>
            <tbody>
              {rebalancing.map((r, i) => (
                <tr key={r.station_id} className="border-b border-border/60 last:border-0">
                  <td className="py-2 pr-4">
                    <span className="mr-2 text-muted">{i + 1}.</span>
                    <Link
                      href={`/stations/${encodeURIComponent(r.station_id)}`}
                      className="text-foreground underline-offset-2 hover:text-accent hover:underline"
                    >
                      {r.name}
                    </Link>
                  </td>
                  <td className="hidden py-2 pr-4 text-right tabular-nums sm:table-cell">{r.stockout_episodes}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{r.estimated_lost_trips.toFixed(0)}</td>
                  <td className="hidden py-2 pr-4 text-right tabular-nums sm:table-cell">{r.truck_hours_needed.toFixed(1)}</td>
                  <td className="py-2 pl-4 text-right font-medium tabular-nums text-accent">
                    {r.lost_trips_per_truck_hour.toFixed(1)}
                  </td>
                </tr>
              ))}
              {rebalancing.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-sm text-muted">
                    No qualifying stockout-prone stations for {CITY_LABELS[city]} (needs &ge;10
                    recurring episodes to rank — see analysis/queries/08_rebalancing_roi.sql).
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Weekdays vs. weekends" subtitle={wvw.test_used}>
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" /> live
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Weekday mean" value={Math.round(wvw.weekday_mean_trips_per_day).toLocaleString()} />
          <StatTile label="Weekend mean" value={Math.round(wvw.weekend_mean_trips_per_day).toLocaleString()} />
          <StatTile
            label="Difference"
            value={`${wvw.pct_difference >= 0 ? "+" : ""}${(wvw.pct_difference * 100).toFixed(1)}%`}
            tone="accent"
          />
          <StatTile
            label="Significance"
            value={wvw.p_value < 0.001 ? "p < 0.001" : `p = ${wvw.p_value.toFixed(4)}`}
          />
        </div>
      </Card>

      {city === "new_york" ? (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            {NYC_FINDINGS.map((f) => (
              <Card key={f.title} className="flex flex-col">
                <div className="text-sm font-medium text-foreground">{f.title}</div>
                <div className="mt-2 text-xl font-semibold text-accent">{f.stat}</div>
                <p className="mt-2 text-xs leading-relaxed text-muted">{f.detail}</p>
              </Card>
            ))}
          </div>

          <Card
            title="Station typology"
            subtitle="NTILE(3) commute-index / weekend-share buckets over 2,361 stations with ≥100 trips"
          >
            <div className="grid grid-cols-3 gap-4">
              <StatTile label="Commuter-hub" value="330" hint="e.g. W 21st St & 6th Ave" />
              <StatTile label="Leisure" value="275" hint="e.g. W 4th St & 7th Ave S" />
              <StatTile label="Mixed" value="1,756" />
            </div>
          </Card>
        </>
      ) : (
        <Card>
          <p className="text-sm text-muted">
            Duration-by-user-type, weather-correlation, and typology findings were computed for NYC
            only (Phase 3). See{" "}
            <a href="/compare" className="text-accent hover:underline">
              Compare Cities
            </a>{" "}
            for what has been run against both.
          </p>
        </Card>
      )}
    </div>
  );
}
