# FinOps Foundation Framework, FOCUS Specification & AI/LLM Token Economics

> **Normative Sources**:
> - **FinOps Foundation Framework**: [finops.org/framework](https://www.finops.org/framework/)
> - **FOCUS (FinOps Open Cost and Usage Specification)**: [focus.finops.org](https://focus.finops.org/)

---

## 1. FinOps Framework — Iterative Lifecycle & Domains

| Lifecycle Phase | Core Objective | Concrete Engineering Actions |
|---|---|---|
| **1. Inform** | Visibility, allocation, forecasting, unit economics | Tag all infra & LLM gateways (`service`, `env`, `team`, `feature`); ingest provider exports in **FOCUS** schema; compute cost per user/transaction |
| **2. Optimize** | Usage optimization & rate optimization | Right-size K8s pods/RDS, eliminate cross-AZ/NAT egress, enforce prefix prompt caching, cap thinking/output tokens, use Batch APIs & Spot/Commitments |
| **3. Operate** | Continuous governance, anomaly response, automation | Configure multi-threshold budget alerts (50%, 80%, 100%), auto-teardown ephemeral preview envs, run `finops_cost_auditor.py` in CI |

### 4 Core FinOps Domains
1. **Understand Usage & Cost** — Data ingestion, FOCUS normalization, allocation, cost anomaly detection.
2. **Quantify Business Value** — Unit economics (`Cost / Active User`, `Cost / Successful Task`), forecasting, budgeting.
3. **Optimize Usage & Cost** — Workload right-sizing, rate/commitment optimization (CUD/Savings Plans/Prompt Caching), architecture efficiency.
4. **Manage the FinOps Practice** — Policy guardrails, engineering/finance alignment, chargeback/showback.

---

## 2. FOCUS Specification Core Columns (Multi-Cloud & SaaS Normalization)

Use FOCUS columns instead of vendor-proprietary billing column names in BI/warehouse queries:
- **`EffectiveCost`**: Amortized cost reflecting commitments, upfront fees, and discounts (use this for unit economics).
- **`BilledCost`**: Cash-basis invoice cost after credits/discounts.
- **`ListCost`** vs **`ContractedCost`**: Benchmark against public list pricing.
- **`ChargeCategory`**: `Usage` | `Purchase` | `Tax` | `Credit` | `Adjustment`.
- **`PricingCategory`**: `On-Demand` | `Commitment` | `Dynamic`.
- **`ServiceCategory` / `ServiceName` / `SubAccountId` / `RegionId` / `ResourceId` / `Tags`**.

---

## 3. AI & LLM Token FinOps Formulas

### Billing Reality: Thinking / Reasoning Tokens
On reasoning models (e.g., Gemini 4, Claude thinking, OpenAI o-series/GPT-5), **thinking/reasoning tokens are billed at the Output Token rate** (typically 3x–5x the Input rate):

$$\text{Monthly Cost} = 30 \times N_{\text{calls/day}} \times \left[ \frac{T_{\text{in}} \cdot (1 - h) \cdot R_{\text{in}} + T_{\text{in}} \cdot h \cdot R_{\text{in}} \cdot (1 - d_{\text{cache}}) + (T_{\text{out}} + T_{\text{think}}) \cdot R_{\text{out}}}{10^6} \right]$$

Where:
- $T_{\text{in}}, T_{\text{out}}, T_{\text{think}}$: average input, visible output, and thinking tokens per call.
- $h \in [0, 1]$: prefix cache hit rate.
- $d_{\text{cache}}$: cached input discount (e.g., `0.90`–`0.95`).
- $R_{\text{in}}, R_{\text{out}}$: price per 1M input/output tokens.

### 5 High-Leverage LLM Cost Controls
1. **Keep Prefix Static**: Place unchanging system prompt + tool definitions + shared domain rules **first**; put `current_date`, `request_id`, and user context at the **end** (inside user messages).
2. **Cap `max_output_tokens` & `thinking_budget`**: Never ship unbounded completions on user-facing chat or agent loops (`OWASP LLM10:2025`).
3. **Route by Complexity**: Use frontier reasoning models for planning/architecture/hard debugging; use fast efficient models for extraction, classification, and bounded execution.
4. **Short-Circuit with Deterministic Code**: Regex/SQL/embeddings first; call an LLM only when deterministic rules cannot decide.
5. **Batch Async Workloads**: Nightly indexing, evals, and bulk summarization belong on 50%-discounted Batch APIs.

---

## 4. Kubernetes & Cloud Infrastructure Checklist

- [ ] Every `Deployment` / `StatefulSet` defines `resources.requests` and `resources.limits` (CPU & memory).
- [ ] Every HPA sets `minReplicas` and bounded `maxReplicas` + scale-down stabilization window.
- [ ] Storage buckets define lifecycle expiration/tiering for logs, temp uploads, and old snapshots.
- [ ] Ephemeral test containers/volumes (`*-test-*`) are destroyed immediately (`docker rm -f -v` / `--rm`).
- [ ] VPC Gateway Endpoints (S3/GCS/DynamoDB) used to avoid paying NAT Gateway per-GB data processing charges.
