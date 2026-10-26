# Ticket Booking MVP

Event ticketing and seat booking platform (BookMyShow-style). Design: [`docs/design.md`](docs/design.md).

| Service | Stack | Local URL |
| --- | --- | --- |
| `web` | Next.js 15, TypeScript, Tailwind, TanStack Query | http://localhost:3000 |
| `api` | FastAPI, SQLAlchemy 2, Alembic | http://localhost:8000 (OpenAPI docs at `/docs`) |
| `db`  | PostgreSQL 16 | `localhost:5432` |

## Prerequisites

- Docker with Compose v2 (`docker compose version`). Your user must be able to talk to the
  Docker daemon. On Linux: `sudo usermod -aG docker $USER`, then log out and back in.
- Optional, for running frontend tooling on the host: Node 22+ with `corepack enable` (provides `pnpm`).

## Quick start

```bash
cp .env.example .env          # adjust secrets if needed
docker compose up --build
```

Open http://localhost:3000. The home page should show **API OK**.

On startup the `api` container runs `alembic upgrade head` and then starts Uvicorn with
hot reload. The `web` container runs `next dev`. Both mount the source, so code edits apply
without a rebuild.

The first time the `db` volume is created, `db/init/01-test-db.sql` creates the
`ticketing_test` database that the backend tests use. If you created the volume before this
script existed, run `docker compose down -v` once to recreate it.

After changing `api/pyproject.toml` or `web/package.json`, rebuild and renew the dependency
volumes: `docker compose up --build -V`.

## Commands

| Task | Command |
| --- | --- |
| Start everything | `docker compose up --build` |
| Backend tests | `docker compose exec api pytest` |
| Coverage | `docker compose exec api pytest --cov=app` |
| New migration | `docker compose exec api alembic revision --autogenerate -m "<message>"` |
| Apply migrations | `docker compose exec api alembic upgrade head` |
| Seed demo data | `docker compose exec api python -m app.seed` *(not implemented yet)* |
| Backend lint | `docker compose exec api ruff check .` |
| Frontend lint | `pnpm --dir web lint` (host) or `docker compose exec web pnpm lint` |
| Frontend tests | `pnpm --dir web test` (host) or `docker compose exec web pnpm test` |

Before you run frontend commands on the host, install dependencies once with `pnpm --dir web install`.

## Layout

```
api/                FastAPI backend: routers → services → repositories
  app/core/         config, errors, error codes, exception handlers
  app/db/           engine and session
  app/models/       SQLAlchemy models (Base with naming convention)
  alembic/          migrations
  tests/            pytest, against real PostgreSQL (ticketing_test)
web/                Next.js frontend
  src/lib/api.ts    the single API client
  src/types/        shared types
db/init/            Postgres init scripts
```

## Configuration

All config comes from environment variables. See `.env.example`. Never commit `.env`.
API errors always have the shape `{"code": "...", "message": "...", "details": {...}}`.
