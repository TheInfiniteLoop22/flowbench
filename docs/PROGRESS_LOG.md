# FlowBench — Progress Log

> Dated, append-only log. Every session that changes scope, hits a
> blocker, makes a non-trivial decision, or diverges from PHASE_PLAN.md
> should get an entry. Newest entry on top. This is the record of *what
> actually happened*, as opposed to SPEC.md (what we intend) and
> PHASE_PLAN.md (what's left).

---

## 2026-09-17 — Project kickoff

**Status**: Planning complete, repo initialized.

- Reviewed and accepted `new-project-proposal.md` as the source pitch.
- Locked two decisions that the proposal left open:
  - Dataset: **Citi Bike (NYC)**, not Divvy.
  - Repo: **public**, named `flowbench`, under github.com/TheInfiniteLoop22.
- Created full docs suite: SPEC.md, PHASE_PLAN.md, BUG_TRACKER.md,
  DECISIONS.md, this log, and README.
- No code written yet. Next session should start Phase 1 (data + staging).

**Open items carried forward**: SPEC.md §2, all four open questions —
none blocking, all scheduled to resolve in the phase where they first
matter.

---

## 2026-09-17 — Scope expansion: bigger analysis library, results scoreboard

User asked for the project to be bigger, more detailed, and to produce
concrete results worth showing — not just a working pipeline. Response
(see [ADR-0004](DECISIONS.md#adr-0004-expand-analysis-library-beyond-the-proposals-mvp-set-p1-tier)):

- Added 4 P1-tier analytical queries beyond the original 5 (station
  typology/clustering, lost-trip estimate, rebalancing ROI ranking,
  weather correlation via Open-Meteo) — SPEC.md §4, PHASE_PLAN.md Phase 3.
- Added SPEC.md §8, "Results & success bar" — a concrete numeric
  definition of done-and-good (scale processed, ≥3 findings with CIs,
  a quantified rebalancing ranking, a documented perf benchmark, a live
  demo).
- Added [RESULTS.md](RESULTS.md) as a living scoreboard — currently all
  placeholders, to be filled with real numbers starting Phase 3.
- Added Phase 7 (Polish & Presentation) to PHASE_PLAN.md — screenshots,
  one-page report, verified live links, final "does a cold reader get it
  in under a minute" pass.
- MVP cut line unchanged; the new queries are P1 (protect, don't cut)
  rather than MVP-blocking.

---

## 2026-09-17 — Phase 1 complete: data + staging

**Status**: Phase 1 ✅ done. 45,688,697 trip rows staged, zero load
errors, all hard data-quality checks passed.

- Set up `docker-compose.yml` (Postgres 16 + PostGIS 3.4, port 5433,
  named volume) and the migration runner (`etl/run_migrations.py`).
- Built `etl/download_and_load.py`: downloads Citi Bike's monthly zips
  directly from the public S3 bucket (no key), loads each split CSV via
  `COPY` into a temp table then into `staging.stg_trips_raw`, tracks
  loaded files in `staging.load_manifest` for idempotent re-runs.
- **Resolved SPEC.md open questions #1 and #2**: locked the window to
  2025-09 through 2026-08 (most recent complete 12 months at build
  time); confirmed `station_id` is text, not integer, and confirmed a
  single stable 13-column schema across the entire window (no drift to
  handle — simpler than the open question anticipated).
- Ran `etl/dq_checks.py` against the full staged set:
  - 0 null `ride_id`, 0 null timestamps, 0 unrecognized category values
    (all hard checks passed)
  - 153,346 rows (~0.3%) null lat/lng, 482 rows (~0.001%) non-positive
    duration, 512 duplicate `ride_id`s (~0.001%) — logged as
    [FB-001/002/003](BUG_TRACKER.md), all low-severity, all deferred to
    a Phase 2 warehouse-load filter/dedup rather than touched in staging
    (staging should stay a faithful raw copy of the source).
- 2,593 distinct stations observed across start+end station IDs.
- Numbers recorded in [RESULTS.md](RESULTS.md) §Scale.
- Raw zips deleted after each load (`--keep-raw` not used) to keep disk
  usage bounded — staging table (~12 GB) is the retained source of
  truth; re-running the ELT script re-downloads from S3 if needed.

**Diversion from original plan**: none of substance — the schema-drift
risk in open question #2 didn't materialize (schema was identical across
all 12 months), which simplified the loader (no per-month schema
branching needed).

**Next**: Phase 2 (warehouse) — star schema migrations, PostGIS geometry
on `dim_station`, `station_hourly_balance` materialized view, and
resolving the three FB-00x issues at load time via filters/dedup.
