-- Phase 5 dashboard support — see warehouse/migrations/0006_*.sql.
REFRESH MATERIALIZED VIEW warehouse.rebalancing_candidates_agg;
