# 02 — Polyglot Unit & Integration Testing Idioms Across 8 Stacks

## 1. Purpose & Activation Conditions
Write clean, idiomatic, fast, and maintainable unit and integration tests tailored to the repository's exact language and test framework — covering **TypeScript/Node/React**, **Python**, **Go**, **PHP/Laravel**, **Java/Kotlin**, **C#/.NET**, **Rust**, and **Dart/Flutter** — without forcing foreign patterns onto a brownfield codebase. Activate whenever authoring or fixing automated tests in any of these stacks.

## 2. Prerequisites
- Inspected repository manifest (`package.json`, `pyproject.toml`, `go.mod`, `composer.json`, `pom.xml`/`build.gradle`, `*.csproj`, `Cargo.toml`, `pubspec.yaml`) and 1–3 existing test files to match local conventions, assertion library, and fixture helpers.

## 3. Technical Principles & Constraints
- **Match Existing Runner & Assertion Style:** Never install Vitest in a Jest repo, or Pest in a pure PHPUnit repo, unless explicitly asked to migrate.
- **Explicit AAA Structure (Arrange -> Act -> Assert):** Keep every test self-contained and readable top-to-bottom without deep nested `beforeEach` magic mutations that obscure preconditions.
- **Strict Parameterization / Table-Driven Tests:** Express validation and boundary matrices using `@pytest.mark.parametrize`, `it.each(...)`, Go `tests := []struct{...}`, xUnit `[Theory][InlineData]`, or JUnit `@ParameterizedTest` instead of copy-pasting 12 near-identical test functions.
- **Real Transaction Rollback Per Test:** Isolate DB-backed integration tests using nested `SAVEPOINT` rollbacks, Laravel `RefreshDatabase`, Rust `#[sqlx::test]`, or isolated schemas rather than slow full DB drops between every test.

## 4. Architecture & Implementation

### Polyglot Idiom Matrix

| Stack | Standard Runner & HTTP Harness | DB Isolation Pattern | Concurrency / Hygiene Flag |
| :--- | :--- | :--- | :--- |
| **TypeScript / Node / React** | `Vitest` or `Jest` + `supertest` + `@testing-library/react` + `MSW` | Per-test TX rollback or worker schema; typed factories (`0 any`, `0 as Type`) | `vitest run --bail=1` / `tsc --noEmit` |
| **Python (FastAPI / Django)** | `pytest` + `pytest-asyncio` + `httpx.AsyncClient` (`ASGITransport`) | `conftest.py` fixture wrapping session in `SAVEPOINT` rollback | `pytest -q --strict-markers` |
| **Go** | `testing` + `net/http/httptest` + table-driven `t.Run` + `t.Parallel()` | Per-test transaction or `testcontainers-go` single container | **`go test -v -race ./...`** (mandatory!) |
| **PHP / Laravel** | `Pest` or `PHPUnit` + Model Factories + `actingAs()` | `uses(RefreshDatabase::class)` + `assertDatabaseHas()` | `php artisan test --parallel` |
| **Java / Kotlin** | `JUnit 5` + `AssertJ` + `MockMvc` / `WebTestClient` | Constructor injection for unit; `@SpringBootTest` + singleton `@Testcontainers` | `./gradlew test` / `mvn test` |
| **C# / .NET** | `xUnit` (`[Theory]`/`[InlineData]`) + `FluentAssertions` + `WebApplicationFactory<Program>` | Respawn or transaction scope against ephemeral SQL/Postgres | `dotnet test --no-restore` |
| **Rust** | `#[test]` / `#[tokio::test]` + `tower::ServiceExt::oneshot` (`axum`) | `#[sqlx::test]` (isolated temporary DB per test automatically) | `cargo test --all-targets` |
| **Dart / Flutter** | `flutter_test` + `mocktail` (`find.bySemanticsLabel` / `find.byKey`) | Deterministic `pumpAndSettle()` across loading/success/empty/error states | `flutter test --reporter expanded` |

### Idiomatic Stack Snippets

#### TypeScript (`Vitest` + `Supertest` — Strict Typing)
```ts
import { describe, it, expect } from 'vitest'
import request from 'supertest'
import { app } from '../src/app'

interface OrderResponseEnvelope {
  readonly data: { readonly id: string; readonly status: string }
}

describe('POST /api/v1/orders', () => {
  it('creates an order and persists PENDING status (201)', async () => {
    const res = await request(app)
      .post('/api/v1/orders')
      .set('Authorization', `Bearer ${validToken}`)
      .set('Idempotency-Key', 'idem-order-001')
      .send({ items: [{ productId: 'prod_01', quantity: 2 }] })

    expect(res.status).toBe(201)
    const body: OrderResponseEnvelope = res.body
    expect(body.data.status).toBe('PENDING')
  })

  it.each([
    { label: 'zero quantity', quantity: 0 },
    { label: 'negative quantity', quantity: -1 },
  ])('rejects $label with 422', async ({ quantity }) => {
    const res = await request(app)
      .post('/api/v1/orders')
      .set('Authorization', `Bearer ${validToken}`)
      .send({ items: [{ productId: 'prod_01', quantity }] })

    expect(res.status).toBe(422)
  })
})
```

#### Python (`pytest` + `httpx.AsyncClient` Parameterized)
```python
import pytest
from httpx import AsyncClient

@pytest.mark.parametrize(
    "payload,expected_status",
    [
        ({"name": "Item Valid", "price_minor": 15000}, 201),
        ({"name": "", "price_minor": 15000}, 422),
        ({"name": "Negative Price", "price_minor": -500}, 422),
    ],
)
@pytest.mark.asyncio
async def test_create_product_validation(
    async_client: AsyncClient, auth_headers: dict[str, str], payload: dict[str, object], expected_status: int
) -> None:
    response = await async_client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert response.status_code == expected_status
```

