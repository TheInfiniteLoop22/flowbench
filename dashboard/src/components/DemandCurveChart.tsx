"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Server Components can't pass functions to Client Components (not
// serializable across the boundary) — a string enum instead of a
// yFormatter callback prop keeps this usable from both.
const FORMATTERS: Record<string, (v: number) => string> = {
  raw: (v) => v.toFixed(0),
  millions: (v) => `${(v / 1_000_000).toFixed(1)}M`,
};

export function DemandCurveChart({
  data,
  valueKey,
  color = "var(--accent)",
  format = "raw",
}: {
  data: Array<Record<string, number>>;
  valueKey: string;
  color?: string;
  format?: keyof typeof FORMATTERS;
}) {
  const yFormatter = FORMATTERS[format];
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="demandFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
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
          tickFormatter={(v) => (yFormatter ? yFormatter(v) : String(v))}
          width={48}
        />
        <Tooltip
          contentStyle={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            fontSize: 12,
          }}
          labelFormatter={(h) => `${String(h).padStart(2, "0")}:00`}
          formatter={(v) => [yFormatter ? yFormatter(Number(v)) : v, "trips"]}
        />
        <Area type="monotone" dataKey={valueKey} stroke={color} strokeWidth={2} fill="url(#demandFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
