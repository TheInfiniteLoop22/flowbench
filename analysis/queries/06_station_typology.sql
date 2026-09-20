-- Query 6 (P1): station typology by demand-curve shape. No ML/clustering
-- library — percentile/window functions only, per SPEC.md §4 query 6.
--
-- For each station:
--   commute_index = (trips in AM peak 7-10h + PM peak 16-19h) / weekday trips
--                   — high for a station whose demand is concentrated in
--                   the two commute windows, low for a flatter curve.
--   weekend_share = weekend trips / total trips, normalized for the
--                   unequal weekday:weekend day count (5:2) so a station
--                   with identical daily volume on every day of the week
--                   scores exactly 0.5, not 0.29.
-- Stations are bucketed into commuter-hub / leisure / mixed using
-- NTILE(3) over each metric (top/bottom tercile) rather than a fixed
-- magic-number threshold, so the classification adapts to this dataset's
-- actual spread.
WITH station_hour AS (
    SELECT
        f.start_station_id AS station_id,
        t.is_weekend,
        extract(hour FROM f.start_time)::int AS hour_of_day
    FROM warehouse.fact_trips f
    JOIN warehouse.dim_time t ON t.date = f.start_date
    WHERE f.start_station_id IS NOT NULL AND NOT t.is_holiday
      AND f.city = 'new_york'  -- second-city stretch: scope to the original NYC-only result, see query 10
),
per_station AS (
    SELECT
        station_id,
        count(*) FILTER (WHERE NOT is_weekend) AS weekday_trips,
        count(*) FILTER (WHERE is_weekend)     AS weekend_trips,
        count(*) FILTER (WHERE NOT is_weekend AND hour_of_day BETWEEN 7 AND 10)  AS am_peak_trips,
        count(*) FILTER (WHERE NOT is_weekend AND hour_of_day BETWEEN 16 AND 19) AS pm_peak_trips,
        count(*) AS total_trips
    FROM station_hour
    GROUP BY station_id
    HAVING count(*) >= 100   -- drop near-zero-volume stations, too noisy to classify
),
metrics AS (
    SELECT
        station_id,
        total_trips,
        (am_peak_trips + pm_peak_trips)::numeric / NULLIF(weekday_trips, 0) AS commute_index,
        -- weekend_share normalized to what an even 7-day spread would give (2/7),
        -- so 1.0 means "exactly proportionally even", not a magic 0.5 cutoff.
        (weekend_trips::numeric / NULLIF(total_trips, 0)) / (2.0 / 7.0) AS weekend_share_index
    FROM per_station
),
tercile AS (
    SELECT
        *,
        ntile(3) OVER (ORDER BY commute_index)      AS commute_tercile,
        ntile(3) OVER (ORDER BY weekend_share_index) AS weekend_tercile
    FROM metrics
)
SELECT
    station_id,
    s.name,
    total_trips,
    round(commute_index, 3)       AS commute_index,
    round(weekend_share_index, 3) AS weekend_share_index,
    CASE
        WHEN commute_tercile = 3 AND weekend_tercile = 1 THEN 'commuter-hub'
        WHEN weekend_tercile = 3 AND commute_tercile = 1 THEN 'leisure'
        ELSE 'mixed'
    END AS typology
FROM tercile
JOIN warehouse.dim_station s USING (station_id)
ORDER BY typology, total_trips DESC;
