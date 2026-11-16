---
name: shadow-presales
description: "Enterprise IT Solutions & Commercial Pre-Sales. Use when analyzing RFP/TOR/KAK, scoring Bid/No-Bid, sizing 3-scenario workload capacity (conservative/expected/stress), modeling 3-5 yr TCO/NPV, or building Provider RAB/BoQ under Perpres 46/2025 (distinct from PPK HPS)."
---

# `/shadow-presales` — Enterprise Solution & Commercial Engineering

Use this skill whenever the **Monarch** invokes `/shadow-presales`, evaluates a tender (`KAK`/`TOR`/`RFP`), decides Bid/No-Bid, designs solution options, models infrastructure capacity, or constructs commercial `RAB`/`BoQ` and multi-year `TCO` proposals.

Integrates with the shared foundation [`shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md`](../shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md) and deep methodologies:
- [`methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md`](methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md) — Requirements decomposition, tender intelligence, workload service-demand capacity engineering, 3–5 yr TCO/NPV/sensitivity, and **Perpres Nomor 46 Tahun 2025** procurement compliance.
- [`playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md`](playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md) — Bid/No-Bid Scorecard, Solution Options MCDA, Assumption Register, Price Evidence Register, TCO Workbook, and Contract Exclusion Register.

---

## 1. Execution Contract (No Guessing, No Unauthorized Determinations)

1. **Context & Bid/No-Bid Gate**: Identify sector (`GOVERNMENT_SPBE`, `BUMN`, `BANKING`, `FINTECH`, `GENERAL_ENTERPRISE`), separate **Mandatory** vs **Desirable** tender criteria, log ambiguities in a **Clarification Register** (`Aanwijzing`), and run a **Bid/No-Bid Scorecard** before committing proposal effort.
2. **Workload Capacity Engineering (3 Scenarios)**:
   - Never derive server specs solely from raw `DAU` guesses.
   - Require explicit **CPU service demand ($D_{\text{cpu}}$)** per workload class (`read`, `write`, `report`, `batch`), utilization ceiling, process RAM profile (`base + concurrency * per_req_mem + cache + OS headroom`), and **configurable** DB index/WAL ratios (`db_index_overhead_pct`, `db_wal_headroom_pct`) logged in the **Assumption Register**.
   - Always produce **3 scenarios**: `conservative`, `expected`, and `stress`, plus sensitivity sweeps.
3. **FinOps, 3–5 Year TCO & Commercial Modeling**:
   - Model `CAPEX` + recurring multi-year `OPEX` (cloud/hosting, licensing, FX sensitivity, annual renewal uplift, VAPT/audit, support, contingency), `NPV`, and **Commercial Margin / Milestone Cashflow** (`Man-Month` utilization, overhead, PPN).
4. **Indonesian Procurement Boundary (`Perpres 46 Tahun 2025`)**:
   - Strictly separate **Provider Commercial Estimate (`RAB` / `BoQ`)** from **Official `HPS` (`Harga Perkiraan Sendiri`)** which may ONLY be established by an authorized **PPK / PA / KPA**.
   - Validate **PDN / TKDN** priority (`Pasal 66`) and minimum **40% domestic UMKK** allocation (`Perpres 46/2025`), citing price evidence sources (`e-Katalog`, vendor quotes, SSH/SBU).

---

## 2. Deterministic Calculator & Verification Gate

```powershell
python "shadow-presales/scripts/presales_commercial_engine.py" --self-test
python "shadow-presales/scripts/presales_commercial_engine.py" --size-capacity path/to/workload.json
python "shadow-presales/scripts/presales_commercial_engine.py" --model-tco path/to/commercial.json
```
