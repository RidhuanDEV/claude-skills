# Greenfield Bootstrap Profiles, Official Generators & Baseline Wiring

> Use this playbook when initializing a new CLI, static site, worker, HTTP backend service, or library with verified official CLI generators and a single vertical production slice.

## 1. Core Concepts
Greenfield initialization fails in two opposite ways: hand-writing brittle config boilerplate from memory, or scaffolding unrequested enterprise bloat (`Redis`, `Kafka`, `Kubernetes`) before one endpoint works. Use the project's **official CLI generator**, verify workspace safety first (`preview_scaffold.py`), wire fail-fast startup config + structured logging + graceful shutdown, and prove one end-to-end slice cleanly.

## 2. Technical Rules & Decision Matrix

| Profile | Verified Official Generator Examples | Minimum Viable Vertical Slice | Conditional Add-Ons (ONLY When Requested/Needed) |
| :--- | :--- | :--- | :--- |
| `cli` | `npm init`, `uv init`, `cargo init`, `go mod init` | 1 command, strict arg parse, clean exit codes (`0`/`1`), unit test | Shell completion, config file loader |
| `static` | `npm create vite@latest`, `npm create astro@latest` | 1 semantic responsive page (`antislop`), reproducible `build`, zero-CLS assets | Search index, sitemap, CSP headers |
| `worker` | `npm init` + TS (`tsx`/Node 22), Python `uv` | 1 idempotent job handler, retry/DLQ semantics, duplicate-delivery test | Queue backend (`BullMQ`/PG `SKIP LOCKED`), OTel |
| `http` | `create-next-app`, `nest new`, `fastify-cli`, `uv` FastAPI | 1 validated endpoint, `pino`/`structlog`/`slog` JSON logger + `X-Request-Id` + PII redact, graceful shutdown, smoke test | OpenAPI 3.1 (`shadow-api`), DB migration, cache |
| `library` | `tsup`/`unbuild`, `uv init --lib`, `cargo init --lib` | Typed public entry export, tree-shakeable ESM/CJS types, consumer smoke test | Dual exports, CHANGELOG |

## 3. Implementation Examples

### Strict-TS Fail-Fast Startup Env Validation + Structured Logger + Graceful Shutdown
```ts
import pino from "pino";

export interface AppConfig {
  readonly port: number;
  readonly nodeEnv: "development" | "test" | "production";
  readonly logLevel: string;
}

export function parseEnv(raw: NodeJS.ProcessEnv): AppConfig {
  const portRaw = raw["PORT"] ?? "3000";
  const port = Number.parseInt(portRaw, 10);
  if (Number.isNaN(port) || port < 1 || port > 65535) {
    throw new Error(`INVALID_CONFIG: PORT must be 1..65535, got '${portRaw}'`);
  }
  const envRaw = raw["NODE_ENV"] ?? "development";
  if (envRaw !== "development" && envRaw !== "test" && envRaw !== "production") {
    throw new Error(`INVALID_CONFIG: Unsupported NODE_ENV '${envRaw}'`);
  }
  return { port, nodeEnv: envRaw, logLevel: raw["LOG_LEVEL"] ?? "info" };
}

export const logger = pino({
  level: process.env["LOG_LEVEL"] ?? "info",
  redact: ["req.headers.authorization", "req.headers.cookie", "*.password", "*.token", "*.secret"],
});

export function registerGracefulShutdown(closeServer: () => Promise<void>, closeDeps: () => Promise<void>): void {
  let shuttingDown = false;
  const shutdown = async (signal: string): Promise<void> => {
    if (shuttingDown) return;
    shuttingDown = true;
    logger.info({ signal }, "graceful shutdown started");
    const timer = setTimeout(() => process.exit(1), 10_000).unref();
    try {
      await closeServer();
      await closeDeps();
      clearTimeout(timer);
      process.exit(0);
    } catch (err: unknown) {
      logger.error({ err }, "graceful shutdown failed");
      process.exit(1);
    }
  };
  process.on("SIGTERM", () => void shutdown("SIGTERM"));
  process.on("SIGINT", () => void shutdown("SIGINT"));
}
```

## 4. Best Practices
- Always run `python scripts/preview_scaffold.py TARGET --profile <profile>` first; if the target folder is non-empty (`REVIEW_EXISTING`), inspect ownership/conventions before generating anything.
- Inspect unfamiliar CLI generator output inside a sibling staging directory when running into existing workspaces, diffing generated files before adopting.
- Emit the 8-field Official-First Decision Record when selecting core runtime dependencies (`shadow-monarch/scripts/official_first_verifier.py`).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Hand-crafting boilerplate & over-provisioning day 1):** Typing `tsconfig.json`, bundler configs, and directory skeletons manually, or adding Kafka + Kubernetes + Grafana when asked for a simple internal CRUD CLI.
  **RIGHT:** Execute verified official CLI generators (`create vite`, `create-next-app`, `uv init`), wire one clean vertical slice, and add infra strictly on proven need.
- **WRONG (Reading raw `process.env.SECRET!` lazily in request paths & `console.log`):** Scattering non-null assertions across handlers (crashes mid-request in prod and logs unredacted secrets).
  **RIGHT:** Parse & validate the complete config upfront before binding sockets, and log via redacted structured JSON loggers.

## 6. Production Considerations
- **Clean-Checkout Reproducibility:** Verify `npm ci` / `uv sync --frozen` + `build` + `test` + smoke execution from a clean directory state before handing off.
- **Health vs Readiness Separation:** Ensure `/healthz` reflects process liveness while `/readyz` checks mandatory dependencies without letting an optional cache outage falsely kill healthy stateless replicas.
