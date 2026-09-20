# FlowBench — Progress Log

> Dated, append-only log. Every session that changes scope, hits a
> blocker, makes a non-trivial decision, or diverges from PHASE_PLAN.md
> should get an entry. Newest entry on top. This is the record of *what
> actually happened*, as opposed to SPEC.md (what we intend) and
> PHASE_PLAN.md (what's left).

---

## 2026-09-17 — Project kickoff

**Status**: Planning complete, repo initialized.

- Reviewed and accepted `new-project-proposal.md` as the source pitch.
- Locked two decisions that the proposal left open:
  - Dataset: **Citi Bike (NYC)**, not Divvy.
  - Repo: **public**, named `flowbench`, under github.com/TheInfiniteLoop22.
- Created full docs suite: SPEC.md, PHASE_PLAN.md, BUG_TRACKER.md,
  DECISIONS.md, this log, and README.
- No code written yet. Next session should start Phase 1 (data + staging).

**Open items carried forward**: SPEC.md §2, all four open questions —
none blocking, all scheduled to resolve in the phase where they first
matter.

---

## 2026-09-17 — Scope expansion: bigger analysis library, results scoreboard

User asked for the project to be bigger, more detailed, and to produce
concrete results worth showing — not just a working pipeline. Response
(see [ADR-0004](DECISIONS.md#adr-0004-expand-analysis-library-beyond-the-proposals-mvp-set-p1-tier)):

- Added 4 P1-tier analytical queries beyond the original 5 (station
  typology/clustering, lost-trip estimate, rebalancing ROI ranking,
  weather correlation via Open-Meteo) — SPEC.md §4, PHASE_PLAN.md Phase 3.
- Added SPEC.md §8, "Results & success bar" — a concrete numeric
  definition of done-and-good (scale processed, ≥3 findings with CIs,
  a quantified rebalancing ranking, a documented perf benchmark, a live
  demo).
- Added [RESULTS.md](RESULTS.md) as a living scoreboard — currently all
  placeholders, to be filled with real numbers starting Phase 3.
- Added Phase 7 (Polish & Presentation) to PHASE_PLAN.md — screenshots,
  one-page report, verified live links, final "does a cold reader get it
  in under a minute" pass.
- MVP cut line unchanged; the new queries are P1 (protect, don't cut)
  rather than MVP-blocking.

---

## 2026-09-17 — Phase 1 complete: data + staging

**Status**: Phase 1 ✅ done. 45,688,697 trip rows staged, zero load
errors, all hard data-quality checks passed.

- Set up `docker-compose.yml` (Postgres 16 + PostGIS 3.4, port 5433,
  named volume) and the migration runner (`etl/run_migrations.py`).
- Built `etl/download_and_load.py`: downloads Citi Bike's monthly zips
  directly from the public S3 bucket (no key), loads each split CSV via
  `COPY` into a temp table then into `staging.stg_trips_raw`, tracks
  loaded files in `staging.load_manifest` for idempotent re-runs.
- **Resolved SPEC.md open questions #1 and #2**: locked the window to
  2025-09 through 2026-08 (most recent complete 12 months at build
  time); confirmed `station_id` is text, not integer, and confirmed a
  single stable 13-column schema across the entire window (no drift to
  handle — simpler than the open question anticipated).
- Ran `etl/dq_checks.py` against the full staged set:
  - 0 null `ride_id`, 0 null timestamps, 0 unrecognized category values
    (all hard checks passed)
  - 153,346 rows (~0.3%) null lat/lng, 482 rows (~0.001%) non-positive
    duration, 512 duplicate `ride_id`s (~0.001%) — logged as
    [FB-001/002/003](BUG_TRACKER.md), all low-severity, all deferred to
    a Phase 2 warehouse-load filter/dedup rather than touched in staging
    (staging should stay a faithful raw copy of the source).
- 2,593 distinct stations observed across start+end station IDs.
- Numbers recorded in [RESULTS.md](RESULTS.md) §Scale.
- Raw zips deleted after each load (`--keep-raw` not used) to keep disk
  usage bounded — staging table (~12 GB) is the retained source of
  truth; re-running the ELT script re-downloads from S3 if needed.

**Diversion from original plan**: none of substance — the schema-drift
risk in open question #2 didn't materialize (schema was identical across
all 12 months), which simplified the loader (no per-month schema
branching needed).

**Next**: Phase 2 (warehouse) — star schema migrations, PostGIS geometry
on `dim_station`, `station_hourly_balance` materialized view, and
resolving the three FB-00x issues at load time via filters/dedup.

---

## 2026-09-17 — Phase 2 complete: warehouse

**Status**: Phase 2 ✅ done. Star schema built, all sanity checks pass.

- Split warehouse SQL into two layers: one-time schema DDL
  (`warehouse/migrations/0002_warehouse_schema.sql`) and idempotent,
  re-runnable transforms (`warehouse/transforms/*.sql`, driven by
  `etl/build_warehouse.py`) — so the warehouse can be rebuilt from
  staging on a schedule without re-migrating, matching the proposal's
  "scheduled batch ELT" design.
- Built `dim_time` (367 days, hardcoded US federal holiday list for the
  window), `dim_user_type`, `dim_station` (2,592 rows, most-recent-
  observation-wins dedup, PostGIS `geometry(Point,4326)`), and
  `fact_trips` (45,687,703 rows) with a PostGIS-computed `distance_m`.
- Resolved FB-002 and FB-003 at warehouse-load time (bad-duration filter,
  `ROW_NUMBER()` dedup on `ride_id`) — staging left untouched, as planned.
- Materialized `station_hourly_balance` (11,875,461 station×hour rows).
- **Hit and fixed a real bug during sanity checks**: max trip distance
  came back as 8,660 km. Traced to a depot/placeholder station
  (`SYS018`, "Bronx WH station") with `(0,0)` coordinates — logged as
  [FB-004](BUG_TRACKER.md), fixed by excluding `(0,0)` in the
  `dim_station` build the same way nulls are excluded. Re-ran the full
  build; max distance is now a sane 35.2 km.
- **Investigated an unexpected sanity-check result rather than
  hand-waving it**: system-wide inflow ≠ outflow by 107,129 trips. My
  first assumption (a date-boundary artifact) was wrong — direct
  counting showed it's a real ~6:1 asymmetry between trips with a
  resolved start-but-not-end station vs. the reverse. Logged as
  [FB-005](BUG_TRACKER.md) and flagged in RESULTS.md as a genuine Phase 3
  finding candidate ("trips that don't return to the network"), not
  swept under the rug.
- Logged two operational notes for later: [FB-006](BUG_TRACKER.md) (the
  fact_trips rebuild takes ~55–58 min — a good Phase 4 optimization
  target) and [FB-007](BUG_TRACKER.md) (local disk at 95%/32GB free —
  not urgent, but tracked).
- Warehouse total size ~25 GB. Numbers recorded in RESULTS.md.

**Diversion from original plan**: discovered TRUNCATE can't touch a
table that's FK-referenced by another, even if that other table is
empty — had to combine `fact_trips` + all three dimension tables into a
single `TRUNCATE ... ,` statement rather than truncating each dim
separately. Documented directly in `000_truncate_fact.sql` so the next
person doesn't hit the same error.

**Next**: Phase 3 (analysis library) — core 5 queries plus the P1 tier
(station typology, lost-trip estimate, rebalancing ROI ranking, weather
correlation), starting with the "unresolved-end-station" finding
surfaced above since it's already half-investigated.

---

## 2026-09-17 — Phase 3 started: analysis library, hit and fixed FB-008

**Status**: 🟡 in progress. Queries 1–4 built under `analysis/`
(`analysis/queries/*.sql` + a same-numbered Python runner each, per
`analysis/README.md`).

- Query 1 (demand by station/hour) ran clean against the existing
  warehouse: sanity check passed, system-wide peak is 17:00 (9.2% of
  daily demand), trough is 04:00 (0.4%).
- **Query 2 (net inflow/outflow per station) surfaced a real bug before
  it became a wrong finding**: the same physical station (identical
  name/lat/lon) showed up as *both* the #1 "bleeder" (near-100% outflow)
  and the #1 "accumulator" (near-100% inflow) — under two different
  `station_id`s (`"5980.1"` vs. `"5980.10"`). Traced to different
  months' source CSVs formatting the same numeric station ID with a
  different number of decimal digits; confirmed 111 station names
  affected this way (`SELECT name, count(DISTINCT station_id) ... HAVING
  count > 1`). Logged as [FB-008](BUG_TRACKER.md) (High — this would
  have directly corrupted the rebalancing ROI ranking, the project's
  headline result).
- **Fixed at the warehouse layer, not by filtering in the query**: added
  `warehouse.normalize_station_id()` (`warehouse/migrations/0003_normalize_station_id.sql`),
  canonicalizing purely-numeric station IDs via Postgres's `trim_scale()`
  so `"5980.1"`/`"5980.10"` collapse to one row; applied it in both
  `003_build_dim_station.sql` (dedup key) and `004_build_fact_trips.sql`
  (join key). Non-numeric placeholder IDs (`SYS016`, `3184.07_OLD`, lab
  stations) are left untouched — confirmed not part of this bug.
- Triggered a full warehouse rebuild (`etl/build_warehouse.py`, ~55–60
  min per FB-006) to apply the fix before trusting *any* per-station
  Phase 3 query. Queries 1–4 will be re-run and re-validated once it
  completes; query 2's numbers captured pre-fix were not recorded to
  RESULTS.md since they're known-wrong.
- Queries 3 (duration by user type) and 4 (weekday/weekend + Shapiro-Wilk-
  gated Welch's-t/Mann-Whitney significance test) are written but not yet
  run against the rebuilt warehouse.

**Next**: re-run and validate queries 1–4 post-rebuild, record real
numbers in RESULTS.md, then move to query 5 (forecasting baseline — the
first thing to cut per the MVP note if time is short) and the P1 tier.

---

## 2026-09-17 — Phase 3 complete: all 9 queries validated

**Status**: Phase 3 ✅ done. Warehouse rebuild (FB-008 fix) completed
(~78 min: `004_build_fact_trips.sql` alone took 4,326s), `warehouse_checks.py`
re-run clean — all Phase 2 reconciliation numbers unchanged (fact_trips
still 45,687,703 rows, FB-005's 107,129 net asymmetry still exact), so the
normalization fix didn't disturb anything it wasn't meant to touch.

- `dim_station` dropped from 2,592 → 2,492 rows. Verified FB-008 directly:
  the previously-split "E 17 St & Broadway" (`5980.1`/`5980.10`) is now a
  single row. Found a small residual, **11 station names still split
  across 22 IDs** — these are genuinely different ID strings (station
  renumbering mid-window, e.g. `"7625.18"`→`"7625.22"`, or `_old`/`_`
  suffixes), not the decimal-formatting bug FB-008 fixed. Logged as
  [FB-009](BUG_TRACKER.md), Low severity, deferred — 22 of 2,492 IDs
  (~0.9%), not worth a name+coordinate re-dedup right now.
- Re-ran query 2 post-fix: the E 17 St/Allen St/N 6 St stations that were
  the #1 bleeder *and* #1 accumulator pre-fix now appear once, with
  sane, much smaller net-imbalance magnitudes (max ~4,000 vs. the
  pre-fix ~40,000 artifact). New top bleeders/accumulators make
  geographic sense (Eastern Pkwy corridor bleeding, Greenwich St/Tribeca
  accumulating).
- **Caught and fixed a second bug during query 5 (forecasting)**: the
  EDA logic picked "linear regression" based on a flawed lag-1-vs-lag-7
  autocorrelation comparison, directly contradicting its own backtest
  (moving average had MAE 19,423 vs. linear regression's 34,050 on the
  same holdout). Root cause: high lag-1 autocorrelation just means the
  series is smooth day-to-day, it says nothing about whether trend beats
  seasonality. Replaced with an empirical decision: pick whichever
  baseline wins a validation holdout carved out *before* the final test
  window, then only report the final window's score for the winner —
  avoids grading a model on the same data used to pick it. Moving average
  won on both splits once the logic was fixed.
- **Caught and fixed a third bug during query 8 (rebalancing ROI)**: the
  first version divided lost-trip estimates by query 2's whole-year net
  deficit, which produced meaningless 1000+ trips/truck-hour ratios for
  stations with near-zero net deficit but a single stockout episode (a
  station can bleed all morning and refill by evening with ~0 net
  effect, yet still cause a real, real lost trip). Redefined effort as
  (number of distinct stockout episodes) × (that station's average
  hourly outflow), and added a `>= 10 episodes` floor to exclude
  one-off flukes — same reliability filter idea as query 6's `>= 100
  trips` floor. Ranking now reads as a real list (Manhattan office
  corridor stations: Park Ave, 5th Ave, E 47-50 St) with defensible
  ratios (~90-130 trips/truck-hour), not noise.
- **Caught a sign/framing bug in query 9's wet-vs-dry-day print**: a
  variable computing a decrease was printed as if it were a raw
  percentage without correcting the framing, making a real 11.8%
  *decrease* on wet days read as a nonsensical "+11.8% trips" increase
  that contradicted the query's own Spearman correlation (r=-0.149,
  negative). Fixed the label to state direction explicitly.
- Headline finding, 4 statistical findings (weekday/weekend, duration by
  user type, temperature/precipitation correlation, lost-trip estimate),
  and the typology/demand-curve/forecast notes are all recorded with real
  numbers in [RESULTS.md](RESULTS.md) — clears the SPEC.md §8 "at least 3
  findings with a number and p-value/CI" bar.
- Confirmed outbound network access works for query 9's Open-Meteo call
  (no key needed, matched trip data 367/367 days) — the stretch query
  wasn't cut.

**Diversion from original plan**: none in scope — all 9 queries (5 core +
4 P1) shipped, none cut, despite the MVP note flagging query 5 as the
first thing to drop if short on time. Three real bugs were found and
fixed *during* analysis rather than after (station-ID duplication, a
flawed model-selection heuristic, a degenerate ROI metric, plus one
reporting sign error) — consistent with this project's stated bar of
investigating anomalies rather than shipping numbers that look plausible
but don't hold up.

**Next**: Phase 4 (API) — FastAPI scaffold, the five read-only endpoints
in SPEC.md §5, and the Phase-4 performance artifact (`EXPLAIN ANALYZE`
before/after on the slowest query — `004_build_fact_trips.sql`'s ~72 min
rebuild, per [FB-006](BUG_TRACKER.md), is the obvious candidate).

---

## 2026-09-17 — Phase 4 complete: API + performance artifact

**Status**: Phase 4 ✅ done. All 5 endpoints live under `api/`, 10 tests
passing against a seeded test warehouse, performance artifact measured
and fixed.

- Built `api/main.py` (FastAPI, lifespan-managed `psycopg2` connection
  pool in `api/db.py`, every connection set read-only) with the 5
  endpoints from SPEC.md §5. `/insights/weekday-vs-weekend` runs the
  same Shapiro-Wilk-gated test selection as `analysis/q04` live, rather
  than serving a cached number, so it stays correct if the warehouse
  changes. `/insights/rebalancing-candidates` exposes the truck-capacity
  assumption (`bikes_per_truck_hour`, default 20) as a query param
  instead of a hardcoded constant.
- Smoke-tested all 5 endpoints against the real 45.7M-row warehouse
  before writing the test suite — numbers matched Phase 3's `analysis/`
  output exactly (e.g. `/insights/weekday-vs-weekend`'s p=0.0044 matches
  RESULTS.md).
- **API tests against a seeded test warehouse (SPEC.md §7)**: rather than
  mocking the DB layer, `api/tests/conftest.py` spins up a real, separate
  `flowbench_test` Postgres database (same local instance, `DROP
  DATABASE`/`CREATE DATABASE` each session) and seeds a small fixture (3
  stations, 14 days, ~130 trips) by running the real
  `warehouse/migrations/*.sql` against it — so tests exercise the actual
  schema and SQL, not a fake. Caught two fixture bugs before they became
  false-negative test coverage: (1) a first fixture draft gave every
  calendar day an identical trip count, which is zero-variance and made
  Shapiro-Wilk return `nan` and crash JSON serialization on
  `/insights/weekday-vs-weekend` — fixed by adding a day-varying "bonus"
  trip batch; (2) too few weekend days (1) tripped the endpoint's `>= 3
  samples per group` guard — fixed by widening the fixture from 6 to 14
  days.
- **Performance artifact (SPEC.md §8)**: `GET /network/imbalance`
  aggregated all 11.8M `station_hourly_balance` rows per request.
  `EXPLAIN ANALYZE` showed a parallel seq scan + external-merge sort,
  667.9ms execution. Added `warehouse.station_hourly_balance_hourly_agg`
  (a ~60k-row rollup: station × hour-of-day → avg net balance) with a
  unique index, refreshed once per warehouse build instead of computed
  per request — re-ran `EXPLAIN ANALYZE`: bitmap index scan, 1.5ms
  execution, **~445x**. Documented in RESULTS.md "Performance" with the
  actual `EXPLAIN ANALYZE` plans.
- New migration `0004_station_hourly_balance_hourly_agg.sql` and
  transform `006_refresh_station_hourly_balance_hourly_agg.sql` — picked
  up automatically by `etl/build_warehouse.py`'s existing glob-and-sort
  logic, no changes needed there.

**Diversion from original plan**: none — all 5 endpoints, the test
suite, and the performance artifact all shipped as scoped.

**Next**: Phase 5 (Dashboard) — Next.js scaffold, map view (imbalance),
station detail view, city-wide trends, insight report page; resolve
SPEC.md open question #3 (PostGIS on the deployment host's free tier)
before picking Neon vs. Supabase.

---

## 2026-09-17 — Phase 5 (dashboard) built, not yet deployed

**Status**: 🟡 in progress. `dashboard/` (Next.js 16 App Router + TS +
Tailwind v4 + Recharts + MapLibre GL) has all four required views working
against the local API; deployment (Vercel/Render/Neon) is the remaining
Phase 5 item.

- `/` — network map (MapLibre, CARTO's free `dark-matter` basemap, no API
  key) with an hour-of-day slider driving `/network/imbalance`; stations
  colored red→teal by net balance, click for a popup + link to detail.
- `/stations/[id]` — demand curve (Recharts) with a 7d/30d/90d/all-time
  toggle against `/stations/{id}/demand`.
- `/trends` — system-wide hourly demand curve + the weekday/weekend
  finding, both live from the API.
- `/insights` — live rebalancing-candidates table and weekday/weekend
  test result, plus the remaining Phase 3 findings (duration by user
  type, weather correlation, lost-trip estimate, typology) recorded as
  static content from RESULTS.md (no live endpoint for those — they're
  one-off analysis findings, not parametrized queries).
- Added one new endpoint, `GET /network/demand` (system-wide hourly
  demand, backed by a new `warehouse.demand_by_hour_agg` rollup), needed
  by the Trends page and not previously exposed.
- **Building the dashboard surfaced three more dashboard-blocking slow
  queries** — fine as Phase 3/4 one-off scripts, not as page loads:
  - `/insights/rebalancing-candidates`: first Insights-page load took
    46s (three window-function passes over 11.8M rows). Fixed with
    `warehouse.rebalancing_candidates_agg`, precomputing the expensive
    per-station pieces once per build; API now does a cheap join + LIMIT
    with the truck-capacity assumption still live. **~46s → ~30ms.**
  - `/insights/weekday-vs-weekend`: 5.9s (join+count over all 45.7M
    fact_trips rows). Fixed with `warehouse.trips_by_day_agg` (a ~366-row
    daily rollup). **~5.9s → ~35ms.**
  - All three fixes follow the same pattern as the Phase-4 performance
    artifact (`station_hourly_balance_hourly_agg`) — precompute once per
    warehouse build, not once per request.
- **Investigated a real data anomaly found while building
  `trips_by_day_agg`**: it has 366 rows, not 367 — one calendar day
  (2026-02-23) has zero trips. Confirmed it's not an ELT gap (staging has
  the same zero), then cross-referenced query 9's Open-Meteo data:
  8.3cm + 13.7cm of snow and 31.9 km/h wind gusts on 2026-02-22/23 — a
  real winter-storm shutdown, not a defect. Demand was already depressed
  the day before (19,037 vs. typical ~50-75k) and recovered gradually
  over the following days. Recorded in RESULTS.md as a nice real-world
  corroboration of the precipitation-demand correlation from query 9,
  not chased further as a bug.
- Hit and fixed one real Next.js bug along the way: Server Components
  can't pass functions as props to Client Components (not serializable
  across the RSC boundary) — `DemandCurveChart`'s `yFormatter` callback
  prop broke `/trends` (500 error) the moment it was called from a server
  component page. Fixed by replacing the callback with a `format: "raw"
  | "millions"` string enum resolved inside the client component.
- Verified end-to-end: `npm run build` (production build, typecheck)
  passes; all 4 routes return 200 via `next dev` + curl; server-rendered
  HTML confirmed to contain real data (station names, stats) via `curl |
  grep`, not just a 200 status. **Not visually verified in an actual
  browser** — no browser/screenshot tool available in this environment,
  only curl against the dev server — so layout/visual polish (spacing,
  the map's actual rendered appearance, hover states) hasn't been
  eyeballed and should be checked before calling this presentation-ready.

**Diversion from original plan**: none in scope, but deployment (Vercel/
Render/Neon, SPEC.md open question #3) didn't happen this session —
Phase 5 is code-complete and running locally, not yet live.

**Next**: finish Phase 5 — resolve SPEC.md open question #3 (PostGIS on
Neon/Supabase's free tier) and deploy (Neon or Supabase for Postgres,
Render for the API, Vercel for the dashboard); then a human visual pass
in an actual browser before calling the dashboard done.

---

## 2026-09-17 — Second-city warehouse rebuild verified, Phase 6 started

**Status**: Second-city (Chicago/Divvy) rebuild ✅ complete and validated.
Phase 6 (write-up) 🟡 in progress.

- Picked up a warehouse rebuild that had been left running from the prior
  session (`004_build_fact_trips.sql` building the combined NYC+Chicago
  dataset — migrations `0009_add_city_dimension.sql` and
  `0010_city_scope_rollups.sql`, plus reworked `003`/`004` transforms,
  were all present but uncommitted). Rather than assume it had hung, confirmed
  via `pg_stat_activity`/`docker stats` that it was genuinely still
  executing (100% CPU, heavy disk I/O) before choosing to let it run
  rather than kill 2+ hours of in-progress work.
- Rebuild finished at ~2h05m (vs. [FB-006](BUG_TRACKER.md)'s ~55-78 min
  single-city benchmark — expected, given the combined dataset is now
  ~51.8M rows vs. 45.7M). `etl/warehouse_checks.py` re-run clean: 0
  referential-integrity failures, 0 `ride_id` collisions across cities, 0
  city/station mismatches — confirms [FB-010](BUG_TRACKER.md)'s
  city-scoping fix holds. `fact_trips` now 51,803,621 rows (45,687,703
  NYC + 6,115,918 Chicago), `dim_station` 4,530 (2,492 + 2,038).
- **Found and fixed a real post-rebuild bug**: all 5 dashboard routes were
  checked by HTTP status; `/compare` (the new Compare Cities page, built
  alongside the second-city work but not yet exercised end-to-end) 500'd.
  Traced to a stale API process — `api/main.py`'s `/cities` endpoint
  existed in source but wasn't in the *running* server's OpenAPI schema,
  because that `uvicorn` process had been started before the second-city
  API changes landed and was never restarted. Killed and restarted it;
  all 5 routes (`/`, `/trends`, `/insights`, `/simulator`, `/compare`) now
  return 200 with real two-city data.
- Ran query 10 (`analysis/q10_cross_city.py`, already written but not yet
  executed against the combined warehouse) — see
  [RESULTS.md](RESULTS.md#cross-city-comparison-query-10) for full
  numbers. Headline: NYC's weekday-vs-weekend effect is statistically
  significant (+16.7%, p=0.0044) but Chicago's is not (+3.8%, p=0.319) —
  consistent with Chicago's much higher casual-rider share (35.3% vs.
  17.4%). Despite that, the two cities' hourly demand *shapes* correlate
  almost perfectly (Spearman rho=0.983, p=1.4e-17).
- Updated [RESULTS.md](RESULTS.md) scale/scoreboard numbers for the
  combined two-city warehouse (was NYC-only from Phase 3) and added the
  cross-city section and a resume-ready summary — clears most of Phase
  6's checklist in [PHASE_PLAN.md](PHASE_PLAN.md).
- **Playwright MCP, which the user set up for this session, never
  actually connected** — `ToolSearch` for browser-automation tools
  returned nothing across several query attempts, only Figma/Weave/
  Artifact tools. Flagged to the user rather than silently skipping or
  fabricating a visual check; all dashboard verification this session
  was HTTP-level (status codes + grepped real data in server-rendered
  HTML), not an actual visual/browser pass.

**Diversion from original plan**: none in scope, but a real visual
browser pass (Phase 5's original "Next" item, and part of Phase 7) is
still outstanding, now blocked on Playwright actually connecting rather
than on the environment lacking a browser tool at all.

**Next**: get Playwright connected and do the actual visual pass (map
rendering, popup behavior, chart legibility, the new city switcher/
`/compare` page) before treating the dashboard as presentation-ready;
finish Phase 6 (README architecture + screenshots + live links, currently
blocked on Phase 5's deployment step which still hasn't happened); then
Phase 7 polish.
