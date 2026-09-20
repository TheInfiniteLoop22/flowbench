# FlowBench — Phase-Wise Implementation Plan

> Living document. Check items off as they're done. If a phase's scope
> changes mid-flight, edit it here directly and log the *why* in
> [PROGRESS_LOG.md](PROGRESS_LOG.md) — this file should always reflect the
> current plan, not the original one.

Legend: ⬜ not started · 🟡 in progress · ✅ done · ❌ cut/deferred

## Phase 0 — Repo & docs setup
- [x] Repo structure, README, docs suite (this file, SPEC, bug tracker, progress log, ADRs)
- [x] GitHub repo created and pushed
- [ ] `.gitignore`, license (optional)

## Phase 1 — Data + staging ✅
- [x] Identify and download a bounded date range of Citi Bike CSVs (target: 12 months) — 2025-09 through 2026-08
- [x] Resolve open question #1 (exact window) and #2 (station ID stability) — updated SPEC.md
- [x] Python ELT script: download → load into `stg_trips_raw` (Postgres, local via Docker Compose)
- [x] Data-quality checks: row counts vs. source, null audit, duplicate check
- [x] Document findings in PROGRESS_LOG.md

## Phase 2 — Warehouse ✅
- [x] Write SQL migration scripts for star schema (`fact_trips`, `dim_station`, `dim_time`, `dim_user_type`)
- [x] PostGIS setup, `geom` column on `dim_station`, distance calc for `fact_trips.distance_m`
- [x] Build and materialize `station_hourly_balance`
- [x] Sanity check: inflow/outflow reconcile exactly to `fact_trips`; system-wide net explained and documented (not silently accepted — see FB-005)

