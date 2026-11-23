# 03. 3–5 Year TCO/NPV Modeling, Commercial RAB/BoQ & `Perpres 46/2025` Compliance

## 1. Purpose & Activation Conditions
Use this playbook when constructing **3–5 Year Total Cost of Ownership (`TCO`) & Net Present Value (`NPV`)** models, commercial **Provider `RAB`/`BoQ`** quotes, man-month margin & cashflow schedules, and Indonesian government procurement compliance checks under **Perpres No. 46 Tahun 2025** (amending Perpres 16/2018 & Perpres 12/2021).

Activate this playbook when:
- Running `presales_commercial_engine.py --model-tco` to model `CAPEX` + multi-year `OPEX`, `NPV`, USD/IDR FX sensitivity (`+10%`), and commercial margin.
- Preparing Indonesian public-sector IT proposals requiring strict **Provider `RAB/BoQ` vs PPK `HPS`** separation, **PDN/TKDN** priority, and **UMKK** compliance.
- Auditing a commercial BoQ before submission to eliminate hidden multi-year OPEX omissions or unauthorized `HPS` wording.

## 2. Prerequisites
- Finalized 3-scenario infrastructure BOM from [`02-three-scenario-workload-capacity-and-db-growth-sizing.md`](02-three-scenario-workload-capacity-and-db-growth-sizing.md) and scope exclusions from [`01-rfp-kak-decomposition-aanwijzing-and-bid-no-bid.md`](01-rfp-kak-decomposition-aanwijzing-and-bid-no-bid.md).
- Documented price evidence sources (`e-Katalog LKPP`, written vendor quotes with validity dates, regional `SSH`/`SBU` / Inkindo billing rates) logged in the **Price Evidence Register** — ZERO fabricated unit prices!

## 3. Technical Principles & Constraints
1. **Strict Legal Authority Boundary (`Perpres 46 Tahun 2025` — Provider `RAB` != Official `HPS`)**:
   - **Official `HPS` (`Harga Perkiraan Sendiri`)** may ONLY be established and signed by an authorized government **PPK / PA / KPA**.
   - Vendor/consultant/AI commercial outputs MUST be titled strictly **"Estimasi RAB / BoQ Penyedia (Non-HPS)"** with `claim_official_hps_authority: false`. Attempting to declare official `HPS` authority triggers hard block `HG3_UNAUTHORIZED_PPK_HPS_DETERMINATION` in `presales_commercial_engine.py`!
   - Note Perpres 46/2025 HPS exemptions: HPS is not required for Pagu `<= Rp 10 juta`, E-purchasing `<= Rp 100 juta`, or integrated procurement (*pekerjaan terintegrasi*).
2. **PDN / TKDN & UMKK Statutory Compliance (`Perpres 46/2025`)**:
   - **Priority Layer 1 (`PDN` / `TKDN`, Pasal 66)**: Prioritize domestic products achieving **`TKDN + BMP >= 40%`** with **`TKDN >= 25%`** (verify active Kemenperin TKDN certificates / `e-Katalog` listings before quoting imported proprietary middleware!).
   - **Mandatory `UMKK` Allocation**: Respect the statutory minimum **`40%`** domestic micro/small/cooperative (`UMKK`) procurement affirmation (note direct construction procurement ceiling raised to `Rp 400 juta` under Perpres 46/2025).
3. **Complete 3–5 Year TCO, NPV & FX Sensitivity Modeling**:
   - Never quote Year-1 build CAPEX in isolation while hiding Years 2–5 recurring OPEX! Always include:
     - **CAPEX (Year 0)**: Discovery/Design, Engineering Build (`Man-Month` fully loaded with overhead), Hardware/Initial Licenses, Data Migration, Security Pentest/VAPT, Training (ToT).
     - **OPEX (Years 1–5)**: Cloud/Hosting + Backup/Egress, Software License Renewals (with explicit annual vendor uplift `5%–10%`), Annual VAPT/Compliance Audit, Harwat/SLA Maintenance (`15%–22%` of build), TLS/Domain/SMS/Email consumption, Contingency.
   - **Discounted Net Present Value (`NPV`)**:
     $$\text{NPV} = \sum_{t=0}^{N} \frac{\text{NetCost}_t}{(1 + r)^t}$$
   - **FX Depreciation Shock**: Stress-test all USD-denominated cloud/SaaS/license line items against **`+10%` IDR/USD depreciation** (and state explicit exchange-rate validity clauses on every quotation!).
4. **Commercial Validity, Tax (`PPN`) & Single Document Engine**:
   - State exact quotation validity window (e.g., `30` calendar days), applicable `PPN` rate per active Indonesian tax law, and milestone payment schedule aligned with cashflow (`Termin 1/2/3`).
   - Render formal `PRESALES_PROPOSAL` deliverables exclusively via `shadow-doc/scripts/doc_orchestrator.py` (`adapt_presales_payload`) — NEVER hand-edit unit prices directly inside exported `.docx` or `.xlsx` files!

