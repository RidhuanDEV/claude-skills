# Cross-Skill Ownership Matrix & Anti-Overlap Contract (`W0` Governance)

> **Purpose:** Define a single accountable `primary_skill` owner, explicit `supporting_skills` / `risk_review_skills` delegation rules, and anti-overlap boundaries across all **59 Shadow Army skills** so multi-skill tasks never produce conflicting guidance or context bloat.

---

## 1. Core Ownership & Anti-Overlap Contract

| Concern / Request Domain | Accountable Primary Owner | Consult / Delegate (`Supporting` / `Risk`) | Explicit Anti-Overlap Boundary |
| :--- | :--- | :--- | :--- |
| **SSO / AuthN / AuthZ / Multi-Tenant Isolation** | `shadow-auth` | `shadow-sec`, `shadow-api`, `shadow-privacy` | Security audit (`shadow-sec`) never replaces auth implementation ownership (`shadow-auth`); preserve existing local SSO SDKs (`ridhuan-sso`). |
| **API Contracts, Transports, OpenAPI & Uploads** | `shadow-api` | `shadow-auth`, `shadow-compat`, `shadow-test` | Never redesign core business domain invariants without `shadow-domain`; never manually edit generated specs. |
| **Cross-Cutting AppSec, STRIDE, Headers & SSRF** | `shadow-sec` | `shadow-auth`, `shadow-supplychain`, `shadow-privacy` | Audits shared trust boundaries & SAST controls; delegates auth implementation to `shadow-auth`, SBOM/SLSA to `shadow-supplychain`, UU PDP to `shadow-privacy`. |
| **UU PDP (UU No. 27/2022), GDPR, DPIA & DSAR** | `shadow-privacy` | `shadow-data`, `shadow-analytics`, `shadow-sec` | Owns lawful basis, retention, DSAR receipts & 72h breach governance; escalate legal interpretation to qualified counsel. |
| **DB Engine, Schema, Indexes, RLS & Locks** | `shadow-db` | `shadow-data`, `shadow-concurrency`, `shadow-perf` | Physical DB schema, query plans & RLS != ETL/warehouse pipelines (`shadow-data`). |
| **Data Pipelines, Migrations, Backfills & Lineage** | `shadow-data` | `shadow-db`, `shadow-privacy`, `shadow-analytics` | Owns Expand-Contract migrations, backfills & retention execution; never alter statutory retention without `shadow-privacy`. |
| **Domain Invariants, Aggregates & State Machines** | `shadow-domain` | `shadow-api`, `shadow-db`, `shadow-test` | Owns business-rule invariants & FSM transitions; keep simple CRUD lightweight. |
| **Async Queues, Outbox/Inbox, Locks & DLQ** | `shadow-concurrency` | `shadow-integrate`, `shadow-db`, `shadow-email` | Owns durable queue/retry/idempotency semantics; delegates external payment/webhook adapters to `shadow-integrate`. |
| **External Payment / Webhook / Third-Party APIs** | `shadow-integrate` | `shadow-concurrency`, `shadow-sec`, `shadow-email` | Owns payment gateways (SNAP BI, Midtrans, Xendit, Stripe) & webhook verification; delegates email deliverability to `shadow-email`. |
| **LLM Runtime, Agents, Tool-Calling & MCP** | `shadow-ai-eng` | `shadow-search`, `shadow-eval`, `shadow-finops`, `shadow-sec` | `shadow-search` owns retrieval indexing/ranking; `shadow-eval` owns benchmark/red-team grading; `shadow-finops` owns token budgets. |
| **Search Retrieval, BM25, Vector ANN & ACLs** | `shadow-search` | `shadow-ai-eng`, `shadow-auth`, `shadow-db` | Owns lexical/vector ranking & pre-top-K tenant ACL filtering; agent orchestration stays in `shadow-ai-eng`. |
| **AI/RAG Evaluation, Graders & OWASP LLM Red-Team** | `shadow-eval` | `shadow-search`, `shadow-ai-eng`, `shadow-quality` | Owns evaluation methodology, held-out splits, inter-rater calibration & red-team gates; reusable across all AI skills. |
| **Telemetry, OTel Tracing, Structured Logs & SLOs** | `shadow-observe` | `shadow-perf`, `shadow-debug`, `shadow-maintain` | `shadow-debug` owns hypothesis-driven RCA; `shadow-observe` owns instrumentation, wide events & burn-rate alerting. |
| **Pre-UAT Load/Stress Testing & Profiling** | `shadow-perf` | `shadow-observe`, `shadow-db`, `shadow-ops` | **Pre-UAT / explicit perf gate ONLY** — excluded during routine feature coding; stress/load tests require explicit `L3` approval. |
| **Email Protocols, SPF/DKIM/DMARC & Deliverability** | `shadow-email` | `shadow-concurrency`, `shadow-privacy`, `shadow-sec` | Owns SMTP/MIME, DNS auth, RFC 8058 bulk-vs-OTP rules, Mailpit & Postmaster incident RCA. |
| **Technical SEO, JSON-LD, Crawl Budget & CrUX** | `shadow-seo` | `modern-web-guidance`, `shadow-illustration`, `shadow-analytics` | Delegates OG image generation to `shadow-illustration`, React/RSC perf to `modern-web-guidance`, referral tracking to `shadow-analytics`. |
| **Product Analytics, Tracking Plans, A/B & Causal** | `shadow-analytics` | `shadow-privacy`, `shadow-data`, `shadow-db` | Owns KPIs, tracking plans, SRM/CUPED/Delta Method/mSPRT & DiD/SCM; infra SRE metrics stay in `shadow-observe`. |
| **Release Rollout, Feature Flags & Rollback** | `shadow-release` | `shadow-ops`, `shadow-compat`, `shadow-supplychain` | `shadow-ops` owns infrastructure & servers; `shadow-release` owns change window, canary & rollback criteria. |
| **Requirements, Planning, UAT & Handover** | `shadow-discovery` / `shadow-plan` / `shadow-uat` / `shadow-handover` | `shadow-pmo`, `shadow-doc` | Requirements (`discovery`) != sprint tasks (`plan`) != staging acceptance (`uat`) != contractual BAST (`handover`) != AI session memory (`handoff`). |
| **Solution vs Enterprise Architecture** | `shadow-architect` vs `shadow-ea` | `shadow-modernize`, `shadow-grc` | Single-application C4/ADRs (`shadow-architect`) != multi-app TOGAF/SPBE portfolio (`shadow-ea`). |
| **Cross-Skill Routing, Budgets & Gate Policy** | `shadow-monarch` | `shadow-quality`, `shadow-eval` | Always enforces `1` accountable `primary_skill`, `<= 4` companion skills, `<= 4` reference modules, and `L0`–`L4` execution boundaries. |

