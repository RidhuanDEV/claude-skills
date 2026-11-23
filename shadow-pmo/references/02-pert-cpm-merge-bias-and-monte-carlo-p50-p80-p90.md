# 02. PERT (`O/M/P`), CPM Merge Bias & Seeded Monte Carlo (`P50/P80/P90`) Schedule Risk

## 1. Purpose & Activation Conditions
Use this playbook when building contractual project schedules, assessing schedule slip impact of Change Requests, or exposing **Merge Bias** in multi-track Work Breakdown Structures (WBS). Deterministic Gantt charts that sum average task durations routinely miss real deadlines by `20%–40%` whenever parallel near-critical tracks converge at integration or UAT milestones; **PERT + CPM + Seeded Monte Carlo** replaces wishful single-date guesses with reproducible probability bands (`P50`, `P80`, `P90`).

Activate this playbook when:
- Computing critical paths (`ES`, `EF`, `LS`, `LF`, `Total Float`) and realistic milestone commitment dates across a WBS DAG (`pmo_governance_engine.py --analyze-schedule`).
- Quantifying exact `P80` schedule impact for a Change Request (`CR`) or client approval delay.
- Checking a WBS dependency graph for hidden cycles or invalid three-point estimates.

## 2. Prerequisites
- Acyclic WBS task list with predecessors and validated three-point estimates (`optimistic <= most_likely <= pessimistic`, all `>= 0`).
- Deterministic simulator [`../scripts/pmo_governance_engine.py`](../scripts/pmo_governance_engine.py) with fixed PRNG `seed` (e.g., `seed: 42`) and `>= 1,000`–`5,000` iterations for reproducible audits.

## 3. Technical Principles & Constraints
1. **Exact Three-Point PERT Mathematics**:
   For every WBS activity $i$ satisfying $0 \le O_i \le M_i \le P_i$:
   - Expected duration: $E_i = \frac{O_i + 4M_i + P_i}{6}$
   - Standard deviation: $\sigma_i = \frac{P_i - O_i}{6}$, Variance: $\sigma_i^2 = \left(\frac{P_i - O_i}{6}\right)^2$
   Reject any task where $O > M$, $M > P$, or $O < 0$ immediately (fail closed!).
2. **Deterministic Critical Path Method (CPM) + Acyclicity Check**:
   - Run topological sort (`_topological_order`) FIRST to block cyclic WBS dependencies before computing Forward Pass (`ES`, `EF`) and Backward Pass (`LS`, `LF`).
   - Identify every critical activity where `Total Float = LS - ES == 0` AND near-critical paths (`Total Float <= 2–3` days) that threaten merge milestones.
3. **Why Deterministic CPM Alone Lies (Merge Bias)**:
   - Suppose 3 independent parallel streams (`Auth`, `Payment`, `Reporting`) each average `10` days (`O=8, M=10, P=16`) before merging into `Staging UAT`. Deterministic CPM predicts UAT starts on Day `10.67`. In reality, UAT cannot start until the **maximum (slowest)** of all 3 finishes—pushing the actual expected join date well past Day `12` (`P80` past Day `14`)!
   - Always run **Seeded Monte Carlo simulation** (`Beta-PERT` or `Triangular` sampling with fixed `seed`) across the full DAG to compute reproducible **`P50`**, **`P80`**, and **`P90`** finish dates.
4. **Three-Tier Commitment Governance**:
   - **`P50` (50% probability)**: Internal engineering sprint stretch target.
   - **`P80` (80% probability)**: **External contractual milestone commitment** to client/sponsor.
   - **`P90` (90% probability)**: Executive risk contingency / penalty-shield buffer.

## 4. Architecture & Implementation
### Acyclic WBS Schedule JSON Input (`pmo_governance_engine.py --analyze-schedule`)
```json
{
  "seed": 42,
  "monte_carlo_iterations": 2000,
  "tasks": [
    { "id": "T1", "name": "Signed API Contract & Auth Foundation", "optimistic": 2, "most_likely": 3, "pessimistic": 5, "predecessors": [] },
    { "id": "T2A", "name": "Payment Gateway Integration", "optimistic": 5, "most_likely": 8, "pessimistic": 15, "predecessors": ["T1"] },
    { "id": "T2B", "name": "ERP Ledger Sync", "optimistic": 5, "most_likely": 8, "pessimistic": 14, "predecessors": ["T1"] },
    { "id": "T3", "name": "Staging UAT & BAST Closure", "optimistic": 4, "most_likely": 6, "pessimistic": 11, "predecessors": ["T2A", "T2B"] }
  ]
}
```

