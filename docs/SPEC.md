# FlowBench — Technical Specification

> Living document. Update this whenever a design decision is made or
> changed. If something here turns out to be wrong once implementation
> starts, edit it and add a line to [PROGRESS_LOG.md](PROGRESS_LOG.md)
> noting the diversion and why — don't leave this file stale.

Last updated: 2026-09-17

## 1. Locked decisions

- **Dataset**: Citi Bike (NYC) — `https://s3.amazonaws.com/tripdata/` public
  bucket, monthly ZIP/CSV, no API key required.
- **Date range for MVP**: 12 consecutive months, single recent full year
  available at build time (exact months to be confirmed in Phase 1 once
  data is inspected — see open question below).
- **Database**: PostgreSQL 15+ with PostGIS extension.
- **Transform tooling**: plain versioned SQL migration files, run in order
  by a small runner script. dbt-core is an optional upgrade, not required
  (see [ADR-0002](DECISIONS.md#adr-0002)).
- **API**: FastAPI, read-only, no auth (no writes, no PII, no reason to
  gate it).
- **Frontend**: Next.js + TypeScript, Recharts for charts, MapLibre GL for
  the station map (both free, no API key).
- **Deployment**: Neon or Supabase (Postgres+PostGIS) / Render (API) /
  Vercel (frontend) — all free tier.

## 2. Open questions (resolve during the phase named)

| # | Question | Resolve in |
|---|---|---|
| 1 | Exact 12-month window (which months have clean, complete Citi Bike data with consistent schema — station-based vs. the newer format) | Phase 1 |
| 2 | Whether Citi Bike's current CSV schema includes stable `station_id`s across the whole window, or whether stations need to be de-duplicated/matched by name+lat/long | Phase 1 |
| 3 | Whether PostGIS is available on the free tier of the chosen host (Neon vs Supabase) at the time of deployment | Phase 5 (deployment) |
| 4 | Forecasting baseline: moving average vs. simple linear regression — pick based on what the EDA in Phase 3 actually shows (don't decide before seeing the data) | Phase 3 |

## 3. Data model

### 3.1 Staging (raw)

`stg_trips_raw` — one row per raw CSV row, minimally typed, no cleaning.
Loaded as-is so the ELT step is re-runnable and auditable against source.

### 3.2 Warehouse (star schema)

**`fact_trips`**
| column | type | notes |
|---|---|---|
| trip_id | bigint, PK | surrogate if source has no stable ID |
| start_station_id | FK → dim_station | |
| end_station_id | FK → dim_station | |
| start_time | timestamp | indexed |
| end_time | timestamp | |
| duration_s | int | derived, validated non-negative |
| user_type | text | member/casual or equivalent |
| distance_m | numeric | derived from station geometries (PostGIS) |

Indexed/partitioned by `start_time` (month partitions once volume is known
from Phase 1 EDA).

**`dim_station`**
| column | type | notes |
|---|---|---|
| station_id | PK | |
| name | text | |
| lat, lon | numeric | |
| capacity | int | nullable — not all sources publish this |
| geom | geometry(Point, 4326) | PostGIS |

**`dim_time`**
| column | type | notes |
|---|---|---|
| date | date, PK | |
| hour | int | 0–23, only needed if trips are bucketed hourly in a separate grain table |
| day_of_week | int | |
| is_weekend | bool | |
| is_holiday | bool | US federal holidays for the study year |
| month | int | |
| season | text | |

**`dim_user_type`**
| column | type | notes |
|---|---|---|
| user_type | PK | e.g. member / casual |

**`station_hourly_balance`** (materialized view)
Net bikes in minus bikes out, per station per hour. The core analytical
artifact — everything in the rebalancing story is derived from this.

```sql
-- sketch, refine in Phase 2
SELECT
  station_id,
  date_trunc('hour', ts) AS hour,
  SUM(inflow) - SUM(outflow) AS net_balance
FROM (...)
GROUP BY station_id, hour;
```

## 4. Analytical query library (Phase 3 deliverables)

**Core (MVP):**

1. Demand by station/hour
2. Net inflow-vs-outflow per station (rebalancing signal)
3. Trip-duration distribution by user type
4. Weekday vs. weekend demand comparison **with a significance test**
   (e.g. Mann-Whitney U or Welch's t-test — pick based on distribution
   shape, don't default to t-test blindly)
5. Short-horizon demand forecast per station (moving average or simple
   regression baseline; see open question #4)

**Extended (P1 — raises the project from "a few charts" to "a real
analysis," do these unless time is genuinely short):**

6. **Station typology / clustering** — bucket stations into profiles
   (commuter-hub / leisure / mixed) from their hourly demand-curve shape
   using SQL percentile/window functions (no ML library needed — k-means
   via `pgvector`/manual centroid SQL is a stretch option, not required).
7. **Lost-trip estimate** — using `station_hourly_balance`, quantify hours
   where a station was likely empty/full and estimate demand that went
   unserved. This is the number that turns "stations run out of bikes"
   into a dollar-shaped business impact statement.
8. **Rebalancing ROI ranking** — given a stated assumption (e.g. one truck
   moves N bikes per hour), rank stations by estimated impact-per-truck-
   hour. This is the artifact `GET /insights/rebalancing-candidates`
   serves.
9. **Weather correlation (stretch)** — join daily demand to free historical
   weather (Open-Meteo API, no key) and test correlation between
   precipitation/temperature and demand drop. Cheap to add, strong
   "thought beyond the given dataset" signal.

Each query gets a sanity check: e.g. total trips in == total trips out
system-wide over a full period. Every finding that ships in the insight
report must carry a number and, where applicable, a confidence interval —
"stations near Union Square run low on weekday mornings" is not a result;
"Station X hits <10% capacity by 8:40am on 83% of weekdays (n=52, 95% CI
78–88%)" is.

## 5. API surface

All read-only, no auth:

- `GET /stations`
- `GET /stations/{id}/demand?range=`
- `GET /network/imbalance?hour=`
- `GET /insights/weekday-vs-weekend`
- `GET /insights/rebalancing-candidates`

## 6. Dashboard

- Network map, stations colored by current imbalance (MapLibre)
- Station detail view: demand curve
- City-wide trends view
- Insight report page: the rebalancing finding, numbers + confidence
  intervals, not just a chart

## 7. Testing strategy

- **Data quality** (ELT): row counts, no orphaned station IDs, no negative
  durations — run as part of the pipeline, fail loud.
- **API**: endpoint tests against a seeded test warehouse (small fixture,
  not the full dataset).
- **Frontend**: no hard requirement for MVP; basic component tests are a
  P1 if time allows.

## 8. Results & success bar

This is the section that defines "done and good," not just "done." A
completed FlowBench should be able to make every one of these statements
truthfully — track actual numbers here as they land (also mirrored, with
narrative, in [RESULTS.md](RESULTS.md)):

- **Scale**: processed N trips (target: several million) across 12 months,
  M stations, in the warehouse.
- **Findings**: at least 3 non-trivial statistical findings stated with a
  number and a confidence interval or p-value — not eyeballed charts.
- **Headline result**: a ranked, quantified rebalancing-candidate list
  (top 10–20 stations) with an estimated impact number (lost trips/week,
  or bikes-short incidents/week) backing each entry.
- **Performance**: at least one query optimized with a documented
  before/after (`EXPLAIN ANALYZE` timings + the index/materialized-view
  that fixed it) — the analytical-workload equivalent of GearGrid's
  transactional query tuning.
- **Presentation**: a live deployed demo (dashboard + API), a one-page
  written insight report, and 2–3 dashboard screenshots/GIFs in the
  README — a reviewer should be able to understand the headline finding
  in under a minute without running anything locally.

## 9. Non-goals (explicit, to prevent scope creep)

- No streaming ingestion (batch is the correct and differentiating choice
  here — see proposal §6).
- No ML/deep-learning forecasting — moving average or simple regression
  only, and that choice must be defensible, not skipped.
- No auth/write API — this is a read-only analytics surface.
- No multi-city support in MVP (tracked as a future extension).
