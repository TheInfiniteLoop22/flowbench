"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, CITY_LABELS, type City, type RebalancingSimulation } from "@/lib/api";
import { Card, StatTile } from "@/components/Card";

export function SimulatorClient() {
  const searchParams = useSearchParams();
  const city = (searchParams.get("city") === "chicago" ? "chicago" : "new_york") as City;
  const [trucks, setTrucks] = useState(2);
  const [hoursPerShift, setHoursPerShift] = useState(8);
  const [bikesPerTruckHour, setBikesPerTruckHour] = useState(20);
  const [sim, setSim] = useState<RebalancingSimulation | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .rebalancingSimulator(trucks, hoursPerShift, bikesPerTruckHour, city)
      .then((s) => {
        setSim(s);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [trucks, hoursPerShift, bikesPerTruckHour, city]);

  const pctRecovered = sim && sim.total_lost_trips_recoverable > 0
    ? sim.total_recovered_trips / sim.total_lost_trips_recoverable
    : 0;

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-lg font-semibold">What-if rebalancing simulator &mdash; {CITY_LABELS[city]}</h1>
        <p className="mt-1 text-sm text-muted">
          The 12-month lost-trip estimate (query 7) and rebalancing ranking (query 8) are both totals over
          the whole window &mdash; this simulator spends a single truck-hour budget (fleet size &times; shift
          length) against that ranked list, highest-ROI station first, to show which stations a given fleet
          would reach and how much of the {sim ? Math.round(sim.total_lost_trips_recoverable).toLocaleString() : "…"}
          -trip addressable total it would recover, not a literal per-day rate.
        </p>
      </div>

      <Card title="Fleet assumptions">
        <div className="grid gap-5 sm:grid-cols-3">
          <Slider label="Trucks" value={trucks} min={1} max={20} onChange={setTrucks} />
          <Slider label="Hours / shift" value={hoursPerShift} min={1} max={16} onChange={setHoursPerShift} />
          <Slider
            label="Bikes moved / truck-hour"
            value={bikesPerTruckHour}
            min={5}
            max={50}
            onChange={setBikesPerTruckHour}
          />
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatTile label="Daily truck-hour budget" value={sim ? sim.budget_hours.toFixed(1) : "…"} />
        <StatTile
          label="Stations reachable"
          value={sim ? `${sim.stations_covered}` : "…"}
          hint={sim ? `${sim.stations_fully_covered} fully serviced` : undefined}
        />
        <StatTile
          label="Trips recovered"
          value={sim ? Math.round(sim.total_recovered_trips).toLocaleString() : "…"}
          tone="accent"
        />
        <StatTile label="Share of addressable total" value={sim ? `${(pctRecovered * 100).toFixed(1)}%` : "…"} />
      </div>

      <Card
        title="Allocation"
        subtitle={loading ? "recalculating…" : `${sim?.allocations.length ?? 0} stations serviced by this budget`}
      >
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-surface">
              <tr className="border-b border-border text-xs uppercase tracking-wide text-muted">
                <th className="py-2 pr-4 font-medium">Station</th>
                <th className="py-2 pr-4 font-medium text-right">Truck-hours</th>
                <th className="py-2 pr-4 font-medium text-right">Trips recovered</th>
                <th className="py-2 pl-4 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {sim?.allocations.map((a, i) => (
                <tr key={a.station_id} className="border-b border-border/60 last:border-0">
                  <td className="py-2 pr-4">
                    <span className="mr-2 text-muted">{i + 1}.</span>
                    {a.name}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums">{a.truck_hours_used.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-right tabular-nums text-accent">
                    {a.trips_recovered.toFixed(0)}
                  </td>
                  <td className="py-2 pl-4 text-right text-xs">
                    {a.fully_covered ? (
                      <span className="text-accent">fully covered</span>
                    ) : (
                      <span className="text-muted">partial (budget exhausted)</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium text-muted">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-foreground">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-accent"
      />
    </div>
  );
}
