-- Phase 4 performance artifact (SPEC.md §8): GET /network/imbalance did a
-- parallel seq scan + sort over all 11.8M rows of station_hourly_balance
-- on every request (EXPLAIN ANALYZE: ~668ms execution). The endpoint only
-- ever needs "avg net_balance per station for a given hour-of-day", a
-- ~60k-row rollup (2,492 stations x 24 hours) that doesn't change until
-- the next warehouse rebuild — so precompute it once instead of
-- recomputing it on every request. See docs/RESULTS.md "Performance" for
-- the measured before/after.
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.station_hourly_balance_hourly_agg AS
SELECT
    b.station_id,
    s.name,
    extract(hour FROM b.hour)::int AS hour_of_day,
    avg(b.net_balance) AS avg_net_balance
FROM warehouse.station_hourly_balance b
JOIN warehouse.dim_station s USING (station_id)
GROUP BY b.station_id, s.name, extract(hour FROM b.hour)::int
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_station_hourly_balance_hourly_agg
    ON warehouse.station_hourly_balance_hourly_agg (hour_of_day, station_id);
