# Ticket Booking MVP — guide for Claude Code

## Project
Event ticketing and seat booking platform (BookMyShow-style), built as a 5-day hackathon MVP.
**Source of truth: `docs/design.md`.** Read the relevant section before building a module.
If the code and the design disagree, stop and ask — never diverge silently.

## Repository layout
```
ticket-booking/
├── CLAUDE.md
├── README.md            # setup instructions (deliverable)
├── docker-compose.yml   # web + api + db
├── .env.example
├── docs/design.md
├── api/                 # FastAPI backend
└── web/                 # Next.js frontend
```

## Stack
- **Backend:** Python 3.12, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2.0 (sync, psycopg 3), Alembic, PostgreSQL 16, pytest, ruff. Package manager: `uv`.
- **Frontend:** Next.js 15 (App Router), TypeScript strict, Tailwind CSS, TanStack Query, `html5-qrcode`. Package manager: `pnpm`. Tests: Vitest + React Testing Library.
- **Auth:** JWT (HS256) with role in claims, bcrypt password hashing.
- **Payments:** Razorpay test mode, wrapped in `api/app/integrations/razorpay_client.py`.

## Backend rules
- Layers: `routers` → `services` → `repositories`. Routers only parse input and call services. Services own transactions and business rules. Repositories hold queries.
- Money is always integer **paise**. Times are UTC (`timestamptz`), shown in IST on the frontend.
- Errors: raise `AppError(code, message, status_code, details)`; the API returns `{"code", "message", "details"}`. Error codes live in one module.
- Every protected endpoint uses a `require_role(...)` dependency. Ownership checks (organizer owns the event, etc.) happen in services.
- **Critical logic follows `docs/design.md` exactly:** seat hold (§11.3), payment confirmation (§11.4), check-in (§11.6).
  - Lock rows with `.with_for_update()` ordered by id.
  - Never call external APIs (Razorpay, email) while holding row locks.
  - Do not change this logic without updating `api/tests/test_concurrency.py`.
- Every model change gets an Alembic migration (autogenerate, then review it).
- Config and secrets come from environment variables via pydantic-settings. Never hardcode secrets.
- Tests run against real PostgreSQL, never SQLite (row locks must be real).

## Frontend rules
- All API calls go through `web/src/lib/api.ts`; shared types live in `web/src/types/`.
- The "selected" seat state is client-only; seats are held only when the user clicks Proceed.
- Route guards in `middleware.ts` are for UX only; the API is the security boundary.
- Seat map, checkout and scanner pages must work on a 360 px wide phone screen.
- Show the API's error `message` to the user; never a raw stack trace.

## Commands
- Start everything: `docker compose up --build`
- Backend tests: `docker compose exec api pytest`
- Coverage: `docker compose exec api pytest --cov=app`
- New migration: `docker compose exec api alembic revision --autogenerate -m "<message>"`
- Apply migrations: `docker compose exec api alembic upgrade head`
- Seed demo data: `docker compose exec api python -m app.seed`
- Lint: `docker compose exec api ruff check .` and `pnpm --dir web lint`
- Frontend tests: `pnpm --dir web test`

## Working style
- One module per task. Write tests in the same task. Run the tests before saying a task is done.
- Keep commits small, with clear messages.
- Ask before adding a dependency that is not listed above.
- Update `README.md` when setup steps or commands change.
