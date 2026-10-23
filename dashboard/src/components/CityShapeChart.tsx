"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function CityShapeChart({
  data,
}: {
  data: Array<{ hour_of_day: number; new_york: number; chicago: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="hour_of_day"
          tickFormatter={(h) => `${String(h).padStart(2, "0")}:00`}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          axisLine={{ stroke: "var(--border)" }}
          tickLine={false}
          interval={1}
        />
        <YAxis
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={48}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip
          contentStyle={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            fontSize: 12,
          }}
          labelFormatter={(h) => `${String(h).padStart(2, "0")}:00`}
          formatter={(v) => `${(Number(v) * 100).toFixed(1)}%`}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="new_york" name="New York" stroke="var(--accent)" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="chicago" name="Chicago" stroke="#f2a63a" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}
