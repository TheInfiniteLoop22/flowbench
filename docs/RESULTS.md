# FlowBench — Results

> This is the scoreboard, not the plan. Fill in real numbers as they land
> during Phase 3 (analysis), Phase 4 (performance), and Phase 6/7
> (write-up, polish). Nothing in this file should be aspirational —
> either it's a measured result or it isn't in here yet. Cross-reference
> [SPEC.md §8](SPEC.md#8-results--success-bar) for the bar each of these
> is meant to clear.

Last updated: 2026-09-17 — Phase 1 (data + staging) complete.

## Scale

| Metric | Value |
|---|---|
| Trips processed (staged) | **45,688,697** rows, zero load errors |
| Date range | 2025-09-01 through 2026-08-31 (12 consecutive months) |
| Stations (distinct, start+end) | **2,593** |
| Staging size on disk | ~12 GB (Postgres, includes indexes) |
| Data-quality pass rate | 99.999% clean on hard checks (0 null IDs/timestamps, 0 bad categories); 3 soft issues tracked as [FB-001](BUG_TRACKER.md), [FB-002](BUG_TRACKER.md), [FB-003](BUG_TRACKER.md) affecting a combined ~0.36% of rows |
| `fact_trips` rows | **45,687,703** (994 dropped: bad duration + duplicate `ride_id`, see FB-002/003) |
| `dim_station` rows | **2,592** (1 depot placeholder excluded, FB-004) |
| `station_hourly_balance` rows | 11,875,461 (station × hour grain) |
| Warehouse (staging + star schema) total size | ~25 GB |
| Referential integrity | 0 orphaned FKs across ~137M FK-checked row-references |
| Distance coverage | 99.7% of trips have a computed `distance_m` (PostGIS geography distance between resolved stations); max 35.2 km, 0 negative |

## Notable finding (surfaced during Phase 2 sanity checks, not yet a Phase 3 query)

**107,129 more trips leave a station than return to one.** Specifically:
128,311 trips have a resolved start station but no resolved end station,
vs. only 21,182 the other way — a ~6:1 asymmetry, not sampling noise or
a date-boundary artifact (verified directly, see [FB-005](BUG_TRACKER.md)).
Candidate explanation: e-bike trips ending outside the docked network.
Worth a real Phase 3 query — "where do undocked-ending trips originate,
and does it cluster by station or by rideable_type" is exactly the kind
of finding this project is supposed to produce.

## Headline finding: rebalancing candidates

*TBD — Phase 3, query 8.* Target shape: a ranked top 10–20 station list
with a quantified impact number per station (e.g. lost trips/week or
bikes-short incidents/week), plus the assumption used to derive it
(trucks/hour capacity) stated explicitly.

## Statistical findings

Each entry needs a number and a confidence interval or p-value — not a
described trend.

1. *TBD — weekday vs. weekend demand (Phase 3, query 4)*
2. *TBD — lost-trip estimate (Phase 3, query 7)*
3. *TBD — third finding, e.g. station typology or weather correlation*

## Performance

| Query | Before | After | Fix applied |
|---|---|---|---|
| *TBD — Phase 4* | — | — | — |

## Presentation artifacts

- [ ] Live dashboard: *link TBD*
- [ ] Live API docs: *link TBD*
- [ ] One-page insight report: *link/file TBD*
- [ ] Screenshots/GIFs: *TBD — Phase 7*

## Resume-ready summary

*Draft once Phase 6 numbers are in — should be 1–2 sentences using the
real figures above, not the pitch's placeholder language.*