### Strict TypeScript PERT Validator & Commitment Band Summary
```typescript
export interface PertTaskInput {
  readonly id: string;
  readonly optimistic: number;
  readonly mostLikely: number;
  readonly pessimistic: number;
  readonly predecessors: readonly string[];
}

export interface PertMetrics {
  readonly id: string;
  readonly expectedDays: number;
  readonly stdDevDays: number;
}

export function computePertActivityMetrics(
  task: PertTaskInput,
): PertMetrics {
  if (
    task.optimistic < 0 ||
    task.optimistic > task.mostLikely ||
    task.mostLikely > task.pessimistic
  ) {
    throw new Error(
      `INVALID_PERT_BOUNDS(${task.id}): require 0 <= O <= M <= P.`,
    );
  }
  const expectedDays =
    (task.optimistic + 4 * task.mostLikely + task.pessimistic) / 6;
  const stdDevDays = (task.pessimistic - task.optimistic) / 6;
  return { id: task.id, expectedDays, stdDevDays };
}
```

### Deterministic Schedule Execution Command
```powershell
python "shadow-pmo/scripts/pmo_governance_engine.py" --analyze-schedule path/to/wbs_dag.json
```

## 5. Platform / Vendor Variations
- **Government Fixed-Deadline Fiscal Contracts (`APBN` / `APBD` Year-End Hard Cutoff)**: Because Indonesian government fiscal years close strictly in December with liquidated damages (`denda keterlambatan 1/1000 per hari`), commit delivery milestones at **`P80`–`P85`** and model client approval latency (PPK FSD sign-off, UAT sign-off) as explicit WBS dependency nodes!
- **Multi-Vendor Integrations**: External vendor sandbox delivery and security pentest clearance typically exhibit heavy right-skew (`P >> M`); capture realistic pessimistic tails explicitly rather than symmetric `±10%` guesses.

## 6. Decision Matrix & Trade-Offs
| Schedule Forecasting Technique | Accuracy Under Parallel Merge | Reproducibility | Verdict |
| :--- | :--- | :--- | :--- |
| **Single-Point Optimistic Gantt** | Very poor (hides variance & merge bias) | Deterministic | **Anti-Pattern for Contracts** |
| **Deterministic CPM Only** | Good for linear chains; **underestimates parallel joins** | Deterministic | Useful baseline only — never sole contract commit |
| **PERT + CPM + Seeded Monte Carlo (`P50/P80/P90`)** | **High** — captures right-skew & merge bias accurately | **100% reproducible** (fixed `seed`) | **Mandatory Standard for `/shadow-pmo`** |

## 7. Real Production Scenario
**Context:** A system integrator bid a 12-week core-banking integration where 4 independent partner APIs merged into Staging UAT. Deterministic CPM calculated `54 working days` (10.8 weeks), so sales promised a fixed 11-week deadline with steep daily penalties.
**Simulation Reveal:** Running `pmo_governance_engine.py --analyze-schedule` (`seed=42`, `2,000` runs) revealed `P50 = 60.2d`, **`P80 = 67.8d` (13.6 weeks)**, and `P90 = 72.4d` solely due to 4-way merge bias before UAT. Presenting the transparent Monte Carlo curve persuaded the sponsor to stagger Partner 3 & 4 into Wave 2 while committing Phase 1 safely at `P80`.

## 8. Failure Modes & Edge Cases
- **WRONG (Committing externally to the deterministic `P50` mean or running unseeded random simulations that shift numbers on every rerun):** Guarantees ~50% probability of missing contractual deadlines and destroys audit reproducibility.
  **RIGHT:** Fix `seed` explicitly, target `P50` internally, commit contractual milestones at `P80`, and hold executive contingency to `P90`.
- **WRONG (Omitting client-owned approval dependencies from the WBS DAG):** When a client delays FSD or staging credential sign-off by 2 weeks, the vendor looks solely responsible for schedule slippage.
  **RIGHT:** Model client sign-offs (`CLIENT-FSD-APPROVAL`, `CLIENT-UAT-EXECUTION`) as explicit predecessor nodes linked to the RAID Dependency Log.

## 9. Testing & Verification
- Execute `python shadow-pmo/scripts/pmo_governance_engine.py --self-test` (`8/8` probes covering cycle detection, invalid `O/M/P` rejection, CPM floats, and seeded Monte Carlo monotonicity `P50 <= P80 <= P90`).
- Verify identical `P50`/`P80`/`P90` values across two consecutive runs with the same `seed`.

## 10. Operational Considerations
- Re-run `--analyze-schedule` whenever a critical-path task slips `> 2` days or a new CR enters CCB review, attaching the `before_p80` vs `after_p80` delta directly to the CR Decision Record.

## 11. Authoritative References
- **PMI Practice Standard for Scheduling (3rd Ed.)** — *CPM, PERT & Quantitative Schedule Risk Analysis (Monte Carlo)*.
- **David Hulett (2009)** — *Practical Schedule Risk Analysis* (Merge Bias & P80 Commitment Governance).
- **Shadow PMO Engine** — [`../scripts/pmo_governance_engine.py`](../scripts/pmo_governance_engine.py).

## 12. Limitations & When NOT to Use
- **Do NOT use** heavy Monte Carlo forecasting for 2-day tactical sprint tasks — use `/shadow-plan` vertical slicing and `sprint_dag_verifier.py` for Agile sprint mechanics.
- **Do NOT fabricate** `O/M/P` durations without documenting whether estimates come from historical velocity (`[EVIDENCE]`) or expert judgment (`[ASSUMPTION]`).
