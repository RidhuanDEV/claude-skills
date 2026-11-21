# Requirements Engineering, Quantified NFRs & Acceptance Contracts

> Use this playbook when eliciting requirements, authoring PRD/SRS/BRD deliverables, quantifying Non-Functional Requirements (NFRs), writing deterministic `Given/When/Then` acceptance criteria, or resolving business rule contradictions.

## 1. Core Concepts
Ambiguity left unresolved in Discovery compounds `10x` into bugs, security holes, and contractual CR disputes later:
- **Epistemic Discipline:** Distinguish verified stakeholder facts (`[EVIDENCE]`), explicit estimates (`[ASSUMPTION]`), recommended designs (`[PROPOSAL]`), and blocking ambiguities (`[NEEDS VALIDATION]`).
- **Deterministic Verifiability:** A requirement without quantified thresholds (`p95 <= 300ms`, `RPO <= 15m`) or testable `Given/When/Then` scenarios covering negative & boundary paths is untestable prose.

## 2. Technical Rules & Decision Matrix

| Discovery Artifact / Trigger | Technique to Apply | Stop / Exit Condition |
| :--- | :--- | :--- |
| Ambiguous deadline, SLA unit (calendar vs workdays), or auth rule | **Single Focused Interactive Question** | Tag `[NEEDS VALIDATION]` and ask Monarch cleanly; NEVER invent billing/auth rules |
| Non-Functional expectations (speed, scale, availability, security) | **Quantified NFR Specification Table** | Every cell specifies measurable metric + load baseline + standard (`ASVS`, `WCAG 2.2 AA`) |
| P0 / P1 Functional Features (`FR-xxx`) | **Executable Gherkin (`Given/When/Then`)** | Covers Happy Path + Negative Validation + Role Boundary + Idempotency/Race |
| Feature scope creep / future nice-to-haves | **Explicit In-Scope vs Out-of-Scope Ledger** | Protects backlog clarity and feeds `/shadow-pmo` contractual scope boundary |

## 3. Implementation Examples

### Quantified NFR Contract Table + Traceable Functional Spec
| NFR-ID | Quality Attribute | Target Metric & Load Baseline | Verification Method |
| :--- | :--- | :--- | :--- |
| `NFR-01` | Latency | API read `p95 <= 250ms`, write `p95 <= 500ms` at `150 RPS` | Pre-UAT k6 staging run (`/shadow-perf`) |
| `NFR-02` | Availability & Recovery | `99.9%` monthly uptime; DB `RPO <= 15m`, `RTO <= 60m` | Ephemeral restore drill (`/shadow-resilience`) |
| `NFR-03` | Security & Privacy | OWASP ASVS L2; UU PDP Specific PII redacted from app logs | Static + API security probes (`/shadow-sec`) |
| `NFR-04` | Accessibility & Responsive | WCAG 2.2 AA (`4.5:1` text); zero horizontal overflow `320px–1440px` | Playwright viewport & AXE check (`/shadow-browser`) |

### Deterministic Gherkin Acceptance Criteria (Happy + Boundary + Ambiguity Guard)
```gherkin
Feature: FR-012 Purchase Order Approval & SLA Clock
  Scenario: Reject self-approval (Maker-Checker Invariant)
    Given user "u-101" submitted Purchase Order "PO-900" in state "PENDING_APPROVAL"
    When user "u-101" sends POST /api/v1/purchase-orders/PO-900/approve
    Then the HTTP status is 403
    And error code is "MAKER_CHECKER_VIOLATION"
    And Purchase Order "PO-900" remains in state "PENDING_APPROVAL"

  Scenario: Clarified Approval SLA [NEEDS VALIDATION: calendar vs Indonesian working days]
    Given escalation SLA is set to 2 business days excluding SKB Bersama national holidays
    When a request remains "PENDING_APPROVAL" past T+2 working days at 17:00 WIB
    Then the reminder webhook fires once per request via inbox/outbox idempotency key
```

## 4. Best Practices
- Red-team the draft PRD before locking Stage 1: compare roles across requirements to catch conflicting rules (e.g., Role A may export CSV while another clause bans bulk PII export).
- Assign stable IDs (`FR-001`, `NFR-001`) from Day 1 so stories (`/shadow-plan`), tests (`/shadow-test`), and Staging RTM (`/shadow-uat`) trace end to end with zero renumbering.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Vague adjectives & silently guessing legal/business edges):** Writing *"The dashboard must load quickly, support filtering, and auto-cancel after 3 days"* without specifying page size, allowed filter fields, `>= 0` timezone boundary, or calendar vs working days.
  **RIGHT:** Specify exact query parameters (`?status=&from=&to=`), timezone (`Asia/Jakarta`), quantified latency target, and ask one focused clarifying question on unsettled business policies.
- **WRONG (Conflating Discovery PRD with Tender Pricing or Paid CR Triage):** Guessing government KAK prices (`HPS`) inside a product SRS or approving out-of-scope Change Requests informally.
  **RIGHT:** Route tender RAB/KAK to `/shadow-presales` and contractual Paid CRs to `/shadow-pmo`.

## 6. Production Considerations
- **Stage 1 Exit Gate:** Do not transition into `/shadow-architect` until In-Scope/Out-of-Scope boundaries, P0 Gherkin criteria, quantified NFRs, and contradiction checks are resolved cleanly.
