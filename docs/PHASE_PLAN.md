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

## Phase 1 — Data + staging ⬜
- [ ] Identify and download a bounded date range of Citi Bike CSVs (target: 12 months)
- [ ] Resolve open question #1 (exact window) and #2 (station ID stability) — update SPEC.md
- [ ] Python ELT script: download → load into `stg_trips_raw` (Postgres, local via Docker Compose)
- [ ] Data-quality checks: row counts vs. source, null audit, duplicate check
- [ ] Document findings in PROGRESS_LOG.md

## Phase 2 — Warehouse ⬜
- [ ] Write SQL migration scripts for star schema (`fact_trips`, `dim_station`, `dim_time`, `dim_user_type`)
- [ ] PostGIS setup, `geom` column on `dim_station`, distance calc for `fact_trips.distance_m`
- [ ] Build and materialize `station_hourly_balance`
- [ ] Sanity check: total inflow == total outflow system-wide

## Phase 3 — Analysis library ⬜
- [ ] Query 1: demand by station/hour
- [ ] Query 2: net inflow/outflow per station (rebalancing signal)
- [ ] Query 3: trip-duration distribution by user type
- [ ] Query 4: weekday/weekend comparison + significance test (resolve which test based on EDA)
- [ ] Query 5: forecasting baseline (resolve open question #4)
- [ ] Validate each against a sanity check; record results

## Phase 4 — API ⬜
- [ ] FastAPI project scaffold
- [ ] `GET /stations`
- [ ] `GET /stations/{id}/demand?range=`
- [ ] `GET /network/imbalance?hour=`
- [ ] `GET /insights/weekday-vs-weekend`
- [ ] `GET /insights/rebalancing-candidates`
- [ ] API tests against seeded test warehouse

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
- [ ] Update README with final architecture, screenshots, live links
- [ ] Resume bullet(s) drafted from actual delivered scope (not the pitch)

## MVP cut line

Per [proposal §12](../new-project-proposal.md#12-mvp-scope): Phases 1–4 +
minimal dashboard (map + one trends chart) + written insight report. The
forecasting baseline (Phase 3, query 5) is the first thing to cut if time
is short — it is explicitly not required to prove the core skill set.

## Advanced / stretch (post-MVP, only if time remains)
- [ ] Short-horizon per-station demand forecast (if cut from MVP)
- [ ] "What-if" rebalancing simulator
- [ ] Second city for cross-city comparison
