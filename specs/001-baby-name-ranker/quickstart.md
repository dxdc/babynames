# Quickstart: Baby Name Discovery & Ranking App

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- uv (Python package manager)
- pnpm (Node package manager)

## Setup

### 1. Database

```bash
createdb babynames
```

### 2. Backend

```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Load name data into PostgreSQL
python -m babynames.db.seed

# Run API server
uvicorn babynames.api.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Frontend runs on `http://localhost:5173`, proxies API calls to `http://localhost:8000`.

### 4. Running Tests

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend unit tests
cd frontend && pnpm test

# E2E tests
cd frontend && pnpm test:e2e
```

### 5. Environment Variables

```bash
# backend/.env
DATABASE_URL=postgresql://localhost/babynames
AUTHENTIK_ISSUER=https://auth.decent.tech/application/o/babynames/
AUTHENTIK_CLIENT_ID=<from Authentik>
AUTHENTIK_JWKS_URL=https://auth.decent.tech/application/o/babynames/jwks/

# frontend/.env
PUBLIC_API_URL=http://localhost:8000
PUBLIC_AUTHENTIK_URL=https://auth.decent.tech
PUBLIC_AUTHENTIK_CLIENT_ID=<from Authentik>
```

### 6. Data Pipeline

The existing data pipeline (`src/babynames.py`) generates CSVs. The new seed script reads these CSVs + enrichment data and loads into PostgreSQL:

```bash
# Regenerate CSVs (if raw data changed)
python src/babynames.py --verbose

# Seed database from CSVs + enrichment
cd backend && python -m babynames.db.seed
```
