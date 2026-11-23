# 01. RFP/KAK Decomposition, `Aanwijzing` Clarification & Bid/No-Bid Gate

## 1. Purpose & Activation Conditions
Use this playbook at the start of any commercial tender (`RFP`, `TOR`, `KAK`), enterprise proposal, or pre-sales solution bid (`/shadow-presales`). Winning a bad tender destroys company margins faster than losing a good one; this playbook enforces structured **Bid/No-Bid gating**, **Mandatory vs Desirable clause decomposition**, **Aanwijzing clarification tracking**, and **Solution Options MCDA** before engineering invests weeks drafting proposals.

Activate this playbook when:
- Analyzing an incoming `RFP` / `TOR` / `KAK` to score Bid/No-Bid feasibility, commercial viability, and disqualification traps.
- Extracting ambiguities, unstated peak traffic numbers, or contradictory SLA clauses into an **Aanwijzing Clarification Register** + **Assumption Register**.
- Comparing 2–3 architectural/commercial solution options transparently for executive review.

## 2. Prerequisites
- Source `RFP` / `TOR` / `KAK` document and explicit client sector (`GOVERNMENT_SPBE | BUMN | BANKING | FINTECH | GENERAL_ENTERPRISE`).
- Companion deep docs: [`../methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md`](../methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md) & [`../playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md`](../playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md).

## 3. Technical Principles & Constraints
1. **Mandatory (`GUGUR`) vs Desirable (`BOBOT`) Separation**:
   - In Indonesian government/BUMN tenders and enterprise RFPs, missing a single **Mandatory (`Pass/Fail / Gugur`)** requirement (e.g., ISO 27001 certification, specific TKDN/PDN threshold, SBU/KBLI classification, or mandatory on-premise residency) causes automatic administrative disqualification regardless of technical brilliance.
   - Audit EVERY Mandatory gate FIRST before writing technical narratives.
2. **Weighted Bid/No-Bid Scorecard (Zero Blind Chasing)**:
   - Evaluate 6 explicit axes (`Strategic Fit`, `Technical Capability`, `Mandatory Qualification Compliance`, `Commercial Margin & Cashflow`, `Schedule Feasibility [P80]`, `Competitive Position`) -> output `BID`, `CONDITIONAL_BID` (subject to Aanwijzing clarification or consortium partner), or `NO_BID`.
3. **Aanwijzing Clarification & Assumption Discipline**:
   - Never silently guess missing traffic peaks, third-party integration ownership, data-migration cleanliness, or cloud hosting liability inside a fixed-price bid.
   - Log every unresolved ambiguity in the **Clarification Register (`Aanwijzing`)** paired with a concrete **Fallback Assumption & Contract Exclusion** in case the buyer does not clarify before bid submission.
4. **Explicit Contract Exclusion Register**:
   - Pair every proposal with an explicit **Scope Boundary & Exclusion Register** (e.g., third-party license fees, SMS/WhatsApp OTP gateway usage, legacy data cleansing, hardware procurement) that feeds directly into `/shadow-pmo` post-award to prevent unpaid scope bleed.

## 4. Architecture & Implementation
### Strict TypeScript Bid/No-Bid Scorecard & Mandatory Disqualifier Gate
```typescript
export type BidDecision = 'BID' | 'CONDITIONAL_BID' | 'NO_BID';

export interface MandatoryGateItem {
  readonly clauseRef: string;
  readonly requirement: string;
  readonly met: boolean;
  readonly mitigationViaPartnerPossible: boolean;
}

export interface BidScorecardInput {
  readonly mandatoryGates: readonly MandatoryGateItem[];
  readonly strategicFit: number;       // 1..5
  readonly technicalCapability: number;// 1..5
  readonly commercialViability: number;// 1..5
  readonly scheduleFeasibility: number;// 1..5
  readonly competitivePosition: number;// 1..5
}

export function evaluateBidNoBid(
  input: BidScorecardInput,
): { readonly decision: BidDecision; readonly weightedScore: number; readonly disqualifiers: readonly string[] } {
  const hardDisqualifiers: string[] = [];
  const partnerMitigable: string[] = [];

  for (const gate of input.mandatoryGates) {
    if (!gate.met) {
      if (gate.mitigationViaPartnerPossible) {
        partnerMitigable.push(gate.clauseRef);
      } else {
        hardDisqualifiers.push(gate.clauseRef);
      }
    }
  }

  const weightedScore =
    input.strategicFit * 0.15 +
    input.technicalCapability * 0.25 +
    input.commercialViability * 0.25 +
    input.scheduleFeasibility * 0.20 +
    input.competitivePosition * 0.15;

  if (hardDisqualifiers.length > 0 || weightedScore < 2.8) {
    return { decision: 'NO_BID', weightedScore, disqualifiers: hardDisqualifiers };
  }
  if (partnerMitigable.length > 0 || weightedScore < 3.6) {
    return { decision: 'CONDITIONAL_BID', weightedScore, disqualifiers: partnerMitigable };
  }
  return { decision: 'BID', weightedScore, disqualifiers: [] };
}
```

