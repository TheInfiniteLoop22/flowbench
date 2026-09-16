-- Phase 1: staging schema for raw Citi Bike trip data.
-- Loaded as close to source as possible (typed loosely, no cleaning) so
-- the ELT step stays re-runnable and auditable against the source CSVs.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.stg_trips_raw (
    ride_id             text,
    rideable_type       text,
    started_at          timestamp,
    ended_at            timestamp,
    start_station_name  text,
    start_station_id    text,   -- text, not numeric: Citi Bike station IDs
                                 -- include non-integer values (e.g. "5905.14")
    end_station_name    text,
    end_station_id      text,
    start_lat           double precision,
    start_lng           double precision,
    end_lat             double precision,
    end_lng             double precision,
    member_casual       text,
    source_file         text NOT NULL,   -- which monthly zip this row came from
    loaded_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_stg_trips_raw_source_file
    ON staging.stg_trips_raw (source_file);

CREATE INDEX IF NOT EXISTS ix_stg_trips_raw_started_at
    ON staging.stg_trips_raw (started_at);

-- Tracks which source files have been loaded, for idempotent re-runs.
CREATE TABLE IF NOT EXISTS staging.load_manifest (
    source_file     text PRIMARY KEY,
    row_count       bigint NOT NULL,
    zip_size_bytes  bigint,
    loaded_at       timestamptz NOT NULL DEFAULT now()
);