#### Go (`testing` Table-Driven + `-race`)
```go
func TestCalculateDiscount(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name      string
		subtotal  int64
		promoCode string
		want      int64
		wantErr   bool
	}{
		{name: "valid 10 percent promo", subtotal: 100_000, promoCode: "HEMAT10", want: 10_000, wantErr: false},
		{name: "negative subtotal rejected", subtotal: -5_000, promoCode: "HEMAT10", want: 0, wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got, err := CalculateDiscount(tt.subtotal, tt.promoCode)
			if (err != nil) != tt.wantErr {
				t.Fatalf("CalculateDiscount() error = %v, wantErr %v", err, tt.wantErr)
			}
			if got != tt.want {
				t.Errorf("CalculateDiscount() = %v, want %v", got, tt.want)
			}
		})
	}
}
```

#### PHP / Laravel (`Pest` + Cross-Tenant IDOR Guard)
```php
use App\Models\Invoice;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;

uses(RefreshDatabase::class);

it('prevents a user from updating another tenants invoice (403 IDOR)', function () {
    $tenantAUser = User::factory()->create(['tenant_id' => 1]);
    $tenantBInvoice = Invoice::factory()->create(['tenant_id' => 2]);

    $this->actingAs($tenantAUser)
        ->patchJson("/api/v1/invoices/{$tenantBInvoice->id}", ['status' => 'PAID'])
        ->assertForbidden();
});
```

## 5. Platform/Vendor Variations
- **Windows PowerShell Execution:** Ensure test commands avoid Unix-only `FOO=1 cmd` prefixes (use `$env:FOO="1"; cmd` or `cross-env`) and avoid `&&` chaining in PowerShell 5.1.
- **SQLite Substitution Warning:** Do NOT test PostgreSQL-specific SQL (`JSONB`, `RLS`, `FOR UPDATE SKIP LOCKED`, `ON CONFLICT` partial indexes, `pgvector`) against an in-memory SQLite mock — SQLite silently masks PostgreSQL constraint, type, and concurrency differences! Use a real ephemeral Postgres container (`06`).
- **Flutter / React Native Widget Tests:** Query by accessible semantic labels (`find.bySemanticsLabel`) first so widget tests simultaneously guard screen-reader accessibility (`/shadow-accessibility`).

## 6. Decision Matrix & Trade-Offs

| Testing Strategy | Real SQL Fidelity | Speed | Setup Effort | When to Use |
| :--- | :--- | :--- | :--- | :--- |
| **In-Memory SQLite Substitute** | Poor for Postgres/MySQL dialects | Very Fast | Low | Only when production actually runs SQLite |
| **Singleton Ephemeral Postgres + `SAVEPOINT`** | **100%** (exact engine/RLS/locks) | Fast (`< 50ms`/test) | Low–Medium | Default for all Postgres/MySQL backends |
| **MSW HTTP Boundary Stub (Frontend)** | Exact fetch/serialization path | Fast | Low | React/Vue/Next component integration tests |
| **`go test -race` / `tokio` Multi-Thread** | Catches real data races | Medium | Zero extra code | Mandatory in CI for concurrent Go/Rust code |

## 7. Real Production Scenario
A Laravel + PostgreSQL payroll app ran its entire PHPUnit suite against `:memory:` SQLite. All 210 tests passed in CI, yet production migrations failed on day one because a PostgreSQL partial unique index and `ILIKE` search query were never exercised by SQLite. Switching the CI suite to a single ephemeral `postgres:16-alpine` container with `RefreshDatabase` added only 9 seconds to CI and caught 4 dialect and RLS isolation bugs immediately.

## 8. Failure Modes & Edge Cases
- **WRONG:** Running `go test ./...` in CI without `-race` on concurrent services (data races corrupt production memory silently).
  **RIGHT:** Always run `go test -race ./...` in CI and local concurrent bug verification.
- **WRONG:** Sharing a single mutable fixture object across tests in Jest/Vitest (`const sharedUser = { ... }` mutated inside test #1, breaking test #2 only when tests run in random order).
  **RIGHT:** Generate fresh immutable fixtures via factory functions inside each test (`buildUserFixture()`).
- **WRONG:** Asserting exact brittle error prose (`expect(msg).toBe("Invalid email address format!")`) when copywriters update wording.
  **RIGHT:** Assert stable HTTP status codes + structured machine-readable `error.code` (`"INVALID_EMAIL"`).

## 9. Testing & Verification
- Run the exact framework test command and observe real exit code `0` and test counts before claiming `PASS`.
- Run `python shadow-test/scripts/suite_hygiene_verifier.py --self-test` to confirm verifier probes pass.

## 10. Operational Considerations
- Configure randomized test ordering (`pytest-randomly`, `vitest --sequence.shuffle`, `go test -shuffle=on`) periodically in CI to expose hidden inter-test ordering dependencies early.

## 11. Authoritative References
- Vitest / Pytest / Go `testing` / Pest / JUnit 5 / xUnit / SQLx / Flutter Official Testing Documentation.
- `references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md` (local curated reference).

## 12. Limitations & When NOT to Use
- Do NOT write heavy visual pixel-diff or real browser layout overflow tests inside JSDOM/Happy-DOM unit tests (JSDOM has no real CSS layout engine!) — route real viewport & layout tests to `/shadow-browser`.
