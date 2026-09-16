-- Builds fact_trips from staging, applying the two filters logged as
-- FB-002 and FB-003 in docs/BUG_TRACKER.md. Staging itself is left
-- untouched — these are warehouse-load-time decisions, not data fixes.
--
-- FK-safety: a station_id is only kept if it resolves in dim_station
-- (built in 003 from non-null-coordinate observations only); otherwise
-- it's set to NULL here rather than violating the FK — a station_id
-- that never once had usable coordinates across 45.7M rows is a source
-- data gap, not something this load should crash on.

-- Table already truncated by 000_truncate_fact.sql.

WITH deduped AS (
    SELECT *,
           row_number() OVER (PARTITION BY ride_id ORDER BY started_at) AS rn
    FROM staging.stg_trips_raw
    WHERE ended_at > started_at   -- drops FB-002 (482 non-positive-duration rows)
)
INSERT INTO warehouse.fact_trips (
    ride_id, rideable_type, start_station_id, end_station_id,
    start_date, start_time, end_time, duration_s, user_type, distance_m
)
SELECT
    d.ride_id,
    d.rideable_type,
    sd.station_id,
    ed.station_id,
    d.started_at::date,
    d.started_at,
    d.ended_at,
    extract(epoch FROM (d.ended_at - d.started_at))::int,
    d.member_casual,
    CASE WHEN sd.geom IS NOT NULL AND ed.geom IS NOT NULL
         THEN ST_Distance(sd.geom::geography, ed.geom::geography)
         ELSE NULL END
FROM deduped d
LEFT JOIN warehouse.dim_station sd ON sd.station_id = d.start_station_id
LEFT JOIN warehouse.dim_station ed ON ed.station_id = d.end_station_id
WHERE d.rn = 1;   -- drops FB-003 (512 duplicate ride_ids), keeps earliest occurrence
