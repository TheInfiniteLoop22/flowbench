"""SQL backing the API endpoints. Read-only, no auth — see docs/SPEC.md §5.

Several of these mirror analysis/queries/*.sql (parametrized for a single
station or hour instead of scanning every station) — kept separate rather
than imported, since the API's job is "answer one request fast" and
analysis/'s job is "compute the full picture once and print it."

Second-city stretch (docs/PHASE_PLAN.md): every query below either takes
a %(city)s param or is safe without one because it's keyed by station_id,
which is globally unique across cities (verified when Chicago was added —
Divvy's "CHI#####" format can't collide with Citi Bike's numeric IDs).
Two rollups (demand_by_hour_agg, trips_by_day_agg) were NOT
station-keyed and would have silently blended both cities' totals — see
FB-010 in docs/BUG_TRACKER.md and warehouse/migrations/0010_*.sql.
"""

CITIES = """
    SELECT city, count(*) AS trip_count, count(DISTINCT start_station_id) AS station_count
    FROM warehouse.fact_trips
    GROUP BY city
    ORDER BY trip_count DESC
"""

# typology (stretch: docs/PHASE_PLAN.md) is null for low-volume stations
# below station_typology_agg's own >=100-trip floor — not every station
# has enough data to classify.
LIST_STATIONS = """
    SELECT d.station_id, d.name, d.lat, d.lon, ty.typology
    FROM warehouse.dim_station d
    LEFT JOIN warehouse.station_typology_agg ty ON ty.station_id = d.station_id
    WHERE d.city = %(city)s
    ORDER BY d.station_id
    LIMIT %(limit)s OFFSET %(offset)s
"""

STATION_EXISTS = "SELECT name FROM warehouse.dim_station WHERE station_id = %(station_id)s"

# Stretch (docs/PHASE_PLAN.md "short-horizon per-station demand
# forecast"): one station's daily trip counts, every date in the window
# represented (including zero-trip days) via the LEFT JOIN to dim_time —
# needed so a 7-day trailing average isn't thrown off by silently
# skipped gaps. Backed by warehouse.station_daily_demand_agg
# (warehouse/migrations/0011_*.sql) instead of a live fact_trips scan —
# fact_trips itself (17GB) doesn't ship to production, only the small
# rollups do. No city filter needed: station_id alone already scopes to
# one city.
STATION_DAILY_DEMAND = """
    SELECT t.date, coalesce(a.trip_count, 0) AS trip_count
    FROM warehouse.dim_time t
    LEFT JOIN warehouse.station_daily_demand_agg a
        ON a.date = t.date AND a.station_id = %(station_id)s
    GROUP BY t.date, a.trip_count
    ORDER BY t.date
"""

# range_days=NULL maps to the 0 ("all time") bucket precomputed in
# warehouse.station_hourly_demand_agg (warehouse/migrations/0011_*.sql)
# — one of the fixed 7/30/90/0 buckets the dashboard's range toggle
# actually offers (dashboard/src/components/StationDetail.tsx's
# RANGES), not a live fact_trips scan. No city filter needed:
# station_id alone already scopes to one city.
STATION_DEMAND = """
    SELECT
        hour_of_day,
        total_trips::numeric / greatest(distinct_days, 1) AS avg_trips_per_day,
        total_trips
    FROM warehouse.station_hourly_demand_agg
    WHERE station_id = %(station_id)s AND range_days = %(range_days)s
    ORDER BY hour_of_day
"""

# Net balance per station at a given hour-of-day, averaged across every
# calendar day in the window. Backed by station_hourly_balance_hourly_agg
# (warehouse/migrations/0004_*.sql), a pre-aggregated rollup — the naive
# form aggregating all 11.8M station_hourly_balance rows per request took
# ~668ms; this takes ~1.5ms. See docs/RESULTS.md "Performance". City
# filter via the dim_station join — the rollup itself is station-keyed
# (safe without its own city column, see module docstring).
NETWORK_IMBALANCE = """
    SELECT a.station_id, a.name, a.hour_of_day, a.avg_net_balance
    FROM warehouse.station_hourly_balance_hourly_agg a
    JOIN warehouse.dim_station s ON s.station_id = a.station_id
    WHERE a.hour_of_day = %(hour_of_day)s AND s.city = %(city)s
    ORDER BY a.avg_net_balance ASC
"""

NETWORK_DEMAND = """
    SELECT hour_of_day, trip_count
    FROM warehouse.demand_by_hour_agg
    WHERE city = %(city)s
    ORDER BY hour_of_day
"""

# Backed by warehouse.trips_by_day_agg (warehouse/migrations/0007_*.sql,
# city-scoped by 0010_*.sql) instead of a live join+count over all
# fact_trips rows (~5.9s per request pre-rollup) — the LEFT JOIN here is
# against a small per-city rollup, not the fact table, so every dim_time
# date is still represented (including any zero-trip days) at a fraction
# of the cost.
WEEKDAY_VS_WEEKEND_DAILY = """
    SELECT t.date, t.is_weekend, t.is_holiday, coalesce(a.trip_count, 0) AS trip_count
    FROM warehouse.dim_time t
    LEFT JOIN warehouse.trips_by_day_agg a ON a.date = t.date AND a.city = %(city)s
    ORDER BY t.date
"""

# Backed by warehouse.rebalancing_candidates_agg (warehouse/migrations/
# 0006_*.sql) — the three window-function passes over 11.8M rows this
# used to do per request took ~46s (first dashboard Insights-page load);
# precomputing the per-station pieces at warehouse-build time and only
# doing the final ORDER BY/LIMIT with the live truck-capacity assumption
# per request takes milliseconds. See docs/RESULTS.md "Performance".
# City filter via the dim_station join — see module docstring.
REBALANCING_CANDIDATES = """
    SELECT
        r.station_id,
        s.name,
        r.num_episodes,
        round(r.estimated_lost_trips) AS estimated_lost_trips,
        round((r.num_episodes * r.avg_hourly_outflow / %(bikes_per_truck_hour)s)::numeric, 2) AS truck_hours_needed,
        round((r.estimated_lost_trips / (r.num_episodes * r.avg_hourly_outflow / %(bikes_per_truck_hour)s))::numeric, 2) AS lost_trips_per_truck_hour
    FROM warehouse.rebalancing_candidates_agg r
    JOIN warehouse.dim_station s ON s.station_id = r.station_id
    WHERE r.num_episodes >= 10 AND r.estimated_lost_trips > 0 AND s.city = %(city)s
    ORDER BY lost_trips_per_truck_hour DESC
    LIMIT %(limit)s
"""

# Stretch ("what-if" rebalancing simulator): the ranking order among
# stations by lost-trips-per-truck-hour doesn't actually depend on
# bikes_per_truck_hour — it's a positive scalar applied equally to every
# row's truck-hours-needed, so it cancels out of the ratio. That lets the
# simulator fetch a single, larger, capacity-independent ranking here and
# apply the live truck-capacity assumption (and the truck-hour budget
# allocation) in Python, rather than re-querying per candidate scenario.
REBALANCING_CANDIDATES_RANKED = """
    SELECT
        r.station_id,
        s.name,
        r.num_episodes,
        r.avg_hourly_outflow,
        r.estimated_lost_trips
    FROM warehouse.rebalancing_candidates_agg r
    JOIN warehouse.dim_station s ON s.station_id = r.station_id
    WHERE r.num_episodes >= 10 AND r.estimated_lost_trips > 0 AND s.city = %(city)s
    ORDER BY (r.estimated_lost_trips / (r.num_episodes * r.avg_hourly_outflow)) DESC
    LIMIT %(limit)s
"""
