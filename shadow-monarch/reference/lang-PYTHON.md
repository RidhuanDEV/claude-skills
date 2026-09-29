# Python / FastAPI / Django / Flask

Target the project's Python version (check `pyproject.toml`); prefer a currently supported version for new work. Follow PEP 8 via the project's formatter.

## 1. Project layout and packaging

```text
pyproject.toml          single source for deps and tool config (uv, Poetry, or pip-tools; use what the repo uses)
src/<package>/          src layout avoids accidental imports from the working directory
  api/ (routers)  services/  repositories/  models/  schemas/  core/ (config, logging, security)
tests/
```
- Pin dependencies with a lockfile; separate dev dependencies. Use virtual environments; never install into system Python.
- No mutable module-level state shared across requests; no work at import time beyond definitions.

## 2. Typing and data

- Type hints everywhere public; run mypy or pyright in CI. Use `X | None`, `Literal`, `TypedDict`, `Protocol`, dataclasses.
- Pydantic v2 models for request/response schemas and settings (`pydantic-settings` validates env at startup).
- Money: `decimal.Decimal` (construct from strings), never float. Time: timezone-aware `datetime.now(timezone.utc)`; `datetime.utcnow()` is deprecated and naive.
- Beware mutable default arguments (`def f(items=[])`) — use `None` and create inside.

## 3. Errors

- Catch specific exceptions; never bare `except:` or `except Exception: pass`. Re-raise with context: `raise OrderError("…") from err`.
- Domain exceptions mapped to HTTP in one place (FastAPI exception handlers, Django middleware/DRF exception handler).
- Use context managers (`with`, `async with`) for files, locks, DB sessions, HTTP clients — guaranteed cleanup.
- Logging: `logging.getLogger(__name__)`, `logger.exception(...)` inside `except` to keep the traceback, lazy formatting
  (`logger.info("order %s", order_id)`), structured JSON in production (structlog or a JSON formatter). Never `print` in services.

## 4. Async

- Do not call blocking I/O (requests, sync DB drivers, `time.sleep`, heavy CPU) inside `async def` — it blocks the event loop.
  Use async clients (httpx.AsyncClient, asyncpg/SQLAlchemy async) or `await asyncio.to_thread(...)`; CPU-bound → process pool or a job queue.
- In FastAPI, plain `def` endpoints run in a threadpool (fine for sync code); `async def` endpoints must be non-blocking.
- Timeouts: `asyncio.timeout()` (3.11+) / `asyncio.wait_for`; httpx `timeout=` always set (httpx has a default, requests has **none** — always pass `timeout=`).
- Structured concurrency with `asyncio.TaskGroup` (3.11+); keep references to created tasks; bound concurrency with `asyncio.Semaphore`.
- Reuse HTTP clients (one `AsyncClient` per app lifespan), not a new client per request.

## 5. FastAPI

- Routers per feature; `Depends` for DB sessions, auth and services; lifespan handler for startup/shutdown resources.
- Separate Pydantic schemas for create/update/read — never expose ORM models directly; `response_model` to control output fields.
- Auth via dependencies (`OAuth2PasswordBearer`/custom) plus object-level checks in services.
- Validation errors return 422 by default — keep the project's error contract consistent via exception handlers.
- Background work: `BackgroundTasks` only for small non-critical tasks; durable work → Celery/RQ/Dramatiq/Arq.

## 6. Django / DRF

- Fat models or service layer — follow the project; keep views thin. Settings split per environment, secrets from env; `DEBUG=False`,
  `ALLOWED_HOSTS`, `SECURE_*`, `CSRF_TRUSTED_ORIGINS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` in production; run `manage.py check --deploy`.
- ORM: `select_related` (FK/one-to-one) and `prefetch_related` (many) against N+1; `only()`/`values()` for narrow reads;
  `F()` expressions and `select_for_update()` inside `transaction.atomic()` for races; `bulk_create`/`update` for batches;
  paginate every list. Use `django-debug-toolbar`/query logging to count queries.
- Raw SQL: `cursor.execute(sql, params)` / `raw(sql, params)` — never f-strings. Avoid `extra()`.
- DRF: serializers with explicit `fields` (never `__all__` for writable sensitive models), permission classes plus object permissions, throttling.
- Migrations: review `sqlmigrate`, separate data migrations, avoid long locks on big tables.

## 7. SQLAlchemy (2.x style)

`select()` API, session per request/unit of work, `with Session.begin():` for transactions, explicit loading strategy
(`selectinload`, `joinedload`) to avoid lazy-load N+1 (and lazy loads fail under async), Alembic for migrations (review autogenerate output).

## 8. Security

- No `pickle`/`yaml.load` (use `yaml.safe_load`) on untrusted data; no `eval`/`exec`; `subprocess.run([...], shell=False)` with arg lists.
- Paths: `Path(base, name).resolve()` then check `is_relative_to(base)`.
- Passwords: `argon2-cffi`/`passlib`/Django's hashers; tokens with `secrets` module; compare with `hmac.compare_digest`.
- Jinja2/Django templates autoescape — do not mark user content `|safe`/`Markup` without sanitizing (bleach/nh3).
- Scan dependencies (`pip-audit`), static analysis (`bandit`, Ruff security rules).

## 9. Testing

pytest with fixtures (DB per test via transactions or Testcontainers), `pytest-asyncio`/`anyio` for async, parametrize for tables,
`freezegun`/`time-machine` for time, `respx`/`responses` for HTTP mocks, hypothesis for property-based tests,
FastAPI `TestClient`/`httpx.AsyncClient(transport=ASGITransport(app))`, Django `TestCase`/pytest-django.

## 10. Tooling

Ruff (lint + format) or Black + isort + flake8 · mypy/pyright · pre-commit · uv/Poetry lockfiles · slim Docker images with a non-root user,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`; Gunicorn + Uvicorn workers (or Uvicorn with `--workers`) in production, not the dev server.

## 11. Common mistakes to catch

Bare `except` · mutable defaults · naive datetimes · float money · blocking calls in `async def` · `requests` without timeout ·
new HTTP client per request · N+1 via lazy relationships · f-string SQL · `DEBUG=True` in prod · secrets in `settings.py` ·
exposing ORM models directly · `print` debugging left behind · `pickle` on untrusted input · global state mutated per request ·
circular imports hidden by function-level imports.
