-- Dedups stations from staging (as either a trip's start or end point).
-- A station's name/lat/lon can drift slightly across 12 months (station
-- renames, GPS jitter) — we take its most recent observed values rather
-- than averaging, since "current name/location" is what a dashboard
-- should show.
--
-- station_id is normalized via warehouse.normalize_station_id() (FB-008)
-- before dedup, so "5980.1" and "5980.10" collapse to one station.
--
-- city (added 0009_add_city_dimension.sql, second-city stretch) is
-- carried straight from staging — a given station_id belongs to exactly
-- one city, so no cross-city dedup conflict is possible.

-- Table already truncated by 000_truncate_fact.sql.

WITH observations AS (
    SELECT warehouse.normalize_station_id(start_station_id) AS station_id, start_station_name AS name,
           start_lat AS lat, start_lng AS lon, started_at AS observed_at, city
    FROM staging.stg_trips_raw
    WHERE start_station_id IS NOT NULL AND start_lat IS NOT NULL AND start_lng IS NOT NULL
      AND NOT (start_lat = 0 AND start_lng = 0)  -- FB-004: depot/placeholder stations (e.g. "SYS018 Bronx WH station") use (0,0)
    UNION ALL
    SELECT warehouse.normalize_station_id(end_station_id), end_station_name, end_lat, end_lng, started_at, city
    FROM staging.stg_trips_raw
    WHERE end_station_id IS NOT NULL AND end_lat IS NOT NULL AND end_lng IS NOT NULL
      AND NOT (end_lat = 0 AND end_lng = 0)
),
ranked AS (
    SELECT station_id, name, lat, lon, city,
           row_number() OVER (PARTITION BY station_id ORDER BY observed_at DESC) AS rn
    FROM observations
)
INSERT INTO warehouse.dim_station (station_id, name, lat, lon, geom, city)
SELECT station_id, name, lat, lon,
       ST_SetSRID(ST_MakePoint(lon, lat), 4326),
       city
FROM ranked
WHERE rn = 1;
