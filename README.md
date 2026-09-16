# FlowBench

Bike-share demand & network analytics warehouse, built on Citi Bike (NYC)
public trip data. Answers one operational question: **where and when does
the station network run short of bikes or docks, and how far in advance
can that be seen coming?**

This is a portfolio project targeting **Data Analysis** roles primarily
(secondary: SWE / Full Stack). Full rationale, scope, and role-fit
argument: [new-project-proposal.md](new-project-proposal.md).

## Status

🟡 **Planning** — see [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md) for the
live status and [docs/PHASE_PLAN.md](docs/PHASE_PLAN.md) for what's next.

## Stack

- **Data**: Citi Bike NYC trip data (public, no API key)
- **Warehouse**: PostgreSQL + PostGIS
- **Transform**: plain versioned SQL (dbt-core optional, see [ADR-0002](docs/DECISIONS.md))
- **API**: FastAPI (read-only)
- **Frontend**: Next.js + TypeScript + Recharts + MapLibre GL
- **Infra**: Docker Compose (local), Neon/Supabase (Postgres), Render (API), Vercel (frontend) — all free-tier

## Docs

| Doc | Purpose |
|---|---|
| [new-project-proposal.md](new-project-proposal.md) | Original pitch — why this project, why now |
| [docs/SPEC.md](docs/SPEC.md) | Detailed technical specification |
| [docs/PHASE_PLAN.md](docs/PHASE_PLAN.md) | Phase-by-phase implementation plan with checkboxes |
| [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md) | Dated log of what happened, decisions made, diversions from plan |
| [docs/BUG_TRACKER.md](docs/BUG_TRACKER.md) | Known issues, open/closed |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records (ADRs) |

## Repo layout (target)

```
flowbench/
├── docs/                  # this documentation suite
├── data/                  # raw/staging data (gitignored, not committed)
├── etl/                   # Python ELT scripts + data-quality checks
├── warehouse/             # SQL migrations, star schema, materialized views
├── api/                   # FastAPI read-only query layer
├── web/                   # Next.js dashboard
└── docker-compose.yml
```
