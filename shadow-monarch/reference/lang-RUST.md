# Rust

Target the project's edition and MSRV (`Cargo.toml`, `rust-toolchain.toml`). Follow the Rust API Guidelines and rustfmt/Clippy defaults.

## 1. Project layout

```text
Cargo.toml              workspace for multi-crate projects; shared deps in [workspace.dependencies]
src/main.rs             thin: config, tracing, runtime, wiring, graceful shutdown
src/lib.rs              application logic (testable without the binary)
src/{routes, services, repo, domain, error.rs, config.rs}
tests/                  integration tests
migrations/
```
- Keep `main` thin; put logic in the library crate. Modules by feature; `pub(crate)` by default; expose a deliberate public API.
- Domain types with invariants as newtypes (`struct Email(String)` with a validating constructor — "parse, don't validate").

## 2. Errors

- Libraries: typed errors with `thiserror` (`#[derive(Error)] enum RepoError { #[error("not found")] NotFound, #[error(transparent)] Db(#[from] sqlx::Error) }`).
- Applications/binaries: `anyhow` (or `eyre`) with `.context("loading config")` at boundaries.
- Propagate with `?`. **No `unwrap()`/`expect()` on fallible runtime paths** (I/O, parsing input, network, locks) — only for true invariants,
  with an `expect("reason why this cannot fail")` message. `panic` is for bugs, not control flow.
- Web: implement `IntoResponse` (axum) / `ResponseError` (actix) for the app error type to map variants to status codes and the JSON error contract;
  log internal details, return safe messages.

## 3. Ownership, borrowing, performance

- Prefer borrowing (`&str`, `&[T]`) in function parameters; take ownership only when storing. Avoid gratuitous `.clone()` to silence the borrow checker —
  restructure or use `Arc` when shared ownership is real.
- `Arc<T>` for shared immutable state; `Arc<Mutex<T>>`/`RwLock` only where needed; keep lock scopes short; **never hold a `std::sync::Mutex` guard across `.await`**
  (use `tokio::sync::Mutex` only if you must hold across await, or restructure).
- Iterators over index loops; `Cow` for maybe-owned data; measure with `criterion`/profilers before micro-optimizing.
- `unsafe` only with a documented `// SAFETY:` justification and a safe wrapper; prefer none.

## 4. Async (tokio)

- One runtime; `#[tokio::main]`. Never block the executor: CPU-heavy or blocking I/O → `tokio::task::spawn_blocking` or `rayon`.
- Timeouts: `tokio::time::timeout(dur, fut)`; HTTP clients (`reqwest::Client::builder().timeout(..)`) created once and reused.
- Structured concurrency: keep `JoinHandle`s / use `JoinSet`, propagate errors, cancel with `CancellationToken` (`tokio-util`) on shutdown.
  Remember dropping a future cancels it — make critical sections cancellation-safe (especially inside `select!`).
- Bounded channels (`mpsc::channel(n)`) for backpressure; unbounded channels only with a proven reason.
- Graceful shutdown: `axum::serve(listener, app).with_graceful_shutdown(signal)`.

## 5. Web services (axum / actix-web)

- axum: `Router` with typed extractors (`Json<T>`, `Path`, `Query`, `State<AppState>`); `AppState` holds pool, config, clients (cheap to clone via `Arc`).
- `tower-http` layers: `TraceLayer`, `TimeoutLayer`, `RequestBodyLimitLayer`, `CorsLayer` (allowlist), compression, request IDs.
- Validation with `serde` (+ `#[serde(deny_unknown_fields)]` for strict DTOs) and `validator`/`garde`, or newtype constructors.
- Separate request/response DTOs from DB rows and domain types.

## 6. Data access

- `sqlx` with compile-time checked queries (`query!`/`query_as!`, offline mode via `cargo sqlx prepare` for CI), or `diesel`/`sea-orm` if the project uses them.
- Always bind parameters (`$1`); never `format!` SQL with input. Transactions: `let mut tx = pool.begin().await?; …; tx.commit().await?;` (drop = rollback).
- Pool sizing via `PgPoolOptions`; migrations with `sqlx migrate`.
- Money: `rust_decimal` or integer minor units; time: `time`/`chrono` with UTC `OffsetDateTime`/`DateTime<Utc>`.

## 7. Security

- Memory safety does not prevent logic bugs: authorization, injection, SSRF, path traversal still apply.
- Passwords: `argon2` crate; randomness: `rand::rngs::OsRng`/`getrandom`; constant-time compare via `subtle`.
- `cargo audit` / `cargo deny` (advisories, licenses, duplicate crates) in CI; minimize dependencies and features; review `build.rs`/proc-macro crates.
- Secrets in `secrecy::SecretString` to avoid accidental logging via `Debug`.

## 8. Observability

`tracing` + `tracing-subscriber` (JSON in production) with spans per request (`#[instrument(skip(password))]`), OpenTelemetry exporter when needed.
No `println!` in services.

## 9. Testing

Unit tests in `#[cfg(test)] mod tests`; integration tests in `tests/`; `#[tokio::test]`; `sqlx::test` for DB-backed tests with isolated databases;
axum handlers via `tower::ServiceExt::oneshot`; `proptest`/`quickcheck` for properties; `insta` snapshots sparingly; `mockall` or hand-written trait fakes.
`cargo test --all-features`.

## 10. Tooling

`cargo fmt` · `cargo clippy -- -D warnings` · `cargo audit`/`cargo deny` · `cargo nextest` (faster tests) · pinned toolchain ·
multi-stage Docker (`cargo-chef` for dependency caching) into distroless/debian-slim, non-root; release profile tuning (`lto`, `codegen-units`) when size/speed matter.

## 11. Common mistakes to catch

`unwrap()` on I/O/input · `.clone()` everywhere · `std::sync::Mutex` held across `.await` · blocking calls in async fns · unbounded channels ·
detached `tokio::spawn` without error handling or shutdown · non-cancellation-safe code in `select!` · `format!`-built SQL ·
`String` for every domain value (no newtypes) · large `enum` error types that leak DB details to clients · missing request timeouts and body limits ·
creating a new `reqwest::Client` per request · `unsafe` without SAFETY comments.
