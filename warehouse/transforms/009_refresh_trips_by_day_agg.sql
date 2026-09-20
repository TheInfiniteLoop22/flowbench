-- Phase 5 dashboard support — see warehouse/migrations/0007_*.sql.
REFRESH MATERIALIZED VIEW warehouse.trips_by_day_agg;
