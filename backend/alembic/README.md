# Alembic Setup Plan (Phase 1)

Current baseline migration:
- `0001_initial_schema.py`

## Usage
1. Ensure `.env` exists at project root with PostgreSQL credentials.
2. Apply baseline schema:
   - `cd backend`
   - `alembic upgrade head`
3. For every schema change:
   - `alembic revision --autogenerate -m "<descriptive_name>"`
   - Review generated migration manually.
   - `alembic upgrade head`

## Rollback
- `alembic downgrade -1`