## Phase 3 — Analysis library ✅
- [x] Query 1: demand by station/hour — peak 17:00 (9.2% of daily demand), trough 04:00 (0.35%)
- [x] Query 2: net inflow/outflow per station (rebalancing signal) — surfaced and fixed [FB-008](BUG_TRACKER.md) before results were trusted
- [x] Query 3: trip-duration distribution by user type — casual 19.8 min avg vs. member 11.6 min avg
- [x] Query 4: weekday/weekend comparison + significance test — resolved via Shapiro-Wilk → Mann-Whitney U (both groups non-normal), p=0.0044
- [x] Query 5: forecasting baseline (resolved open question #4) — 7-day moving average beat linear regression on a validation holdout (empirical choice, not assumed upfront); test MAE=19,423, MAPE=12.4%
- [x] Query 6 (P1): station typology/clustering by demand-curve shape — 330 commuter-hub / 275 leisure / 1,756 mixed
- [x] Query 7 (P1): lost-trip estimate from `station_hourly_balance` — 302,565 estimated lost trips network-wide (0.66% of observed demand)
- [x] Query 8 (P1): rebalancing ROI ranking (feeds `/insights/rebalancing-candidates`) — top 20 ranked, ~90-130 lost trips/truck-hour
- [x] Query 9 (stretch): weather correlation via Open-Meteo (no key) — temp Spearman r=0.833 (p=8.3e-96), precip r=-0.149 (p=0.0042)
- [x] Validate each against a sanity check; record results in [RESULTS.md](RESULTS.md)

All nine query `.sql`/`.py` pairs live under `analysis/` (see `analysis/README.md`).
Two bugs surfaced and fixed/logged during this phase: [FB-008](BUG_TRACKER.md)
(High, fixed — station-ID decimal-formatting duplicates, required a full
warehouse rebuild) and [FB-009](BUG_TRACKER.md) (Low, deferred — a small
residual of genuinely-renumbered station IDs).

## Phase 4 — API ✅
- [x] FastAPI project scaffold (`api/main.py`, `api/db.py` pooled read-only connections, `api/schemas.py`)
- [x] `GET /stations`
- [x] `GET /stations/{id}/demand?range=`
- [x] `GET /network/imbalance?hour=`
- [x] `GET /insights/weekday-vs-weekend`
- [x] `GET /insights/rebalancing-candidates`
- [x] API tests against seeded test warehouse — `api/tests/`, a disposable `flowbench_test` DB (3 stations/14 days/~130 trips), 10 tests passing
- [x] Pick the single slowest/most important query, run `EXPLAIN ANALYZE`,
      add an index or materialized view, record before/after timing —
      `GET /network/imbalance`: 667.9ms → 1.5ms (~445x), see [RESULTS.md](RESULTS.md#performance)

## Phase 5 — Dashboard 🟡 in progress (built, not yet deployed)
- [x] Next.js scaffold, TypeScript, Recharts, MapLibre GL — `dashboard/` (Next.js 16, App Router, Tailwind v4)
- [x] Map view: stations colored by imbalance — `/`, hour-of-day slider, CARTO dark-matter basemap (no API key)
- [x] Station detail view: demand curve — `/stations/[id]`, 7d/30d/90d/all-time range toggle
- [x] City-wide trends view — `/trends`, system-wide hourly demand + weekday/weekend comparison
- [x] Insight report page (numbers + confidence intervals) — `/insights`, live rebalancing ranking + live weekday/weekend test + Phase 3 findings
- [ ] Resolve deployment open question #3 (PostGIS on free tier)
- [ ] Deploy: Postgres (Neon/Supabase), API (Render), frontend (Vercel)

Building the dashboard surfaced three dashboard-page-load-blocking API
queries (fine as one-off analysis scripts, not as live page loads) —
fixed with the same materialized-rollup pattern as the Phase-4
performance artifact. See [RESULTS.md](RESULTS.md#performance):
`/insights/rebalancing-candidates` ~46s → ~30ms,
`/insights/weekday-vs-weekend` ~5.9s → ~35ms. All dashboard pages now
load in well under 200ms end-to-end.

## Phase 6 — Write-up ✅
- [x] Rebalancing finding write-up with numbers + confidence intervals
- [x] Fill in [RESULTS.md](RESULTS.md) headline numbers (scale, findings, ROI ranking) — updated for the combined 51.8M-trip, two-city warehouse; added query 10 (cross-city comparison) results
- [x] Update README with final architecture — data-flow diagram, full
      endpoint list, dashboard routes (screenshots/live links deferred to
      Phase 7, which owns deployment verification)
- [x] Resume bullet(s) drafted from actual delivered scope (not the pitch) — see RESULTS.md "Resume-ready summary"

## Phase 7 — Polish & presentation 🟡 in progress
- [x] 5 of 6 dashboard screenshots embedded in README (station detail,
      trends, insights, simulator, compare) — the map view's WebGL
      basemap rendered blank under headless Playwright automation in
      this sandboxed environment (tile requests returned 200, controls
      painted, canvas stayed black — a headless-GPU capture limitation,
      not an app bug). Retry manually in a real browser, or revisit with
      a different capture tool, to get the 6th.
- [x] One-page insight report exported (PDF) — [docs/flowbench-insight-report.pdf](../docs/flowbench-insight-report.pdf),
      a `page.pdf()` print of the live `/insights` route
- [ ] Live demo links (frontend + API docs) verified working from a clean
      browser session, not just localhost — deferred, needs deployment
      (Neon/Render/Vercel accounts) which the user chose to skip this pass
- [x] Performance benchmark write-up (from Phase 4) added to RESULTS.md — see [RESULTS.md#performance](docs/RESULTS.md#performance)
- [x] Final pass: does a reader with zero context get the headline finding
      in under a minute from the README alone? If not, fix the README, not
      the reader's expectations. — added a "Headline finding" callout
      (90–130 lost trips/truck-hour) right after the intro, and refreshed
      the Status section (it still said Phase 6 was in progress after
      Phase 6 was completed).

## MVP cut line

Per [proposal §12](../new-project-proposal.md#12-mvp-scope): Phases 1–4 +
minimal dashboard (map + one trends chart) + written insight report. The
forecasting baseline (Phase 3, query 5) is the first thing to cut if time
is short — it is explicitly not required to prove the core skill set.

## Advanced / stretch (post-MVP, only if time remains)
- [x] Short-horizon per-station demand forecast — `GET /stations/{id}/forecast`, same 7-day-moving-average method query 5 validated system-wide, applied per-station (not independently re-validated per station); shown on the dashboard's station detail page
- [x] "What-if" rebalancing simulator — `GET /insights/rebalancing-simulator?trucks=&hours_per_shift=&bikes_per_truck_hour=`, greedy ROI-ordered budget allocation; `/simulator` dashboard page with live sliders
- [x] Station typology exposed via API/dashboard (not originally listed here, added during this pass) — `warehouse.station_typology_agg`, `typology` field on `GET /stations`, a map color-mode toggle
- [x] Second city for cross-city comparison — Chicago/Divvy added: `warehouse/migrations/0009_add_city_dimension.sql`, `0010_city_scope_rollups.sql`, combined warehouse rebuilt to 51.8M trips/4,530 stations across both cities, query 10 (`analysis/q10_cross_city.py`) run and validated, dashboard `/compare` page and city switcher live. See RESULTS.md "Cross-city comparison" and [FB-010](BUG_TRACKER.md).

New stretch ideas worth considering if more time remains:
- [ ] Anomaly annotations on the Trends chart — the 2026-02-23 snowstorm
      (docs/RESULTS.md "Performance" aside) is a concrete example: flag
      days >2 std. deviations from their weekday/weekend baseline
      automatically rather than only when someone happens to notice a
      gap.
- [ ] Expose station clustering (query 6) results as a filterable list
      alongside the map's typology color mode — e.g. "show only
      commuter-hub stations" — the data already exists in
      `station_typology_agg`, this is a small UI addition on top of it.
