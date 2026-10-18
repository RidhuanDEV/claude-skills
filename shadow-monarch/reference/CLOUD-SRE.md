# CLOUD-SRE — Cloud Architecture, Infrastructure as Code (IaC), Kubernetes, SRE & SysAdmin

Use when designing or operating cloud infrastructure (AWS, GCP, Azure, Cloudflare), writing Terraform/OpenTofu,
Kubernetes/Helm manifests, Linux server administration (`systemd`, firewall, networking), defining SLI/SLO/Error Budgets,
or performing FinOps and Disaster Recovery planning. Pair with `DEVOPS.md` for Docker and CI/CD pipelines.

## 1. Infrastructure as Code (Terraform / OpenTofu / Pulumi) authoring rules

- **Remote state & locking**: store state in encrypted remote backend (S3 + DynamoDB lock / GCS / Terraform Cloud);
  never commit `.tfstate` or `.tfvars` containing secrets to version control.
- **Module & file layout**:
  - Standard module files: `versions.tf` (pinned provider & Terraform versions), `variables.tf` (explicit `type`,
    `description`, and `validation` blocks), `main.tf`, `outputs.tf` (`sensitive = true` where needed).
  - Separate environments (`dev`, `staging`, `prod`) via isolated state workspaces/directories passing variables into
    versioned modules — never copy-paste entire resource blocks without structure.
- **Safety & naming**:
  - Tag every billable resource with `Environment`, `Service`, `Owner`, `ManagedBy = "terraform"`.
  - Use `lifecycle { prevent_destroy = true }` on stateful production resources (RDS/CloudSQL, S3 buckets, KMS keys).
  - Always inspect `terraform plan` output for unintended replacements (`-/+ destroy and then create replacement`) before apply.

## 2. Kubernetes (K8s) & Helm authoring rules

Every production workload manifest (`Deployment`, `StatefulSet`, `CronJob`) MUST define:
- **Resource bounds**: explicit `resources.requests` (CPU/Memory for scheduling) and `resources.limits` (memory limit =
  request to prevent unpredictable OOMKill eviction spikes; avoid aggressive CPU limits that cause throttling).
- **Health probes**:
  - `startupProbe` for slow-starting apps.
  - `livenessProbe` (checks local process health only — never external DBs, or a DB blip restarts all pods).
  - `readinessProbe` (checks ability to serve traffic; removes pod from Service endpoints during failure/shutdown).
- **Graceful termination**: `terminationGracePeriodSeconds` aligned with app shutdown timeout, plus a `preStop` sleep
  (e.g., 5–10s) when load balancers/kube-proxy need time to drain in-flight connections.
- **High availability & security**:
  - `PodDisruptionBudget` (`minAvailable` or `maxUnavailable`), `topologySpreadConstraints` / anti-affinity across nodes/AZs.
  - `securityContext`: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, drop `ALL` capabilities.
  - Isolate namespaces with default-deny `NetworkPolicy` and least-privilege `Role` / `ServiceAccount` (disable `automountServiceAccountToken` when unused).
  - Pin image tags (`v1.4.2` or `@sha256:...`); never deploy `:latest`.

## 3. Linux SysAdmin, systemd & networking rules

- **`systemd` service units** (`/etc/systemd/system/<app>.service`):
  - Run under a dedicated unprivileged system user (`User=appuser`, `Group=appuser`, `WorkingDirectory=/srv/app`).
  - Restart policy: `Restart=on-failure`, `RestartSec=5s`, `StartLimitIntervalSec=60`, `StartLimitBurst=5`.
  - Hardening directives: `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `ProtectHome=true`.
- **Host & network security**:
  - SSH: disable password login (`PasswordAuthentication no`) and root login (`PermitRootLogin no`); use Ed25519 keys or Bastion/SSM/Tailscale.
  - Firewall (`ufw` / `nftables` / Security Groups): default deny incoming; allow only required ingress ports (`80/443` on load balancer; DB/Redis ports restricted to private VPC/subnet CIDRs).
  - Time sync (`chrony`/`systemd-timesyncd`), log rotation (`logrotate` or journald size limits) so disk never hits 100%.

## 4. Site Reliability Engineering (SRE): SLI, SLO & Error Budgets

- **SLI (Service Level Indicator)**: quantitative measure of user experience:
  - *Availability*: ratio of successful responses (non-5xx) to total valid requests.
  - *Latency*: proportion of requests faster than threshold (e.g., `p95 < 300ms`, `p99 < 800ms` measured at ingress/LB).
  - *Quality / Freshness*: data pipeline lag or queue processing delay (`< 5 minutes`).
- **SLO (Service Level Objective)**: target percentage over a rolling window (e.g., `99.9%` over 28 days = `40.3 minutes`
  error budget). Alert on **multi-window burn rate** (fast burn 1h/5m pages on-call; slow burn 6h/30m creates ticket).
- **Capacity & load testing**: validate peak capacity (2x–3x expected peak) before major launches; identify whether the
  first bottleneck is DB connections, CPU, memory, network bandwidth, or third-party rate limits.

## 5. Disaster Recovery (DR), Backups & FinOps

- **3-2-1 Backup & Restore**: 3 copies, 2 storage media/tiers, 1 offsite/cross-region immutable copy. Automate periodic
  restore drills into an isolated staging DB to verify **RPO** (data loss window) and **RTO** (recovery duration).
- **FinOps (Cloud Cost Control)**:
  - Set billing budgets and anomaly alerts on every cloud account.
  - Watch hidden cost multipliers: NAT Gateway / cross-AZ data egress, unattached EBS volumes/elastic IPs, high-cardinality
    custom metrics, verbose INFO/DEBUG log ingestion, and oversized idle RDS/EKS nodes.

## 6. Anti-patterns

ClickOps in production consoles without backporting to Terraform · K8s pods without resource requests or readiness probes ·
`livenessProbe` querying the database · `0.0.0.0/0` open on port `22`, `5432`, or `6379` · backups that have never been
restored · alerting on CPU 70% instead of user-facing SLO burn rate.
