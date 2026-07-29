# EmployeeMint — Multi-Tenant HRMS SaaS

A configuration-driven, multi-tenant HRMS platform for companies with 10–5,000 employees.

## Architecture

- **Backend:** FastAPI + PostgreSQL (RLS) + Redis + Celery
- **Frontend:** React 18 + TypeScript + Vite + TanStack Query + Zustand + Tailwind
- **Auth:** JWT (access + refresh) with tenant context in claims
- **Multi-tenancy:** Shared DB/schema with `tenant_id` + PostgreSQL Row-Level Security

See [docs/SPEC.md](docs/SPEC.md) for the full product specification.  
See **[docs/HLD.md](docs/HLD.md)** (High Level Design) and **[docs/LLD.md](docs/LLD.md)** (Low Level Design) for architecture, tech stack, users, and flows with diagrams.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### 1. Clone and configure

```bash
cp .env.example .env
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis minio
```

### 3. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload
```

### 4. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### 5. Full stack via Docker

```bash
docker compose up --build
```

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173
- MinIO console: http://localhost:9001

### Default credentials

| Role | Email | Password |
|------|-------|----------|
| Platform Admin | admin@employeemint.local | changeme |

## Project Structure

```
/backend          FastAPI application
/frontend         React SPA
/docs/SPEC.md     Master specification (contract)
/docs/HLD.md      High Level Design (architecture, users, journeys)
/docs/LLD.md      Low Level Design (APIs, data model, sequences)
/docs/assets/     Architecture and flow diagrams
```

## Development

- Read `/docs/SPEC.md` before making changes
- API is versioned at `/api/v1/`
- Run backend tests: `cd backend && pytest`
- Generate OpenAPI client: `cd frontend && npm run generate-api`
