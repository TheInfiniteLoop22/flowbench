-- Phase 5: the dashboard's Insights page calls GET /insights/rebalancing-
-- candidates on every page load. The underlying query (analysis/q08,
-- api/queries.py's original REBALANCING_CANDIDATES) runs three window-
-- function passes over all 11.8M station_hourly_balance rows per
-- request — first load measured ~46s, unusable for a dashboard page.
-- Same fix as 0004/0005: precompute the expensive per-station pieces
-- (episode count, average hourly outflow, estimated lost trips) once per
-- warehouse build; the API then only does a cheap final join + ORDER BY
-- LIMIT, and the truck-capacity assumption stays a live query param
-- rather than baked into the materialized numbers.
CREATE MATERIALIZED VIEW IF NOT EXISTS warehouse.rebalancing_candidates_agg AS
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
)
SELECT
    e.station_id,
    count(*) FILTER (WHERE e.episode_start) AS num_episodes,
    avg(e.outflow)                          AS avg_hourly_outflow,
    coalesce(lt.estimated_lost_trips, 0)    AS estimated_lost_trips
FROM episodes e
LEFT JOIN lost_trips lt ON lt.station_id = e.station_id
GROUP BY e.station_id, lt.estimated_lost_trips
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS ux_rebalancing_candidates_agg ON warehouse.rebalancing_candidates_agg (station_id);
