"""Seeds a small, disposable test warehouse (SPEC.md §7: "API tests
against a seeded test warehouse (small fixture, not the full dataset)")
in a separate database (flowbench_test) inside the same local Postgres
instance the dev warehouse uses — never touches the real 45M-row
warehouse.

DATABASE_URL is overridden to point at flowbench_test *before* api.db is
imported, so the app's connection pool never sees the real dev database.
"""
import os
import pathlib
import sys

import psycopg2
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "etl"))

BASE_DSN = os.environ.get("DATABASE_URL", "postgresql://flowbench:flowbench@localhost:5433/flowbench")
# Swap the db name in the DSN for a dedicated test database.
_TEST_DSN = BASE_DSN.rsplit("/", 1)[0] + "/flowbench_test"
os.environ["DATABASE_URL"] = _TEST_DSN

MIGRATIONS_DIR = REPO_ROOT / "warehouse" / "migrations"


def _admin_dsn():
    return BASE_DSN.rsplit("/", 1)[0] + "/postgres"


@pytest.fixture(scope="session", autouse=True)
def seeded_test_warehouse():
    # (Re)create flowbench_test from scratch against the 'postgres' admin db.
    admin_conn = psycopg2.connect(_admin_dsn())
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = 'flowbench_test' AND pid <> pg_backend_pid()"
        )
        cur.execute("DROP DATABASE IF EXISTS flowbench_test")
        cur.execute("CREATE DATABASE flowbench_test")
    admin_conn.close()

    conn = psycopg2.connect(_TEST_DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name == "0000_schema_migrations.sql":
                continue  # bookkeeping table only, not needed for a throwaway test DB
            cur.execute(path.read_text(encoding="utf-8"))

        # --- small hand-built fixture: 3 stations, 6 days, ~40 trips ---
        cur.execute("""
            INSERT INTO warehouse.dim_user_type (user_type) VALUES ('member'), ('casual')
        """)
        cur.execute("""
            INSERT INTO warehouse.dim_station (station_id, name, lat, lon, geom, city) VALUES
                ('S1', 'Test Station One',   40.730, -73.990, ST_SetSRID(ST_MakePoint(-73.990, 40.730), 4326), 'new_york'),
                ('S2', 'Test Station Two',   40.740, -73.995, ST_SetSRID(ST_MakePoint(-73.995, 40.740), 4326), 'new_york'),
                ('S3', 'Test Station Three', 40.735, -73.985, ST_SetSRID(ST_MakePoint(-73.985, 40.735), 4326), 'new_york'),
                ('C1', 'Test Chicago Station', 41.880, -87.630, ST_SetSRID(ST_MakePoint(-87.630, 41.880), 4326), 'chicago')
        """)
        cur.execute("""
            INSERT INTO warehouse.dim_time (date, day_of_week, day_name, is_weekend, is_holiday, month, year, season)
            SELECT
                d::date,
                extract(dow FROM d)::smallint,
                to_char(d, 'FMDay'),
                extract(dow FROM d) IN (0, 6),
                d::date = '2025-09-01',
                extract(month FROM d)::smallint,
                extract(year FROM d)::smallint,
                'fall'
            FROM generate_series('2025-09-01'::date, '2025-09-14'::date, interval '1 day') d
        """)

        # 4 trips/hour-ish spread across stations/hours/days so demand,
        # imbalance, and the weekday/weekend split all have something to
        # chew on; deliberately small, not a scaled-down copy of prod data.
        cur.execute("""
            INSERT INTO warehouse.fact_trips
                (ride_id, rideable_type, start_station_id, end_station_id,
                 start_date, start_time, end_time, duration_s, user_type, distance_m)
            SELECT
                'T' || row_number() OVER (),
                'classic_bike',
                station_id,
                CASE WHEN station_id = 'S1' THEN 'S2' WHEN station_id = 'S2' THEN 'S3' ELSE 'S1' END,
                d::date,
                d + (hour || ' hours')::interval,
                d + (hour || ' hours')::interval + interval '10 minutes',
                600,
                CASE WHEN hour % 2 = 0 THEN 'member' ELSE 'casual' END,
                500.0
            FROM generate_series('2025-09-01'::date, '2025-09-14'::date, interval '1 day') d
            CROSS JOIN (VALUES ('S1'), ('S2'), ('S3')) s(station_id)
            CROSS JOIN generate_series(8, 18, 5) hour
        """)
        # A second, day-varying batch on top of the fixed baseline above —
        # without it, every day has an identical trip count (3 stations x
        # 3 hours), which is zero-variance and makes Shapiro-Wilk (used by
        # /insights/weekday-vs-weekend) degenerate (nan p-value).
        cur.execute("""
            INSERT INTO warehouse.fact_trips
                (ride_id, rideable_type, start_station_id, end_station_id,
                 start_date, start_time, end_time, duration_s, user_type, distance_m)
            SELECT
                'B' || row_number() OVER (),
                'classic_bike', 'S1', 'S2',
                d::date, d + interval '9 hours', d + interval '9 hours 10 minutes',
                600, 'member', 500.0
            FROM generate_series('2025-09-01'::date, '2025-09-14'::date, interval '1 day') d
            CROSS JOIN generate_series(1, (extract(day FROM d)::int % 5) + 1) extra
        """)

        # A handful of Chicago trips (second-city stretch) so city-filtered
        # endpoints have something real to distinguish from NYC's fixture.
        cur.execute("""
            INSERT INTO warehouse.fact_trips
                (ride_id, rideable_type, start_station_id, end_station_id,
                 start_date, start_time, end_time, duration_s, user_type, distance_m, city)
            SELECT
                'CHI' || row_number() OVER (),
                'electric_bike', 'C1', 'C1',
                d::date, d + interval '9 hours', d + interval '9 hours 5 minutes',
                300, 'member', 100.0, 'chicago'
            FROM generate_series('2025-09-01'::date, '2025-09-14'::date, interval '1 day') d
        """)

        cur.execute("REFRESH MATERIALIZED VIEW warehouse.station_hourly_balance")
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.station_hourly_balance_hourly_agg")
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.demand_by_hour_agg")
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.rebalancing_candidates_agg")
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.trips_by_day_agg")
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.station_typology_agg")
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.station_daily_demand_agg")
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.station_hourly_demand_agg")

    conn.close()
    yield
