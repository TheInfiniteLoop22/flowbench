"""Downloads Citi Bike monthly trip-data zips and loads them into
staging.stg_trips_raw. Idempotent: a (zip, member-csv) pair already
recorded in staging.load_manifest is skipped on re-run.

Usage:
    python etl/download_and_load.py --start 202509 --end 202608
    python etl/download_and_load.py --start 202509 --end 202608 --keep-raw
"""
import argparse
import io
import pathlib
import sys
import zipfile
from datetime import datetime

import requests

from db import get_conn

BASE_URL = "https://s3.amazonaws.com/tripdata"
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"

EXPECTED_COLUMNS = [
    "ride_id", "rideable_type", "started_at", "ended_at",
    "start_station_name", "start_station_id", "end_station_name",
    "end_station_id", "start_lat", "start_lng", "end_lat", "end_lng",
    "member_casual",
]


def month_range(start: str, end: str):
    start_dt = datetime.strptime(start, "%Y%m")
    end_dt = datetime.strptime(end, "%Y%m")
    y, m = start_dt.year, start_dt.month
    while (y, m) <= (end_dt.year, end_dt.month):
        yield f"{y:04d}{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def download(yyyymm: str) -> pathlib.Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / f"{yyyymm}-citibike-tripdata.zip"
    if dest.exists():
        print(f"  [{yyyymm}] zip already on disk, skipping download")
        return dest
    url = f"{BASE_URL}/{yyyymm}-citibike-tripdata.zip"
    print(f"  [{yyyymm}] downloading {url}")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print(f"  [{yyyymm}] downloaded {dest.stat().st_size / 1e6:.1f} MB")
    return dest


def already_loaded(conn, source_file: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM staging.load_manifest WHERE source_file = %s", (source_file,)
        )
        return cur.fetchone() is not None


def load_csv_member(conn, zf: zipfile.ZipFile, member: str, source_file: str):
    with zf.open(member) as raw:
        text_stream = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        header = text_stream.readline().strip().split(",")
        if header != EXPECTED_COLUMNS:
            raise ValueError(
                f"{source_file}: unexpected column layout.\n"
                f"  expected: {EXPECTED_COLUMNS}\n"
                f"  got:      {header}\n"
                f"This is exactly the schema-drift risk flagged in SPEC.md open "
                f"question #2 — inspect this file by hand before proceeding."
            )

        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE UNLOGGED TABLE IF NOT EXISTS staging._load_tmp (
                    ride_id text, rideable_type text, started_at timestamp,
                    ended_at timestamp, start_station_name text,
                    start_station_id text, end_station_name text,
                    end_station_id text, start_lat double precision,
                    start_lng double precision, end_lat double precision,
                    end_lng double precision, member_casual text
                )
                """
            )
            cur.execute("TRUNCATE staging._load_tmp")
            cur.copy_expert(
                "COPY staging._load_tmp FROM STDIN WITH (FORMAT csv, NULL '')",
                text_stream,
            )
            cur.execute("SELECT count(*) FROM staging._load_tmp")
            row_count = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO staging.stg_trips_raw (
                    ride_id, rideable_type, started_at, ended_at,
                    start_station_name, start_station_id, end_station_name,
                    end_station_id, start_lat, start_lng, end_lat, end_lng,
                    member_casual, source_file
                )
                SELECT ride_id, rideable_type, started_at, ended_at,
                    start_station_name, start_station_id, end_station_name,
                    end_station_id, start_lat, start_lng, end_lat, end_lng,
                    member_casual, %s
                FROM staging._load_tmp
                """,
                (source_file,),
            )
            cur.execute(
                "INSERT INTO staging.load_manifest (source_file, row_count) "
                "VALUES (%s, %s)",
                (source_file, row_count),
            )
        conn.commit()
        print(f"    loaded {member}: {row_count:,} rows")
        return row_count


def process_month(conn, yyyymm: str, keep_raw: bool) -> int:
    zip_path = download(yyyymm)
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        members = [n for n in zf.namelist() if n.endswith(".csv") and "__MACOSX" not in n]
        for member in sorted(members):
            source_file = f"{zip_path.name}:{member}"
            if already_loaded(conn, source_file):
                print(f"  [{yyyymm}] {member} already loaded, skipping")
                continue
            total += load_csv_member(conn, zf, member, source_file)
    if not keep_raw:
        zip_path.unlink()
        print(f"  [{yyyymm}] deleted raw zip (pass --keep-raw to retain)")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYYMM, inclusive")
    ap.add_argument("--end", required=True, help="YYYYMM, inclusive")
    ap.add_argument("--keep-raw", action="store_true", help="keep downloaded zips on disk")
    args = ap.parse_args()

    conn = get_conn()
    grand_total = 0
    try:
        for yyyymm in month_range(args.start, args.end):
            print(f"[{yyyymm}] processing")
            grand_total += process_month(conn, yyyymm, args.keep_raw)
    finally:
        conn.close()

    print(f"\nDone. {grand_total:,} rows loaded across "
          f"{args.start}-{args.end}.")


if __name__ == "__main__":
    sys.exit(main())
