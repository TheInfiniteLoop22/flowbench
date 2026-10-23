-- Dashboard rollup refresh — see warehouse/migrations/0006_*.sql.
REFRESH MATERIALIZED VIEW warehouse.rebalancing_candidates_agg;
