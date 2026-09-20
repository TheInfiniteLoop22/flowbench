"""Query 3: trip-duration distribution by user type. See docs/SPEC.md §4.

Usage: python analysis/q03_duration.py
"""
import pathlib
import time

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "03_duration_by_user_type.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"{len(rows)} user types in {elapsed:.1f}s\n")

            cur.execute("SELECT count(*) FROM warehouse.fact_trips")
            total = cur.fetchone()[0]
            total_n = sum(r[cols.index("n")] for r in rows)
            status = "OK" if total_n == total else "FAIL"
            print(f"  [{status}] sum(n) across user types == fact_trips rows: {total_n:,} vs {total:,}\n")

            header = "  ".join(f"{c:>12}" for c in cols)
            print(header)
            for row in rows:
                print("  ".join(f"{v:>12,}" if isinstance(v, (int, float)) else f"{v:>12}" for v in row))

            mean_min = {r[0]: r[cols.index("mean_s")] / 60 for r in rows}
            median_min = {r[0]: r[cols.index("median_s")] / 60 for r in rows}
            print("\nIn minutes (mean / median):")
            for user_type in mean_min:
                print(f"  {user_type}: mean {mean_min[user_type]:.1f} min, median {median_min[user_type]:.1f} min")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
