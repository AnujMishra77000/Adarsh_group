# Adarsh Optical Group CRM

Production-grade CRM, backend API, and public website for an optical business.

## App Layout
- `backend/` - FastAPI API, database models, Alembic migrations, background workers.
- `crm/` - independent React/Vite CRM app for shop entry, login, dashboard, customers, billing, prescriptions, chat, campaigns, analytics, and staff management.
- `website/` - independent React/Vite public website for Adarsh Optical Group.
- `frontend/` - legacy combined frontend retained temporarily during the split. Use `crm/` and `website/` for new development.

## Completed Modules
- JWT auth with refresh tokens (`admin`, `staff` roles)
- Dashboard with live KPIs and revenue trend chart
- Customer CRUD + history (prescriptions + bills)
- Prescription CRUD + PDF generation + send-to-vendor (WhatsApp)
- Vendor CRUD with active/inactive control
- Billing CRUD with discount/final/balance calculations
- Invoice PDF generation + send-to-customer (WhatsApp)
- Campaign CRUD + scheduling + per-recipient campaign logs
- Revenue analytics (today / last 7 days / last 30 days)
- Audit logging for critical operations
- WhatsApp logging for all message/document events

## Tech Stack
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic, Celery, Redis
- CRM: React, TypeScript, Vite, Tailwind, TanStack Query, React Hook Form, Zod, Recharts
- Website: React, TypeScript, Vite, Tailwind
- Database: PostgreSQL (production) or SQLite (local fallback)

## Shop Registry
The CRM uses these canonical shop codes:

- `adarsh-optical-centre` - Adarsh Optical Centre
- `adarsh-optometric-clinic` - Adarsh Optometric Clinic, Khadakpada, Kalyan West
- `adarsh-opticals-muxar` - Adarsh Opticals, near Muxar Hospital
- `adarsh-eye-boutique` - Adarsh Eye Boutique

Legacy aliases still resolve for compatibility:

- `adarsh-optical-center` -> `adarsh-optical-centre`
- `adarsh-optometric-center` -> `adarsh-optometric-clinic`
- `aadarsh-eye-boutique-center` -> `adarsh-eye-boutique`

If an existing `SHOP_DATABASES` entry still uses a legacy key, the backend keeps routing that shop to the legacy database key so existing `shop_key` rows continue to work. Migration path: create backups, migrate DB mappings to canonical keys, backfill stored `shop_key` values to canonical codes, then remove the legacy mappings after verification.

Shop mobile numbers are only identifiers, not authentication secrets. Configure mobile/identifier lookup on the backend with `SHOP_IDENTIFIER_MAPPINGS`, for example `{"9876543210":"adarsh-eye-boutique"}`. Keep real mobile mappings in uncommitted local/deployment `.env` files only. The CRM app calls `POST /api/v1/public/shops/resolve`, receives only safe shop metadata, stores the selected shop in `sessionStorage`, and still requires admin/staff login for CRM access.

## Version Control Safety
Never commit real `.env` files, credentials, database files, customer PDFs, uploads, or generated runtime storage. Only `.env.example` templates should be committed. Local SQLite databases, invoice PDFs, prescription PDFs, private chat files, logs, and temp files are ignored and should be regenerated or backed up outside Git.

## Local Run (No Docker, SQLite)
Use these exact commands.

### 1. Backend setup
```bash
cd /Users/anujmishra/Developer/Eye_boutique/backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Backend environment
Create `backend/.env` with:
```env
PROJECT_NAME=Adarsh Optical Group CRM
ENVIRONMENT=development
API_V1_PREFIX=/api/v1
SECRET_KEY=change-this-to-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14
ALLOW_LONG_REFRESH_TOKENS_IN_PRODUCTION=false
ALLOW_ADMIN_REGISTRATION=false
AUTH_LOGIN_RATE_LIMIT_ATTEMPTS=10
AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
AUTH_LOGIN_LOCKOUT_FAILED_ATTEMPTS=5
AUTH_LOGIN_LOCKOUT_SECONDS=300
ADMIN_MASTER_PASSWORD=change-this-admin-master-password
SHOP_DATABASES={"adarsh-optical-centre":"sqlite:///./adarsh_optical_centre.db","adarsh-optometric-clinic":"sqlite:///./adarsh_optometric_clinic.db","adarsh-opticals-muxar":"sqlite:///./adarsh_opticals_muxar.db","adarsh-eye-boutique":"sqlite:///./adarsh_eye_boutique.db"}
SHOP_IDENTIFIER_MAPPINGS={}
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:5174","http://127.0.0.1:5174"]
BACKEND_PUBLIC_URL=http://localhost:8000
MEDIA_ROOT=storage
MEDIA_URL_PREFIX=/media
WHATSAPP_API_BASE_URL=https://graph.facebook.com
WHATSAPP_API_VERSION=v20.0
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_DEFAULT_COUNTRY_CODE=91
WHATSAPP_REQUEST_TIMEOUT_SECONDS=25
WHATSAPP_RETRY_ATTEMPTS=3
```

### 3. Initialize database + seed users
```bash
cd /Users/anujmishra/Developer/Eye_boutique/backend
source .venv/bin/activate
python -m app.scripts.init_dev_db
```

### 4. Run backend API
```bash
cd /Users/anujmishra/Developer/Eye_boutique/backend
source .venv/bin/activate
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

