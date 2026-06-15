# Aadarsh Eye Boutique Care Centre CRM

Production-grade CRM and operations dashboard for an optical business.

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
- Frontend: React, TypeScript, Vite, Tailwind, TanStack Query, React Hook Form, Zod, Recharts
- Database: PostgreSQL (production) or SQLite (local fallback)

## Local Run (No Docker, SQLite)
Use these exact commands.

### 1. Backend setup
```bash
cd /Users/anujmishra/Desktop/Eye_boutique/backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Backend environment
Create `backend/.env` with:
```env
PROJECT_NAME=Aadarsh Eye Boutique Care Centre CRM
ENVIRONMENT=development
API_V1_PREFIX=/api/v1
SECRET_KEY=change-this-to-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=36500
ADMIN_MASTER_PASSWORD=adarsh@1234
DATABASE_URL=sqlite:///./eye_boutique.db
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
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
cd /Users/anujmishra/Desktop/Eye_boutique/backend
source .venv/bin/activate
python -m app.scripts.init_dev_db
```

### 4. Run backend API
```bash
cd /Users/anujmishra/Desktop/Eye_boutique/backend
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
cd /Users/anujmishra/Desktop/Eye_boutique/backend
source .venv/bin/activate
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### 7. Frontend setup + run
```bash
cd /Users/anujmishra/Desktop/Eye_boutique/frontend
npm install
printf "VITE_API_BASE_URL=http://localhost:8000/api/v1\nVITE_APP_NAME=Aadarsh Eye Boutique Care Centre\n" > .env
npm run dev -- --host 0.0.0.0 --port 5173
```

## Seed Login
- Admin: `admin@aadarsh-eye.com` / `Admin@12345`
- Staff: `staff@aadarsh-eye.com` / `Staff@12345`

## Useful URLs
- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/healthz`

## Notes
- For deployment, switch to PostgreSQL and set `DATABASE_URL` (or `POSTGRES_*`) accordingly.
- Campaign scheduling requires Redis + Celery worker running.
- WhatsApp sending works only when Meta Cloud credentials are configured in `.env`.

## Manual QA Smoke
Run this after backend setup to validate core workflows:

In-process mode (no running server required):
```bash
cd /Users/anujmishra/Desktop/Eye_boutique/backend
source .venv/bin/activate
python -m app.scripts.manual_qa_smoke --in-process
```

Live-server mode (when API is running at localhost:8000):
```bash
cd /Users/anujmishra/Desktop/Eye_boutique/backend
source .venv/bin/activate
python -m app.scripts.manual_qa_smoke --base-url http://localhost:8000/api/v1
```

Strict external checks (fail if WhatsApp/worker infra is unavailable):
```bash
python -m app.scripts.manual_qa_smoke --base-url http://localhost:8000/api/v1 --strict-external
```