## 4. Architecture & Implementation
### Strict TypeScript Perpres 46/2025 Authority & TCO NPV Guard
```typescript
export interface CommercialProposalInput {
  readonly documentTitle: string;
  readonly claimOfficialHpsAuthority: boolean;
  readonly discountRate: number; // e.g., 0.08
  readonly annualCashflowsIdr: readonly number[]; // Year 0..N
  readonly usdLinkedOpexShare: number; // 0..1
  readonly priceEvidenceRefs: readonly string[];
}

export function auditCommercialProposalCompliance(
  input: CommercialProposalInput,
): { readonly compliant: boolean; readonly npvIdr: number; readonly blockers: readonly string[] } {
  const blockers: string[] = [];

  if (
    input.claimOfficialHpsAuthority ||
    /\b(?:dokumen\s+)?hps\s+resmi\b/i.test(input.documentTitle)
  ) {
    blockers.push(
      'HG3_UNAUTHORIZED_PPK_HPS_DETERMINATION: Provider estimate must be labeled Estimasi RAB/BoQ Penyedia (Non-HPS).',
    );
  }
  if (input.priceEvidenceRefs.length === 0) {
    blockers.push('MISSING_PRICE_EVIDENCE: Attach e-Katalog, vendor quote, or SSH/SBU reference.');
  }
  if (input.annualCashflowsIdr.length < 3) {
    blockers.push('INCOMPLETE_TCO_HORIZON: Model >= 3 years of CAPEX + recurring OPEX.');
  }

  let npvIdr = 0;
  for (let t = 0; t < input.annualCashflowsIdr.length; t += 1) {
    const cf = input.annualCashflowsIdr[t] ?? 0;
    npvIdr += cf / Math.pow(1 + input.discountRate, t);
  }

  return {
    compliant: blockers.length === 0,
    npvIdr: Math.round(npvIdr),
    blockers,
  };
}
```

### Commercial TCO & Compliance Verification Command
```powershell
python "shadow-presales/scripts/presales_commercial_engine.py" --model-tco path/to/commercial.json
```

## 5. Platform / Vendor Variations
- **Indonesian Public Sector (`K/L/PD` & `BUMN`)**: Cite **e-Katalog LKPP**, **Kemenperin TKDN** certificates, and **Inkindo / SBU** man-month billing guides cleanly in the Price Evidence Register; never title vendor quotes `"HPS"`.
- **Private SaaS / Commercial B2B Bids**: Focus on `3–5` year TCO vs status-quo ROI, payback period, USD/IDR FX hedge clause for hyperscaler/LLM API costs (`/shadow-finops`), and explicit milestone payment terms protecting working capital.

## 6. Decision Matrix & Trade-Offs
| Commercial Architecture Choice | Year-0 CAPEX | Years 1–5 OPEX | TKDN / Lock-In Impact |
| :--- | :--- | :--- | :--- |
| **Open-Source Core + Local Support (e.g., Postgres, Redis, Keycloak)** | Moderate (engineering) | Low–Moderate (infra + Harwat, `$0` per-seat USD license) | High domestic service content; immune to USD seat-license hikes |
| **Proprietary Imported Enterprise Suite** | High initial license | High recurring USD annual maintenance (`+8%`/yr + FX risk) | Risks failing `PDN/TKDN` Layer-1 preference unless justified |

## 7. Real Production Scenario
**Context:** A local SI prepared a government portal bid totaling `Rp 2.4B` titled *"Dokumen HPS Resmi Pengembangan Aplikasi"*, quoting Year-1 build cost only while relying on an imported `$38,000/yr` proprietary BI license with zero FX buffer and no e-Katalog/TKDN proof.
**Pre-Submission Audit Fix:** Running `presales_commercial_engine.py --model-tco` blocked the unauthorized `"HPS"` title (`HG3`), revealed that 5-year USD license renewals + `+10%` FX shock added `Rp 3.4B` in hidden OPEX, and recommended replacing the imported BI license with an open-source + local-support stack documented cleanly as **"Estimasi RAB/BoQ Penyedia (Non-HPS)"** backed by Inkindo & e-Katalog references—clearing procurement evaluation cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG (Titling a vendor BoQ `"Dokumen HPS Resmi"` or fabricating unit prices with no quote/e-Katalog reference):** Violates Perpres 46/2025 PPK legal authority and creates audit liability.
  **RIGHT:** Label strictly **"Estimasi RAB/BoQ Penyedia (Non-HPS)"** (`claim_official_hps_authority: false`) and log verifiable evidence for every rate in the Price Evidence Register.
- **WRONG (Quoting Year-1 CAPEX only or hand-editing totals inside Word `.docx`):** Causes total mismatches between BoQ tables and executive summaries and blindsides buyers with Years 2–5 renewal shocks.
  **RIGHT:** Compute all CAPEX/OPEX/NPV/PPN math deterministically via `presales_commercial_engine.py` and render via `shadow-doc/scripts/doc_orchestrator.py`.

## 9. Testing & Verification
- Run `python shadow-presales/scripts/presales_commercial_engine.py --self-test` (`8/8` probes including `HG3_UNAUTHORIZED_PPK_HPS_DETERMINATION` recall check) and `--model-tco <commercial.json>`.
- Cross-check sum of BoQ line items + `PPN` equals exact grand total across `.docx` and `.xlsx` outputs generated via `/shadow-doc`.

## 10. Operational Considerations
- Keep commercial spreadsheets and source JSONs version-controlled per bid revision (`Rev 0 -> Post-Aanwijzing Rev 1 -> BAFO Final`) so final negotiated unit rates flow accurately into `/shadow-pmo` EVM baselines (`BAC`) if awarded.

## 11. Authoritative References
- **Perpres Nomor 46 Tahun 2025** (Second Amendment to Perpres 16/2018) — *Pengadaan Barang/Jasa Pemerintah (HPS, PDN/TKDN Pasal 66, UMKK 40%)*.
- **Inkindo / Standar Biaya Masukan (SBM) Kemenkeu** — Indonesian IT consulting billing-rate benchmarks.
- **Shadow Presales Methodology** — [`../methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md`](../methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-presales` to issue legally binding government `HPS` approvals — only an authorized PPK / PA / KPA may establish official `HPS`.
- **Do NOT use** for post-award Paid Change Request triage or EVM tracking — hand awarded contracts to `/shadow-pmo`.
