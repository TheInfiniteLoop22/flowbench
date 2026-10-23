import type { Metadata } from "next";
import Link from "next/link";
import { api, CITY_LABELS, type City, type StationImbalance } from "@/lib/api";
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
    stat: "Spearman r = 0.833, p = 1.2×10⁻⁹⁵",
    detail:
      "n=367 days, via Open-Meteo's free historical archive. Precipitation has a smaller but still significant effect (r=-0.149, p=0.0042); days with >1mm precipitation average 11.8% fewer trips than dry days.",
  },
] as const;

export default async function InsightsPage({ searchParams }: PageProps<"/insights">) {
  const { city: cityParam } = await searchParams;
  const city = (cityParam === "chicago" ? "chicago" : "new_york") as City;

  const [wvw, morning, evening] = await Promise.all([
    api.weekdayVsWeekend(city),
    api.networkImbalance(8, city),
    api.networkImbalance(17, city),
  ]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-lg font-semibold">Insight report &mdash; {CITY_LABELS[city]}</h1>
        <p className="mt-1 text-sm text-muted">
          Numbers with a live badge are computed on request from the current warehouse for the
          selected city; the rest are NYC-specific findings recorded in the README (Chicago equivalents not yet computed — see{" "}
          <code className="text-[11px]">analysis/q09_cross_city.py</code>).
        </p>
      </div>

      <Card
        title="Weekdays vs. weekends"
        subtitle={`${wvw.test_used}, ${wvw.weekday_days} weekdays vs ${wvw.weekend_days} weekend days (holidays excluded)`}
      >
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" /> live
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Weekday mean" value={Math.round(wvw.weekday_mean_trips_per_day).toLocaleString()} />
          <StatTile label="Weekend mean" value={Math.round(wvw.weekend_mean_trips_per_day).toLocaleString()} />
          <StatTile
            label="Difference (raw)"
            value={`${wvw.pct_difference >= 0 ? "+" : ""}${(wvw.pct_difference * 100).toFixed(1)}%`}
            hint={formatP(wvw.p_value)}
          />
          {wvw.adjusted_pct_difference != null && wvw.adjusted_p_value != null && (
            <StatTile
              label="Season-adjusted"
              value={`${wvw.adjusted_pct_difference >= 0 ? "+" : ""}${(wvw.adjusted_pct_difference * 100).toFixed(1)}%`}
              tone="accent"
              hint={formatP(wvw.adjusted_p_value)}
            />
          )}
        </div>
        <p className="mt-3 text-xs leading-relaxed text-muted">
          Daily trips swing far more with the seasons than with the weekday, so the raw comparison understates
          the weekday effect (especially in Chicago). The season-adjusted figure divides each day by the mean of
          the surrounding 29 days before comparing.
        </p>
      </Card>

      <Card
        title="Rush-hour imbalance"
        subtitle="Average net bikes per hour (arrivals minus departures) at the most-affected stations"
      >
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" /> live
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <ImbalanceList hour={8} rows={morning} />
          <ImbalanceList hour={17} rows={evening} />
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

        </>
      ) : (
        <Card>
          <p className="text-sm text-muted">
            Duration-by-user-type and weather-correlation findings were computed for NYC
            only. See{" "}
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

function ImbalanceList({ hour, rows }: { hour: number; rows: StationImbalance[] }) {
  const bleeding = rows.slice(0, 5);
  const filling = rows.slice(-5).reverse();
  const item = (r: StationImbalance) => (
    <li key={r.station_id} className="flex justify-between gap-3 py-1 text-sm">
      <Link
        href={`/stations/${encodeURIComponent(r.station_id)}`}
        className="truncate text-foreground underline-offset-2 hover:text-accent hover:underline"
      >
        {r.name}
      </Link>
      <span className={`tabular-nums ${r.avg_net_balance < 0 ? "text-danger" : "text-accent"}`}>
        {r.avg_net_balance > 0 ? "+" : ""}
        {r.avg_net_balance.toFixed(1)}
      </span>
    </li>
  );
  return (
    <div>
      <div className="text-sm font-medium">{String(hour).padStart(2, "0")}:00</div>
      <div className="mt-2 text-xs uppercase tracking-wide text-muted">Emptying fastest</div>
      <ul>{bleeding.map(item)}</ul>
      <div className="mt-3 text-xs uppercase tracking-wide text-muted">Filling fastest</div>
      <ul>{filling.map(item)}</ul>
    </div>
  );
}

function formatP(p: number) {
  return p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(4)}`;
}
