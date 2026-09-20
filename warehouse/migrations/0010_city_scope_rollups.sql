-- Second-city stretch: audited every existing rollup (0004-0008) for
-- whether adding Chicago would silently blend it with NYC. Two are
-- keyed by station_id, which is already globally unique across cities
-- (checked before adding Chicago — see 0009's comment) and so are safe
-- as-is: station_hourly_balance_hourly_agg, rebalancing_candidates_agg,
-- station_typology_agg — a station_id row can only ever belong to one
-- city, grouping by it never merges two cities' numbers. The API filters
-- these by joining dim_station.city, no rebuild needed.
--
-- Two are NOT safe: demand_by_hour_agg and trips_by_day_agg both
-- aggregate "every trip, this hour/day" into a single network-wide
-- number with no per-station grouping — exactly the kind of rollup that
-- would have quietly summed NYC's ~125k trips/day with Chicago's ~2k/day
-- into one meaningless total the moment Chicago's fact_trips rows
-- landed. Caught by re-reading each rollup's GROUP BY before the
-- warehouse rebuild that adds Chicago, not after a wrong number shipped.
-- Dropped and recreated with city in the grouping/unique index.

DROP MATERIALIZED VIEW IF EXISTS warehouse.demand_by_hour_agg;
CREATE MATERIALIZED VIEW warehouse.demand_by_hour_agg AS
SELECT
    city,
    extract(hour FROM start_time)::int AS hour_of_day,
    count(*) AS trip_count
FROM warehouse.fact_trips
WHERE start_station_id IS NOT NULL
GROUP BY city, 2
WITH NO DATA;

CREATE UNIQUE INDEX ux_demand_by_hour_agg ON warehouse.demand_by_hour_agg (city, hour_of_day);

DROP MATERIALIZED VIEW IF EXISTS warehouse.trips_by_day_agg;
CREATE MATERIALIZED VIEW warehouse.trips_by_day_agg AS
SELECT city, start_date AS date, count(*) AS trip_count
FROM warehouse.fact_trips
GROUP BY city, start_date
WITH NO DATA;

CREATE UNIQUE INDEX ux_trips_by_day_agg ON warehouse.trips_by_day_agg (city, date);
