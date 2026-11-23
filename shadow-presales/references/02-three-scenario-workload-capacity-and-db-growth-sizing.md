# 02. Three-Scenario Workload Capacity & Multi-Year DB Growth Sizing

## 1. Purpose & Activation Conditions
Use this playbook whenever sizing compute (`vCPU`), memory (`RAM`), high-availability replica counts, network bandwidth, and 3–5 year database storage for a commercial proposal, infrastructure BoQ, or capacity review (`/shadow-presales`). Guessing *"2 servers of 8 vCPU because we have 50,000 DAU"* causes catastrophic launch-day outages or massively overpriced losing bids; this playbook grounds sizing in **queuing service demand ($D_{\text{cpu}}$)** across **3 explicit scenarios (`Conservative / Expected / Stress`)**.

Activate this playbook when:
- Calculating server/cloud infrastructure specs for an RFP, KAK, or architecture sizing exercise (`presales_commercial_engine.py --size-capacity`).
- Modeling 3–5 year PostgreSQL/MySQL storage growth including index bloat, WAL/binlog headroom, and backup retention.
- Running sensitivity sweeps when traffic metrics are `[ASSUMPTION]` rather than measured production telemetry.

## 2. Prerequisites
- Workload classification (`read`, `write`, `report`, `batch`) with explicit baseline RPS and CPU service demand (`cpu_service_demand_sec`), tagged `[EVIDENCE]` (if measured) or `[ASSUMPTION]` (logged in the Assumption Register).
- Deterministic sizing engine [`../scripts/presales_commercial_engine.py`](../scripts/presales_commercial_engine.py).

## 3. Technical Principles & Constraints
1. **Service-Demand Sizing (Never Raw `DAU` Guesses)**:
   - Convert daily/peak traffic explicitly into **requests per second (`RPS`) per workload class** (`read`, `write`, `report`, `batch`), each carrying a documented CPU service demand $D_{\text{cpu}}$ (seconds of CPU per request) and memory-per-concurrent-request profile.
   - Target CPU utilization ceiling MUST remain inside safe queuing headroom **`0.10 <= target_cpu_utilization <= 0.65`** (hard engine upper guard `0.85` — NEVER size at `95%–100%` utilization where queuing latency explodes nonlinearly!).
   - Compute required vCPU:
     $$\text{vCPU} = \max\left(\text{ha\_instances} \times 2,\; \left\lceil \frac{\sum_c (\text{RPS}_c \cdot m \cdot D_{\text{cpu},c})}{U_{\text{target}}} \right\rceil\right)$$
   - Enforce **`ha_instances >= 2`** (N+1 redundancy) for any production workload requiring `>= 99.5%` availability — zero single-point-of-failure server quotes!
2. **Mandatory 3-Scenario Output + Sensitivity Sweep**:
   - Always output **3 scenarios**:
     - **`Conservative (1.0x)`**: Baseline steady-state commitment.
     - **`Expected (1.5x)`**: Target Year-1/Year-2 production capacity (**recommended sizing anchor**).
     - **`Stress (3.0x)`**: Peak event / fiscal-deadline / viral burst envelope (drives autoscale ceiling & burst headroom).
3. **Explicit Memory & Multi-Year DB Storage Formula**:
   - **Application RAM**: `base_runtime_mb + (peak_concurrency * mem_mb_per_concurrent) + in_process_cache_mb + OS_headroom_pct`.
   - **Database Storage (`3–5` Years)**:
     $$\text{DB\_GB} = \frac{\text{row\_bytes} \times \text{rows\_per\_year} \times \text{retention\_years}}{1024^3} \times (1 + \text{idx\_pct}) \times (1 + \text{wal\_pct})$$
     Always attach a **`+20%` index-overhead sensitivity check** and separate backup/archive object storage (`3-2-1` retention) from primary SSD IOPS storage!
4. **Honest Assumption Tagging**:
   - Every unmeasured `rps_baseline`, `cpu_service_demand_sec`, `db_row_bytes`, or `db_index_overhead_pct` MUST be explicitly listed in `assumptions[]` with `status: "ASSUMPTION"` (never falsely marked `"MEASURED"`).

## 4. Architecture & Implementation
### Workload Capacity Sizing Input JSON (`presales_commercial_engine.py --size-capacity`)
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
    { "name": "core-read-api", "rps_baseline": 40, "cpu_service_demand_sec": 0.025, "mem_mb_per_concurrent": 3.0 },
    { "name": "core-write-tx", "rps_baseline": 12, "cpu_service_demand_sec": 0.065, "mem_mb_per_concurrent": 6.0 },
    { "name": "export-report", "rps_baseline": 2, "cpu_service_demand_sec": 0.350, "mem_mb_per_concurrent": 32.0 }
  ],
  "assumptions": [
    { "id": "ASM-01", "statement": "Peak concurrency reaches 1.5x daily mean during morning shift login.", "status": "ASSUMPTION" },
    { "id": "ASM-02", "statement": "PostgreSQL B-tree + GIN indexes add ~35% raw table overhead.", "status": "ASSUMPTION" }
  ]
}
```

### Strict TypeScript Capacity & Utilization Sanity Guard
```typescript
export interface WorkloadClass {
  readonly name: string;
  readonly rpsBaseline: number;
  readonly cpuServiceDemandSec: number;
}

export interface SizingGuardInput {
  readonly targetCpuUtilization: number;
  readonly haInstances: number;
  readonly multiplier: number;
  readonly classes: readonly WorkloadClass[];
}

