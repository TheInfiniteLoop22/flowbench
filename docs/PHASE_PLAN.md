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

## Phase 3 — Analysis library ⬜ (next up)
- [ ] Query 1: demand by station/hour
- [ ] Query 2: net inflow/outflow per station (rebalancing signal)
- [ ] Query 3: trip-duration distribution by user type
- [ ] Query 4: weekday/weekend comparison + significance test (resolve which test based on EDA)
- [ ] Query 5: forecasting baseline (resolve open question #4)
- [ ] Query 6 (P1): station typology/clustering by demand-curve shape
- [ ] Query 7 (P1): lost-trip estimate from `station_hourly_balance`
- [ ] Query 8 (P1): rebalancing ROI ranking (feeds `/insights/rebalancing-candidates`)
- [ ] Query 9 (stretch): weather correlation via Open-Meteo (no key)
- [ ] Validate each against a sanity check; record results in [RESULTS.md](RESULTS.md) as they land — don't wait until Phase 6

## Phase 4 — API ⬜
- [ ] FastAPI project scaffold
- [ ] `GET /stations`
- [ ] `GET /stations/{id}/demand?range=`
- [ ] `GET /network/imbalance?hour=`
- [ ] `GET /insights/weekday-vs-weekend`
- [ ] `GET /insights/rebalancing-candidates`
- [ ] API tests against seeded test warehouse
- [ ] Pick the single slowest/most important query, run `EXPLAIN ANALYZE`,
      add an index or materialized view, record before/after timing —
      this is the Phase-4 performance artifact referenced in SPEC.md §8

## Phase 5 — Dashboard ⬜
- [ ] Next.js scaffold, TypeScript, Recharts, MapLibre GL
- [ ] Map view: stations colored by imbalance
- [ ] Station detail view: demand curve
- [ ] City-wide trends view
- [ ] Insight report page (numbers + confidence intervals)
- [ ] Resolve deployment open question #3 (PostGIS on free tier)
- [ ] Deploy: Postgres (Neon/Supabase), API (Render), frontend (Vercel)

## Phase 6 — Write-up ⬜
- [ ] Rebalancing finding write-up with numbers + confidence intervals
- [ ] Fill in [RESULTS.md](RESULTS.md) headline numbers (scale, findings, ROI ranking)
- [ ] Update README with final architecture, screenshots, live links
- [ ] Resume bullet(s) drafted from actual delivered scope (not the pitch)

## Phase 7 — Polish & presentation ⬜
- [ ] 2–3 dashboard screenshots/GIFs embedded in README
- [ ] One-page insight report exported (PDF or a dashboard route) — the
      thing you'd actually attach to an application
- [ ] Live demo links (frontend + API docs) verified working from a clean
      browser session, not just localhost
- [ ] Performance benchmark write-up (from Phase 4) added to RESULTS.md
- [ ] Final pass: does a reader with zero context get the headline finding
      in under a minute from the README alone? If not, fix the README, not
      the reader's expectations.

## MVP cut line

Per [proposal §12](../new-project-proposal.md#12-mvp-scope): Phases 1–4 +
minimal dashboard (map + one trends chart) + written insight report. The
forecasting baseline (Phase 3, query 5) is the first thing to cut if time
is short — it is explicitly not required to prove the core skill set.

## Advanced / stretch (post-MVP, only if time remains)
- [ ] Short-horizon per-station demand forecast (if cut from MVP)
- [ ] "What-if" rebalancing simulator
- [ ] Second city for cross-city comparison
