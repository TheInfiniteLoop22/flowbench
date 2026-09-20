"""Query 6 (P1): station typology by demand-curve shape. See docs/SPEC.md §4.

Usage: python analysis/q06_typology.py
"""
import pathlib
import time
from collections import Counter

from db import get_conn

SQL = (pathlib.Path(__file__).resolve().parent / "queries" / "06_station_typology.sql").read_text()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            t0 = time.time()
            cur.execute(SQL)
            rows = cur.fetchall()
            elapsed = time.time() - t0
            print(f"{len(rows):,} classified stations in {elapsed:.1f}s\n")

            counts = Counter(r[5] for r in rows)
            for typology, n in counts.most_common():
                print(f"  {typology:14} {n:5,} stations")

            for typology in ("commuter-hub", "leisure", "mixed"):
                top5 = [r for r in rows if r[5] == typology][:5]
                print(f"\nTop 5 '{typology}' stations by volume:")
                for station_id, name, total, commute_idx, weekend_idx, _ in top5:
                    print(f"  {name[:40]:40}  total={total:>7,}  "
                          f"commute_index={commute_idx}  weekend_share_index={weekend_idx}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
