"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const LINKS = [
  { href: "/", label: "Network Map", icon: "◉" },
  { href: "/trends", label: "Trends", icon: "△" },
  { href: "/insights", label: "Insights", icon: "✦" },
  { href: "/simulator", label: "Simulator", icon: "⚙" },
  { href: "/compare", label: "Compare Cities", icon: "⇄" },
];

const CITIES: Array<{ value: string; label: string }> = [
  { value: "new_york", label: "New York" },
  { value: "chicago", label: "Chicago" },
];

export function Nav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const city = searchParams.get("city") ?? "new_york";

  const setCity = (next: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("city", next);
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <nav className="flex h-14 shrink-0 items-center gap-1 border-b border-border bg-surface px-4 md:h-full md:w-56 md:flex-col md:items-stretch md:gap-1 md:border-b-0 md:border-r md:px-3 md:py-5">
      <div className="mr-4 flex items-center gap-2 md:mb-6 md:mr-0 md:px-2">
        <span className="inline-block h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_10px_var(--accent)]" />
        <span className="text-sm font-semibold tracking-wide text-foreground">FlowBench</span>
      </div>

      {pathname !== "/compare" && (
        <div className="hidden md:mb-4 md:block md:px-2">
          <div className="text-[11px] uppercase tracking-wide text-muted">City</div>
          <div className="mt-1.5 flex gap-1 rounded-lg border border-border bg-surface-2 p-1">
            {CITIES.map((c) => (
              <button
                key={c.value}
                onClick={() => setCity(c.value)}
                className={`flex-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                  city === c.value ? "bg-accent-soft text-accent" : "text-muted hover:text-foreground"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-1 items-center gap-1 md:flex-col md:items-stretch md:gap-1">
        {LINKS.map((link) => {
          const active = pathname === link.href;
          const href = link.href === "/compare" ? link.href : `${link.href}?city=${city}`;
          return (
            <Link
              key={link.href}
              href={href}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:bg-surface-2 hover:text-foreground"
              }`}
            >
              <span className="text-xs opacity-80">{link.icon}</span>
              {link.label}
            </Link>
          );
        })}
      </div>
      <div className="hidden text-[11px] leading-snug text-muted md:block md:px-2">
        Citi Bike NYC &amp; Divvy Chicago &middot; 12mo
      </div>
    </nav>
  );
}
