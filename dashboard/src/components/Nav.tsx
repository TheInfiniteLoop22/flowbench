"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const LINKS = [
  { href: "/", label: "Network Map", short: "Map", icon: "◉" },
  { href: "/trends", label: "Trends", short: "Trends", icon: "△" },
  { href: "/insights", label: "Insights", short: "Insights", icon: "✦" },
  { href: "/simulator", label: "Simulator", short: "Simulate", icon: "⚙" },
  { href: "/compare", label: "Compare Cities", short: "Compare", icon: "⇄" },
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
  const showCity = pathname !== "/compare";

  const setCity = (next: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("city", next);
    router.push(`${pathname}?${params.toString()}`);
  };

  const hrefFor = (href: string) => (href === "/compare" ? href : `${href}?city=${city}`);
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);

  const citySwitch = (
    <div
      role="group"
      aria-label="City"
      className="flex gap-1 rounded-lg border border-border bg-surface-2 p-1"
    >
      {CITIES.map((c) => (
        <button
          key={c.value}
          onClick={() => setCity(c.value)}
          aria-pressed={city === c.value}
          className={`flex-1 whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            city === c.value ? "bg-accent-soft text-accent" : "text-muted hover:text-foreground"
          }`}
        >
          {c.label}
        </button>
      ))}
    </div>
  );

  return (
    <>
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4 md:hidden">
        <Link href={hrefFor("/")} className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_10px_var(--accent)]" />
          <span className="text-sm font-semibold tracking-wide text-foreground">FlowBench</span>
        </Link>
        {showCity && citySwitch}
      </header>

      <nav
        aria-label="Primary"
        className="hidden shrink-0 border-r border-border bg-surface md:flex md:h-full md:w-56 md:flex-col md:px-3 md:py-5"
      >
        <Link href={hrefFor("/")} className="mb-6 flex items-center gap-2 px-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_10px_var(--accent)]" />
          <span className="text-sm font-semibold tracking-wide text-foreground">FlowBench</span>
        </Link>

        {showCity && (
          <div className="mb-4 px-2">
            <div className="mb-1.5 text-[11px] uppercase tracking-wide text-muted">City</div>
            {citySwitch}
          </div>
        )}

        <div className="flex flex-1 flex-col gap-1">
          {LINKS.map((link) => {
            const active = isActive(link.href);
            return (
              <Link
                key={link.href}
                href={hrefFor(link.href)}
                aria-current={active ? "page" : undefined}
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
        <div className="px-2 text-[11px] leading-snug text-muted">
          Citi Bike NYC &amp; Divvy Chicago &middot; 12mo
        </div>
      </nav>

      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-30 flex h-16 border-t border-border bg-surface/95 backdrop-blur md:hidden"
      >
        {LINKS.map((link) => {
          const active = isActive(link.href);
          return (
            <Link
              key={link.href}
              href={hrefFor(link.href)}
              aria-current={active ? "page" : undefined}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] transition-colors ${
                active ? "text-accent" : "text-muted"
              }`}
            >
              <span className="text-base leading-none">{link.icon}</span>
              {link.short}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
