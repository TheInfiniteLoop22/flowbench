# FlowBench Warehouse (Phase 2)

Star schema built from `staging.stg_trips_raw`. See
[docs/SPEC.md](../docs/SPEC.md) §3.2 for the table design and rationale.

## Layout

- `migrations/` — schema DDL, applied once each by `etl/run_migrations.py`
  (tracked in `schema_migrations`). Defines table structure only.
- `transforms/` — idempotent SQL that populates the schema from staging:
  `TRUNCATE` + `INSERT ... SELECT` for the dimension/fact tables, and a
  `REFRESH MATERIALIZED VIEW` for `station_hourly_balance`. Safe to
  re-run any time staging changes (e.g. after loading a new month) —
  this is the "rebuild the warehouse periodically" step described in
  the proposal's batch-ELT design (proposal §6).

## Build

```bash
python etl/build_warehouse.py    # applies migrations, then runs all transforms in order
python etl/warehouse_checks.py   # referential integrity + inflow/outflow sanity checks
```

## Notes

- `000_truncate_fact.sql` truncates `fact_trips` together with all three
  dimension tables in a single statement — Postgres refuses to truncate
  a table that's FK-referenced by another, even an empty one, so the
  dimensions can't be cleared separately from the fact table.
- `dim_station` excludes rows with null *or* `(0,0)` coordinates (the
  latter caught a real depot/placeholder station — see
  [BUG_TRACKER.md FB-004](../docs/BUG_TRACKER.md)) — a station that
  never has usable coordinates simply won't appear, and any trip
  referencing it gets a null FK rather than crashing the build.
- `fact_trips` currently takes ~55–60 minutes to rebuild from 45.7M
  staging rows — tracked as [FB-006](../docs/BUG_TRACKER.md) for
  Phase 4 optimization, not addressed yet since this is a batch job, not
  a hot path.