### Aanwijzing Clarification & Fallback Assumption Table
| CLR-ID | KAK / RFP Clause | Ambiguity / Missing Input | Question for `Aanwijzing` | Fallback Assumption if Unanswered (`[ASSUMPTION]`) |
| :--- | :--- | :--- | :--- | :--- |
| `CLR-01` | `KAK Bab III.4` | States *"supports national traffic"* with zero concurrent user / RPS figures | What are baseline & peak concurrent users and peak RPS? | Sized at 3 scenarios (`Conservative 40 RPS`, `Expected 60 RPS`, `Stress 120 RPS`) |
| `CLR-02` | `KAK Bab IV.2` | Mentions *"integrasi dengan sistem keuangan eksisting"* with no API spec | Is an active REST/SOAP API provided by the agency, and who owns legacy adapters? | Assumes documented REST API provided by agency by Week 2; legacy DB/ERP changes excluded |
| `CLR-03` | `KAK Bab V` | Unclear whether cloud hosting is agency-owned (`PDN`) or vendor-billed | Are cloud/VM hosting costs included in vendor RAB or provided by agency? | Quoted as optional separate OPEX annex; excluded from core build price |

## 5. Platform / Vendor Variations
- **Indonesian Public Procurement (`LPSE` / `e-Katalog` / `Perpres 46/2025`)**: Check `KBLI`, `SBU`, `TKDN/PDN` minimum thresholds, and `UMKK` reservation criteria during the Mandatory Gate check BEFORE allocating solution architects.
- **Banking & BUMN Multi-Stage RFPs**: Separate **Technical Envelope (Sampul 1)** (architecture, security compliance, SLA, zero pricing!) cleanly from **Commercial Envelope (Sampul 2)** (RAB/BoQ, TCO, payment terms) so commercial numbers never leak into technical evaluation docs.

## 6. Decision Matrix & Trade-Offs
| Pre-Sales Outcome | When to Trigger | Business Benefit |
| :--- | :--- | :--- |
| **`BID`** | All mandatory gates met + weighted score `>= 3.6` | Focused proposal investment with strong win & delivery probability |
| **`CONDITIONAL_BID`** | Missing 1 partner-mitigable gate (e.g., KSO / consortium) or open Aanwijzing blockers | Forces concrete risk resolution before committing final fixed price |
| **`NO_BID`** | Unmitigable mandatory disqualifier or margin/schedule trap (`score < 2.8`) | Saves senior engineering weeks and avoids catastrophic loss-making contracts |

## 7. Real Production Scenario
**Context:** A software house received a 110-page ministry KAK with a 9-day submission deadline. Eager to win, sales started writing architecture slides immediately without checking administrative clauses.
**Catch:** Running the Mandatory Gate audit exposed `KAK §2.1`: mandatory on-premise installation in a specific certified local cloud (`PDN`), plus an unstated 5-year historical migration from an undocumented FoxPro database (`CLR-02`). Logging 6 sharp `Aanwijzing` questions forced the agency to clarify that legacy migration was Phase 2 and allowed the team to partner with a qualified local infra provider (`CONDITIONAL_BID -> BID`), winning the tender profitably with zero hidden liability.

## 8. Failure Modes & Edge Cases
- **WRONG (Bidding blindly on every RFP & absorbing undefined legacy migrations or cloud hosting inside a fixed price):** Turns a "won" tender into a multi-month financial loss.
  **RIGHT:** Gate every tender via Bid/No-Bid scorecard, log every missing metric in the Aanwijzing Clarification + Assumption Register, and attach a crisp Contract Exclusion Register.
- **WRONG (Leaking commercial pricing into Technical Envelope `Sampul 1`):** Causes instant administrative disqualification in two-envelope Indonesian tenders.
  **RIGHT:** Keep technical architecture/capacity documents strictly separate from commercial RAB/BoQ annexes.

## 9. Testing & Verification
- Verify `100%` of Mandatory KAK/RFP clauses appear in a signed Compliance Matrix (`COMPLIANT | PARTIAL_WITH_PARTNER | NON_COMPLIANT`) before drafting full solution sections.
- Cross-check every unmeasured numerical input in the proposal carries `[ASSUMPTION]` status and appears in the Assumption Register.

## 10. Operational Considerations
- Hand the finalized **Assumption Register**, **Clarification Answers (Berita Acara Aanwijzing)**, and **Contract Exclusion Register** directly to `/shadow-discovery` and `/shadow-pmo` immediately upon contract award so delivery teams inherit every commercial boundary intact.

## 11. Authoritative References
- **Perpres No. 46 Tahun 2025** (amending Perpres 16/2018 & Perpres 12/2021) — *Pengadaan Barang/Jasa Pemerintah (Aanwijzing, Kualifikasi, PDN/TKDN, UMKK)*.
- **Shadow Presales Playbooks** — [`../playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md`](../playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-presales` for post-award Paid Change Request disputes or Earned Value tracking — hand post-contract governance to `/shadow-pmo`.
- **Do NOT use** for detailed functional Gherkin SRS authoring after kickoff — route post-award requirements engineering to `/shadow-discovery`.
