-- Phase 5 dashboard support — see warehouse/migrations/0005_*.sql.
REFRESH MATERIALIZED VIEW warehouse.demand_by_hour_agg;
