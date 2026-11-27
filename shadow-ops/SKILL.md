---
name: shadow-ops
description: "Use when configuring Docker, Kubernetes, Terraform, TLS, reverse proxies, VPS, or CI/CD infrastructure. Not for rollout governance (/shadow-release)."
---

# Shadow Ops (`/shadow-ops`) — Full-Spectrum DevOps, Immutable Deployments & Infrastructure Hardening

Use this skill whenever the **Monarch** asks to containerize, deploy, harden, configure, back up, or troubleshoot a server/infrastructure environment.

> [!CAUTION]
> **Read-Only Default (`L0` vs `L4`):** Inspecting logs, checking service status, running `terraform plan`, running `ops_hardening_verifier.py`, and generating Docker/Nginx/CI/CD configs are safe **`L0_READ_ONLY`** actions. Executing live deployments, restarting production services, running `terraform apply`, modifying firewall rules, or rotating production credentials is **`L4_HIGH_IMPACT`** requiring explicit 7-part confirmation from the **Monarch** (`shadow-monarch/scripts/execution_approval_gate.py`).

- **Owner:** Docker/Compose hardening, Nginx/Caddy reverse proxies & TLS, Linux VPS/`systemd`/PM2, CI/CD pipelines, Kubernetes/Helm/Terraform IaC, monitoring stack provisioning, and 3-2-1 backup infrastructure.
- **Boundaries:** SLO/burn-rate alert policy & tracing instrumentation (`shadow-observe`), SemVer 8-gate release management (`shadow-release`), restore drill RPO/RTO verification (`shadow-resilience`), and SBOM/SLSA provenance gates (`shadow-supplychain`).

## Reference Guide

Load ONLY the 1–2 playbooks or vendored OWASP/H5BP standards needed for the active infrastructure subtask:

| Module / Standard | Topic | Load When |
| :--- | :--- | :--- |
| [01-DOCKER-AND-COMPOSE-PRODUCTION.md](references/01-DOCKER-AND-COMPOSE-PRODUCTION.md) | Multi-stage Dockerfiles, non-root `USER`, `127.0.0.1`/internal networks, log rotation, `mem_limit`, `HEALTHCHECK` | Writing or hardening Dockerfiles & `docker-compose.prod.yml` |
| [02-NGINX-CADDY-REVERSE-PROXY-HARDENING.md](references/02-NGINX-CADDY-REVERSE-PROXY-HARDENING.md) | Reverse proxy headers, SSE `proxy_buffering off`, upload limits, TLS 1.2/1.3, rate limits, HSTS | Configuring Nginx/Caddy TLS, proxy timeouts, or upload/SSE routing |
| [03-LINUX-SYSADMIN-SYSTEMD-PM2-VPS.md](references/03-LINUX-SYSADMIN-SYSTEMD-PM2-VPS.md) | Non-root `systemd` units, PM2 cluster mode, `ufw`/SSH hardening, `sysctl`, swap & disk hygiene | Hardening bare-metal/VPS Linux servers or non-Docker deployments |
| [04-CICD-GITHUB-GITLAB-ZERO-DOWNTIME.md](references/04-CICD-GITHUB-GITLAB-ZERO-DOWNTIME.md) | Build-once promote-everywhere CI/CD, GitHub/GitLab pipelines, blue-green & rollback wiring | Building zero-downtime CI/CD deployment workflows |
| [05-KUBERNETES-TERRAFORM-IAC.md](references/05-KUBERNETES-TERRAFORM-IAC.md) | K8s Deployments, probes, PDB/HPA, network policies, Terraform state & read-only `plan` drift | Provisioning Kubernetes manifests, Helm charts, or Terraform IaC |
| [06-OBSERVABILITY-PROMETHEUS-LOKI-OTEL.md](references/06-OBSERVABILITY-PROMETHEUS-LOKI-OTEL.md) | Provisioning Prometheus, Loki, Tempo, OTel Collector & Grafana stack containers | Deploying or sizing the self-hosted monitoring infrastructure |
| [07-BACKUP-DR-AND-INCIDENT-RUNBOOKS.md](references/07-BACKUP-DR-AND-INCIDENT-RUNBOOKS.md) | 3-2-1-1-0 encrypted DB backup pipelines, offsite WORM sync, ops incident triage | Setting up automated database backup infrastructure & storage |
| [08-BOUNDED-EXEC-AND-WATCHDOG.md](references/08-BOUNDED-EXEC-AND-WATCHDOG.md) | Hard wall-clock timeouts, idle no-output watchdogs (`bounded_exec.py`), SSH keepalives & exact-PID tree kill | Running long/blocking scripts, SSH/Docker commands, or preventing hung jobs |
| [OWASP_Docker_Security_Cheat_Sheet.md](references/vendor/OWASP_Docker_Security_Cheat_Sheet.md) | Vendored OWASP Docker container security rules | Deep container capability, seccomp, and daemon security review |
| [OWASP_CI_CD_Security_Cheat_Sheet.md](references/vendor/OWASP_CI_CD_Security_Cheat_Sheet.md) | Vendored OWASP CI/CD pipeline hardening | Hardening runners, artifacts, and pipeline permissions |
| [OWASP_Kubernetes_Security_Cheat_Sheet.md](references/vendor/OWASP_Kubernetes_Security_Cheat_Sheet.md) | Vendored OWASP Kubernetes security rules | Hardening K8s RBAC, Pod Security Standards, and secrets |
| [OWASP_Logging_Cheat_Sheet.md](references/vendor/OWASP_Logging_Cheat_Sheet.md) | Vendored OWASP operational logging hygiene | Securing log shippers, storage, and PII scrubbing at infra layer |
| [OWASP_Secrets_Management_Cheat_Sheet.md](references/vendor/OWASP_Secrets_Management_Cheat_Sheet.md) | Vendored OWASP secrets lifecycle & rotation | Designing secret managers and zero-downtime dual-key rotation |
| Vendored H5BP Nginx Configs | [H5BP_nginx_main.conf](references/vendor/H5BP_nginx_main.conf), [H5BP_nginx_ssl_engine.conf](references/vendor/H5BP_nginx_ssl_engine.conf), [H5BP_nginx_compression.conf](references/vendor/H5BP_nginx_compression.conf) | Referencing battle-tested H5BP Nginx TLS & compression directives |
| [LICENSES.md](references/vendor/LICENSES.md) | Upstream licenses for the vendored files (OWASP cheat sheets: CC BY-SA 4.0; H5BP: MIT) and the `VENDOR.json` hash lock | Before copying, adapting or redistributing any vendored text |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`OPS-EVAL-01..08`) | Auditing Docker ufw traps, shared-hosting fit, SDK portability, and `L4` gates |

