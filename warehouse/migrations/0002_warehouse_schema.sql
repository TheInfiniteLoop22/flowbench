-- Phase 2: star schema DDL. Tables here are populated (and repopulated)
-- by warehouse/transforms/*.sql, not by this migration — this file only
-- defines structure, run once. See docs/SPEC.md §3.2.

CREATE SCHEMA IF NOT EXISTS warehouse;

CREATE TABLE IF NOT EXISTS warehouse.dim_time (
    date            date PRIMARY KEY,
    day_of_week     smallint NOT NULL,   -- 0=Sunday .. 6=Saturday
    day_name        text NOT NULL,
    is_weekend      boolean NOT NULL,
    is_holiday      boolean NOT NULL,
    month           smallint NOT NULL,
    year            smallint NOT NULL,
    season          text NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouse.dim_user_type (
    user_type   text PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS warehouse.dim_station (
    station_id  text PRIMARY KEY,
    name        text NOT NULL,
    lat         double precision NOT NULL,
    lon         double precision NOT NULL,
    capacity    int,                 -- not published by source; left null (SPEC.md §3.2)
    geom        geometry(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_dim_station_geom ON warehouse.dim_station USING gist (geom);

CREATE TABLE IF NOT EXISTS warehouse.fact_trips (
    ride_id             text PRIMARY KEY,
    rideable_type       text NOT NULL,
    start_station_id    text REFERENCES warehouse.dim_station (station_id),
    end_station_id      text REFERENCES warehouse.dim_station (station_id),
    start_date          date NOT NULL REFERENCES warehouse.dim_time (date),
    start_time          timestamp NOT NULL,
    end_time            timestamp NOT NULL,
    duration_s          integer NOT NULL,
    user_type           text NOT NULL REFERENCES warehouse.dim_user_type (user_type),
    distance_m          double precision   -- null when either station is unresolved
);

CREATE INDEX IF NOT EXISTS ix_fact_trips_start_time ON warehouse.fact_trips (start_time);
CREATE INDEX IF NOT EXISTS ix_fact_trips_start_station ON warehouse.fact_trips (start_station_id, start_time);
CREATE INDEX IF NOT EXISTS ix_fact_trips_end_station ON warehouse.fact_trips (end_station_id, start_time);

-- The core analytical artifact: net bikes in minus out, per station per
-- hour. Populated via REFRESH MATERIALIZED VIEW (transforms/005).
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.station_hourly_balance AS
SELECT
    station_id,
    hour,
    SUM(inflow)  AS inflow,
    SUM(outflow) AS outflow,
    SUM(inflow) - SUM(outflow) AS net_balance
FROM (
    SELECT end_station_id AS station_id, date_trunc('hour', end_time) AS hour,
           1 AS inflow, 0 AS outflow
    FROM warehouse.fact_trips
    WHERE end_station_id IS NOT NULL
    UNION ALL
    SELECT start_station_id AS station_id, date_trunc('hour', start_time) AS hour,
           0 AS inflow, 1 AS outflow
    FROM warehouse.fact_trips
    WHERE start_station_id IS NOT NULL
) flows
GROUP BY station_id, hour
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_station_hourly_balance
    ON warehouse.station_hourly_balance (station_id, hour);
