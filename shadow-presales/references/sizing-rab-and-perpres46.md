# Infrastructure Sizing, RAB/BoQ Commercial Modeling & Perpres 46/2025 Compliance

> Use this playbook when scoring Bid/No-Bid opportunities, sizing multi-scenario infrastructure (`Conservative / Expected / Stress`), modeling 3–5 year TCO/NPV, or building Provider RAB/BoQ under **Perpres No. 46 Tahun 2025** (amending Perpres 16/2018).

## 1. Core Concepts
Pre-sales engineering separates **Provider Commercial Costing (`RAB/BoQ`)** from government **Owner Estimate (`HPS` determined strictly by PPK)** and prevents under-sized single-number server quotes:
- **Legal Authority Boundary (Perpres 46/2025):** Vendor/AI estimators produce **Provider RAB/BoQ** (`claim_official_hps_authority: false`). Setting or approving official **HPS** belongs exclusively to PPK (with Perpres 46/2025 exempting HPS for Pagu `<= Rp10 jt`, E-purchasing `<= Rp100 jt`, and integrated tenders).
- **PDN / TKDN & UMKK Compliance:** Prioritize Layer-1 Domestic Products (`TKDN + BMP >= 40%` and `TKDN >= 25%`) and mandatory **UMKK** affirmation (`>= 40%` domestic/UMKK budget allocation; direct construction procurement ceiling raised to `Rp400 jt`).

## 2. Technical Rules & Decision Matrix

| Decision Dimension | Rule / Scenario | Calculation & Gate Criteria |
| :--- | :--- | :--- |
| **3-Scenario Workload Sizing** | `Conservative (1.0x)` / `Expected (1.5x)` / `Stress (3.0x)` | Compute `vCPU = max(ha*2, ceil(sum(rps * cpu_demand) / target_util))` (`0.10..0.85` target); enforce `ha_instances >= 2` |
| **DB Storage Growth** | Raw size + Index + WAL over 3–5 yr retention | `DB_GB = (row_bytes * rows_yr * years / 1024^3) * (1 + idx_pct) * (1 + wal_pct)` + `+20%` index sensitivity check |
| **Provider RAB vs PPK HPS** | Vendor offer vs Owner ceiling | Label strictly `Estimasi RAB/BoQ Penyedia`; tag unmeasured traffic inputs as `[ASSUMPTION]` (`status != "MEASURED"`) |
| **3–5 Yr TCO & NPV** | Discounted CAPEX + OPEX (`NPV`) + FX shock | `NPV = Sum_{t=0..N} NetCost_t / (1 + r)^t`; stress-test vendor USD licenses against `+10%` FX depreciation |

## 3. Implementation Examples

### Sizing & TCO JSON Input (`scripts/presales_commercial_engine.py`)
```json
{
  "target_cpu_utilization": 0.60,
  "ha_instances": 2,
  "scenario_multipliers": { "conservative": 1.0, "expected": 1.5, "stress": 3.0 },
  "db_row_bytes": 1024,
  "rows_per_year": 2500000,
  "retention_years": 5,
  "db_index_overhead_pct": 0.35,
  "db_wal_headroom_pct": 0.30,
  "workload_classes": [
    { "name": "core-api", "rps_baseline": 40, "cpu_service_demand_sec": 0.045, "mem_mb_per_concurrent": 4.0 }
  ],
  "assumptions": [
    { "id": "ASM-01", "statement": "Peak concurrency reaches 1.5x daily mean.", "status": "ASSUMPTION" }
  ]
}
```
```powershell
python "shadow-presales/scripts/presales_commercial_engine.py" --size-capacity workload.json
python "shadow-presales/scripts/presales_commercial_engine.py" --model-tco commercial.json
```

## 4. Best Practices
- Track every unverified request-per-second, payload byte size, or cloud egress estimate in an explicit **Assumption Register** linked to customer validation sign-off during *Aanwijzing*.
- Include multi-year maintenance (`Harwat`), backup storage, cloud egress, TLS/domain renewals, and support SLAs inside OPEX — never quote only Year-1 license CAPEX.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Naming Vendor RAB "HPS" or hiding assumptions in peak-only sizing):** Submitting a table titled "Dokumen HPS Resmi" as a vendor (`HG3_UNAUTHORIZED_PPK_HPS_DETERMINATION`), or sizing 1 server instance with `100%` CPU target.
  **RIGHT:** Label offers **"Estimasi RAB/BoQ Penyedia (Non-HPS)"**, enforce `ha_instances >= 2`, `target_cpu_utilization <= 0.65`, and present Conservative/Expected/Stress scenarios.
- **WRONG (Direct-editing `.docx` commercial proposals):** Tweaking unit prices directly in Word instead of regenerating from source commercial JSON/Markdown.
  **RIGHT:** Recompute numbers via `presales_commercial_engine.py` and render formal proposals exclusively via `shadow-doc/scripts/doc_orchestrator.py`.

## 6. Production Considerations
- **TKDN / Import Risk:** Verify Katalog Elektronik / TKDN certificates upfront before locking proprietary imported middleware into a tender bill of materials.
- **Commercial Validity:** Attach quotation expiry dates, exchange-rate adjustment clauses, and PPN rate (`11%` / regulatory update) cleanly to every BoQ table.
