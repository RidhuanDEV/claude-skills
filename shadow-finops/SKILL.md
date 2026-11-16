---
name: shadow-finops
description: "Cloud, Kubernetes & AI/LLM Token FinOps. Use when analyzing or optimizing cloud, K8s, database, or LLM token costs under FinOps Framework and FOCUS, configuring prefix prompt caching, or capping thinking/output token budgets."
---

# `/shadow-finops` — Cloud, Kubernetes & AI/LLM Token FinOps Auditor

Use this skill whenever the **Monarch** invokes `/shadow-finops`, investigates cloud/database/AI cost spikes, designs multi-agent or RAG token budgets, or reviews Kubernetes/Terraform infrastructure for production efficiency.

Grounded in industry-canonical specifications documented in [`references/FINOPS-FRAMEWORK-FOCUS-AND-LLM-COST.md`](references/FINOPS-FRAMEWORK-FOCUS-AND-LLM-COST.md):
1. **FinOps Foundation Framework** (`Inform` -> `Optimize` -> `Operate` phases across 4 Domains: *Understand Usage & Cost*, *Quantify Business Value*, *Optimize Usage & Cost*, *Manage the FinOps Practice*) — `https://www.finops.org/framework/`.
2. **FOCUS (FinOps Open Cost and Usage Specification)** — `https://focus.finops.org/` unified billing schema (`BilledCost`, `EffectiveCost`, `ChargeCategory`, `PricingCategory`, `Tags`).

---

## 1. The 4-Pillar FinOps Engineering Workflow

### Pillar 1: Inform — Cost Visibility & FOCUS Normalization
- Enforce mandatory cost allocation tags/labels (`env`, `service`, `owner`, `tenant_tier`) across cloud resources, Kubernetes workloads, and LLM gateway requests.
- Normalize multi-cloud/SaaS billing datasets using **FOCUS** columns (`EffectiveCost` for amortized commitments, `BilledCost` for cash invoice, `ChargeCategory`, `PricingCategory`) and measure **Unit Economics** (e.g., cost per 1,000 API calls, cost per resolved customer ticket, cost per tenant/month).

### Pillar 2: Optimize — AI / LLM Token Economics
- **Prefix Prompt Caching**: Keep static system instructions, tool schemas, and shared knowledge bases at the **start** of the prompt. Never inject dynamic timestamps (`datetime.now()`, `Date.now()`), request IDs, or random UUIDs into the system prefix (which invalidates KV/prefix caches and destroys 75%–95% cached input discounts).
- **Output & Thinking Token Caps**: Remember that **reasoning/thinking tokens are billed as output tokens**. Enforce explicit `max_output_tokens` / `max_completion_tokens` and bounded `thinking_budget` per route (`OWASP LLM10:2025`).
- **Model Tier Routing & Batch APIs**: Route complex planning/architecture/root-cause tasks to frontier reasoning tiers, routine coding/extraction to efficient workhorse tiers, and asynchronous offline jobs (evals, bulk classification, doc indexing) to Batch APIs (typically 50% cheaper).

### Pillar 3: Optimize — Cloud, Kubernetes & Database Infrastructure
- **Kubernetes Workloads**: Require `resources.requests` and `resources.limits` + bounded Horizontal Pod Autoscaler (`minReplicas`/`maxReplicas`) on every `Deployment`/`StatefulSet`; right-size over-provisioned CPU/RAM (>50% idle P95).
- **Network & Egress**: Keep chatty app-to-DB/cache traffic inside the same region/AZ where possible; replace cross-NAT S3/GCS transfers with VPC gateway endpoints.
- **Storage & Non-Prod Hygiene**: Enforce S3/GCS lifecycle rules (transition stale logs/backups to IA/Glacier or delete expired previews), pause/auto-sleep staging DBs off-hours, and eliminate orphaned unattached EBS/PD volumes and stale container images.

### Pillar 4: Operate — Budgets, Burn Alerts & Automated Audit
Run the deterministic FinOps auditor and cost estimator:

```powershell
python "shadow-finops/scripts/finops_cost_auditor.py" --audit .
python "shadow-finops/scripts/finops_cost_auditor.py" --estimate-llm --calls-per-day 50000 --input-tokens 8000 --output-tokens 600 --thinking-tokens 1200 --cache-hit-rate 0.80 --input-rate 1.50 --output-rate 7.50 --cached-discount 0.95
python "shadow-finops/scripts/finops_cost_auditor.py" --self-test
```

Report every optimization with **Current Cost / Risk -> Concrete Change -> Estimated Monthly Savings -> Trade-off (Latency / Reliability)**.
