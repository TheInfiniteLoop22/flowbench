-- Deployment prep -- see warehouse/migrations/0011_*.sql.
REFRESH MATERIALIZED VIEW warehouse.station_daily_demand_agg;
REFRESH MATERIALIZED VIEW warehouse.station_hourly_demand_agg;
