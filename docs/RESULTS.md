# FlowBench — Results

> This is the scoreboard, not the plan. Fill in real numbers as they land
> during Phase 3 (analysis), Phase 4 (performance), and Phase 6/7
> (write-up, polish). Nothing in this file should be aspirational —
> either it's a measured result or it isn't in here yet. Cross-reference
> [SPEC.md §8](SPEC.md#8-results--success-bar) for the bar each of these
> is meant to clear.

Last updated: 2026-09-17 — second-city (Chicago/Divvy) warehouse rebuild complete, cross-city query validated.

## Scale

| Metric | Value |
|---|---|
| Trips processed (staged, both cities) | **51,804,679** rows, zero load errors |
| Date range | 2025-09-01 through 2026-08-31 (12 consecutive months), both cities |
| Cities | NYC (Citi Bike): 45,687,703 trips, 2,492 stations · Chicago (Divvy): 6,115,918 trips, 2,038 stations |
| Stations (distinct, both cities) | **4,530** |
| Data-quality pass rate | 99.999% clean on hard checks (0 null IDs/timestamps, 0 bad categories); soft issues tracked as [FB-001](BUG_TRACKER.md)–[FB-003](BUG_TRACKER.md) |
| `fact_trips` rows | **51,803,621** (1,058 dropped: bad duration + duplicate `ride_id`, see FB-002/003) |
| `dim_station` rows | **4,530** (1 NYC depot placeholder excluded, FB-004; 111 NYC duplicate-ID station names collapsed, FB-008; 11 NYC station names remain split on genuinely different IDs, FB-009, deferred) |
| `station_hourly_balance` rows | 11,875,461+ (station × hour grain) |
| Warehouse (staging + star schema) total size | ~32 GB |
| Referential integrity | 0 orphaned FKs; 0 `ride_id` collisions across cities; 0 city/station mismatches (verified post-rebuild, see [FB-010](BUG_TRACKER.md)) |
| Distance coverage | 95.7% of trips have a computed `distance_m` (PostGIS geography distance between resolved stations); max 48,332 m, 0 negative |
| System-wide net (inflow − outflow) | -171,650 (900,354 resolved-start/unresolved-end vs. 728,704 the reverse — same asymmetry pattern as [FB-005](BUG_TRACKER.md), now measured across both cities) |

## Data-quality bug caught mid-analysis: FB-008

Query 2 (net inflow/outflow) initially showed the same physical station
(identical name/lat/lon) as simultaneously the #1 "bleeder" (near-100%
outflow) and #1 "accumulator" (near-100% inflow) — traced to different
months' source CSVs formatting the same numeric `station_id` with a
different number of decimal digits (e.g. `"5980.1"` vs. `"5980.10"`),
splitting 111 station names across 222 IDs. Fixed with
`warehouse.normalize_station_id()` and a full warehouse rebuild before
trusting any per-station Phase 3 result — see [FB-008](BUG_TRACKER.md).
All numbers below are post-fix.

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

