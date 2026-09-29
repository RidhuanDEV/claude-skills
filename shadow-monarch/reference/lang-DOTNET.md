# .NET / C# / ASP.NET Core / EF Core

Target the project's existing .NET version; prefer current LTS for new work. Follow .NET naming guidelines and the repo's `.editorconfig`.

## 1. Project layout

- Small/medium services: one Web project organized by feature (`Features/Orders/{CreateOrder.cs, OrderEndpoints.cs, OrderDto.cs}`),
  plus a test project. Vertical slices are fine.
- Larger: `Api` (endpoints, DI, middleware) → `Application` (use cases, validators, interfaces) → `Domain` (entities, value objects, rules)
  → `Infrastructure` (EF Core, HTTP clients, messaging). Domain references nothing else. Do not create layers the app does not need.
- Minimal APIs or controllers — follow what the project uses. Group endpoints with `MapGroup` and extension methods.
- Enable `<Nullable>enable</Nullable>` and `<TreatWarningsAsErrors>` (at least for nullable warnings). Use `record` for DTOs/value objects.

## 2. Dependency injection lifetimes

- **Singleton**: stateless or thread-safe services, `HttpClient` handlers via factory, caches.
- **Scoped**: per request — `DbContext`, unit-of-work, request context.
- **Transient**: lightweight stateless services.
- **Captive dependency bug**: never inject Scoped (e.g. `DbContext`) into a Singleton; in background services create a scope with
  `IServiceScopeFactory.CreateAsyncScope()`. Enable `ValidateScopes`/`ValidateOnBuild` in development.
- Use the Options pattern (`IOptions<T>` / `IOptionsMonitor<T>`) with `.ValidateDataAnnotations().ValidateOnStart()` for config.

## 3. Async/await

- Async all the way; never `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` on request paths (thread-pool starvation, deadlocks).
- Accept and pass `CancellationToken` through endpoints → services → EF Core → `HttpClient`.
- No `async void` except event handlers. Do not fire-and-forget `Task`s for important work — use a queue/`BackgroundService`/`Channel<T>`.
- `ConfigureAwait(false)` matters in libraries, not in ASP.NET Core app code.
- `ValueTask` only when measured to matter; never await a `ValueTask` twice.

## 4. Errors and API responses

- Use `ProblemDetails` (RFC 9457): `builder.Services.AddProblemDetails()` + `app.UseExceptionHandler()` and an `IExceptionHandler`
  that maps domain exceptions (NotFound, Conflict, Validation, Forbidden) to status codes. No stack traces outside Development.
- Exceptions for exceptional cases; for expected business outcomes a `Result<T>` pattern is fine if the codebase uses it — be consistent.
- Validation: FluentValidation or DataAnnotations/endpoint filters; validate every DTO server-side. Avoid over-posting: bind to DTOs, never entities.
- Never `catch (Exception) { }`. Catch specific exceptions; `throw;` to rethrow (not `throw ex;`, which loses the stack).

## 5. EF Core

- `DbContext` is scoped and **not thread-safe** — never share across parallel tasks.
- Read queries: `AsNoTracking()`, project with `Select` to DTOs, avoid loading whole graphs.
- N+1: avoid lazy loading proxies in APIs; use `Include`/`ThenInclude` deliberately or projections; `AsSplitQuery()` for big cartesian includes.
- Always paginate (`Skip/Take` with stable `OrderBy`, or keyset). Watch client-side evaluation and `ToList()` before filtering.
- Raw SQL: `FromSql($"… {param}")` / `ExecuteSql` interpolation is parameterized; **never** `FromSqlRaw` with concatenated input.
- Concurrency: `[Timestamp]`/`rowversion` or `IsConcurrencyToken()`; handle `DbUpdateConcurrencyException`.
- Bulk changes: `ExecuteUpdateAsync`/`ExecuteDeleteAsync` (EF Core 7+).
- Transactions: one `SaveChangesAsync` is already atomic; use `BeginTransactionAsync` for multi-step, with execution strategy when retries are enabled.
- Migrations: review generated SQL (`dotnet ef migrations script`), do not auto-migrate on startup in multi-instance production; apply via pipeline/bundles.
- Use `decimal` (with explicit precision `HasPrecision(18,2)`) for money; `DateTimeOffset` or UTC `DateTime` for instants.

## 6. HTTP clients and resilience

- `IHttpClientFactory` (named/typed clients); never `new HttpClient()` per request (socket exhaustion) nor a static one ignoring DNS changes.
- Set timeouts; add resilience with `Microsoft.Extensions.Http.Resilience` (Polly v8: retry with jitter, circuit breaker, timeout).

## 7. Security

- Authentication/authorization middleware order: `UseRouting` → `UseCors` → `UseAuthentication` → `UseAuthorization`.
- Policy-based authorization (`AddAuthorization(o => o.AddPolicy(...))`), resource-based checks with `IAuthorizationService` for object-level access.
- JWT bearer: validate issuer, audience, lifetime, signing key; short-lived tokens. Cookies: `HttpOnly`, `Secure`, `SameSite`.
- ASP.NET Core Identity uses PBKDF2 by default; do not roll your own hashing. Data Protection keys persisted and shared across instances.
- Antiforgery for cookie-authenticated form/state-changing endpoints. Rate limiting via `AddRateLimiter`.
- Secrets: User Secrets in dev, Key Vault / secret manager in prod; never in `appsettings.json` committed.
- Never use `BinaryFormatter`.

## 8. Logging and observability

`ILogger<T>` with **message templates** (`logger.LogInformation("Order {OrderId} created", id)`), not string interpolation.
Structured sink (Serilog or OpenTelemetry exporter). Health checks: `AddHealthChecks()` with separate liveness/readiness endpoints.
OpenTelemetry for traces/metrics.

## 9. Background work

`BackgroundService` with `stoppingToken`, scoped services via scope factory, bounded `Channel<T>` for in-process queues,
Hangfire/Quartz/MassTransit for durable jobs. Handle exceptions — an unhandled exception stops the host by default (.NET 6+).

## 10. Testing

xUnit + FluentAssertions/Shouldly; `WebApplicationFactory<Program>` for integration tests; Testcontainers for SQL Server/PostgreSQL
(not EF InMemory for relational behavior); NSubstitute/Moq for boundaries; Respawn to reset DB state.

## 11. Tooling

`dotnet format` · Roslyn analyzers (`<AnalysisLevel>latest</AnalysisLevel>`, `EnableNETAnalyzers`) · `dotnet list package --vulnerable` ·
Central Package Management (`Directory.Packages.props`) for multi-project solutions · `dotnet publish` into `mcr.microsoft.com/dotnet/aspnet` runtime image, non-root.

## 12. Common mistakes to catch

Sync-over-async · captive `DbContext` in singletons · `DbContext` shared across threads · `new HttpClient()` per call ·
entities returned directly from APIs · missing `CancellationToken` · `FromSqlRaw` concatenation · N+1 via lazy loading ·
unpaginated `ToListAsync()` · `throw ex;` · string-interpolated log messages · `DateTime.Now` instead of UTC/`TimeProvider` ·
`float`/`double` for money · auto-migrate on startup in scaled deployments · secrets in `appsettings.json`.
