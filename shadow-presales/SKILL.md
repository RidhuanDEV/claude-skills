---
name: shadow-presales
description: "Use when assessing RFP/TOR/KAK tenders, Bid/No-Bid, capacity estimates, provider BoQ/RAB, or multiyear TCO and NPV. Not for post-award PRD/SRS (/shadow-discovery)."
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

## 3. Document Rendering Boundary (`SA-DOC-ENGINE-001`)

- `/shadow-presales` owns Bid/No-Bid, 3-scenario workload capacity, TCO/NPV, and Perpres 46/2025 RAB logic; NEVER duplicate `.docx`/`.pdf`/`.html` renderers.
- Route formal `PRESALES_PROPOSAL` deliverables through `shadow-doc/scripts/doc_orchestrator.py` (existing project generator first, or Global Engine via `domain_adapters.py::adapt_presales_payload`).

## Reference Guide

Load only the specific playbook or methodology matching your active pre-sales subtask:

| Task / Scenario | Load Reference |
| :--- | :--- |
| RFP/KAK Mandatory vs Desirable Decomposition, `Aanwijzing` Clarification Register & Bid/No-Bid Gate | [references/01-rfp-kak-decomposition-aanwijzing-and-bid-no-bid.md](references/01-rfp-kak-decomposition-aanwijzing-and-bid-no-bid.md) |
| 3-Scenario Service-Demand Workload Capacity Sizing (`Conservative/Expected/Stress`) & 3–5 Yr DB Growth | [references/02-three-scenario-workload-capacity-and-db-growth-sizing.md](references/02-three-scenario-workload-capacity-and-db-growth-sizing.md) |
| 3–5 Yr TCO/NPV, USD FX Shock, Commercial Provider RAB/BoQ & `Perpres 46/2025` (Non-HPS, PDN/TKDN, UMKK) | [references/03-tco-npv-commercial-rab-and-perpres-46-2025-compliance.md](references/03-tco-npv-commercial-rab-and-perpres-46-2025-compliance.md) |
| Deep Methodology & Commercial Templates | [methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md](methodologies/CAPACITY-TCO-AND-TENDER-METHODOLOGY.md) & [playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md](playbooks/ENGAGEMENT-PLAYBOOK-AND-TEMPLATES.md) |
| Deterministic Pre-Sales Sizing/TCO Engine & Specialist Eval Suite | [scripts/presales_commercial_engine.py](scripts/presales_commercial_engine.py) & [evaluations.md](evaluations.md) |

Do not load unrelated references unnecessarily.