Top 5 of the 20-station ranked list from query 8 (full list:
`python analysis/q08_rebalancing_roi.py`), by estimated lost trips
recovered per hour of truck rebalancing time (assumption: one truck
moves 20 bikes/hour; effort = number of distinct stockout episodes ×
that station's average hourly outflow, not the whole-year net deficit —
see the query's header comment for why):

| Station | Stockout episodes (12mo) | Est. lost trips | Truck-hours needed | Lost trips / truck-hour |
|---|---|---|---|---|
| 108 St & 52 Ave | 11 | 53 | 0.4 | 127.2 |
| Grand Concourse & E 144 St | 10 | 106 | 0.8 | 127.0 |
| Pioneer St & Richards St | 10 | 74 | 0.6 | 123.2 |
| E 48 St & 5 Ave | 12 | 533 | 4.4 | 120.4 |
| E 32 St & Park Ave | 12 | 646 | 5.6 | 114.8 |

Network-wide estimated lost trips (all stations, 12 months): **302,565**
(0.66% of observed trips) — see query 7.

## Statistical findings

Each entry needs a number and a confidence interval or p-value — not a
described trend.

1. **Weekdays average 16.7% more trips/day than weekends** (excluding
   holidays): weekday mean 131,331 trips/day (n=251) vs. weekend mean
   112,538 trips/day (n=106). Both groups failed a Shapiro-Wilk normality
   check (weekday p<0.0001, weekend p=0.0007), so the test used is
   Mann-Whitney U (not a default t-test): U=15,841, **p=0.0044**. See
   query 4.
2. **Trip duration differs sharply by user type**: casual riders average
   19.8 min/trip (median 12.7 min, n=7,938,556) vs. members at 11.6
   min/trip (median 8.4 min, n=37,749,147) — casual trips run ~70%
   longer on average, consistent with leisure vs. commute usage. See
   query 3.
3. **Temperature is a strong driver of system-wide demand**: Spearman
   r=0.833 between daily max temperature and daily trip count
   (**p=8.3×10⁻⁹⁶**, n=367 days, via Open-Meteo's free historical
   archive). Precipitation has a smaller but still significant effect:
   r=-0.149 (p=0.0042); days with >1mm precipitation (n=128) average
   11.8% fewer trips than dry days (n=239), Mann-Whitney p=0.0044. See
   query 9.
4. **Estimated 302,565 lost trips (0.66% of observed demand) network-wide
   over 12 months** from stations running structurally low relative to
   their own typical range — see query 7 (stated-assumption relative-
   inventory model, not a measured stockout count) and the rebalancing
   ranking above.

## Notable finding (not a formal statistical test, but a real number worth reporting)

**Station typology** (query 6, NTILE(3) commute-index/weekend-share
buckets over 2,361 stations with ≥100 trips): 330 commuter-hub stations
(e.g. W 21st St & 6th Ave, commute_index=0.594 — nearly 60% of weekday
trips fall in the AM/PM commute windows), 275 leisure stations (e.g. W
4th St & 7th Ave S, weekend_share_index=1.168 — weekend demand is 17%
above what an even 7-day spread would predict), 1,756 mixed. Confirms the
network has a real, quantifiable commuter/leisure split, not just an
eyeballed one. The terciles are computed per city (the dashboard's
`station_typology_agg` reproduces these NYC counts exactly); Chicago, ranked
against Chicago only, comes out at 166 commuter-hub / 140 leisure / 775 mixed
over 1,081 stations with ≥100 trips.

**Demand curve**: system-wide peak hour is 17:00 (9.2% of daily trips),
trough is 04:00 (0.35%) — a ~26x swing between busiest and quietest hour.

**Forecast baseline** (query 5, resolving SPEC.md open question #4
empirically rather than upfront): a 7-day trailing moving average beat a
simple linear trend on a held-out validation window (MAE 26,826 vs.
48,341) — the daily trend is real but weak (R²=0.071) and not worth
losing the day-of-week shape a trailing mean captures. Final test-holdout
performance (last 28 days, moving average): MAE=19,423, MAPE=12.4%.

## Cross-city comparison (query 10)

NYC (Citi Bike) vs. Chicago (Divvy), same 12-month window, same warehouse
schema and query logic (`analysis/q10_cross_city.py`):

| Metric | New York | Chicago |
|---|---|---|
| Total trips | 45,687,703 | 6,115,918 |
| Distinct start stations | 2,405 | 1,991 |
| Mean trip duration | 784 s (13.1 min) | 919 s (15.3 min) |
| Median trip duration | 544 s (9.1 min) | 556 s (9.3 min) |
| Casual-rider share | 17.4% | 35.3% |
| Peak hour | 17:00 (9.2% of daily demand) | 17:00 (10.5% of daily demand) |
| Trough hour | 04:00 (0.4%) | 04:00 (0.3%) |
| Peak/trough ratio | 26.3x | 37.1x |
| Weekday vs. weekend | **+16.7%**, Mann-Whitney **p=0.0044** (significant) | **+3.8%**, Mann-Whitney **p=0.319** (not significant) |

Two findings worth calling out:

1. **NYC's weekday commute pattern doesn't clearly replicate in Chicago.**
   NYC trips are ~16.7% higher on weekdays, a statistically significant
   effect (p=0.0044, same Shapiro-Wilk→Mann-Whitney test as query 4).
   Chicago's weekday uplift is smaller (+3.8%) and **not** statistically
   significant (p=0.319, n=367 days) — i.e. we can't reject the
   possibility that Chicago's weekday/weekend difference is noise. This
   tracks with Chicago's much higher casual-rider share (35.3% vs. 17.4%):
   a network used more for leisure than commuting should show a weaker
   weekday signal, and it does.
2. **The *shape* of daily demand is nearly identical between cities**
   despite the very different weekday effect and 7.5x difference in scale:
   Spearman correlation between the two cities' hour-of-day demand curves
   is **rho=0.983 (p=1.4×10⁻¹⁷, n=24 hours)**. Both cities peak at 17:00
   and trough at 04:00. Chicago's peak/trough ratio (37.1x) is steeper
   than NYC's (26.3x) — a smaller, more leisure-skewed network still
   empties out more sharply overnight, likely because it has less
   round-the-clock commute traffic to fill the trough hours.

## Performance

| Query | Before | After | Fix applied |
|---|---|---|---|
| `GET /network/imbalance?hour=` | 667.9ms execution (parallel seq scan + external-merge sort over all 11.8M `station_hourly_balance` rows, `EXPLAIN ANALYZE`) | 1.5ms execution (bitmap index scan, `EXPLAIN ANALYZE`) — **~445x** | Added `warehouse.station_hourly_balance_hourly_agg`, a materialized rollup (station × hour-of-day → avg net balance, ~60k rows) with a unique index on `(hour_of_day, station_id)`, refreshed once per warehouse build rather than recomputed per request. See `warehouse/migrations/0004_station_hourly_balance_hourly_agg.sql` and `warehouse/transforms/006_refresh_station_hourly_balance_hourly_agg.sql`. |
| `GET /insights/rebalancing-candidates` | ~46s wall time (three window-function passes — `percentile_cont`, `lag()`, running `sum() OVER` — over all 11.8M `station_hourly_balance` rows, per request) | ~30ms wall time — **~1,500x** | Found during Phase 5 (dashboard Insights page first load). Added `warehouse.rebalancing_candidates_agg`, precomputing the expensive per-station pieces (stockout-episode count, avg hourly outflow, estimated lost trips) once per warehouse build; the API now only joins that ~2,500-row rollup to `dim_station` and does the final `ORDER BY`/`LIMIT` with the truck-capacity assumption applied live. See `warehouse/migrations/0006_*.sql`. |
| `GET /insights/weekday-vs-weekend` | ~5.9s wall time (`LEFT JOIN` + `count()` over all 45.7M `fact_trips` rows to get a per-day total, per request) | ~35ms wall time — **~170x** | Found during Phase 5 (dashboard Trends page). Added `warehouse.trips_by_day_agg` (~366-row daily rollup — see the note below), refreshed once per warehouse build. See `warehouse/migrations/0007_*.sql`. |

**Aside (not a bug — investigated, explained)**: `trips_by_day_agg` has
366 rows, not 367 — 2026-02-23 has zero trips. Checked staging directly:
February's source files loaded completely (manifest row counts match),
so it's not an ELT gap. Cross-referenced against query 9's Open-Meteo
data for that week: 2026-02-22 to 2026-02-23 saw 8.3cm + 13.7cm of
snowfall and wind gusts up to 31.9 km/h — a winter storm. Demand was
already depressed on the 22nd (19,037 trips vs. a typical ~50-75k) and
fell to zero on the 23rd, recovering gradually through the 24th-26th.
A real, weather-driven system-wide shutdown, not a data defect — and a
nice corroboration of query 9's precipitation-demand correlation finding.

## Presentation artifacts

- [x] Live dashboard: https://flowbench-eight.vercel.app (Vercel, free tier)
- [x] Live API docs: https://flowbench-api-c2z8.onrender.com/docs (Render free tier; Postgres on Neon free tier — the API can take up to a minute to wake after idle)
- [x] One-page insight report: [docs/flowbench-insight-report.pdf](flowbench-insight-report.pdf) (PDF export of the `/insights` dashboard route)
- [x] Screenshots: [docs/screenshots/](screenshots/) — map, station detail, trends, insights, simulator, compare (all 6 pages, captured from the live site)

## Resume-ready summary

Built and deployed an end-to-end bike-share analytics platform (ELT →
PostGIS star-schema warehouse → FastAPI → Next.js/MapLibre dashboard)
covering **51.8M trips across two cities** (NYC Citi Bike, Chicago Divvy)
over a 12-month window, live on free-tier Vercel, Render and Neon. Produced
a ranked rebalancing-ROI recommendation (the top 20 stations each recover an
estimated ~90–130 lost trips per truck-hour — a modeled estimate from
inferred stockout periods, not an observed count) and ran six hypothesis
tests with reported p-values (five significant, one not — Chicago's
weekday/weekend effect), choosing t-test vs. Mann-Whitney via a
Shapiro-Wilk normality check. Cut a key API query ~445x (667.9 ms → 1.5 ms,
`EXPLAIN ANALYZE` before/after) with precomputed rollups, and used the same
approach to shrink the deployed database from ~25 GB to ~144 MB so it fits a
free tier. Found and fixed several data-integrity bugs before they reached
results (duplicate station IDs, a flawed forecast-model-selection heuristic,
a degenerate ROI metric, and rollups that silently blended two cities).
