# FlowBench — Analysis library (Phase 3)

Each query is a `.sql` file in `queries/` plus a same-numbered Python
runner (`qNN_<name>.py`) that executes it against `warehouse.*`, prints a
sanity check, and reports the numbers that get copied into
[docs/RESULTS.md](../docs/RESULTS.md). Runners are read-only — no
warehouse tables are written by anything in this directory.

Convention, matching `etl/`: `from db import get_conn` (see `analysis/db.py`,
which just points at `etl/db.py` so both layers share one connection
helper and one `.env`).

Usage: `python analysis/qNN_<name>.py` from the repo root.

See [docs/SPEC.md §4](../docs/SPEC.md#4-analytical-query-library-phase-3-deliverables)
for what each query is and why, and [docs/PHASE_PLAN.md](../docs/PHASE_PLAN.md)
for status.

`q10_cross_city.py` (stretch, second city) is the exception to the
"query = one city" rule — it queries `warehouse.fact_trips` for both
`city='new_york'` and `city='chicago'` and prints them side by side. See
docs/PROGRESS_LOG.md for how/why Chicago (Divvy) was added.
