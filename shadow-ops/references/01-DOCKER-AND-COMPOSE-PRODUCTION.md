# 01 — Production Dockerfiles & Docker Compose Hardening

Pair with [`vendor/OWASP_Docker_Security_Cheat_Sheet.md`](vendor/OWASP_Docker_Security_Cheat_Sheet.md).

---

## 1. Mandatory Production `Dockerfile` Standards

1. **Multi-Stage Builds Only**: Separate `deps`, `builder`, and `runner` stages so compilers, devDependencies, and source maps never enter the production image.
2. **Pin Base Images & Use Minimal Runtimes**:
   - Node.js: `node:22-bookworm-slim` or `node:22-alpine` (use `-slim` when native glibc bindings like `sharp`, `prisma`, or `bcrypt` are present).
   - Python: `python:3.12-slim-bookworm` + `uv` or virtual environment copy.
   - Go / Rust: `gcr.io/distroless/static-debian12:nonroot` or `alpine:3.20`.
   - PHP/Laravel: `serversideup/php:8.3-fpm-nginx-alpine` or custom `php:8.3-fpm-alpine` + `opcache` + `jit` enabled.
3. **Run as Non-Root User (`USER`)**:
   - Always drop root privileges before `ENTRYPOINT`/`CMD`.
4. **PID 1 Signal Handling (`tini` / `init: true`)**:
   - Use `ENTRYPOINT ["/usr/bin/tini", "--"]` or `init: true` in Compose and `exec` form `CMD ["node", "dist/main.js"]` so `SIGTERM` triggers graceful HTTP/DB connection draining.
5. **Mandatory `.dockerignore`**:
   - Exclude `.git`, `node_modules`, `.venv`, `.env*`, `dist`, `coverage`, `docs`, `*.log`, `tests`.

### Reference Template: Node.js / TypeScript Production `Dockerfile`
```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:22-bookworm-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:22-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN apt-get update && apt-get install -y --no-install-recommends tini curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder --chown=node:node /app/package.json ./
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/dist ./dist
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:3000/healthz || exit 1
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "dist/main.js"]
```

---

## 2. Production `docker-compose.prod.yml` Standards

Every service in `docker-compose.prod.yml` MUST include:
- **`init: true`** and **`restart: unless-stopped`**
- **`security_opt: ["no-new-privileges:true"]`** and **`cap_drop: ["ALL"]`**
- **Resource bounds (`deploy.resources.limits`)** so a memory leak in one container never triggers host-wide Linux OOM killer on the database.
- **Bounded JSON logging (`max-size: "20m"`, `max-file: "5"`)** so container stdout never fills 100% of the VPS disk.
- **Internal vs External network isolation** (`frontend_net` vs `backend_internal` with `internal: true` so Postgres/Redis cannot be reached from outside).
- **Localhost Port Binding (`127.0.0.1:5432:5432`)**: Never publish `ports: ["5432:5432"]` directly on `0.0.0.0` because Docker bypasses `ufw` iptables chains by default! Always bind to `127.0.0.1` or omit `ports:` entirely for internal DBs.

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    init: true
    restart: unless-stopped
    env_file: .env.production
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - proxy_net
      - backend_net
    deploy:
      resources:
        limits:
          cpus: "1.50"
          memory: 1024M
        reservations:
          cpus: "0.25"
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "20m"
        max-file: "5"

  postgres:
    image: postgres:16.4-alpine
    restart: unless-stopped
    shm_size: 256mb
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend_net
    logging:
      driver: "json-file"
      options:
        max-size: "20m"
        max-file: "5"

networks:
  proxy_net:
  backend_net:
    internal: true

volumes:
  pg_data:
```
