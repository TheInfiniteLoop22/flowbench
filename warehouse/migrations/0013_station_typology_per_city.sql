-- Fix: station_typology_agg (0008) bucketed stations with NTILE(3) over every
-- station in the warehouse. That was correct while the warehouse was NYC-only,
-- but NTILE is rank-based: once Chicago was added, each city's stations were
-- being cut against a two-city distribution, so NYC's counts drifted from the
-- NYC-only Phase 3 result in docs/RESULTS.md (299/247/1,815 vs. 330/275/1,756
-- for the same 2,361 stations). 0010's audit only checked for station_id
-- collisions and missed that rank-based cut-offs depend on the pool.
--
-- Recreated with the terciles computed PER CITY (PARTITION BY city), matching
-- analysis/queries/06 (query 6), which is scoped to one city. Columns are
-- unchanged, so the API and the production copy of the table keep their shape.
DROP MATERIALIZED VIEW IF EXISTS warehouse.station_typology_agg;

CREATE MATERIALIZED VIEW warehouse.station_typology_agg AS
WITH station_hour AS (
    SELECT
        f.city,
        f.start_station_id AS station_id,
        t.is_weekend,
        extract(hour FROM f.start_time)::int AS hour_of_day
    FROM warehouse.fact_trips f
    JOIN warehouse.dim_time t ON t.date = f.start_date
    WHERE f.start_station_id IS NOT NULL AND NOT t.is_holiday
),
per_station AS (
    SELECT
        city,
        station_id,
        count(*) FILTER (WHERE NOT is_weekend) AS weekday_trips,
        count(*) FILTER (WHERE is_weekend)     AS weekend_trips,
        count(*) FILTER (WHERE NOT is_weekend AND hour_of_day BETWEEN 7 AND 10)  AS am_peak_trips,
        count(*) FILTER (WHERE NOT is_weekend AND hour_of_day BETWEEN 16 AND 19) AS pm_peak_trips,
        count(*) AS total_trips
    FROM station_hour
    GROUP BY city, station_id
    HAVING count(*) >= 100
),
metrics AS (
    SELECT
        city,
        station_id,
        total_trips,
        (am_peak_trips + pm_peak_trips)::numeric / NULLIF(weekday_trips, 0) AS commute_index,
        (weekend_trips::numeric / NULLIF(total_trips, 0)) / (2.0 / 7.0) AS weekend_share_index
    FROM per_station
),
tercile AS (
    SELECT *,
        ntile(3) OVER (PARTITION BY city ORDER BY commute_index)       AS commute_tercile,
        ntile(3) OVER (PARTITION BY city ORDER BY weekend_share_index) AS weekend_tercile
    FROM metrics
)
SELECT
    station_id,
    total_trips,
    round(commute_index, 3)       AS commute_index,
    round(weekend_share_index, 3) AS weekend_share_index,
    CASE
        WHEN commute_tercile = 3 AND weekend_tercile = 1 THEN 'commuter-hub'
        WHEN weekend_tercile = 3 AND commute_tercile = 1 THEN 'leisure'
        ELSE 'mixed'
    END AS typology
FROM tercile
WITH NO DATA;

CREATE UNIQUE INDEX ux_station_typology_agg ON warehouse.station_typology_agg (station_id);
