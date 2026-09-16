-- Table already truncated by 000_truncate_fact.sql.

INSERT INTO warehouse.dim_user_type (user_type)
SELECT DISTINCT member_casual FROM staging.stg_trips_raw
WHERE member_casual IS NOT NULL;
