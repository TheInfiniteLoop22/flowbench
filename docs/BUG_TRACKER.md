# FlowBench — Bug Tracker

> Lightweight, file-based tracker. GitHub Issues can be used in parallel
> once the repo has active development; this file is the always-in-repo
> source of truth and should be kept in sync. Move fixed items to the
> "Closed" table with the commit/PR that fixed them — don't delete history.

## Open

| ID | Severity | Summary | Found in | Notes |
|---|---|---|---|---|
| FB-001 | Low | 153,346 rows (~0.3%) have null start/end lat or lng | Phase 1 DQ checks | Source data gap, not a load bug. Decide in Phase 2: exclude these rows from `fact_trips` distance calc, or keep with `distance_m` null. Leaning toward the latter — don't drop rows just because one derived column can't be computed. |
| FB-002 | Low | 482 rows (~0.001%) have `ended_at <= started_at` | Phase 1 DQ checks | Source data anomaly (clock skew / bad rides). Exclude from duration-based analysis (Phase 3 queries 3–5) via a `WHERE duration_s > 0` filter; keep the raw rows in staging untouched for auditability. |
| FB-003 | Low | 512 duplicate `ride_id` values across the 12-month window | Phase 1 DQ checks | Likely a handful of IDs reused across month boundaries or genuine source dupes (~0.001% of 45.7M rows). Resolve in Phase 2 warehouse load with `ROW_NUMBER() OVER (PARTITION BY ride_id ORDER BY started_at) = 1` dedup, not by touching staging. |

## Closed

| ID | Severity | Summary | Found in | Fixed by | Notes |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Severity guide

- **Blocker** — halts a phase, no workaround
- **High** — wrong data/results, must fix before moving on
- **Medium** — works but needs cleanup, won't block next phase
- **Low** — cosmetic, nice-to-have

## Conventions

- ID format: `FB-###`, incrementing, never reused.
- Log the bug the moment it's found, even mid-session — don't batch this
  at the end, it gets lost.
