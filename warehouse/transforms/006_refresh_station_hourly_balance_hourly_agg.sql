-- Phase 4 performance artifact — see warehouse/migrations/0004_*.sql.
-- Must run after 005 (station_hourly_balance itself must be fresh first).
REFRESH MATERIALIZED VIEW warehouse.station_hourly_balance_hourly_agg;