---

## 2. Routing Contract Fields & Handoff Protocol

Every non-trivial task routed via `shadow-monarch/scripts/skill_router.py` produces a structured Decision Record enforcing:
- **Accountability:** Exactly one `primary_skill` owns final technical synthesis; `supporting_skills` and `risk_review_skills` contribute scoped inputs without contradicting the owner's boundaries.
- **Budget Discipline:** Total active companion skills `<= 4`; loaded `reference_modules <= 4`; trivial tasks load `0` reference modules.
- **2-Step Progressive Disclosure:** Load `SKILL.md`, inspect `## Reference Guide`, and load only the `1–2` `references/*.md` files matching the active subtask.
- **Safety & Approval Boundary:** `permission_policy.max_auto_level` bounds execution (`L0_READ_ONLY` for code review; `L1_SAFE_VERIFICATION` for local unit/offline checks; explicit Monarch approval mandatory for `L2`/`L3`/`L4`).

---

## 3. Wave Enhancement Governance (`W0`–`W7`)

1. **Repository-Native Layout:** Standardize on `SKILL.md` (with `## Reference Guide`) + `references/` + optional `scripts/` + `tests/` + `evaluations.md`. Do **not** migrate `shadow-monarch/reference/` or create empty `workflows/`/`examples/` directories.
2. **Evidence Over LOC:** Never impose arbitrary module quotas; every module must close a verified repository gap and include normal, edge, failure (`WRONG` vs `RIGHT`), and verification guidance.
3. **Honest Measurement:** Offline checks report `PASS` / `FAIL` with exact command proof; unexecuted live/LLM-cost evaluations MUST be labeled `NOT_RUN` explicitly.