export function computeScenarioVcpu(
  input: SizingGuardInput,
): { readonly totalVcpu: number; readonly perNodeVcpu: number } {
  if (input.targetCpuUtilization < 0.1 || input.targetCpuUtilization > 0.85) {
    throw new Error('INVALID_TARGET_UTILIZATION: must lie in [0.10, 0.85].');
  }
  if (input.haInstances < 2) {
    throw new Error('SINGLE_POINT_OF_FAILURE: production sizing requires haInstances >= 2.');
  }
  const rawCpuCores = input.classes.reduce(
    (sum, cls) => sum + cls.rpsBaseline * input.multiplier * cls.cpuServiceDemandSec,
    0,
  );
  const requiredVcpu = Math.max(
    input.haInstances * 2,
    Math.ceil(rawCpuCores / input.targetCpuUtilization),
  );
  const perNodeVcpu = Math.ceil(requiredVcpu / input.haInstances);
  return { totalVcpu: perNodeVcpu * input.haInstances, perNodeVcpu };
}
```

### Deterministic Verification Command
```powershell
python "shadow-presales/scripts/presales_commercial_engine.py" --size-capacity path/to/workload.json
```

## 5. Platform / Vendor Variations
- **On-Premise / Government Data Center (`PDN` / Fixed VM Procurement)**: Fixed hardware cannot elastically scale overnight — anchor physical procurement closer to **Expected-to-Stress headroom** with room for Year 3–5 storage growth.
- **Public Cloud (AWS / GCP / Azure / Alibaba Cloud ID)**: Size **Reserved / Committed baseline** at `Conservative/Expected` (lower OPEX via `/shadow-finops`) and configure horizontal autoscaling (`HPA`/ASG) to absorb `Stress (3.0x)` bursts without paying 24/7 for idle peak hardware.

## 6. Decision Matrix & Trade-Offs
| Sizing Parameter | Conservative Choice | Aggressive Risky Choice | Trade-Off |
| :--- | :--- | :--- | :--- |
| **`target_cpu_utilization`** | `0.50`–`0.60` (Recommended) | `0.85`–`0.95` | Higher utilization cuts BOM cost slightly but triggers tail-latency (`p99`) spikes under micro-bursts |
| **`ha_instances`** | `>= 2` across AZs/hosts | `1` single VM | Single node saves 50% infra cost but violates `99.5%+` SLA during OS patching or host failure |
| **DB Storage Horizon** | `5` years + index/WAL + `+20%` sensitivity | Raw Year-1 row count only | Ignoring indexes/WAL/retention causes emergency disk-full outages in Month 14 |

## 7. Real Production Scenario
**Context:** A vendor initially quoted a single `4 vCPU / 8 GB` VM for an agency's annual tax-reporting portal based on *"20,000 registered taxpayers"*.
**Sizing Correction:** Modeling workload classes separately (`export-report` at `0.35s` CPU & `32 MB` RAM per PDF generation during the final 3 days before deadline -> `Stress 3.0x`) via `presales_commercial_engine.py` proved the single VM would hit `100%` CPU and OOM-crash during deadline week. Sizing `2x 8 vCPU / 16 GB` app nodes behind Nginx plus an isolated worker queue + `5`-year indexed Postgres SSD storage kept the bid realistic and survived live deadline peaks with `p95 = 210ms`.

## 8. Failure Modes & Edge Cases
- **WRONG (Sizing from `DAU` alone at `100%` CPU on `1` single server without index/WAL overhead):** Produces fragile under-sized quotes that fail UAT/Pre-UAT load tests (`/shadow-perf`).
  **RIGHT:** Model workload classes (`RPS * D_cpu`), enforce `ha_instances >= 2`, `target_cpu_utilization <= 0.65`, 3 scenarios (`1.0x / 1.5x / 3.0x`), and multi-year DB growth with index/WAL headroom.
- **WRONG (Presenting guessed traffic metrics as `"MEASURED"` facts):** Exposes the vendor to warranty SLA liability if actual traffic turns out 5x higher.
  **RIGHT:** Mark unmeasured inputs strictly `status: "ASSUMPTION"` in the Assumption Register tied to contractual sizing bounds.

## 9. Testing & Verification
- Run `python shadow-presales/scripts/presales_commercial_engine.py --size-capacity <workload.json>` and verify all 3 scenarios + DB sensitivity numbers are deterministic and consistent.
- Run `--self-test` (`8/8` probes) confirming single-instance/high-utilization traps are caught cleanly.

## 10. Operational Considerations
- Hand the finalized **Expected** and **Stress** workload profiles directly to `/shadow-perf` as the Pre-UAT staging load-test baseline (`[APPROVAL-REQUIRED: L3]`) and to `/shadow-finops` for post-launch cloud cost tracking.

## 11. Authoritative References
- **Neil J. Gunther (2007)** — *Guerrilla Capacity Planning* (Service Demand Law $U = X \cdot D$ & Queuing Headroom).
- **Brendan Gregg (2020)** — *Systems Performance (2nd Ed.)* — Utilization Saturation & Headroom Modeling.
- **Shadow Presales Engine** — [`../scripts/presales_commercial_engine.py`](../scripts/presales_commercial_engine.py).

## 12. Limitations & When NOT to Use
- **Do NOT use** analytical capacity sizing to replace actual Pre-UAT staging load benchmarking on real application binaries — validate post-build via `/shadow-perf` under explicit `L3` approval.
- **Do NOT use** for runtime Kubernetes pod right-sizing on live billing exports — delegate live cloud/LLM spend optimization to `/shadow-finops`.
