# FlowBench — Architecture Decision Records

> One entry per non-obvious decision. Short, dated, append-only. If a
> decision is later reversed, add a new ADR that supersedes it — don't
> edit history.

## ADR-0001 — Dataset: Citi Bike (NYC) over Divvy (Chicago)

**Date**: 2026-09-17
**Status**: Accepted

**Context**: Proposal named both Citi Bike and Divvy as viable free,
no-key public bike-share datasets.

**Decision**: Use Citi Bike (NYC).

**Why**: Larger dataset (better for demonstrating warehouse/query-
performance work at meaningful scale), more widely recognized by name in
interviews, well-documented monthly CSV format.

**Consequences**: Schema quirks specific to Citi Bike's CSV format
(station ID stability, format changes over time) need to be checked in
Phase 1 — tracked as SPEC.md open question #1/#2.

---

## ADR-0002 — Plain SQL migrations over dbt-core (default choice)

**Date**: 2026-09-17
**Status**: Accepted, revisitable

**Context**: Proposal flagged dbt-core as optional — a named,
resume-recognizable tool, but not required; plain versioned SQL is an
equally legitimate simpler alternative.

**Decision**: Start with plain versioned SQL migration scripts run by a
small script/runner. Revisit dbt-core only if the transform layer grows
complex enough to benefit from its dependency graph/testing features.

**Why**: Keeps the "this is a SQL project" story clean and avoids adding
a tool for resume-keyword reasons rather than need. Can be introduced
later without re-architecting (dbt models are still just SQL).

**Consequences**: If dbt is adopted later, this ADR should be superseded
by a new one recording that decision and the trigger for it.

---

## ADR-0003 — Repo visibility: public from the start

**Date**: 2026-09-17
**Status**: Accepted

**Context**: This project is being built explicitly for resume/portfolio
use.

**Decision**: `flowbench` repo is public on GitHub from day one, under
github.com/TheInfiniteLoop22.

**Why**: The point of the project is to be viewed by recruiters/
interviewers; no reason to gate it behind private visibility during
build. All docs in this repo (including this one) are written assuming
an external reader.

**Consequences**: Keep secrets (DB URLs, API keys) out of git via
`.gitignore` from the first commit onward — never commit `.env` files.
