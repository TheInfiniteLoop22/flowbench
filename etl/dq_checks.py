"""Data-quality checks against staging.stg_trips_raw. Run after loading.
Fails loud (non-zero exit) if a hard check is violated.

Usage: python etl/dq_checks.py
"""
import sys

from db import get_conn

HARD_CHECKS_FAILED = []
WARNINGS = []


def check(cur, description, sql, threshold=0, hard=True):
    cur.execute(sql)
    value = cur.fetchone()[0]
    status = "OK" if value <= threshold else ("FAIL" if hard else "WARN")
    print(f"  [{status}] {description}: {value}")
    if value > threshold:
        (HARD_CHECKS_FAILED if hard else WARNINGS).append(description)


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM staging.stg_trips_raw")
            total = cur.fetchone()[0]
            print(f"Total staged rows: {total:,}\n")

            print("Row counts vs. source manifest:")
            cur.execute(
                """
                SELECT m.source_file, m.row_count, s.actual
                FROM staging.load_manifest m
                JOIN (
                    SELECT source_file, count(*) AS actual
                    FROM staging.stg_trips_raw GROUP BY source_file
                ) s USING (source_file)
                WHERE m.row_count != s.actual
                """
            )
            mismatches = cur.fetchall()
            if mismatches:
                for row in mismatches:
                    print(f"  [FAIL] {row[0]}: manifest={row[1]} actual={row[2]}")
                    HARD_CHECKS_FAILED.append(f"row count mismatch: {row[0]}")
            else:
                print("  [OK] every loaded file's staged row count matches its manifest entry")

            print("\nNull / integrity audits:")
            check(cur, "rows with null ride_id", """
                SELECT count(*) FROM staging.stg_trips_raw WHERE ride_id IS NULL
            """)
            check(cur, "rows with null started_at or ended_at", """
                SELECT count(*) FROM staging.stg_trips_raw
                WHERE started_at IS NULL OR ended_at IS NULL
            """)
            check(cur, "rows with null start/end lat or lng", """
                SELECT count(*) FROM staging.stg_trips_raw
                WHERE start_lat IS NULL OR start_lng IS NULL
                   OR end_lat IS NULL OR end_lng IS NULL
            """, hard=False)
            check(cur, "rows with negative or zero duration", """
                SELECT count(*) FROM staging.stg_trips_raw
                WHERE ended_at <= started_at
            """, hard=False)
            check(cur, "duplicate ride_id values", """
                SELECT count(*) FROM (
                    SELECT ride_id FROM staging.stg_trips_raw
                    GROUP BY ride_id HAVING count(*) > 1
                ) d
            """, hard=False)
            check(cur, "rows with unrecognized member_casual value", """
                SELECT count(*) FROM staging.stg_trips_raw
                WHERE member_casual NOT IN ('member', 'casual')
            """)
            check(cur, "rows with unrecognized rideable_type value", """
                SELECT count(*) FROM staging.stg_trips_raw
                WHERE rideable_type NOT IN ('classic_bike', 'electric_bike', 'docked_bike')
            """, hard=False)

    finally:
        conn.close()

    print()
    if HARD_CHECKS_FAILED:
        print(f"FAILED: {len(HARD_CHECKS_FAILED)} hard check(s) did not pass:")
        for c in HARD_CHECKS_FAILED:
            print(f"  - {c}")
        return 1
    print(f"All hard checks passed. {len(WARNINGS)} soft warning(s) — "
          f"expected for real-world data, tracked here rather than hidden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
