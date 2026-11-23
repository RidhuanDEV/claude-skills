# 03. Quantified NFR Contracts & 5-Dimension Assumption Risk Matrices

## 1. Purpose & Activation Conditions
Use this playbook when defining Non-Functional Requirements (`NFR-*`) and surfacing product/engineering assumptions across the five risk dimensions (*Value, Usability, Viability, Feasibility, Ethics*) prior to architectural sign-off (`/shadow-architect`). Unquantified adjectives like *"fast"*, *"scalable"*, or *"highly available"* cannot be engineered, sized, or accepted at UAT; this playbook forces every quality attribute into a testable contract with a load baseline and explicit verification owner.

Activate this playbook when:
- Writing the NFR chapter of a PRD, SRS, or Technical Proposal.
- Reviewing an existing spec that lacks latency percentiles, concurrency targets, RPO/RTO bounds, security assurance levels, or privacy compliance criteria.
- Prioritizing unverified product or legacy-integration assumptions before committing sprint capacity.

## 2. Prerequisites
- Approved stakeholder actors and P0/P1 Functional Requirements from [`01-epistemic-discovery-and-ambiguity-gates.md`](01-epistemic-discovery-and-ambiguity-gates.md) and [`02-functional-requirements-and-gherkin-acceptance.md`](02-functional-requirements-and-gherkin-acceptance.md).
- Known target deployment constraints (region, compliance jurisdiction such as Indonesia UU PDP / OJK / SPBE, expected user concurrency and annual data growth).

## 3. Technical Principles & Constraints
1. **Quantified Triplet Rule**: Every `NFR-*` MUST specify three measurable elements:
   - **Metric & Threshold**: Exact quantitative boundary (`p95 <= 250ms`, `RPO <= 15m`, `4.5:1` contrast, `OWASP ASVS L2`).
   - **Operating Baseline / Workload Envelope**: Under what traffic or data volume the threshold applies (`at 150 RPS with 500k active rows`, `at 320px–1440px viewport`).
   - **Verification Method & Owning Gate**: Exact test/audit tool that measures compliance (`/shadow-perf`, `/shadow-resilience`, `/shadow-sec`, `/shadow-browser`).
2. **Five-Dimension Assumption Risk Scoring**: Map every `[ASSUMPTION]` across **Value** (will users want it?), **Usability** (can users operate it?), **Viability** (does legal/business/cost work?), **Feasibility** (can our stack/integrations support it?), and **Ethics / Privacy** (does it respect UU PDP, consent, and fairness?).
3. **Worst-Risk-First Validation**: High-impact, low-evidence assumptions MUST be validated via cheapest falsifiable experiment (codebase spike, clickable wireframe, synthetic data check, or stakeholder sign-off) BEFORE Sprint 1 engineering begins.
4. **Honest Capacity Provenance**: Label peak traffic estimates `[ASSUMPTION]` unless backed by production analytics or contractual KAK workload tables (`[EVIDENCE]`).

## 4. Architecture & Implementation
### Quantified NFR Specification Contract Table
| NFR-ID | Quality Attribute | Quantified Threshold & Operating Baseline | Standard / Normative Anchor | Verification Method & Gate |
| :--- | :--- | :--- | :--- | :--- |
| `NFR-01` | Read / Write Latency | API read `p95 <= 250ms`, write `p95 <= 500ms` at `150 RPS` (`1M` ledger rows) | ISO/IEC 25010 Performance Efficiency | Pre-UAT k6 staging run (`/shadow-perf`) |
| `NFR-02` | Availability & Disaster Recovery | `99.9%` monthly SLO (`<= 43.2m` downtime); DB `RPO <= 15m`, `RTO <= 60m` | ISO/IEC 25010 Reliability | Ephemeral backup restore drill (`/shadow-resilience`) |
| `NFR-03` | Application Security & Privacy | OWASP ASVS 5.0 Level 2; Specific PII (`NIK`, financial, health) redacted from logs; DSAR erasure SLA `<= 3x24h` | OWASP ASVS 5.0, UU No. 27/2022 (UU PDP) | Static + API authz probes (`/shadow-sec`, `/shadow-privacy`) |
| `NFR-04` | Accessibility & Responsive UI | WCAG 2.2 AA (`4.5:1` text, `3:1` controls, `44x44px` touch); zero horizontal overflow `320px–1440px` + `200%` zoom | W3C WCAG 2.2 AA | Playwright viewport + axe audit (`/shadow-browser`, `/shadow-accessibility`) |
| `NFR-05` | Auditability & Retention | Immutable append-only audit trail for auth, approvals & exports retained `>= 5 years` (`Asia/Jakarta` timestamps) | ISO/IEC 27001:2022 A.8.15 | Integration test + schema constraint check (`/shadow-test`, `/shadow-db`) |

