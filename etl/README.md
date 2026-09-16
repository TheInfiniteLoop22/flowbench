# FlowBench ETL (Phase 1: data + staging)

Downloads Citi Bike's public monthly trip-data zips (no API key) and
loads them into `staging.stg_trips_raw` in Postgres, raw and untyped
beyond basic column types — no cleaning at this stage. See
[docs/SPEC.md](../docs/SPEC.md) §2–3 for the schema and rationale.

## Setup

```bash
# from repo root
docker compose up -d          # starts Postgres+PostGIS on localhost:5433
cp .env.example .env          # adjust if you changed docker-compose.yml
pip install -r etl/requirements.txt
python etl/run_migrations.py  # creates staging schema/tables
```

## Load data

```bash
# download + load a range of months (YYYYMM, inclusive)
python etl/download_and_load.py --start 202509 --end 202608

# keep the downloaded zips on disk instead of deleting after load
python etl/download_and_load.py --start 202509 --end 202608 --keep-raw
```

Idempotent: re-running skips any (zip, csv-part) already recorded in
`staging.load_manifest`, so an interrupted run can be safely resumed.

## Validate

```bash
python etl/dq_checks.py
```

Runs the data-quality checks described in [docs/PHASE_PLAN.md](../docs/PHASE_PLAN.md)
Phase 1: row counts vs. manifest, null audits, duplicate `ride_id`
check, and duration sanity check. Hard checks (null `ride_id`, missing
timestamps, unrecognized category values) fail the run; soft checks
(null lat/lng, negative duration, duplicate IDs) warn but don't block —
these are the kind of real-world data blemishes worth tracking, not
worth stopping the pipeline over.