---

## 1. Enhanced Production Operations Doctrine

1. **Immutable Deployments & Release Provenance:** Build once, tag with exact Git SHA / SemVer (`v1.2.0-sha26acae3`) + OCI `@sha256:` digest, and promote that exact artifact from Staging to Production (`/shadow-release`). Never hot-edit (`vim`/`nano`) inside running production containers.
2. **Environment Parity & Realistic Target Fit:** Compare application-visible capabilities across dev, staging, and production (DB collation, proxy headers, TLS, connection limits, shared-hosting vs VPS vs K8s limits). Record owner, affected workflow, and target-specific smoke checks for each divergence (`test_ops_profiles_and_plan.py`).
3. **7 Non-Negotiable Production Hardening Rules:**
   - Never run containers or `systemd` services as `root`.
   - Never bind internal DB/Redis ports (`5432`, `3306`, `6379`, `27017`) to `0.0.0.0` in Docker Compose (Docker bypasses `ufw`!) — bind to `127.0.0.1` or keep on an `internal: true` network.
   - Always set memory limits (`mem_limit` / `resources.limits.memory`) and log rotation (`max-size: "20m"`, `max-file: "5"`).
   - Always configure healthchecks (`HEALTHCHECK`, `readinessProbe`) and graceful `SIGTERM` (`init: true` / `tini` / `preStop`).
   - Always provide automated post-deploy smoke checks and 1-command rollback (`/shadow-release`).
   - Pair monitoring stacks with actionable SLO alerts (`/shadow-observe`) and backup scripts with automated restore drills (`/shadow-resilience`).
   - Detect IaC drift with read-only `plan` before `apply`, rotate secrets via dual-key overlap windows, and enforce `/shadow-supplychain` pinned image/action digests.
4. **Minimal Infrastructure & Local SDK Portability:** Do not introduce unrequested Docker, Redis, Kafka, or microservices; when containerizing projects using local internal SDKs (e.g. `file:../sdk/sso-client`), preserve the local SDK via workspace build context and document portability caveats explicitly instead of substituting an unverified registry package.

---

## 2. Deterministic Hardening Verification

```powershell
python shadow-ops/scripts/ops_hardening_verifier.py --self-test
python shadow-ops/scripts/ops_hardening_verifier.py --check-compose docker-compose.prod.yml --check-dockerfile Dockerfile
python -m unittest discover -s shadow-ops/tests -v
```
