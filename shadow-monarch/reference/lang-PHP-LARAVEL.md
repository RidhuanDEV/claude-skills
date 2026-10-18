# PHP / Laravel

Target the project's PHP and Laravel versions (check `composer.json`); use supported versions for new work. Follow PSR-12 via the project's formatter (Laravel Pint).

## 1. Project structure

- Controllers thin: validate via **Form Requests**, authorize via **Policies/Gates**, delegate to **Actions/Services**, return **API Resources**.
- Business logic in Action/Service classes or domain models — not in controllers, routes, Blade views or model observers with hidden side effects.
- `declare(strict_types=1);` in new files; typed properties, parameter and return types; readonly properties / enums (PHP 8.1+) for value objects and statuses.
- Config via `config/*.php` reading `env()` — call `env()` **only** inside config files (it returns null once config is cached).
- Route model binding with scoping (`->scopeBindings()`) for nested resources.

## 2. Validation and mass assignment

- Every write goes through a Form Request (`rules()`, `authorize()`); use `$request->validated()` / `safe()` — never `$request->all()` into `create()`/`update()`.
- Define `$fillable` (allowlist) on models; never `$guarded = []` on models that receive user input.
- Enable `Model::shouldBeStrict()` in non-production (prevents lazy loading, silently discarded attributes, missing attributes).

## 3. Eloquent and database

- **N+1**: eager load with `with()` / `load()`; `Model::preventLazyLoading()` in dev; use Laravel Debugbar/Telescope to count queries.
- Select needed columns; `paginate()` / `cursorPaginate()` for lists; `chunkById()`/`lazyById()` for batch processing — never `all()` on large tables.
- Transactions: `DB::transaction(fn () => ..., attempts: 3)`; `lockForUpdate()` for check-then-act races; atomic `increment()`/`decrement()`.
- Raw SQL: `DB::select('… where id = ?', [$id])` / `whereRaw('…', [$bindings])` — never interpolate input. Column names from input (sorting) via allowlist.
- Unique constraints in migrations, not only `unique` validation rules (validation is racy).
- Migrations: never edit applied migrations; add new ones; consider locks on large tables; `down()` implemented where feasible.
- Soft deletes (`SoftDeletes`) only with a real need; unique indexes must account for them.
- Money: integer minor units or `brick/money`; never float. Dates: Carbon immutable (`CarbonImmutable`), store UTC, set `APP_TIMEZONE` deliberately.

## 4. Errors and responses

- Custom exceptions with `render()`/`report()` or the exception handler (`bootstrap/app.php` in Laravel 11+) mapping to a consistent JSON error contract.
- `APP_DEBUG=false` in production — debug pages leak env values and code.
- `abort_if` / `abort_unless` for guard clauses; `findOrFail` → 404 automatically.
- Logging via `Log::` channels with context arrays; JSON formatter in production; never log passwords/tokens.

## 5. Queues, jobs, scheduling

- Slow or retryable work (mail, notifications, reports, webhooks) goes to queued jobs (`ShouldQueue`) on Redis/SQS/database with Horizon for monitoring.
- Jobs define `$tries`, `$backoff`, `$timeout`, `failed()` handling; make them idempotent (`ShouldBeUnique`, `WithoutOverlapping` middleware, DB unique keys).
- Dispatch after commit (`->afterCommit()` or `after_commit` config) so jobs never see uncommitted data.
- Scheduler: `withoutOverlapping()`, `onOneServer()` for multi-server deployments.

## 6. HTTP client

`Http::timeout(5)->connectTimeout(2)->retry(3, 200, throw: false)` — always set timeouts; `Http::fake()` in tests.
Verify webhook signatures; process heavy webhooks in jobs.

## 7. Security

- Auth: Sanctum (SPA cookie or API tokens) or Passport (OAuth2); Fortify/Breeze/Jetstream scaffolding. Passwords via `Hash::make` (bcrypt/argon2).
- Authorization: Policies on every resource action (`$this->authorize('update', $post)` or `can` middleware); UI hiding is not authorization.
- CSRF middleware stays on for web routes; exclude only verified webhook routes.
- Blade `{{ }}` escapes; `{!! !!}` only for sanitized HTML (HTMLPurifier/`mews/purifier`).
- File uploads: `file|mimes:jpg,png,pdf|max:2048` plus content checks for images; store with `store()` (generated names) on a private disk; serve via signed/temporary URLs.
- Rate limiting: `RateLimiter::for(...)` + `throttle` middleware on login, OTP, API.
- Never `unserialize()` untrusted data; avoid `eval`, `exec`, `shell_exec`; use `Process` facade with argument arrays.
- `APP_KEY` secret and stable; `.env` never committed; `config:cache`, `route:cache`, `view:cache` in deploys.
- Encrypted casts (`'encrypted'`) for sensitive columns where appropriate.

## 8. Performance

OPcache enabled in production; Octane only when the app is stateless-safe (no static/singleton request state leaks); cache with tags/TTL and explicit
invalidation; queue heavy work; eager load; index columns used in `where`/`orderBy`.

## 9. Testing

Pest or PHPUnit; `RefreshDatabase` (or `LazilyRefreshDatabase`) with a real DB matching production (MySQL/PostgreSQL, not SQLite if behavior differs);
model factories; HTTP tests (`$this->postJson(...)->assertStatus(201)->assertJsonPath(...)`); fakes: `Queue::fake()`, `Mail::fake()`, `Http::fake()`,
`Storage::fake()`, `Event::fake()`; `actingAs($user)` plus authorization-failure tests; `travelTo()` for time.

## 10. Tooling

Laravel Pint · Larastan/PHPStan (level as high as practical) · Rector for upgrades · `composer audit` · Composer lockfile committed ·
PHP-FPM + Nginx or FrankenPHP/Octane containers, non-root, `composer install --no-dev --optimize-autoloader` in production.

## 11. Common mistakes to catch

`$request->all()` into `create()` · `$guarded = []` · N+1 in Blade/Resources · `env()` outside config · `APP_DEBUG=true` in prod ·
jobs dispatched before commit · non-idempotent jobs with retries · no HTTP client timeout · `{!! !!}` with user input ·
missing policies (IDOR) · uploads stored under `public/` with original names · `all()` on large tables · float money ·
logic in model events that surprises readers · business logic in routes/closures · SQLite tests hiding MySQL/PostgreSQL behavior.
