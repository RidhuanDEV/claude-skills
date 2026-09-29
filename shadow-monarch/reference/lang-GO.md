# Go

Idiomatic Go is simple, explicit and boring. Follow Effective Go, Go Code Review Comments, and the project's existing style.

## 1. Project layout

```text
cmd/<app>/main.go        wiring only: config, logger, DB, servers, graceful shutdown
internal/<domain>/       handler.go, service.go, repository.go, model.go (package by feature, not by layer)
internal/platform/       db, httpserver, logging, config
pkg/                     only for code intentionally importable by other modules (often unnecessary)
migrations/
```
- Package names: short, lowercase, no `util`/`common`/`helpers`. Avoid stutter (`user.Service`, not `user.UserService`).
- Accept interfaces, return concrete structs. Define interfaces where they are **consumed**, keep them small.
- No global mutable state; pass dependencies via constructors (`NewService(repo Repository, log *slog.Logger)`).
- `init()` only for trivial registration; never for I/O.

## 2. Errors

- Always handle `err`. Never `if err != nil { return nil }` (loses the error) or `_ = f()` on meaningful errors.
- Wrap with context: `fmt.Errorf("load order %d: %w", id, err)`. Check with `errors.Is` / `errors.As`, never string comparison.
- Sentinel errors for expected conditions: `var ErrNotFound = errors.New("order not found")`; typed errors when callers need data.
- Map `sql.ErrNoRows` (or `pgx.ErrNoRows`) to a domain `ErrNotFound` in the repository.
- Handle errors once: either log or return, not both at every layer. Log at the boundary (handler/worker).
- `panic` only for programmer errors/impossible states; recover in HTTP middleware to return 500 and log.
- Check errors from `Close()` on writers (files, `tx.Commit`); `defer rows.Close()` and check `rows.Err()`.

## 3. context.Context

- First parameter `ctx context.Context` on anything doing I/O or long work; never store it in structs; never pass `nil` (use `context.TODO()` temporarily).
- Propagate request contexts into DB calls (`QueryContext`, pgx methods), HTTP clients (`http.NewRequestWithContext`), and goroutines.
- Set deadlines: `ctx, cancel := context.WithTimeout(ctx, 3*time.Second); defer cancel()`.
- Context values only for request-scoped metadata (request ID, auth principal) with unexported key types.

## 4. Concurrency

- Every goroutine has an owner, a way to stop (ctx cancellation or closed channel) and a way to report errors.
  Use `errgroup.WithContext` for fan-out with error propagation; `sync.WaitGroup` when no errors.
- Bound concurrency: worker pools, `errgroup.SetLimit(n)`, buffered semaphores. Never spawn unbounded goroutines per item.
- Channels: the sender closes; never close from the receiver; avoid sending on closed channels; use `select` with `ctx.Done()`.
- Protect shared state with `sync.Mutex`/`RWMutex` or confine it to one goroutine; `sync/atomic` for counters.
  Copying a struct containing a mutex is a bug (`go vet` catches it).
- Loop variable capture: fixed per-iteration since Go 1.22 — but check the module's `go` version in `go.mod`.
- Run tests with `-race` in CI.
- `time.After` in loops leaks timers until they fire; prefer `time.NewTimer` + `Stop` or context deadlines.

## 5. HTTP services

- Standard `net/http` (Go 1.22+ has method + path patterns: `mux.HandleFunc("GET /orders/{id}", h.get)`), or chi/echo/gin if already used.
- **Always configure server timeouts**: `ReadHeaderTimeout`, `ReadTimeout`, `WriteTimeout`, `IdleTimeout`. Never use `http.ListenAndServe` with defaults in production.
- **Never use `http.DefaultClient`** for outbound calls — create a client with `Timeout` and tuned `Transport`; always `defer resp.Body.Close()` and drain/limit reads (`io.LimitReader`).
- Limit request bodies: `http.MaxBytesReader`. Decode JSON with `dec.DisallowUnknownFields()` for strict DTOs.
- Graceful shutdown: `signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)` → `srv.Shutdown(ctx)` with a deadline → close DB/queues.
- Middleware: request ID, structured logging, recovery, auth, CORS, rate limiting.

## 6. Data access

- `database/sql` + `pgx` (PostgreSQL) or `sqlx`; `sqlc` for type-safe generated queries; GORM only if the project already uses it (watch hidden N+1 and zero-value update pitfalls).
- Always placeholders (`$1` / `?`); never `fmt.Sprintf` SQL with user input.
- Configure pool: `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`.
- Transactions: `tx, err := db.BeginTx(ctx, nil)`; `defer tx.Rollback()` (no-op after commit); `return tx.Commit()`.
- Nullable columns: `sql.NullString`/pointers; be explicit.
- Migrations: goose, golang-migrate or atlas.

## 7. Logging and config

- `log/slog` (Go 1.21+) with JSON handler in production; attach request ID via context-aware helpers.
- Config from env (e.g. `envconfig`, `koanf`, or plain `os.Getenv` + validation); fail fast at startup.

## 8. Testing

- Table-driven tests with `t.Run(tc.name, …)`; `t.Parallel()` where safe; `t.Helper()` in helpers; `t.Cleanup`.
- `httptest.NewRecorder`/`NewServer` for handlers and fake upstreams; Testcontainers-go for real DB.
- Fakes over mocks where possible (small interfaces make this easy). Golden files for large outputs.
- Benchmarks with `testing.B`; fuzzing with `testing.F` for parsers.
- `go test -race -cover ./...`.

## 9. Tooling

`gofmt`/`goimports` (non-negotiable) · `go vet` · `staticcheck` or `golangci-lint` · `govulncheck` for vulnerabilities ·
`go mod tidy` · pinned Go version in `go.mod` and CI. Build static binaries (`CGO_ENABLED=0`) into distroless/scratch images when no cgo is needed.

## 10. Common mistakes to catch

Ignored errors · nil map writes · nil pointer on unchecked returns · typed-nil interface (`var p *T = nil; var i I = p; i != nil`) ·
goroutine leaks (blocked sends, missing cancel) · unbounded goroutines · data races · `defer` inside long loops ·
slices sharing backing arrays after `append` · `range` over a map assuming order · `time.Now()` in tests without injection ·
`http.DefaultClient`/no server timeouts · reading entire bodies without limits · `interface{}`/`any` everywhere instead of types ·
premature interfaces with one implementation used only for mocking · using `pkg/` and deep package trees for small services.
