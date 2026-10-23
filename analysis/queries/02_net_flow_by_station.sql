-- Query 2: net inflow/outflow per station — the rebalancing signal.
-- Built on station_hourly_balance (the core artifact): sum net
-- balance per station over the whole window. A station with a large
-- negative sum structurally bleeds bikes (needs restocking); a large
-- positive sum structurally accumulates them (needs emptying). Feeds
-- query 7's ROI ranking.
SELECT
    b.station_id,
    s.name,
    sum(b.inflow)        AS total_inflow,
    sum(b.outflow)       AS total_outflow,
    sum(b.net_balance)   AS total_net,
    count(*)             AS hours_observed
FROM warehouse.station_hourly_balance b
JOIN warehouse.dim_station s ON s.station_id = b.station_id
WHERE s.city = 'new_york'  -- second city: scope to the original NYC-only result, see query 9
GROUP BY b.station_id, s.name
ORDER BY total_net ASC;
