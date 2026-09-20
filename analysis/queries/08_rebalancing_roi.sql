-- Query 8 (P1): rebalancing ROI ranking. Feeds GET /insights/rebalancing-candidates.
--
-- Stated assumptions (per SPEC.md §4 query 8):
--   1. One truck moves TRUCK_BIKES_PER_HOUR = 20 bikes per hour of
--      rebalancing effort (a round mid-estimate for loading/unloading at
--      a dock over a service stop, not a measured figure — the ranking
--      is proportional in this constant, not sensitive to its value).
--   2. A rebalancing visit is triggered once per distinct "likely empty"
--      episode (a contiguous run of query 7's likely-empty hours, not
--      per hour — a truck doesn't re-visit every hour of a single
--      multi-hour stockout), and drops off enough bikes to cover that
--      station's own average hourly outflow — i.e. "one typical hour's
--      worth of demand" per visit, a deliberately conservative resupply.
--
-- Why not use query 2's whole-window net deficit as the effort term (an
-- earlier version of this query did): a station can have near-zero net
-- deficit over 12 months (bikes leave in the morning, come back by
-- evening) while still generating real lost trips from short rush-hour
-- stockouts. Dividing lost trips by a near-zero whole-year deficit
-- produced meaningless 1000+ trips/truck-hour ratios for tiny stations.
-- Episode count ties effort to the same transient-stockout phenomenon
-- that generates the lost-trip estimate, not an unrelated yearly total.
WITH running AS (
    SELECT
        station_id, hour, extract(hour FROM hour)::int AS hour_of_day, outflow,
        sum(net_balance) OVER (PARTITION BY station_id ORDER BY hour) AS cum_balance
    FROM warehouse.station_hourly_balance
),
thresholds AS (
    SELECT station_id, percentile_cont(0.05) WITHIN GROUP (ORDER BY cum_balance) AS p5_balance
    FROM running GROUP BY station_id
),
flagged AS (
    SELECT r.*, (r.cum_balance <= th.p5_balance) AS likely_empty
    FROM running r JOIN thresholds th USING (station_id)
),
episodes AS (
    SELECT *,
        likely_empty AND NOT coalesce(
            lag(likely_empty) OVER (PARTITION BY station_id ORDER BY hour), false
        ) AS episode_start
    FROM flagged
),
typical_outflow AS (
    SELECT station_id, hour_of_day, percentile_cont(0.5) WITHIN GROUP (ORDER BY outflow) AS median_outflow
    FROM flagged WHERE NOT likely_empty GROUP BY station_id, hour_of_day
),
lost_trips AS (
    SELECT
        f.station_id,
        sum(CASE WHEN f.likely_empty THEN greatest(coalesce(t.median_outflow, 0) - f.outflow, 0) ELSE 0 END) AS estimated_lost_trips
    FROM flagged f
    LEFT JOIN typical_outflow t ON t.station_id = f.station_id AND t.hour_of_day = f.hour_of_day
    GROUP BY f.station_id
),
effort AS (
    SELECT
        e.station_id,
        count(*) FILTER (WHERE e.episode_start)     AS num_episodes,
        avg(e.outflow)                              AS avg_hourly_outflow
    FROM episodes e
    GROUP BY e.station_id
)
SELECT
    ef.station_id,
    s.name,
    ef.num_episodes,
    round(lt.estimated_lost_trips)                                                    AS estimated_lost_trips,
    round((ef.num_episodes * ef.avg_hourly_outflow / 20.0)::numeric, 2)                AS truck_hours_needed,   -- TRUCK_BIKES_PER_HOUR = 20
    round((lt.estimated_lost_trips / (ef.num_episodes * ef.avg_hourly_outflow / 20.0))::numeric, 2) AS lost_trips_per_truck_hour
FROM effort ef
JOIN warehouse.dim_station s ON s.station_id = ef.station_id
JOIN lost_trips lt ON lt.station_id = ef.station_id
-- Require >=10 episodes: a station with only 1-2 stockouts all year is a
-- noise-dominated ratio (one flukey episode with a high median-outflow
-- baseline swamps a near-zero truck-hours denominator), not a real,
-- recurring rebalancing target. city = 'new_york' (second-city stretch):
-- scope to the original NYC-only result, see query 10.
WHERE ef.num_episodes >= 10 AND lt.estimated_lost_trips > 0 AND s.city = 'new_york'
ORDER BY lost_trips_per_truck_hour DESC
LIMIT 20;