### 5. Start Redis (required for campaigns/worker)
If Redis is not running:
```bash
brew install redis
brew services start redis
```

### 6. Run Celery worker (for scheduled campaigns)
Open a new terminal:
```bash
cd /Users/anujmishra/Developer/Eye_boutique/backend
source .venv/bin/activate
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### 7. CRM setup + run
```bash
cd /Users/anujmishra/Developer/Eye_boutique/crm
npm install
printf "VITE_API_BASE_URL=http://localhost:8000/api/v1\nVITE_APP_NAME=Adarsh Optical Group CRM\n" > .env
npm run dev -- --host 127.0.0.1 --port 5173
```

### 8. Website setup + run
```bash
cd /Users/anujmishra/Developer/Eye_boutique/website
npm install
printf "VITE_CRM_URL=http://127.0.0.1:5173/crm\n" > .env
npm run dev -- --host 127.0.0.1 --port 5174
```

## Seed Login
- Admin: `admin+<shop-code>@adarsh-optical.local` / `Admin@12345`
- Staff: `staff+<shop-code>@adarsh-optical.local` / `Staff@12345`
- Example: `admin+adarsh-eye-boutique@adarsh-optical.local`

## Useful URLs
- CRM: `http://localhost:5173/crm`
- Public website: `http://localhost:5174`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/healthz`

## Local Checks
Run these before production-readiness changes and before opening a PR.

Backend:
```bash
cd /Users/anujmishra/Developer/Eye_boutique/backend
source venv/bin/activate
python -m compileall app
ruff check app tests
pytest --cov=app --cov-report=term-missing
```

CRM:
```bash
cd /Users/anujmishra/Developer/Eye_boutique/crm
npm ci
npm run typecheck
npm run lint
npm run build
npm test
```

Website:
```bash
cd /Users/anujmishra/Developer/Eye_boutique/website
npm ci
npm run typecheck
npm run lint
npm run build
npm test
```

CI should run backend compile, ruff, pytest with coverage, then CRM install/typecheck/lint/build/Vitest and website install/typecheck/lint/build/Vitest.

## Notes
- For deployment, switch each `SHOP_DATABASES` entry to PostgreSQL and keep one database per center.
- Campaign scheduling requires Redis + Celery worker running.
- WhatsApp sending works only when Meta Cloud credentials are configured in `.env`.

## Production Environment Guidance
When `ENVIRONMENT=production`, the backend validates configuration during settings startup and refuses unsafe values before the app starts.

Required production rules:
- `SECRET_KEY` must be a unique high-entropy value of at least 32 characters. Do not use example placeholders.
- `ADMIN_MASTER_PASSWORD` must be changed from the default and be at least 12 characters.
- `ACCESS_TOKEN_EXPIRE_MINUTES` must be greater than `0`.
- `REFRESH_TOKEN_EXPIRE_DAYS` must be `30` or less. Longer refresh tokens require the explicit documented override `ALLOW_LONG_REFRESH_TOKENS_IN_PRODUCTION=true`.
- `BACKEND_CORS_ORIGINS` must be explicitly set to trusted frontend origins and must not include `*`.
- `/auth/admin/register` is disabled by default in production. Enable it only for controlled setup windows with `ALLOW_ADMIN_REGISTRATION=true`, then turn it off again.
- Login throttling is keyed by IP, shop, and normalized email/login id. Tune `AUTH_LOGIN_RATE_LIMIT_*` and `AUTH_LOGIN_LOCKOUT_*` for your deployment.
- Generated invoice and prescription PDFs are private customer documents. In production the backend does not mount `MEDIA_ROOT` as public static files; use authenticated downloads at `/api/v1/bills/{bill_id}/pdf/download` and `/api/v1/prescriptions/{prescription_id}/pdf/download`. Email and WhatsApp delivery use the server-side private file path.

Recommended production token baseline:
```env
ENVIRONMENT=production
SECRET_KEY=<generate-a-unique-64-plus-character-secret>
ADMIN_MASTER_PASSWORD=<generate-a-unique-admin-master-password>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14
ALLOW_LONG_REFRESH_TOKENS_IN_PRODUCTION=false
ALLOW_ADMIN_REGISTRATION=false
AUTH_LOGIN_RATE_LIMIT_ATTEMPTS=10
AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
AUTH_LOGIN_LOCKOUT_FAILED_ATTEMPTS=5
AUTH_LOGIN_LOCKOUT_SECONDS=300
BACKEND_CORS_ORIGINS=["https://crm.example.com"]
```

## Manual QA Smoke
Run this after backend setup to validate core workflows:

In-process mode (no running server required):
```bash
cd /Users/anujmishra/Developer/Eye_boutique/backend
source .venv/bin/activate
python -m app.scripts.manual_qa_smoke --in-process
```

Live-server mode (when API is running at localhost:8000):
```bash
cd /Users/anujmishra/Developer/Eye_boutique/backend
source .venv/bin/activate
python -m app.scripts.manual_qa_smoke --base-url http://localhost:8000/api/v1
```

Strict external checks (fail if WhatsApp/worker infra is unavailable):
```bash
python -m app.scripts.manual_qa_smoke --base-url http://localhost:8000/api/v1 --strict-external
```
