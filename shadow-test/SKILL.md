---
name: shadow-test
description: Polyglot Automated Unit, Integration, and API Contract Test Generator supporting TypeScript/JS (Vitest/Jest), Python (Pytest), Go (testing), PHP/Laravel (Pest/PHPUnit), Java/Kotlin (JUnit 5), .NET (xUnit), Rust, and Flutter. Trigger with /shadow-test.
---

# Shadow Test (`/shadow-test`) — Polyglot Automated Testing Engine

Use this skill whenever the **Monarch** asks to write, expand, fix, or audit unit tests, integration tests, or API contract tests in any programming language or framework.

---

## 1. Local Knowledge Base Routing

1. Read [`references/POLYGLOT-TESTING-MATRIX.md`](references/POLYGLOT-TESTING-MATRIX.md) for idiomatic test structures across TypeScript/Node/React, Python, Go, PHP/Laravel, Java/Kotlin, C#/.NET, Rust, and Dart/Flutter.
2. For JavaScript/TypeScript/Node.js backend & frontend testing, consult [`references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md`](references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md).

---

## 2. Execution Workflow

### Step 1: Auto-Detect Project Stack & Existing Test Runner
Inspect the workspace root to match the project's native testing tool:
- **`package.json`**: Check if `vitest`, `jest`, `@playwright/test`, or `supertest` is installed (`npm test`).
- **`pyproject.toml` / `requirements.txt`**: Check for `pytest`, `pytest-asyncio`, `httpx`, or Django `manage.py test`.
- **`go.mod`**: Use standard `go test -v -race ./...` with table-driven subtests (`t.Run`).
- **`composer.json`**: Check for `pestphp/pest` (`./vendor/bin/pest`) or `phpunit/phpunit` (`php artisan test`).
- **`pom.xml` / `build.gradle`**: Use `JUnit 5` (`mvn test` / `./gradlew test`).
- **`*.csproj` / `*.sln`**: Use `dotnet test` (`xUnit` / `NUnit`).
- **`Cargo.toml`**: Use `cargo test`.
- **`pubspec.yaml`**: Use `flutter test`.

### Step 2: Generate the Mandatory 8-Point Test Coverage Matrix
For every module, service, or endpoint under test, write deterministic tests covering:
1. **Happy Path (`200`/`201`)**: Assert observable output and state change (not internal private method calls).
2. **Validation & Schema Failure (`400`/`422`)**: Missing required fields, invalid types, out-of-range numbers.
3. **Unauthenticated (`401`)**: Missing or invalid token.
4. **Forbidden / Cross-Tenant IDOR (`403`/`404`)**: User from Tenant A accessing Tenant B's resource.
5. **Not Found (`404`)**: Non-existent ID.
6. **Idempotency / Conflict (`409`)**: Duplicate key or repeated request.
7. **Boundary Values**: `0`, `-1`, empty list `[]`, max length + 1, timezone/midnight edge cases, decimal/currency rounding.
8. **State Isolation**: Ensure transactions roll back or test data uses isolated fixtures so tests never pollute the development database.

### Step 3: Execute & Verify 100% Green Pass
Always run the generated test suite via terminal command and fix any failing assertions or strict type errors (`0 any`, `0 as Type` in TypeScript) before reporting completion to the **Monarch**.
