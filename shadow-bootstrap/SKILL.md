---
name: shadow-bootstrap
description: Initialize and scaffold a new production-grade project from zero after architecture decisions are locked. Sets up repository structure, strict TypeScript/linting, runtime env validation, DB/ORM, testing framework, Docker dev environment, Git hooks, CI, and developer README. Trigger with /shadow-bootstrap.
---

# Shadow Bootstrap (`/shadow-bootstrap`) — Project Foundation & Zero-to-Runnable Scaffold

Use this skill **after** architectural decisions (`/shadow-architect`) are confirmed to initialize a clean, reproducible project foundation from scratch. Never pick a tech stack arbitrarily — follow the approved ADR or the **Monarch**'s stack instruction.

---

## 1. The 8 Mandatory Bootstrap Pillars

When scaffolding a new repository (Monorepo or Single-Service), `/shadow-bootstrap` MUST set up and verify all 8 pillars:

### 1. Repository & Directory Structure
- Clean separation of concerns:
  - **Backend**: `src/config/`, `src/modules/<domain>/{controller,service,repository,dto,entities}`, `src/common/{middleware,errors,guards,logger}`, `tests/`.
  - **Frontend**: `src/app/` (or `pages/`), `src/components/ui/`, `src/features/<domain>/`, `src/lib/`, `src/types/`.
  - **Documentation & Specs**: `docs/{adr,api,db,uat,handover}/`, `openapi.yaml`, `postman_collection.json`.
- Standard `.gitignore`, `.gitattributes` (enforcing LF line endings for scripts), and `.editorconfig`.

### 2. Strict Compiler, Linter & Formatter Configuration
- **TypeScript**: `tsconfig.json` with `"strict": true`, `"noImplicitAny": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true`, and clean path aliases (`@/*`).
- **Python**: `pyproject.toml` with `ruff` + `mypy --strict` / `pyright`.
- **Go**: `.golangci.yml` with `govet`, `errcheck`, `staticcheck`.
- **PHP/Laravel**: `pint.json` + `phpstan.neon` (Larastan level 6+).

### 3. Fail-Fast Startup Environment Validation
- Create `src/config/env.ts` (or `config.py` / `config.go`) that validates all required environment variables at process boot using a schema validator (`zod`, `pydantic-settings`, etc.) and fails fast with a clear human-readable error if any variable is missing or malformed.
- Create a complete, well-commented `.env.example` (never commit real secrets in `.env`).

### 4. Standard Error Envelope, Structured Logger & Health Probes
- Global error handler returning a deterministic JSON error envelope (`statusCode`, `errorCode`, `message`, `details`, `requestId`).
- Correlation `X-Request-Id` middleware + structured JSON logger (`pino` / `structlog` / `zap`).
- Built-in `/healthz` (liveness: process up) and `/readyz` (readiness: DB + Redis ping) endpoints.

### 5. Database, ORM, Migration & Deterministic Seed Setup
- Configure the chosen ORM/query builder (`Prisma`, `Drizzle`, `TypeORM`, `SQLAlchemy`/`Alembic`, `GORM`/`sqlc`, `Eloquent`).
- Create the initial migration and an idempotent `seed` script (`npm run db:seed`) so a fresh developer machine gets working reference data immediately.

### 6. Local Development `docker-compose.dev.yml`
- Provide a one-command local infrastructure file (`docker compose -f docker-compose.dev.yml up -d`) spinning up local PostgreSQL/MySQL, Redis, Mailpit (local SMTP testing UI), and MinIO (if object storage is needed) with healthchecks and named volumes.

### 7. Testing Framework & Initial Smoke Spec
- Wire up the test runner (`Vitest`/`Jest`, `Pytest`, `Go test`, `Pest`) with a passing initial test (`GET /healthz -> 200 OK`) so `npm test` / `pytest` works out of the box from commit #1.

### 8. Developer `README.md` & Fresh-Clone Verification
- Write a crisp `README.md` covering Prerequisites, 5-step Quick Start (`cp .env.example .env`, `docker compose up -d`, `npm install`, `npm run db:migrate && npm run db:seed`, `npm run dev`), and available scripts.
- **Verification Gate**: Execute install, typecheck, lint, build, and the healthcheck test before declaring bootstrap complete.