### Typed Assumption Risk Matrix Evaluator
```typescript
export type AssumptionDimension =
  | 'VALUE'
  | 'USABILITY'
  | 'VIABILITY'
  | 'FEASIBILITY'
  | 'ETHICS_PRIVACY';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface AssumptionEntry {
  readonly id: string;
  readonly dimension: AssumptionDimension;
  readonly hypothesis: string;
  readonly impactIfFalse: RiskLevel;
  readonly evidenceConfidence: 'NONE' | 'WEAK' | 'MODERATE' | 'STRONG';
  readonly cheapestValidationTest: string;
  readonly owner: string;
}

export function requiresPreBuildValidation(entry: AssumptionEntry): boolean {
  const highImpact =
    entry.impactIfFalse === 'HIGH' || entry.impactIfFalse === 'CRITICAL';
  const lowEvidence =
    entry.evidenceConfidence === 'NONE' || entry.evidenceConfidence === 'WEAK';
  return highImpact && lowEvidence;
}
```

### 5-Dimension Assumption Risk Register Template
| ASM-ID | Dimension | Hypothesis (`[ASSUMPTION]`) | Impact if False | Evidence Confidence | Cheapest Validation Experiment | Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ASM-01` | `FEASIBILITY` | Legacy ERP SOAP endpoint tolerates `50 RPS` burst during month-end sync | `CRITICAL` | `NONE` | Check ERP vendor SLA doc + bounded staging sandbox probe (10 reqs) | Pre-Architect |
| `ASM-02` | `VIABILITY` | Bank settlement reconciliation accepts `T+1` async batch without real-time webhook | `HIGH` | `WEAK` | Finance controller confirmation in discovery sign-off | Pre-Architect |
| `ASM-03` | `ETHICS_PRIVACY` | Exporting masked `NIK` (`******1234`) satisfies regional auditor workflow | `HIGH` | `NONE` | Confirm with Compliance Lead / DPO under UU PDP Pasal 4 | Pre-Sprint 1 |
| `ASM-04` | `USABILITY` | Field operators can complete approval on `375px` mobile over unstable 3G | `MEDIUM` | `WEAK` | Clickable wireframe test + offline-draft check (`/shadow-design`) | Pre-UAT |

## 5. Platform / Vendor Variations
- **Public-Facing Consumer Web / SEO Platforms**: Add explicit Core Web Vitals NFRs (`LCP <= 2.5s`, `INP <= 200ms`, `CLS <= 0.1` at p75 CrUX / RUM) collaborating with `/shadow-seo`.
- **Financial & Regulated Indonesian Systems (OJK / BI / SPBE)**: Explicitly bind NFRs to POJK 11/2022 / PADK OJK 1/2026 cyber-resilience thresholds, UU PDP Pasal 46 `3x24` hour breach-notification readiness, and data residency rules where contractually mandated.
- **Mobile-First Field Apps**: Quantify cold-start budget (`<= 2.0s` mid-tier Android), offline queue durability, local encrypted storage (`MASVS-STORAGE`), and binary size ceilings (`/shadow-mobile`).

## 6. Decision Matrix & Trade-Offs
| Quality Dimension | Conservative Baseline | High-Rigor Regulated Target | Trade-Off to Surface to Stakeholder |
| :--- | :--- | :--- | :--- |
| **Availability & RPO/RTO** | `99.5%`, `RPO <= 24h`, `RTO <= 4h` | `99.9%+`, `RPO <= 15m`, `RTO <= 60m` | Multi-AZ standby & PITR WAL archiving add recurring infra cost (`/shadow-finops`) |
| **Security Assurance** | OWASP ASVS L1 (basic web hygiene) | OWASP ASVS L2/L3 + MFA/Passkeys + immutable audit | Higher upfront auth & verification effort, mandatory for money/PII |
| **Latency & Caching** | `p95 <= 500ms` direct DB | `p95 <= 150ms` with read cache / CDN | Adds cache invalidation complexity (`/shadow-cache`) |

## 7. Real Production Scenario
**Context:** A government citizen-portal SRS originally specified *"The system shall be fast, highly available, and secure."* Because no numeric RPO/RTO or concurrency baseline was negotiated during Discovery, engineering provisioned a single-node database with nightly dumps (`RPO = 24h`).
**Incident:** Four months after launch, a corrupted storage volume during a peak tax-filing deadline cost 14 hours of citizen submissions and failed the agency's SPBE audit.
**Lesson:** Specifying `NFR-02` (`RPO <= 15m`, `RTO <= 60m` verified via monthly `/shadow-resilience` restore drill) and surfacing `ASM-01` (multi-AZ cost trade-off) during Stage 1 Discovery would have aligned budget, architecture, and audit expectations before a single server was ordered.

## 8. Failure Modes & Edge Cases
- **WRONG (Unfalsifiable NFR adjectives):** Writing *"NFR-01: System must be super fast, 100% secure, and handle unlimited users with zero downtime."*
  **RIGHT:** Specify realistic, measurable targets (`p95 <= 300ms` at `200 RPS`, `99.9%` monthly availability, OWASP ASVS L2, `RPO <= 15m`) paired with concrete verification methods; `100%` availability and `"unlimited"` scale are physically invalid contracts.
- **WRONG (Hiding risky assumptions in appendices without owners):** Writing *"Assumes third-party identity API has 99.99% uptime and free sandbox"* with zero validation plan.
  **RIGHT:** Score `impactIfFalse = HIGH/CRITICAL`, `evidenceConfidence = NONE`, and require an explicit pre-build validation check before architecture freezes.

## 9. Testing & Verification
- **NFR Measurability Audit**: Confirm `100%` of `NFR-*` entries contain (1) numeric threshold or normative standard version, (2) load/environment baseline, and (3) explicit verification gate skill.
- **Assumption Coverage Check**: Verify all `CRITICAL`/`HIGH` assumptions with `NONE`/`WEAK` evidence have an assigned owner and validation test before exiting Stage 1 Discovery.
- **Stage 1 Exit Gate Sign-Off**: Run through all 6 Stage 1 checklist items in `shadow-discovery/SKILL.md` before transitioning to `/shadow-architect`.

## 10. Operational Considerations
- Hand verified `NFR-*` baselines directly to `/shadow-architect` (topology & capacity decisions), `/shadow-observe` (SLI/SLO & burn-rate alerts), and `/shadow-perf` (Pre-UAT staging load profiles — note that executing live load tests remains an `L3` approval-gated step, never auto-run during Discovery).
- Revisit the Assumption Risk Matrix at every Sprint Review to convert validated `[ASSUMPTION]` entries into `[EVIDENCE]` or trigger scope pivots early.

## 11. Authoritative References
- **ISO/IEC 25010:2023** — *Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model*.
- **OWASP ASVS 5.0.0** — *Application Security Verification Standard* (`https://owasp.org/www-project-application-security-verification-standard/`).
- **UU No. 27 Tahun 2022 (UU PDP)** — *Undang-Undang Pelindungan Data Pribadi* (Data Spesifik vs Umum, breach notification, DSAR).
- **W3C WCAG 2.2** — *Web Content Accessibility Guidelines 2.2 (AA)*.
- **Shadow Design PM Discovery Pack** — `pm-product-discovery/skills/identify-assumptions-new/SKILL.md` & `prioritize-assumptions/SKILL.md`.

## 12. Limitations & When NOT to Use
- **Do NOT use** to execute live load/stress benchmarks — `/shadow-discovery` only *specifies* NFR targets (`L0`); execution belongs strictly to `/shadow-perf` under explicit `L3` approval.
- **Do NOT use** for detailed cloud bill sizing / 3–5 year TCO/NPV commercial modeling — route to `/shadow-presales` or `/shadow-finops`.
- **Do NOT use** as legal advice for regulatory compliance clauses — escalate statutory interpretation to qualified legal counsel (`/shadow-privacy` / `/shadow-grc`).
