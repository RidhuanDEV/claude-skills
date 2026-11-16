# Capacity Engineering, Financial Modeling & Tender Intelligence Methodology

## 1. Requirements & Tender Intelligence (`Aanwijzing` & Bid/No-Bid)

1. **Requirement Triage**: Decompose KAK/RFP clauses into `REQ-XXX`, tagged as `MANDATORY_DISQUALIFYING` vs `SCORED_DESIRABLE`, and flag contradictions or missing NFRs (`RPO/RTO`, peak TPS, data residency, retention years) in the **Clarification Register**.
2. **Bid/No-Bid Gate**: Evaluate weighted feasibility across Strategic Fit (20%), Technical Readiness (25%), Compliance/Certification Eligibility (20%), Commercial Margin & Cashflow Risk (20%), and Delivery Capacity (15%). Recommend `BID`, `CONDITIONAL_BID`, or `NO_BID`.

---

## 2. Workload-Based Capacity Engineering (Not Naive DAU Multipliers)

For each workload class $k$ (e.g., `api_read`, `payment_write`, `export_report`, `nightly_batch`), measure or explicitly register:
- Arrival rate $\lambda_k$ (`RPS`) under `conservative`, `expected`, and `stress` multipliers.
- Measured or estimated **CPU service demand** $D_{\text{cpu},k}$ (seconds of CPU time per request) and target max CPU utilization $\rho_{\max}$ (typically `0.60`–`0.70` so queueing latency stays bounded):
  $$\text{vCPU}_{\text{raw}} = \frac{\sum_k (\lambda_k \cdot D_{\text{cpu},k})}{\rho_{\max}}, \quad \text{vCPU}_{\text{ha}} = \max(\text{min\_ha\_vcpu}, \lceil \text{vCPU}_{\text{raw}} \rceil)$$
- **Memory Profiling**:
  $$\text{RAM}_{\text{MB}} = \text{OS\_Base\_MB} + \text{App\_Runtime\_MB} + \text{Cache\_MB} + \sum_k (\lambda_k \cdot \bar{W}_k \cdot M_{\text{req},k})$$
  where $\bar{W}_k$ is average response residence time (seconds) and $M_{\text{req},k}$ is per-concurrent-request memory footprint (Little's Law $L_k = \lambda_k \bar{W}_k$).
- **Database Storage Parameterization** (never treat ratios as universal constants):
  $$S_{\text{db}} = S_{\text{raw}} \times (1 + r_{\text{index}}) \times (1 + r_{\text{wal\_headroom}})$$
  Default baseline starting points when unmeasured (must be tagged `ASSUMPTION_UNVERIFIED`): $r_{\text{index}} = 0.35$, $r_{\text{wal\_headroom}} = 0.30$ — override with actual PostgreSQL/MySQL `pg_total_relation_size` metrics whenever available.

---

## 3. Financial Engineering (3–5 Year TCO, NPV & Commercial Margin)

- **CAPEX (Year 0)**: Initial implementation Man-Months, perpetual/initial licenses, hardware/setup, independent VAPT, UAT/training.
- **Annual OPEX (Years 1..N)**: Cloud/hosting + annual escalation ($g_{\text{infra}}$), FX exposure on USD-denominated SaaS/cloud ($f_{\text{fx}}$), software renewal uplift, L2/L3 SLA support, and compliance/backup operations.
- **Net Present Value (TCO)**:
  $$\text{NPV}_{\text{TCO}} = \text{CAPEX}_0 + \sum_{t=1}^{N} \frac{\text{OPEX}_t}{(1 + r_{\text{discount}})^t}$$
- **Commercial Provider Modeling**: Track `Direct Cost` (loaded man-month cost = salary/rate * utilization factor + overhead) + `Third-Party Cost` -> `Target Margin %` -> `Pre-Tax Bid Price` -> `PPN` -> `Milestone Cashflow`.

---

## 4. Indonesian Government Procurement Rules (`Perpres No. 46 Tahun 2025`)

> Source: **Peraturan Presiden Nomor 46 Tahun 2025** (enacted 30 April 2025, Perubahan Kedua atas Perpres Nomor 16 Tahun 2018).

1. **Strict RAB vs HPS Separation**: Consultants preparing vendor bids or budget planning inputs produce a **Provider Commercial Estimate (`RAB` / `BoQ`)** backed by verifiable price evidence (`e-Katalog`, vendor quotations, SSH/SBU). **Only an authorized PPK (or PA/KPA-designated certified PPTK in Pemda APBD)** may establish and approve official **HPS (`Harga Perkiraan Sendiri`)**.
2. **PPK Competence & HPS Expanded Functions**: Perpres 46/2025 strengthens mandatory PPK typology certification and expands HPS role across bid guarantees, personnel/equipment qualification, and price-reasonableness checks.
3. **PDN / TKDN & UMKK Priority**: Enforce **Pasal 66** priority ordering for domestic products (PDN/TKDN + BMP layering) and verify minimum **40% budget allocation for domestic UMKK** products (`Pasal 65`).
