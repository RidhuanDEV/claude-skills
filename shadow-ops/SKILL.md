---
name: shadow-ops
description: Full-Spectrum DevOps, Linux SysAdmin, Docker/Compose, Kubernetes, Nginx/Caddy Reverse Proxy, CI/CD (GitHub Actions/GitLab CI), Observability (Prometheus/Loki/OTel), 3-2-1 Backups, and Incident Runbooks backed by a local OWASP & H5BP knowledge base. Trigger with /shadow-ops.
---

# Shadow Ops (`/shadow-ops`) — Full-Spectrum DevOps, SysAdmin, Cloud & SRE

Use this skill whenever the **Monarch** asks to containerize, deploy, harden, configure, monitor, back up, or troubleshoot a server/infrastructure environment.

---

## 1. Local Knowledge Base Routing (Always Consult Before Generating Configs)

`/shadow-ops` includes both **7 curated production runbooks** and **8 official downloaded OWASP & H5BP reference specs** in [`references/`](references/):

| Operational Domain | Local Playbook | Vendored Official Standard (`references/vendor/`) |
| :--- | :--- | :--- |
| **Docker & `docker-compose.prod.yml`** | [`01-DOCKER-AND-COMPOSE-PRODUCTION.md`](references/01-DOCKER-AND-COMPOSE-PRODUCTION.md) | [`OWASP_Docker_Security_Cheat_Sheet.md`](references/vendor/OWASP_Docker_Security_Cheat_Sheet.md) |
| **Nginx / Caddy / Reverse Proxy / SSL** | [`02-NGINX-CADDY-REVERSE-PROXY-HARDENING.md`](references/02-NGINX-CADDY-REVERSE-PROXY-HARDENING.md) | [`H5BP_nginx_main.conf`](references/vendor/H5BP_nginx_main.conf), [`H5BP_nginx_ssl_engine.conf`](references/vendor/H5BP_nginx_ssl_engine.conf), [`H5BP_nginx_compression.conf`](references/vendor/H5BP_nginx_compression.conf) |
| **Linux VPS, `systemd`, PM2, Firewall, `sysctl`** | [`03-LINUX-SYSADMIN-SYSTEMD-PM2-VPS.md`](references/03-LINUX-SYSADMIN-SYSTEMD-PM2-VPS.md) | — |
| **CI/CD Pipelines & Zero-Downtime Rollback** | [`04-CICD-GITHUB-GITLAB-ZERO-DOWNTIME.md`](references/04-CICD-GITHUB-GITLAB-ZERO-DOWNTIME.md) | [`OWASP_CI_CD_Security_Cheat_Sheet.md`](references/vendor/OWASP_CI_CD_Security_Cheat_Sheet.md), [`OWASP_Secrets_Management_Cheat_Sheet.md`](references/vendor/OWASP_Secrets_Management_Cheat_Sheet.md) |
| **Kubernetes (K8s), Helm & Terraform IaC** | [`05-KUBERNETES-TERRAFORM-IAC.md`](references/05-KUBERNETES-TERRAFORM-IAC.md) | [`OWASP_Kubernetes_Security_Cheat_Sheet.md`](references/vendor/OWASP_Kubernetes_Security_Cheat_Sheet.md) |
| **Observability (Prometheus, Loki, Grafana, OTel)** | [`06-OBSERVABILITY-PROMETHEUS-LOKI-OTEL.md`](references/06-OBSERVABILITY-PROMETHEUS-LOKI-OTEL.md) | [`OWASP_Logging_Cheat_Sheet.md`](references/vendor/OWASP_Logging_Cheat_Sheet.md) |
| **3-2-1 DB Backups, DR & Incident Triage** | [`07-BACKUP-DR-AND-INCIDENT-RUNBOOKS.md`](references/07-BACKUP-DR-AND-INCIDENT-RUNBOOKS.md) | — |

---

## 2. Execution Workflow

1. **Inspect Project Stack First**:
   - Check runtime (`package.json`, `pyproject.toml`, `go.mod`, `composer.json`, `Cargo.toml`, `*.csproj`, `pom.xml`), database engine, port bindings, health check routes (`/healthz`, `/readyz`), and existing deployment files.
2. **Load Matching Reference Playbook**:
   - Read the relevant `01-*.md` to `07-*.md` file and `references/vendor/*` cheatsheet so generated files include production hardening from day one.
3. **Enforce the 7 Non-Negotiable Production Ops Rules**:
   - **Never run containers or `systemd` services as `root`**.
   - **Never bind internal database/Redis ports (`5432`, `3306`, `6379`, `27017`) to `0.0.0.0` in Docker Compose** — bind to `127.0.0.1` or keep on an `internal: true` network because Docker bypasses `ufw` iptables rules!
   - **Always set container/process memory limits & log rotation (`max-size: "20m"`, `max-file: "5"` or `logrotate`)** so runaway logs or memory leaks never take down the host VPS.
   - **Always include healthchecks (`HEALTHCHECK`, `readinessProbe`) and graceful `SIGTERM` handling (`tini` / `init: true` / `preStop`)**.
   - **Always provide an automated post-deploy smoke check and rollback path** in CI/CD scripts.
   - **Always provide a `.env.example` template** documenting every required production environment variable without committing secrets.
   - **Always pair stateful database deployments with an automated backup & restore verification script**.
