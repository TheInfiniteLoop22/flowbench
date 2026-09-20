# FlowBench Dashboard (Phase 5)

Next.js 16 (App Router, TypeScript, Tailwind v4), Recharts, and MapLibre
GL over the [FlowBench API](../api/README.md). See
[docs/SPEC.md §6](../docs/SPEC.md#6-dashboard) for the required views.

## Run locally

Requires the API running (`uvicorn api.main:app` from the repo root, or
`docker-compose up` + `python etl/build_warehouse.py` first if you
haven't built the warehouse yet):

```
cp .env.local.example .env.local   # points at http://127.0.0.1:8000
npm install
npm run dev
```

Open `http://localhost:3000`.

## Pages

- **`/` — Network map**: every station on a MapLibre dark basemap
  (CARTO's free `dark-matter` style, no API key), colored and sized by
  net inflow/outflow at a selectable hour-of-day (slider, 0–23), or
  colored by typology (commuter-hub/leisure/mixed). Click a station for
  its net balance and a link to its demand curve.
- **`/stations/[id]` — Station detail**: hourly demand curve for one
  station, a 7d/30d/90d/all-time range toggle, and a 7-day forecast
  (stretch: `analysis`'s moving-average baseline applied per-station).
- **`/trends` — City-wide trends**: system-wide hourly demand curve,
  peak/trough stats, and the weekday-vs-weekend finding with its test
  statistic.
- **`/insights` — Insight report**: the live rebalancing-candidates
  ranking (query params exposed: truck capacity), the live
  weekday/weekend test result, and the remaining Phase 3 findings
  (duration by user type, weather correlation, lost-trip estimate,
  station typology — NYC only) recorded from `docs/RESULTS.md`.
- **`/simulator` — What-if rebalancing simulator** (stretch): pick a
  truck fleet (count × shift length × bikes/truck-hour) and see which
  stations it would reach and how many of the estimated lost trips it
  would recover, computed via `GET /insights/rebalancing-simulator`.
- **`/compare` — Compare cities** (stretch, second city): NYC (Citi
  Bike) vs. Chicago (Divvy) side by side — scale, demand-curve shape
  (normalized so the very different absolute volumes don't hide whether
  the *rhythm* is similar), and the weekday/weekend effect in each city.

A city selector in the nav (New York / Chicago) drives every page except
Compare via a `?city=` URL param, so links stay shareable.

## Design

Dark-first, single accent color (teal, `--accent` in `globals.css`) — a
deliberately narrow palette so the map's red/teal inflow-outflow color
scale reads unambiguously as the one place color carries meaning.
Cards, stat tiles, and the nav live in `src/components/`; there's no
design-system dependency, just Tailwind utility classes against the CSS
custom properties in `src/app/globals.css`.

## Performance note

The first two builds of this dashboard exposed three slow API queries
(`/network/imbalance`: 668ms &rarr; 1.5ms; `/insights/rebalancing-candidates`:
~46s &rarr; ~30ms; `/insights/weekday-vs-weekend`: ~5.9s &rarr; ~35ms) that
were fine as one-off analysis scripts (Phase 3) but not as
dashboard-page-load-blocking API calls. All three were fixed the same
way: a materialized rollup refreshed once per warehouse build instead of
recomputing the aggregate on every request — see
`warehouse/migrations/0004-0007_*.sql` and
[docs/RESULTS.md](../docs/RESULTS.md#performance).
