# New Project Proposal — FlowBench: Bike-Share Demand & Network Analytics Warehouse

Phase 11 of the portfolio audit ([`portfolio-gaps.md`](portfolio-gaps.md))
concluded a 5th project wasn't *necessary* to hit the brief's own target of
~4. This document exists because the user asked for one good addition
anyway — so it names the single best candidate and specs it properly,
rather than just gesturing at it.

## 1. Project title

**FlowBench** — a data warehouse and analytics platform over bike-share
trip data, built to answer one real operational question: *where and when
does the station network run short of bikes or docks, and how far in
advance can that be seen coming?*

## 2. Problem statement

Bike-share systems (Citi Bike/NYC, Divvy/Chicago, and similar) publish
their full historical trip data for free, with no API key — every trip's
start/end station, timestamp, duration, and (for most cities) real
lat/long. Operators run "rebalancing" trucks to move bikes from stations
that fill up to stations that empty out, and getting that wrong is a
direct customer-experience and cost problem. Turning millions of raw trip
rows into an answer an operator could act on — which stations, which
hours, how confident — is a genuine data-analysis problem, not a toy one.

## 3. Why this project is needed in the portfolio

Of the three selected projects (GearGrid, ReviewLens, Latent Studio), none
does **dimensional modeling** (star schema / OLAP-shaped design, as opposed
to GearGrid's OLTP booking schema or ReviewLens's streaming-ingestion
schema), none does **geospatial SQL**, and none is framed as classic
**data-analyst work** (SQL + EDA + statistical inference + a dashboard,
without an ML pipeline in the middle). ReviewLens currently carries the
portfolio's entire Data Analysis signal, and it's shaped like data
engineering. This project would be the one instance in the whole portfolio
of "here's a business question, here's the SQL and the stats that answer
it, here's the confidence behind the answer" — the mode most Data Analyst
interviews actually probe.

## 4. Target roles

**Data Analysis** (primary — this is the whole point), **SWE** (schema
design, query performance), **Full Stack** (secondary — a real but
lighter-weight dashboard layer than GearGrid/Latent Studio).

## 5. Core functionality

- Ingest a bounded, named slice of public trip data (e.g., 12 months for
  one city) into a raw staging table.
- Transform into a star schema: a `fact_trips` table plus
  `dim_station` (with lat/long), `dim_time` (date/hour/day-of-week/
  weekday-vs-weekend/holiday flags), `dim_user_type`.
