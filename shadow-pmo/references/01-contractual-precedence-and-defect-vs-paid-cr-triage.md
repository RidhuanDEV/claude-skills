# 01. Contractual Document Precedence & Defect vs Paid Change Request (`CR`) Triage

## 1. Purpose & Activation Conditions
Use this playbook when a client or stakeholder raises a mid-project request, scope dispute, or warranty question and you must determine objectively whether the item is an **In-Scope Defect / Warranty Obligation** or a **Paid Change Request (`PAID_CR`) Candidate**. Informal chat messages or verbal expectations cannot silently overwrite signed legal contracts—nor may an AI agent unilaterally issue binding legal or commercial verdicts without **Change Control Board (`CCB`) / Contract Counsel / Authorized PPK or Sponsor** approval.

Activate this playbook when:
- Triaging disputed items from Staging UAT (`/shadow-uat`), Warranty/Harwat (`/shadow-maintain`), or mid-sprint stakeholder escalations (`/shadow-plan`).
- Constructing an immutable **CR Decision Record** citing exact contractual clauses and schedule/effort deltas (`pmo_governance_engine.py --evaluate-cr`).
- Separating contractual PMO governance (`/shadow-pmo`) from routine Agile backlog slicing (`/shadow-plan`).

## 2. Prerequisites
- Access to the authoritative contractual baseline documents (or explicit statement of which higher-precedence documents are missing/unreviewed so confidence is capped honestly).
- Deep companion docs: [`../methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md`](../methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md) & [`../playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md`](../playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md).
- Deterministic engine: [`../scripts/pmo_governance_engine.py`](../scripts/pmo_governance_engine.py).

## 3. Technical Principles & Constraints
1. **Strict Contractual Precedence Hierarchy**:
   Always evaluate disputed scope from highest legal rank downward — NEVER compare solely against an informal SRS draft or chat history:
   1. **Master Contract / SPK & Change Clauses** (highest authority)
   2. **Signed Contractual Addendum(s)** (supersedes earlier conflicting clauses)
   3. **KAK / TOR / Statement of Work (SOW)**
   4. **Signed FSD / SRS / Baseline PRD**
   5. **Signed UAT Baseline (`Berita Acara UAT`), Warranty Clauses & Formal Meeting Minutes (`MoM`)**
   Plus **Implicit Statutory / Baseline Security Obligations** (e.g., preventing SQL injection, enforcing authentication, or honoring mandatory tax/UU PDP legal baselines already active at contract signing—a vendor cannot charge a Paid CR just to fix basic broken security!).
2. **No Unauthorized Commercial / Legal Determinations (`requires_human_approval: true`)**:
   - Classify recommendations strictly as `IN_SCOPE_DEFECT`, `WARRANTY_OBLIGATION`, `CLARIFICATION_NEEDED`, or **`PAID_CHANGE_REQUEST_CANDIDATE`** (never final binding invoice!).
   - Every commercial/paid CR candidate MUST route explicitly to **Change Control Board (CCB) / Contract Counsel / Authorized Client PPK or Sponsor** for formal approval and Addendum signing.
3. **Immutable CR Decision Record Traceability**:
   - Record `cr_id`, `requester`, `request_date`, `cited_contract_clauses`, `precedence_verdict`, `effort_delta_md`, `p80_schedule_delta_days`, `commercial_impact`, `requires_human_approval: true`, and `ccb_decision_ref`.
4. **Anti-Scope-Creep Protection During Active Sprints**:
   - Never silently absorb an unapproved out-of-scope request into an active sprint backlog ("we will squeeze it in for free") — even small unlogged favors destroy EVM baselines (`CPI`/`SPI`) and create precedent for unbounded unpaid scope.

## 4. Architecture & Implementation
### Contractual Triage Decision Matrix
| Request Nature | Contract Hierarchy Evidence | Classification | Governance Path |
| :--- | :--- | :--- | :--- |
| Behavior breaks signed `FR-*`, KAK clause, or basic security/statutory obligation | Covered in Rank 1–4 or statutory baseline | **`IN_SCOPE_DEFECT`** | Fix immediately + regression test; `0` CR fee |
| New module, new external integration, new regulatory workflow not in Contract/Addendum/KAK/SRS | Absent from Ranks 1–4 | **`PAID_CHANGE_REQUEST_CANDIDATE`** | Compute effort + `P80` schedule impact -> submit to **CCB / PPK / Counsel** (`requires_human_approval: true`) |
| Request contradicts a clause between KAK and earlier SRS | Higher rank wins (`Contract > Addendum > KAK > SRS`) | Follow higher-rank document + log `CLARIFICATION_NEEDED` if ambiguous | Escalate to CCB / Legal for written interpretation |
| Zero-cost cosmetic swap within agreed effort budget with no milestone slip | Documented under Change Clause minor-swap cap | **`ZERO_COST_CR_CANDIDATE`** | Still log in CR Register & obtain written PM/Client sign-off |

