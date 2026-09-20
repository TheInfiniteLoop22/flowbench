-- Stretch (docs/PHASE_PLAN.md "second city for cross-city comparison"):
-- adds Chicago (Divvy) alongside the existing NYC (Citi Bike) data.
--
-- Design choice: `city` is an additive column, NOT part of any primary
-- key. Checked Divvy's actual station_id format before committing to
-- this (`CHI#####`, e.g. "CHI02098") against Citi Bike's (numeric,
-- e.g. "6492.08") — the two namespaces cannot collide, so
-- warehouse.dim_station.station_id stays a single global PK and
-- fact_trips needs no composite-FK rework. This keeps the blast radius
-- on the existing, already-validated NYC pipeline to "one new column
-- with a backfill default" rather than restructuring keys/indexes on a
-- 45.7M-row table.
--
-- Adding a NOT NULL column with a constant default is a metadata-only
-- change in Postgres 11+ (no full table rewrite), safe even on
-- fact_trips at its current size.
ALTER TABLE staging.stg_trips_raw ADD COLUMN IF NOT EXISTS city text NOT NULL DEFAULT 'new_york';
ALTER TABLE warehouse.dim_station ADD COLUMN IF NOT EXISTS city text NOT NULL DEFAULT 'new_york';
ALTER TABLE warehouse.fact_trips ADD COLUMN IF NOT EXISTS city text NOT NULL DEFAULT 'new_york';

CREATE INDEX IF NOT EXISTS ix_fact_trips_city_start_time ON warehouse.fact_trips (city, start_time);
CREATE INDEX IF NOT EXISTS ix_dim_station_city ON warehouse.dim_station (city);
