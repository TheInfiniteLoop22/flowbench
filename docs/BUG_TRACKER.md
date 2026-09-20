# FlowBench — Bug Tracker

> Lightweight, file-based tracker. GitHub Issues can be used in parallel
> once the repo has active development; this file is the always-in-repo
> source of truth and should be kept in sync. Move fixed items to the
> "Closed" table with the commit/PR that fixed them — don't delete history.

## Open

| ID | Severity | Summary | Found in | Notes |
|---|---|---|---|---|
| FB-001 | Low | 153,346 rows (~0.3%) have null start/end lat or lng | Phase 1 DQ checks | Source data gap, not a load bug. Decide in Phase 2: exclude these rows from `fact_trips` distance calc, or keep with `distance_m` null. Leaning toward the latter — don't drop rows just because one derived column can't be computed. |
| FB-002 | Low | 482 rows (~0.001%) have `ended_at <= started_at` | Phase 1 DQ checks | Source data anomaly (clock skew / bad rides). Exclude from duration-based analysis (Phase 3 queries 3–5) via a `WHERE duration_s > 0` filter; keep the raw rows in staging untouched for auditability. |
| FB-003 | Low | 512 duplicate `ride_id` values across the 12-month window | Phase 1 DQ checks | Likely a handful of IDs reused across month boundaries or genuine source dupes (~0.001% of 45.7M rows). Resolve in Phase 2 warehouse load with `ROW_NUMBER() OVER (PARTITION BY ride_id ORDER BY started_at) = 1` dedup, not by touching staging. |
| FB-004 | Low | One depot/placeholder station (`SYS018`, "Bronx WH station") has coordinates `(0, 0)` — produced a bogus 8,660 km max trip distance before being filtered | Phase 2 warehouse build (`warehouse_checks.py` distance sanity) | Fixed: `warehouse/transforms/003_build_dim_station.sql` now excludes `(0,0)` observations the same way it excludes nulls. Only 2 trips reference this station; they get a null `end_station_id`/`distance_m` like any other unresolved station, consistent with FB-001's handling. |
| FB-005 | Info (not a bug) | System-wide inflow ≠ outflow by 107,129 trips in `station_hourly_balance` | Phase 2 warehouse checks | Not a boundary-date artifact as first assumed — confirmed via direct count: 128,311 trips have a resolved start station but unresolved end station, vs. 21,182 the other way round (difference = 107,129, exactly the observed gap). Real characteristic of the source data (e.g. e-bike trips ending outside the docked network), not a pipeline defect. Worth surfacing directly in Phase 3's analysis as a "trips that didn't return to the network" figure — see [RESULTS.md](RESULTS.md). |
| FB-006 | Medium (performance) | `004_build_fact_trips.sql` takes ~55–58 minutes to rebuild all 45.7M rows (dedup window function + double join to `dim_station`) | Phase 2 warehouse build | Not blocking — it's a periodic batch rebuild, not a hot path (see proposal §6: "batch, not streaming"). But it's slow enough to be worth `EXPLAIN ANALYZE`-ing properly. Good candidate for the Phase 4 "documented before/after query optimization" deliverable (SPEC.md §8) rather than a one-off fix now. |
| FB-007 | Low (operational) | Local dev disk is at 95% usage (32 GB free) after staging + warehouse (~25 GB combined) | Phase 2 warehouse build | Not urgent, but worth watching before adding more months of data or a second dataset. Options if it becomes a problem: drop `staging.stg_trips_raw` after a successful warehouse build and re-download on demand (the ELT script already supports this — data isn't lost, just not resident), or move Postgres's Docker volume to another disk. |
| FB-008 | High | 111 station names were split across two `station_id`s in `dim_station` (e.g. `"5980.1"` vs. `"5980.10"`, same name/lat/lon) because different months' source CSVs formatted the same numeric station ID with a different number of decimal digits | Phase 3, query 2 (net inflow/outflow) — the split showed up as a station appearing simultaneously as the #1 "bleeder" (all outflow) and #1 "accumulator" (all inflow) under two different IDs | Fixed: added `warehouse.normalize_station_id()` (`warehouse/migrations/0003_normalize_station_id.sql`), which canonicalizes purely-numeric station IDs via `trim_scale()` so `"5980.1"`/`"5980.10"` collapse to one row. Applied in `003_build_dim_station.sql` (dedup key) and `004_build_fact_trips.sql` (join key). Non-numeric placeholder IDs (`SYS016`, `3184.07_OLD`, etc.) are left untouched — not part of this bug. Requires a full warehouse rebuild to take effect. |

| FB-010 | High (caught before rebuild, not shipped) | Two performance rollups added in Phase 4/5 (`demand_by_hour_agg`, `trips_by_day_agg`) aggregate network-wide with no per-station grouping — adding Chicago's fact_trips rows would have silently summed NYC and Chicago into one blended number per hour/day | Phase 3 (second-city stretch), auditing every existing rollup for city-safety before the warehouse rebuild that adds Chicago | Fixed: `warehouse/migrations/0010_city_scope_rollups.sql` drops and recreates both with `city` in the `GROUP BY` and unique index. Three other rollups (`station_hourly_balance_hourly_agg`, `rebalancing_candidates_agg`, `station_typology_agg`) are keyed by `station_id`, which is already globally unique across cities (verified — Divvy's `CHI#####` format can't collide with Citi Bike's numeric IDs) — confirmed safe as-is, not rebuilt. |
| FB-009 | Low | 11 station names (22 `station_id`s) are still split after the FB-008 fix — same name/near-identical lat/lon but genuinely different ID strings, not just decimal formatting (e.g. `"7625.18"` vs `"7625.22"`, or a `"_old"`/`"_"`/`"_OLD"` suffix like `"3184.07"` vs `"3184.07_OLD"`) | Phase 3, verifying the FB-008 fix (`SELECT name, count(DISTINCT station_id) ... HAVING count > 1` after rebuild) | Likely genuine mid-window station re-numbering by the source, not a formatting bug — `normalize_station_id()` correctly leaves these alone since they aren't purely-numeric-with-trailing-zeros. Small residual (22 of 2,492 station_ids, ~0.9%) — not blocking Phase 3; a proper fix would dedup by (name, rounded lat/lon) rather than by ID string, deferred unless a query result turns out sensitive to it. |

## Closed

| ID | Severity | Summary | Found in | Fixed by | Notes |
|---|---|---|---|---|---|
| FB-011 | Medium | `/compare` dashboard page 500'd because the running `uvicorn` API process was stale — `GET /cities` existed in `api/main.py` source but wasn't in the live server's OpenAPI schema | Post-warehouse-rebuild dashboard verification (checking all 5 routes by HTTP status after the second-city rebuild) | Killed the stale process (`taskkill`) and restarted it as `python -m uvicorn api.main:app` from the repo root (it uses a relative import, `from . import queries`, so it must be launched as a module, not run directly from `api/`) | Not a code bug — the second-city API changes were correct, they just hadn't been picked up by the long-running dev server. Worth remembering for Phase 6/7: any time `api/main.py` changes, the dev `uvicorn` process needs a restart or `--reload` unless it's already running with that flag. |

## Severity guide

- **Blocker** — halts a phase, no workaround
- **High** — wrong data/results, must fix before moving on
- **Medium** — works but needs cleanup, won't block next phase
- **Low** — cosmetic, nice-to-have

## Conventions

- ID format: `FB-###`, incrementing, never reused.
- Log the bug the moment it's found, even mid-session — don't batch this
  at the end, it gets lost.
