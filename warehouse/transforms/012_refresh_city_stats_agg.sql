-- Deployment prep -- see warehouse/migrations/0012_*.sql.
REFRESH MATERIALIZED VIEW warehouse.city_stats_agg;
