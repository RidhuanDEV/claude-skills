# 03. Cloud, Kubernetes, Database, Egress & Storage Infrastructure Optimization

## 1. Purpose & Activation Conditions
Use this playbook in the **Optimize** phase to eliminate recurring cloud, Kubernetes, database, network egress, and storage waste without degrading production SLOs or reliability. Every infrastructure optimization MUST explicitly weigh **demand distribution, startup latency, queue lag, failover headroom, committed discounts, and cost per completed operation**.

Activate this playbook when:
- Auditing Kubernetes manifests (`requests`/`limits`, HPA bounds, node sizing, Spot/Preemptible suitability) or Terraform/IaC templates.
- Investigating surprise NAT Gateway, cross-AZ data transfer, idle RDS/managed DB, or unexpiring S3/GCS storage bills.
- Enforcing non-production off-hours schedules and zero orphan volumes/containers.

## 2. Prerequisites
- FOCUS amortized spend breakdown (`01-finops-framework-focus-schema-and-unit-economics.md`) identifying the top 3–5 cost drivers.
- Production latency/utilization telemetry (`/shadow-observe`) so right-sizing decisions NEVER blindly starve peak burst headroom (`p95`/`p99` latency or OOMKill risk!).

## 3. Technical Principles & Constraints
1. **Workload-Aware Capacity vs Autoscaling (Never Default Blindly to Either)**:
   - Compare **demand distribution** (steady 24/7 vs spiky business-hours), **container startup latency**, **queue lag tolerance**, **failover headroom (`N+1`)**, and **committed-use discounts (1–3 yr CUD/Savings Plans)** before choosing fixed reserved capacity vs aggressive HPA/KEDA autoscaling.
   - Always quantify **cost per completed operation** — autoscaling that spins slow cold-starting pods up/down every 3 minutes can cost MORE and hurt `p99` latency compared to right-sized committed baseline nodes!
2. **Kubernetes Resource Hygiene (`finops_cost_auditor.py`)**:
   - Every `Deployment` and `StatefulSet` MUST define explicit `resources.requests` AND `resources.limits` (CPU/memory) sized from real p95/p99 usage (avoid setting CPU `limits` overly tight on bursty web apps without testing throttling, while ALWAYS bounding memory `limits` to prevent node-wide OOM cascades).
   - Every `HorizontalPodAutoscaler` (`HPA`) MUST enforce bounded `minReplicas` AND `maxReplicas` + `behavior.scaleDown.stabilizationWindowSeconds` (prevents runaway scale-out DDoS bills AND flapping!).
   - Reserve **Spot / Preemptible** nodes strictly for fault-tolerant, checkpointed stateless workers/batch jobs — NEVER for single-primary stateful databases!
3. **Network & Cross-AZ / NAT Egress Elimination**:
   - Keep chatty application-to-database and application-to-Redis traffic inside the same region (and topology-aware same-AZ routing where resilience allows).
   - Route S3/GCS/Object Storage and managed container registry pulls through **VPC Gateway Endpoints / Private Google Access** instead of paying per-GB NAT Gateway processing fees (`$0.045/GB` adds up silently to thousands per month!).
   - Serve static assets/media behind CDN caching (`/shadow-cache`) rather than raw origin cloud egress.
4. **Database, Storage Lifecycle & Non-Prod Hygiene**:
   - Enforce bucket lifecycle rules transitioning logs/backups (`> 30d` -> Infrequent Access / Archive; delete expired temp/preview uploads automatically).
   - Auto-pause or scale down `dev`/`staging` databases and preview environments outside business hours (saves `~65%` of non-prod runtime cost with zero prod impact).
   - Delete unattached orphaned EBS/Persistent Disks, stale container images, and ephemeral Docker test containers (`--rm --label shadow.ephemeral=true`).

## 4. Architecture & Implementation
### Hardened Cost-Bounded Kubernetes Deployment & HPA Template
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-api
  labels:
    service: order-api
    env: production
    team: checkout
spec:
  template:
    spec:
      containers:
        - name: api
          image: ghcr.io/org/order-api@sha256:PLACEHOLDER
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              memory: "1Gi"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-api
  minReplicas: 2
  maxReplicas: 12
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
```

### Strict TypeScript Infrastructure Optimization Recommendation Contract
```typescript
export interface FinOpsOptimizationItem {
  readonly resourceId: string;
  readonly currentMonthlyEffectiveUsd: number;
  readonly proposedChange: string;
  readonly estimatedMonthlySavingsUsd: number;
  readonly latencyOrReliabilityTradeoff: string;
  readonly approvalTier: 'L1' | 'L4';
}

