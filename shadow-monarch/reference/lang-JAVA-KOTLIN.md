# Java / Kotlin / Spring Boot

Target the project's JDK (prefer current LTS for new work) and Spring Boot version (Boot 3 requires Java 17+ and `jakarta.*` namespaces).
Kotlin: follow official Kotlin coding conventions; Java: the project's style (often Google Java Style).

## 1. Project layout

- Package by feature: `com.acme.orders.{api, application, domain, infrastructure}` rather than global `controller/service/repository` packages.
- Controllers (`@RestController`) thin → services (`@Service`, transactional use cases) → repositories (Spring Data) / adapters.
- Constructor injection only (final fields in Java; primary constructor in Kotlin); no field `@Autowired`.
- DTOs as Java `record`s / Kotlin `data class`es; never expose JPA entities through APIs.
- Config with `@ConfigurationProperties` + `@Validated`; profiles for environments; secrets from env/vault, not `application.yml` in git.

## 2. Errors and validation

- Bean Validation (`@Valid`, `@NotNull`, `@Size`, …) on request DTOs; Kotlin: annotate with `@field:` targets.
- `@RestControllerAdvice` mapping domain exceptions to `ProblemDetail` (Spring 6+ supports RFC 9457 natively). No stack traces in responses
  (`server.error.include-stacktrace=never`).
- Do not catch `Exception` broadly and swallow; do not use exceptions for normal control flow in hot paths.
- Kotlin: embrace null-safety; avoid `!!`; model expected failures with sealed classes or `Result` when the codebase does.
- `Optional` in Java only as a return type, never for fields/parameters.

## 3. JPA / Hibernate

- **N+1**: default to `FetchType.LAZY` for associations (note `@ManyToOne` defaults to EAGER — override it); fetch deliberately with
  `JOIN FETCH`, `@EntityGraph` or DTO projections. Enable SQL logging/statistics in dev.
- Disable Open Session In View (`spring.jpa.open-in-view=false`) to avoid lazy loading in the web layer.
- `@Transactional` on service methods (public, called from another bean — self-invocation bypasses the proxy); `readOnly = true` for reads;
  keep transactions short; no remote calls inside. Understand that checked exceptions do not roll back by default.
- Optimistic locking with `@Version`; handle `OptimisticLockingFailureException`. Pessimistic with `@Lock(PESSIMISTIC_WRITE)` when needed.
- Pagination with `Pageable` (deterministic sort) or keyset; never `findAll()` on big tables.
- Entities: `equals/hashCode` based on ID carefully (Kotlin: avoid `data class` for entities; use the `kotlin-jpa`/`allopen` plugins).
- Queries: JPQL/Criteria/`@Query` with named parameters — never string concatenation. Batch inserts with `hibernate.jdbc.batch_size`.
- Migrations with Flyway or Liquibase; `ddl-auto=validate` (never `update`/`create` in production).
- Money: `BigDecimal` (with explicit scale/rounding) or `Long` minor units; time: `Instant`/`OffsetDateTime`, UTC.

## 4. Concurrency

- Spring beans are singletons: no mutable per-request state in fields.
- Java 21 virtual threads (`spring.threads.virtual.enabled=true`) simplify blocking I/O — but watch `synchronized` pinning on older JDKs and ThreadLocal-heavy libs.
- Use `ExecutorService` with bounded pools (never unbounded `newCachedThreadPool` for untrusted load); `CompletableFuture` with explicit executors and timeouts.
- Kotlin coroutines: structured concurrency (`coroutineScope`, `supervisorScope`), never `GlobalScope`, `withContext(Dispatchers.IO)` for blocking calls,
  propagate cancellation, `withTimeout`.
- Thread-safe collections (`ConcurrentHashMap`) or immutability; `AtomicLong` for counters.

## 5. HTTP clients and resilience

`RestClient` (Spring 6.1+) or `WebClient`, configured with connect/read timeouts (defaults may be infinite). Resilience4j for retry with backoff,
circuit breaker, bulkhead, rate limiter. Propagate trace context (Micrometer Tracing / OpenTelemetry).

## 6. Security (Spring Security 6)

- `SecurityFilterChain` bean (lambda DSL); deny by default (`anyRequest().authenticated()`); method security (`@PreAuthorize`) plus object-level checks.
- Password encoding: `PasswordEncoderFactories.createDelegatingPasswordEncoder()` (bcrypt) or Argon2.
- JWT resource server: validate issuer/audience; keep tokens short-lived. CSRF: keep enabled for cookie sessions; disable only for pure stateless token APIs.
- CORS allowlist via `CorsConfigurationSource`. Actuator: expose only `health`/`info` publicly; secure the rest.
- Avoid Java native deserialization of untrusted data; keep Jackson default typing off. Log injection: sanitize user input in logs.

## 7. Observability

SLF4J with parameterized messages (`log.info("Order {} created", id)`), JSON logs (Logback encoder) with trace IDs via MDC,
Micrometer metrics, Actuator health groups (liveness/readiness) for Kubernetes probes.

## 8. Testing

JUnit 5 + AssertJ (Kotest for Kotlin); Mockito / MockK; slice tests (`@WebMvcTest`, `@DataJpaTest`) for speed; `@SpringBootTest` + Testcontainers
(`@ServiceConnection`) for integration; MockMvc/WebTestClient for HTTP; ArchUnit for enforcing architecture rules.

## 9. Tooling

Gradle (Kotlin DSL) or Maven — follow the repo; dependency locking / BOM management; Spotless/ktlint/detekt/Checkstyle/Error Prone;
OWASP Dependency-Check or Snyk; layered jars/Buildpacks or a JRE-only runtime image, non-root, container-aware memory settings (`-XX:MaxRAMPercentage`).

## 10. Common mistakes to catch

Field injection · entities returned from controllers · EAGER associations and N+1 · Open Session In View · `@Transactional` self-invocation or on private methods ·
`ddl-auto=update` in prod · `findAll()` without paging · missing HTTP client timeouts · mutable state in singleton beans · `GlobalScope` / blocking calls in coroutines ·
`!!` everywhere · `double` for money · `LocalDateTime` for instants · swallowed exceptions · Actuator fully exposed · CSRF disabled for cookie-based auth.
