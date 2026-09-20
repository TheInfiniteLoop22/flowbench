import type { ReactNode } from "react";

export function Card({
  title,
  subtitle,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl border border-border bg-surface p-5 ${className}`}>
      {title && (
        <div className="mb-4">
          <h2 className="text-sm font-medium text-foreground">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}

export function StatTile({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "accent" | "danger";
}) {
  const valueColor =
    tone === "accent" ? "text-accent" : tone === "danger" ? "text-danger" : "text-foreground";
  return (
    <div className="rounded-xl border border-border bg-surface-2 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${valueColor}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}