export function auditOptimizationProposals(
  items: readonly FinOpsOptimizationItem[],
): readonly string[] {
  const issues: string[] = [];
  for (const item of items) {
    if (item.estimatedMonthlySavingsUsd > item.currentMonthlyEffectiveUsd) {
      issues.push(`${item.resourceId}: savings cannot exceed current monthly cost.`);
    }
    if (item.latencyOrReliabilityTradeoff.trim().length < 10) {
      issues.push(`${item.resourceId}: must explicitly state latency/reliability trade-off.`);
    }
  }
  return issues;
}
```

## 5. Platform / Vendor Variations
- **AWS**: Enable **S3 & DynamoDB VPC Gateway Endpoints** (`$0` data processing vs NAT Gateway), adopt **Graviton (ARM64)** instances for ~20% better price-performance on Node/Go/Python/Postgres, and layer Compute Savings Plans for steady `p20` baseline load (`60%–70%` coverage max so flexibility remains!).
- **GCP**: Enable Private Google Access + Cloud Storage Autoclass / Lifecycle policies, leverage Sustained Use & Committed Use Discounts (`CUD`), and watch BigQuery on-demand bytes-scanned queries (enforce partition filters + `maximum_bytes_billed`!).
- **Single-VPS / Mid-Size Indonesia Deployments**: Focus first on right-sizing PostgreSQL `shared_buffers` & indexes (`/shadow-db`) before blindly upgrading from 8 vCPU to 32 vCPU, and enforce strict backup/log retention pruning so disk expansion stops snowballing.

## 6. Decision Matrix & Trade-Offs
| Optimization Action | Typical Monthly Savings | Reliability Risk | Action Tier |
| :--- | :--- | :--- | :--- |
| **VPC Gateway Endpoint (S3/GCS) replacing NAT egress** | `30%–90%` of NAT bill | None (improves latency!) | Safe infra change (`L4` prod apply) |
| **Off-hours Staging DB / Preview Auto-Sleep** | `55%–68%` of non-prod spend | None to production | High-ROI quick win |
| **S3/GCS Lifecycle Expiration + Orphan Volume Cleanup** | `20%–50%` of storage spend | Verify retention/UU PDP legal hold first! | Require backup/retention check |
| **1–3 Yr Savings Plan / CUD on Steady Baseline (`65%` floor)** | `25%–45%` on compute/DB | Lock-in if architecture shrinks sharply | Commit baseline floor only, never peak |

## 7. Real Production Scenario
**Context:** A logistics SaaS platform saw AWS bills jump `+$3,200/mo` with flat user growth.
**FinOps Diagnosis:** FOCUS query grouped by `ServiceName` + `UsageType` showed two silent leaks: (1) `48 TB/mo` of worker PDF uploads routed through a NAT Gateway instead of a free S3 Gateway Endpoint (`$2,160/mo`), and (2) 19 unattached GP3 EBS volumes + unexpiring debug logs in S3 Standard (`$680/mo`) plus `maxReplicas: 80` on a staging HPA left scaled up after a load test.
**Resolution:** Adding the S3 VPC Gateway Endpoint, configuring 30-day S3 lifecycle rules, capping staging HPA `maxReplicas: 4` with off-hours sleep, and deleting verified unattached volumes cut **`$2,940/mo`** with zero latency regression.

## 8. Failure Modes & Edge Cases
- **WRONG (Cutting production DB/pod memory blindly without checking p99 peak or failover headroom, or committing 100% of peak capacity to 3-year RIs):** Triggers production `OOMKilled` outages or locks the company into paying for unused servers after optimization.
  **RIGHT:** Right-size from p95/p99 telemetry preserving `N+1` failover headroom, commit only the steady baseline floor (`60%–70%`), and state every latency/reliability trade-off explicitly.
- **WRONG (Leaving `HPA` without `maxReplicas` or shipping Kubernetes pods without `resources.requests`/`limits`):** Allows a retry loop or traffic spike to scale endlessly and burn an entire quarterly cloud budget overnight.
  **RIGHT:** Enforce `requests`, `limits`, and bounded `maxReplicas` in CI via `finops_cost_auditor.py --audit .`.

## 9. Testing & Verification
- Run `python shadow-finops/scripts/finops_cost_auditor.py --audit .` to statically flag missing K8s `requests`/`limits`, unbounded HPAs, and lifecycle gaps.
- Verify every proposed optimization explicitly reports: **Current Cost -> Concrete Change -> Estimated Monthly Savings -> Latency/Reliability Trade-off**.

## 10. Operational Considerations
- Execute cloud/Terraform cost changes (`terraform apply`, volume deletion, commitment purchases) strictly under explicit **`L4`** Monarch approval and verify zero rollback risk before touching stateful storage.

## 11. Authoritative References
- **FinOps Foundation** — *Cloud Rate Optimization, Workload Right-Sizing & Kubernetes FinOps Capabilities* (`https://www.finops.org/framework/`).
- **AWS / GCP / Azure Well-Architected Cost Optimization Pillars**.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-finops` to configure TLS, systemd, or Nginx hardening — delegate server provisioning and DevOps to `/shadow-ops`.
- **Do NOT delete** old database backups or audit logs under storage lifecycle rules before confirming statutory retention mandates (`/shadow-privacy`, `/shadow-grc`).
