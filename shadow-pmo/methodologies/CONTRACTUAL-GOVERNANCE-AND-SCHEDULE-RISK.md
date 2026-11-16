# Contractual Governance, Integrated Change Control & Schedule Risk Methodology

## 1. Contractual Precedence & Defensible CR Triage

Evaluate every mid-project request in strict document precedence order:
1. **Master Services Agreement / Kontrak Induk** (warranty period, defect definition, change clauses, liability caps).
2. **Signed Contract Addenda / CCO**.
3. **KAK / TOR / Statement of Work (SOW)** (deliverables, exclusion register, regulatory baseline).
4. **Approved Functional/System Specification (`FSD`/`SRS`) & Acceptance Criteria**.
5. **Statutory / Implicit Baseline Obligations** (e.g., mandatory security/privacy fixes implied by signed compliance clauses).

### Classification Outcomes (Subject to CCB / Legal Review)
- **`IN_SCOPE_DEFECT`**: Behavior violates signed acceptance criteria/FSD within active scope or warranty period.
- **`IMPLICIT_STATUTORY_OR_BASELINE_OBLIGATION`**: Required to satisfy an explicit contractual NFR or active statute already in scope (cannot be billed as a new CR unless scope expanded).
- **`SCOPE_CLARIFICATION_REVIEW`**: Ambiguous KAK/FSD clause lacking signed exclusion — escalate to CCB/Sponsor before charging or absorbing cost.
- **`PAID_CHANGE_REQUEST_CANDIDATE`**: Introduces net-new workflow, entity, external integration, or altered regulatory/business baseline beyond signed scope — requires formal **CR Impact Assessment + CCB/PPK approval** (never unilaterally declared legally binding by AI).

---

## 2. PERT + Critical Path Method (CPM) + Monte Carlo Schedule Risk

For each WBS task $i$ with predecessors $P_i$ and 3-point estimates $(O_i, M_i, P_i)$:
$$E_i = \frac{O_i + 4M_i + P_i}{6}, \qquad \sigma_i = \frac{P_i - O_i}{6}$$
1. **Forward Pass**: $ES_i = \max_{p \in P_i} EF_p$, $EF_i = ES_i + E_i$. Project expected critical duration $T_{\text{CPM}} = \max_i EF_i$.
2. **Backward Pass**: $LF_i = \min_{s \in S_i} LS_s$, $LS_i = LF_i - E_i$, $\text{Float}_i = LS_i - ES_i$. Tasks with $\text{Float}_i \approx 0$ form the **Critical Path**.
3. **Monte Carlo Simulation (Merge Bias Aware)**: Because parallel near-critical paths cause **merge bias** (true completion time exceeds deterministic CPM expectation $T_{\text{CPM}}$), sample each task from PERT-Beta/triangular distribution over $N \ge 2{,}000$ runs (with deterministic seed) and report **`P50`**, **`P80`** (recommended commitment target), and **`P90`**.

---

## 3. Earned Value Management (EVM)

- `CV = EV - AC` · `SV = EV - PV`
- `CPI = EV / AC` (`< 1.0` over budget) · `SPI = EV / PV` (`< 1.0` behind schedule)
- `EAC (typical) = BAC / CPI` · `TCPI = (BAC - EV) / (BAC - AC)`
