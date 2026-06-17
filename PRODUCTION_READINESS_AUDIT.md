# Production Readiness Audit

Baseline date: 2026-06-15

## Current Stack

- Backend: FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, python-jose JWTs, bcrypt, Redis, Celery, WeasyPrint, structlog.
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Axios, React Hook Form, Zod, Recharts, lucide-react.
- Infrastructure: Docker Compose with PostgreSQL 16, Redis 7, backend, Celery worker, Celery beat, and frontend services.
- Local development: SQLite tenant databases under `backend/`, Python virtualenv under `backend/venv`, frontend dependencies under `frontend/node_modules`.

## Current Auth Flow

- Auth endpoints live under `/api/v1/auth`.
- Admin registration requires a shop context plus `ADMIN_MASTER_PASSWORD`.
- Login accepts `email` or `login_id`, resolves the shop context, verifies the bcrypt password, and returns an access token plus refresh token.
- JWT payloads include `sub`, `role`, `shop_code`, `type`, `iat`, optional `exp`, and `jti`.
- Refresh tokens are hashed with SHA-256 and persisted in `refresh_tokens`; refresh rotates tokens and revokes the old token.
- Protected routes use `OAuth2PasswordBearer`, decode the access token, validate token type, shop context, role context, active user status, and role-based permissions where required.
- Frontend stores shop-scoped access tokens, refresh tokens, active role, and profile data in `localStorage`, and Axios automatically adds `Authorization` and `X-Shop-Key` headers.

## Current Shop/Tenant Flow

- Shops are configured through `SHOP_DATABASES`, mapping shop keys to database URLs.
- Shop context can be resolved from explicit request payload, `X-Shop-Code`/`X-Shop-Key` headers, JWT `shop_code`, or host/subdomain.
- `TenantDBManager` validates the shop key and lazily creates one SQLAlchemy engine/sessionmaker per shop.
- Each protected request opens a DB session for the resolved shop.
- Frontend shop choices are hardcoded in `frontend/src/features/shops/config.ts`, including shop keys, names, phone numbers, and passcodes.
- Global email uniqueness across shops is enforced by checking other tenant databases unless disabled by `AUTH_ENFORCE_GLOBAL_EMAIL_UNIQUENESS`.

## Current Database Strategy

- Alembic migrations exist in `backend/alembic/versions`.
- `backend/app/scripts/migrate_all_shops.py` runs Alembic upgrades for every configured tenant database.
- `backend/app/scripts/init_dev_db.py` creates tables and seeds local dev users for each configured shop.
- `backend/entrypoint.sh` currently runs `alembic upgrade head`, which targets one configured database URL rather than explicitly migrating every tenant database.
- Local `.env` currently uses SQLite tenant DBs; Docker Compose is oriented around PostgreSQL and Redis.
- Media files are stored on local disk under `backend/storage`, and chat private storage defaults to `backend/private_storage/chat`.

## Risky Files Committed In The Repo

- Tracked SQLite database files:
  - `backend/eye_boutique_dev.db`
  - `backend/eye_boutique_shop1.db`
  - `backend/eye_boutique_shop2.db`
  - `backend/eye_boutique_shop3.db`
- Tracked generated PDF artifacts:
  - `backend/storage/invoices/*.pdf`
  - `backend/storage/prescriptions/*.pdf`
- Actual `.env` files are present locally but are not tracked by Git.
- `backend/venv`, `frontend/node_modules`, `frontend/dist`, `__pycache__`, and TypeScript build info files are ignored.

## Current Build And Test Commands

- Backend syntax check:
  - Command: `cd backend && venv/bin/python -m compileall app`
  - Status: Passed.
  - Output summary: Python modules under `app` compiled successfully.
- Frontend dependency verification:
  - Command: `cd frontend && npm ci`
  - Status: Passed.
  - Output summary: 209 packages installed; npm warned that Recharts 2.x is deprecated.
- Frontend production build:
  - Command: `cd frontend && npm run build`
  - Status: Passed.
  - Output summary: `tsc -b && vite build` completed successfully; Vite built production assets into `frontend/dist`.
- Existing script commands:
  - Backend local run: `cd backend && ./run_local.sh`
  - Backend migrate all tenants: `cd backend && venv/bin/python -m app.scripts.migrate_all_shops`
  - Backend seed/init local DBs: `cd backend && venv/bin/python -m app.scripts.init_dev_db`
  - Backend manual smoke: `cd backend && venv/bin/python -m app.scripts.manual_qa_smoke --in-process`
  - Frontend dev: `cd frontend && npm run dev`
  - Frontend typecheck: `cd frontend && npm run typecheck`
  - Frontend preview: `cd frontend && npm run preview`
- No dedicated backend unit test command was found in the current repo.

## Recommended Order Of Changes

1. Repository hygiene: remove committed SQLite databases and generated PDFs from Git history/current tracking, keep local/runtime artifacts ignored, and document safe local seed data.
2. Production configuration validation: fail startup when production secrets, token expiry, CORS origins, tenant DB mappings, Redis settings, or media paths are unsafe.
3. Tenant migration safety: replace single-DB container startup migration with an explicit all-tenant migration path and a clear readiness failure when a tenant schema is missing.
4. Deployment hardening: split dev and production Docker commands, remove `--reload` from production, avoid bind-mounting application source in production, and add health/readiness checks for DB and Redis.
5. Auth/security hardening: add login rate limiting, review token lifetimes, move frontend token storage strategy toward a safer model, and add request IDs/audit visibility.
6. Storage strategy: move generated PDFs and private chat uploads to a production storage backend or mounted persistent volume with backup/retention rules.
7. Observability: add structured request logging, error tracking, metrics, and operational runbooks for migrations, backups, restores, and worker failures.
8. Test coverage: add backend unit/integration tests for auth, tenant routing, migrations, and critical billing/prescription flows; add frontend smoke tests for login, shop selection, and protected routing.
