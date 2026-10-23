-- Postgres refuses to TRUNCATE a table with any FK pointing at it,
-- regardless of whether the referencing table currently has rows — so
-- fact_trips and all three dimension tables it references must be
-- truncated together, in one statement, every rebuild.
TRUNCATE TABLE warehouse.fact_trips, warehouse.dim_time, warehouse.dim_station, warehouse.dim_user_type;
