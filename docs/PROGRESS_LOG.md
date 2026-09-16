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
