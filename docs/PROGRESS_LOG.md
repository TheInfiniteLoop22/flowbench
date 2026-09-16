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
