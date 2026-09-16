-- Rebuilds warehouse.dim_time from the observed date range in staging.
-- Idempotent: safe to re-run on every warehouse build.
--
-- Holiday list is hardcoded to US federal holidays that fall within the
-- observed 2025-09..2026-08 window (see docs/SPEC.md §3.2). If the
-- staging window changes, extend this list accordingly — it is
-- deliberately not computed (floating holidays like "3rd Monday of
-- January" are easy to get wrong in SQL; a short explicit list is safer
-- and auditable at a glance).

-- Table already truncated by 000_truncate_fact.sql (must happen together
-- with fact_trips due to the FK — see that file's comment).

WITH bounds AS (
    SELECT min(started_at)::date AS min_date, max(started_at)::date AS max_date
    FROM staging.stg_trips_raw
),
days AS (
    SELECT generate_series(min_date, max_date, interval '1 day')::date AS date
    FROM bounds
),
holidays (date) AS (
    VALUES
        ('2025-09-01'::date),  -- Labor Day
        ('2025-10-13'::date),  -- Columbus Day
        ('2025-11-11'::date),  -- Veterans Day
        ('2025-11-27'::date),  -- Thanksgiving
        ('2025-12-25'::date),  -- Christmas Day
        ('2026-01-01'::date),  -- New Year's Day
        ('2026-01-19'::date),  -- MLK Day
        ('2026-02-16'::date),  -- Washington's Birthday
        ('2026-05-25'::date),  -- Memorial Day
        ('2026-06-19'::date)   -- Juneteenth
)
INSERT INTO warehouse.dim_time (date, day_of_week, day_name, is_weekend, is_holiday, month, year, season)
SELECT
    d.date,
    extract(dow FROM d.date)::smallint,
    to_char(d.date, 'Day'),
    extract(dow FROM d.date) IN (0, 6),
    h.date IS NOT NULL,
    extract(month FROM d.date)::smallint,
    extract(year FROM d.date)::smallint,
    CASE extract(month FROM d.date)
        WHEN 12 THEN 'winter' WHEN 1 THEN 'winter' WHEN 2 THEN 'winter'
        WHEN 3 THEN 'spring' WHEN 4 THEN 'spring' WHEN 5 THEN 'spring'
        WHEN 6 THEN 'summer' WHEN 7 THEN 'summer' WHEN 8 THEN 'summer'
        ELSE 'fall'
    END
FROM days d
LEFT JOIN holidays h ON h.date = d.date;