### Strict TypeScript Contractual Precedence & CR Escalation Guard
```typescript
export type ContractRank =
  | 'MASTER_CONTRACT'
  | 'SIGNED_ADDENDUM'
  | 'KAK_TOR_SOW'
  | 'SIGNED_FSD_SRS'
  | 'UAT_WARRANTY_MOM';

export type CrVerdict =
  | 'IN_SCOPE_DEFECT'
  | 'PAID_CHANGE_REQUEST_CANDIDATE'
  | 'CLARIFICATION_NEEDED';

export interface CrTriageInput {
  readonly crId: string;
  readonly violatesSignedBaseline: boolean;
  readonly violatesBasicSecurityOrStatute: boolean;
  readonly explicitlyExcludedInContract: boolean;
  readonly addsUncontractedCapability: boolean;
  readonly reviewedRanks: readonly ContractRank[];
}

export function evaluateContractualCrTriage(
  input: CrTriageInput,
): { readonly verdict: CrVerdict; readonly requiresHumanApproval: boolean; readonly note: string } {
  const checkedTopTier =
    input.reviewedRanks.includes('MASTER_CONTRACT') ||
    input.reviewedRanks.includes('KAK_TOR_SOW');

  if (!checkedTopTier) {
    return {
      verdict: 'CLARIFICATION_NEEDED',
      requiresHumanApproval: true,
      note: 'Cannot finalize CR verdict from SRS/MoM alone without inspecting Master Contract / KAK precedence.',
    };
  }
  if (input.violatesSignedBaseline || input.violatesBasicSecurityOrStatute) {
    return {
      verdict: 'IN_SCOPE_DEFECT',
      requiresHumanApproval: false,
      note: 'Deviation from signed baseline or statutory/security baseline; remediate in-scope without CR fee.',
    };
  }
  if (input.explicitlyExcludedInContract || input.addsUncontractedCapability) {
    return {
      verdict: 'PAID_CHANGE_REQUEST_CANDIDATE',
      requiresHumanApproval: true,
      note: 'Exceeds signed contractual baseline; route impact assessment to CCB / Contract Counsel / PPK for formal approval.',
    };
  }
  return {
    verdict: 'CLARIFICATION_NEEDED',
    requiresHumanApproval: true,
    note: 'Ambiguous boundary; escalate to CCB with cited clauses.',
  };
}
```

### Engine Verification Command (`pmo_governance_engine.py`)
```powershell
python "shadow-pmo/scripts/pmo_governance_engine.py" --evaluate-cr path/to/cr_request.json
```

## 5. Platform / Vendor Variations
- **Indonesian Government Contracts (`SPK` / `Perpres 46/2025` Contract Addendum)**: Note statutory ceilings on contract value increases (e.g., max `+10%` addendum cap under Indonesian public procurement law) and mandatory **PPK** authority — NEVER promise or start work on paid additions before an official signed **Addendum Kontrak** exists!
- **Private Enterprise Time-and-Materials vs Fixed-Price SOW**: On Fixed-Price SOWs, protect margin via formal CR + `P80` milestone revision; on T&M retainers, record scope shifts in CR logs anyway so burn-rate forecasts and stakeholder expectations stay transparent.

## 6. Decision Matrix & Trade-Offs
| Triage Mistake | Commercial / Delivery Risk | Prevention Control |
| :--- | :--- | :--- |
| Judging CR from SRS alone while ignoring Signed Addendum | Misses later addendum scope cuts or additions | Inspect full 5-rank hierarchy first |
| Charging a Paid CR for basic SQLi/XSS/auth bug | Reputational damage & legal breach of professional care | Always classify baseline security flaws as `IN_SCOPE_DEFECT` |
| Absorbing 5 "small favors" verbally via WhatsApp | Silent 30% schedule slip & margin erosion | Require logged `CR Decision Record` for every baseline change |

## 7. Real Production Scenario
**Context:** Midway through a fixed-price BUMN portal build, a division VP messaged the dev lead on Slack requesting *"Add live SAP S/4HANA real-time journal posting before Go-Live—it's just one extra API."* Simultaneously, QA found an authorization bug allowing operators to approve their own submissions.
**Resolution:** Checking the Contractual Hierarchy (`SPK -> KAK §3.4 -> Signed FSD`) proved SAP real-time posting was explicitly listed in KAK *Out-of-Scope Phase 2* (CSV export was Phase 1), whereas maker-checker authorization was required in `FSD §4.2`. `pmo_governance_engine.py` classified the auth bug as `IN_SCOPE_DEFECT` (fixed immediately) and the SAP request as `PAID_CHANGE_REQUEST_CANDIDATE` (`+14d P80` delta -> routed to CCB), protecting the Phase 1 Go-Live date cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG (Issuing a binding legal/commercial CR verdict from SRS text alone or absorbing unapproved scope silently):** Violates contract hierarchy and bypasses CCB/PPK authority.
  **RIGHT:** Audit across all 5 contractual ranks, classify paid candidates with `requires_human_approval: true`, and escalate formal approval to CCB / Counsel / PPK.
- **WRONG (Treating an obvious security vulnerability as a "Paid CR" because the word "SQL injection" wasn't in the KAK):** Violates implicit statutory and professional baseline duty.
  **RIGHT:** Classify baseline AppSec/auth correctness defects as `IN_SCOPE_DEFECT`.

## 9. Testing & Verification
- Run `python shadow-pmo/scripts/pmo_governance_engine.py --self-test` (`8/8` probes) and `--evaluate-cr <cr_request.json>`.
- Confirm every `PAID_CHANGE_REQUEST_CANDIDATE` record sets `requires_human_approval: true` and cites specific contract/KAK clause numbers.

## 10. Operational Considerations
- Maintain a single numbered **Scope Baseline & CR Register** synchronized across `/shadow-uat` (UAT CR triage), `/shadow-handover` (warranty scope), and `/shadow-doc` (`templates/12_CHANGE_REQUEST.md`).

## 11. Authoritative References
- **PMI PMBOK Guide (7th Ed.)** — *Integrated Change Control & Scope Baseline Governance*.
- **Perpres No. 16/2018 & Perpres No. 46/2025** — *Contract Modification / Addendum Governance (Indonesia Public Procurement)*.
- **Shadow PMO Methodology** — [`../methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md`](../methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-pmo` for routine Agile story slicing inside an already approved sprint scope — route sprint task planning to `/shadow-plan`.
- **Do NOT issue** binding legal interpretations of disputed contract clauses; escalate legal disputes to qualified Contract Counsel.
