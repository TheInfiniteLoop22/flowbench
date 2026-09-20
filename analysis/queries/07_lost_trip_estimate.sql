-- Query 7 (P1): lost-trip estimate from station_hourly_balance.
--
-- We don't have real dock counts (dim_station.capacity is null per
-- SPEC.md §3.2 — not published by the source), so this is necessarily a
-- *relative* model, stated explicitly:
--   1. Track each station's running cumulative net balance (inflow minus
--      outflow) over the whole window, starting at 0. This is a relative
--      bike level, not an absolute dock count.
--   2. A station-hour is "likely empty" if that running level is at or
--      below its OWN 5th percentile across the whole window — i.e. the
--      station is unusually depleted relative to its own typical range,
--      not against a fixed number.
--   3. Lost trips in a likely-empty hour = (that station's own median
--      outflow for that hour-of-day, computed over its NON-depleted
--      hours) minus (actual outflow that hour), floored at 0 — the
--      demand that would have shown up if the station weren't running
--      low, based on its own normal pattern at that hour.
-- Assumption stated up front (per SPEC.md §4): a rider who finds a
-- station empty simply doesn't take a trip from it (no waiting/retry
-- modeled) — this gives a conservative floor on lost demand, not a
-- ceiling.
WITH running AS (
    SELECT
        station_id,
        hour,
        extract(hour FROM hour)::int AS hour_of_day,
        outflow,
        sum(net_balance) OVER (PARTITION BY station_id ORDER BY hour) AS cum_balance
    FROM warehouse.station_hourly_balance
),
thresholds AS (
    SELECT
        station_id,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY cum_balance) AS p5_balance
    FROM running
    GROUP BY station_id
),
flagged AS (
    SELECT r.*, (r.cum_balance <= th.p5_balance) AS likely_empty
    FROM running r
    JOIN thresholds th USING (station_id)
),
typical_outflow AS (
    SELECT
        station_id,
        hour_of_day,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY outflow) AS median_outflow
    FROM flagged
    WHERE NOT likely_empty
    GROUP BY station_id, hour_of_day
)
SELECT
    f.station_id,
    s.name,
    count(*) FILTER (WHERE f.likely_empty) AS likely_empty_hours,
    count(*) AS hours_observed,
    round(sum(
        CASE WHEN f.likely_empty
             THEN greatest(coalesce(t.median_outflow, 0) - f.outflow, 0)
             ELSE 0 END
    )) AS estimated_lost_trips
FROM flagged f
JOIN warehouse.dim_station s ON s.station_id = f.station_id
LEFT JOIN typical_outflow t ON t.station_id = f.station_id AND t.hour_of_day = f.hour_of_day
WHERE s.city = 'new_york'  -- second-city stretch: scope to the original NYC-only result, see query 10
GROUP BY f.station_id, s.name
HAVING count(*) FILTER (WHERE f.likely_empty) > 0
ORDER BY estimated_lost_trips DESC;
