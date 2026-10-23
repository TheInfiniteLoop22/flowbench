# FlowBench

Bike-share demand and network analytics, built on Citi Bike (NYC) and Divvy
(Chicago) public trip data. It asks one operational question: **where and
when does the station network run short of bikes or docks, and does that
pattern hold outside the city it was first observed in?**

51.8M trips across two cities flow through a batch ELT pipeline into a
PostgreSQL/PostGIS star-schema warehouse, are served by a read-only FastAPI
service, and are explored in a Next.js dashboard.

**Live demo** (free tiers):

- Dashboard: https://flowbench-eight.vercel.app
- API docs: https://flowbench-api-c2z8.onrender.com/docs

The API sleeps after idle on Render's free tier, so the first request can
take 30–50 seconds; a scheduled GitHub Action
([keep-warm](.github/workflows/keep-warm.yml)) pings it every 10 minutes.

## Findings

| Finding | Result |
|---|---|
| Demand rhythm | Peak at 17:00 (9.2% of daily trips), trough at 04:00 (0.35%): a ~26x swing |
| Weekday vs. weekend (NYC) | Weekdays +16.7% trips/day, Mann-Whitney U p = 0.0044 |
| Does that hold in Chicago? | Not clearly: +3.8%, p = 0.319 (not significant) |
| Rider type | Casual trips average 19.8 min vs. 11.6 min for members (~70% longer) |
| Weather | Daily max temperature vs. daily trips: Spearman r = 0.833 (p ≈ 10⁻⁹⁶, n = 367 days) |
| Forecast | 7-day moving average beat a linear trend on a validation holdout; 12.4% MAPE on the final 28 days |
| Rush hour | Specific stations empty or fill fastest at 08:00 and 17:00 (live on the Insights page) |

**Exploratory estimate**: the source data has no dock counts, so a rough
lost-trip model (about 302,565 trips, 0.66% of demand) approximates a
station's bike level from cumulative net flow, treats "likely empty" as
below the station's own 5th percentile, and assumes one truck moves 20
bikes per hour. It is a hypothesis for where to look, not a measured result.

## Data engineering notes

- **Scale and cleaning**: 51,804,679 staged rows; 1,058 dropped at load
  time (non-positive durations and duplicate `ride_id`s). Staging is never
  modified, so every drop is auditable.
- **A bug worth telling**: net-flow analysis showed one physical station as
  both the biggest "bleeder" and the biggest "accumulator". Different
  months formatted the same numeric `station_id` differently (`"5980.1"`
  vs. `"5980.10"`), splitting 111 stations in two. Fixed with
  `warehouse.normalize_station_id()` and a full rebuild.
- **City-safe rollups**: when Chicago was added, two network-wide rollups
  would have silently blended both cities; they now carry a `city` column.
- **Performance**: `GET /network/imbalance` went from 668 ms to 1.5 ms
  (~445x, `EXPLAIN ANALYZE`) by precomputing a station × hour rollup.
- **Free-tier deployment**: the 17 GB `fact_trips` table stays local;
  production holds only the dimensions and precomputed rollups (~144 MB), and
  no live endpoint queries `fact_trips`.

## Architecture

```
Citi Bike / Divvy CSVs (public, no key)
        │  etl/download_and_load.py
        ▼
staging.stg_trips_raw (Postgres)
        │  warehouse/migrations + transforms (plain, versioned SQL)
        ▼
star schema: fact_trips, dim_station, dim_time, dim_user_type
        │  + materialized rollups (station_hourly_balance, demand_by_hour,
        │    trips_by_day, rebalancing_candidates, station demand, city stats)
        ▼
analysis/  (9 SQL + Python queries)
        │
api/       (FastAPI, read-only, pooled connections)
        │  JSON over HTTP
        ▼
dashboard/ (Next.js App Router, Recharts, MapLibre GL)
```

**Stack**: PostgreSQL + PostGIS, Python (psycopg2, scipy, numpy), FastAPI,
Next.js + TypeScript, Recharts, MapLibre GL. Docker Compose locally; Neon
(Postgres), Render (API) and Vercel (dashboard) in production.

### API (`api/main.py`)

City-scoped endpoints take `?city=new_york|chicago` (default `new_york`).

| Endpoint | Purpose |
|---|---|
| `GET /cities` | Trip and station counts per city |
| `GET /stations` | Station list with coordinates |
| `GET /stations/{id}/demand?range=` | Hourly demand curve (7d / 30d / 90d / all-time) |
| `GET /stations/{id}/forecast` | 7-day moving-average forecast |
| `GET /network/demand` | System-wide hourly demand |
| `GET /network/imbalance?hour=` | Net bike balance per station at an hour of day |
| `GET /insights/weekday-vs-weekend` | Live Mann-Whitney U test on daily trips |
| `GET /insights/rebalancing-candidates` | Exploratory stockout ranking |

### Dashboard (`dashboard/src/app/`)

| Route | Purpose |
|---|---|
| `/` | Map: stations colored by net imbalance, hour slider with play |
| `/stations/[id]` | Demand curve and forecast |
| `/trends` | City-wide hourly demand and the weekday/weekend result |
| `/insights` | Weekday/weekend test, rush-hour imbalance, recorded findings, exploratory ranking |
| `/compare` | NYC vs. Chicago |

## Run locally

```bash
docker compose up -d                      # Postgres + PostGIS on :5433
cp .env.example .env
pip install -r etl/requirements.txt -r api/requirements-dev.txt

python etl/run_migrations.py
python etl/download_and_load.py --city new_york --start 202509 --end 202608
python etl/download_and_load.py --city chicago  --start 202509 --end 202608
python etl/build_warehouse.py             # ~1-2 hours for the full 51.8M rows
python etl/warehouse_checks.py

uvicorn api.main:app --reload             # http://127.0.0.1:8000/docs
cd dashboard && npm install && npm run dev  # http://localhost:3000
pytest api/tests                          # API tests on a seeded fixture warehouse
```

Analysis scripts: `python analysis/qNN_<name>.py` (read-only).

## Known limitations

- The full warehouse rebuild takes 1–2 hours (batch job, not optimized).
- 11 NYC station names (22 IDs) remain split across genuinely different ID
  strings, likely mid-window renumbering by the source (~0.9% of NYC stations).
- The lost-trip and rebalancing figures are assumption-based (see above).

## Repo layout

```
etl/         Python ELT scripts and data-quality checks
warehouse/   SQL migrations, star schema, materialized rollups, rebuild scripts
analysis/    Analytical query library (SQL + Python runners)
api/         FastAPI read-only query layer and tests
dashboard/   Next.js dashboard
```