- A library of real analytical queries: demand by station/hour, net
  inflow-vs-outflow per station (the actual rebalancing signal), trip-
  duration distributions by user type, weekday/weekend demand comparison
  with a significance test, and simple short-horizon demand forecasting
  per station (a moving-average or basic regression baseline — not deep
  learning; this project's edge is SQL and stats, not ML).
- A dashboard: network map colored by current imbalance, a station detail
  view with its demand curve, a city-wide trends view, and one written
  "insight report" page presenting the rebalancing finding with numbers
  and confidence intervals, not just a chart.

## 6. Proposed architecture

```
Public trip-data CSVs (S3/GCS, no key) ─► Python ELT script ─► Postgres (raw staging)
                                                                     │
                                                     dbt-style SQL transforms
                                                                     ▼
                                                    Postgres warehouse (star schema)
                                                     + PostGIS for station geometry
                                                                     │
                                                            FastAPI (read-only, query layer)
                                                                     │
                                                       Next.js + a mapping lib (MapLibre/Leaflet)
                                                              + charts (Recharts)
```

Deliberately batch, not streaming — ReviewLens already owns the streaming
story; this project's differentiator is analytical/warehouse-shaped SQL,
and a scheduled batch ELT (a cron job or a simple orchestrated script) is
the *correct* tool for that, not a regression to "add Kafka everywhere."

## 7. Technology stack

PostgreSQL + **PostGIS** (new to this portfolio), Python (pandas/Polars for
the ELT step, or plain SQL transforms — either is fine, prefer SQL where
it can do the job to keep the "this is a SQL project" story clean), FastAPI
for a thin read-only query API, Next.js + TypeScript + Recharts + a
lightweight mapping library (MapLibre GL or Leaflet — both free, no API
key), Docker Compose. Optionally `dbt-core` for the staging→warehouse
transforms if the user wants a named, resume-recognizable transformation
tool; plain versioned SQL migration scripts are an equally legitimate,
simpler alternative and should not be treated as required.

## 8. Database design

Star schema, not the OLTP shape used by GearGrid/Windscapes:

- `fact_trips(trip_id, start_station_id, end_station_id, start_time,
  end_time, duration_s, user_type, distance_m)` — one row per trip,
  partitioned or indexed by `start_time`.
- `dim_station(station_id, name, lat, lon, capacity, geom [PostGIS point])`
- `dim_time(date, hour, day_of_week, is_weekend, is_holiday, month, season)`
- A derived/materialized `station_hourly_balance` view: net bikes in minus
  bikes out per station per hour — the core analytical artifact the
  rebalancing insight is built from.

This is the concrete "new concept" claim: a schema designed for fast
aggregate queries over dimensions, not for transactional correctness —
worth being able to explain *why* it's shaped differently from GearGrid's
schema in an interview.

## 9. APIs

Read-only, intentionally small: `GET /stations`, `GET /stations/{id}/demand?range=`,
`GET /network/imbalance?hour=`, `GET /insights/weekday-vs-weekend`,
`GET /insights/rebalancing-candidates` (the ranked list of stations most
worth trucking bikes to/from, with the supporting numbers). No writes, no
auth needed — this is an analytics surface, not a transactional app, and
should not be forced into looking like one.

## 10. Major engineering concepts

Dimensional modeling (star schema, fact/dimension separation), OLAP-shaped
query design (window functions, `GROUP BY` rollups, materialized views),
geospatial SQL (PostGIS distance/clustering queries — e.g., "stations
within 500m of a chronically empty station"), statistical inference
(confidence intervals on demand estimates, a proper significance test for
the weekday/weekend claim rather than eyeballing a chart), query
performance work analogous to GearGrid's `EXPLAIN`-verified queries but for
analytical rather than transactional workloads, and a simple, honestly-
scoped forecasting baseline (explicitly not deep learning — the point is
knowing when a moving average is the right tool, which is itself a
demonstrable judgment call).

## 11. Development phases

1. **Data + staging** — download a bounded date range, load raw CSVs into
   a staging table, validate row counts/nulls.
2. **Warehouse** — build the star schema, write the transform
   scripts/models, materialize `station_hourly_balance`.
3. **Analysis library** — write and validate the core analytical queries
   against known sanity checks (e.g., total trips in equals total trips
   out over a full period).
4. **API** — thin FastAPI layer over the warehouse.
5. **Dashboard** — map view, station detail, trends, insight report page.
6. **Write-up** — the rebalancing finding, stated with numbers and
   confidence intervals, as the project's headline artifact.

## 12. MVP scope

Phases 1–4 plus a minimal dashboard (map + one trends chart) and the
written insight report — the report *is* the deliverable that makes this
a "data analysis" project rather than "a dashboard." Cut the forecasting
baseline from MVP if time is short; it's the one component that isn't
required to prove the core skill set.

## 13. Advanced features

The short-horizon per-station demand forecast; a "what-if" rebalancing
simulator (given a fixed number of trucks, which stations to prioritize);
comparing two cities' networks if a second free dataset is added.

## 14. Testing strategy

Data-quality assertions on the ELT step (row counts, no orphaned station
IDs, no negative durations) run as part of the pipeline — this is the
analytics-project equivalent of unit tests and is a real, checkable
engineering practice, not decoration. API tests for the query endpoints
against a seeded test warehouse. No frontend test suite is a hard
requirement for MVP given the project's center of gravity is the data
layer, but basic component tests are a reasonable P1 if time allows.

## 15. Deployment strategy

Same free-tier pattern as the rest of the portfolio: Postgres on Neon/
Supabase (PostGIS is supported on both), FastAPI on Render, Next.js on
Vercel. The warehouse only needs to be rebuilt periodically (not
continuously), so no always-on compute beyond the thin API is required —
keeps this cheap to keep alive, unlike a streaming pipeline.

## 16. Expected resume value

Fills the portfolio's clearest remaining gap for a named target role
(Data Analysis) with a project whose headline isn't "I made charts" but "I
designed a warehouse schema, wrote the analytical SQL, and used statistics
to back a specific operational recommendation." Complements, rather than
duplicates, all three existing projects — different domain, different
database paradigm (OLAP vs. GearGrid's OLTP and ReviewLens's streaming
ingestion), different core skill (statistical/analytical SQL vs. ML).

## 17. Interview questions it could enable

Why a star schema instead of a normalized OLTP schema for this workload?
How did you validate the weekday/weekend difference was real and not
noise? How would this schema change if trip volume were 100x larger? Why
batch ELT instead of streaming, given ReviewLens already does streaming —
what's the actual trade-off? How did you pick the forecasting baseline,
and why not something fancier?

## 18. Future extension ideas

A second city's dataset for a cross-city comparison; a lightweight
anomaly-detection pass (flagging days with unusual demand — weather
events, holidays) layered onto the existing warehouse without changing its
shape; exposing the warehouse to a BI tool (Metabase, self-hosted, free)
as an alternative front end to the custom dashboard, to show awareness of
when *not* to build a custom UI.
