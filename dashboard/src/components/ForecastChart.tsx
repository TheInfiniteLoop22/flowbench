"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ForecastDay } from "@/lib/api";

export function ForecastChart({ data }: { data: ForecastDay[] }) {
  // Recharts needs one row per x-value with separate keys per series so
  // the dashed forecast line doesn't connect back through the solid
  // history line — duplicate the boundary point so the two segments meet.
  const rows = data.map((d, i) => {
    const prevIsHistory = i > 0 && !data[i - 1].is_forecast;
    const isBoundary = d.is_forecast && prevIsHistory;
    return {
      date: d.date.slice(5),
      history: !d.is_forecast || isBoundary ? d.trip_count : null,
      forecast: d.is_forecast || isBoundary ? d.trip_count : null,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          axisLine={{ stroke: "var(--border)" }}
          tickLine={false}
          interval={Math.ceil(rows.length / 10)}
        />
        <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          contentStyle={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="history" name="Actual" stroke="var(--accent)" dot={false} strokeWidth={2} connectNulls={false} />
        <Line
          type="monotone"
          dataKey="forecast"
          name="Forecast (7d moving avg)"
          stroke="#f2a63a"
          strokeDasharray="4 3"
          dot={false}
          strokeWidth={2}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
