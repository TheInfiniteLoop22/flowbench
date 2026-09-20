-- FB-008: the source CSVs represent the same physical station_id with
-- inconsistent decimal formatting across different months (e.g. "5980.1"
-- in one month's file, "5980.10" in another) — 111 station names ended up
-- split across two distinct station_id values in dim_station, corrupting
-- any per-station aggregate (net flow, demand, clustering) for every
-- affected station. See docs/BUG_TRACKER.md.
--
-- Canonicalize purely-numeric station_ids via trim_scale() (Postgres 13+),
-- which normalizes "5980.10" and "5980.1" to the same "5980.1". Ids that
-- aren't cleanly numeric (depot/lab placeholders like "SYS016" or
-- "3184.07_OLD") are left untouched — they're already excluded or kept
-- distinct by other filters, not part of this bug.
CREATE OR REPLACE FUNCTION warehouse.normalize_station_id(raw text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE
        WHEN raw ~ '^[0-9]+(\.[0-9]+)?$' THEN trim_scale(raw::numeric)::text
        ELSE raw
    END
$$;
