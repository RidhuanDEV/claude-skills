---
name: shadow-refactor
description: "Behavior-Preserving Codebase Evolution. Use when safely refactoring legacy modules, writing characterization (golden master) tests, extracting pure seams, executing branch-by-abstraction with read-only shadow parity, cleaning scoped dead code, or preserving side-effect ordering within existing conventions. Do NOT use for topology redesign (shadow-architect/shadow-ea), TCO due diligence (shadow-modernize), or bug hunting (shadow-debug)."
---

# `/shadow-refactor` — Behavior-Preserving Codebase Evolution

- **Owner:** Safe, incremental structural improvements inside existing codebases without altering external contracts, rounding/validation quirks, side-effect ordering, or local conventions.
- **Boundaries:** Single-system topology/ADR design (`shadow-architect`), enterprise portfolio architecture (`shadow-ea`), M&A legacy due diligence & 3–5 yr TCO (`shadow-modernize`), bug root-cause diagnosis (`shadow-debug`), and repo-wide static gates (`shadow-quality`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active refactoring subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-characterization-tests-and-invariant-ledgers.md](references/01-characterization-tests-and-invariant-ledgers.md) | 1–3 local precedent discovery, Invariant Ledger, Golden Master characterization tests (`PASS` pre- & post-edit) | Starting any legacy refactor or handling untested production modules |
| [02-seam-injection-and-pure-extraction.md](references/02-seam-injection-and-pure-extraction.md) | Narrow `Ports`/`Clock` seams with default production bindings, Functional Core / Imperative Shell, zero caller breakage | Splitting complex God controllers or making I/O-coupled functions unit-testable |
| [03-branch-by-abstraction-and-strangler-seams.md](references/03-branch-by-abstraction-and-strangler-seams.md) | Trunk-safe 5-step Branch-by-Abstraction, read-only shadow parity comparator, module strangler seams | Replacing high-risk hot-path algorithms cleanly across incremental PRs |
| [04-side-effect-ordering-dead-code-and-scope-discipline.md](references/04-side-effect-ordering-dead-code-and-scope-discipline.md) | `DB_COMMIT -> CACHE/EVENT` ordering invariants, scoped dead-code cleanup, AST-safe renames, `L1` vs `L2` scope bounds | Executing diffs cleanly without collateral file edits or side-effect races |
| [methodologies/CHARACTERIZATION-AND-SEMANTIC-EQUIVALENCE.md](methodologies/CHARACTERIZATION-AND-SEMANTIC-EQUIVALENCE.md) | Formal characterization & semantic equivalence methodology | Designing thorough equivalence proofs for tricky legacy code |
| [playbooks/INVARIANT-LEDGER-AND-ROLLBACK.md](playbooks/INVARIANT-LEDGER-AND-ROLLBACK.md) | Canonical Invariant Ledger & 1-command rollback template | Recording pre-refactor invariants and rollback steps |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`REF-EVAL-01..07`) | Auditing characterization discipline, zero silent contract drift, ordering, and scope bounds |

---

## 1. Preconditions, Permissions & Failure Handling
- **Default Access (`L0`/`L1`):** Read-only precedent & caller discovery first; refactoring strictly inside explicitly requested modules with passing characterization tests is **`L1_SAFE_VERIFICATION`**. Unrequested refactors or edits outside requested modules are **`L2_SCOPE_EXPANSION`** requiring explicit Monarch approval (`shadow-monarch/scripts/execution_approval_gate.py`).
- **Missing Test Suite Rule:** A missing test suite is a **high risk**, NEVER license for an aggressive rewrite. Capture passing characterization tests (`exit 0` on unmodified code) BEFORE modifying production paths.
- **Convention & SDK Lock:** Never introduce a new architecture layer without an approved ADR, and preserve existing package managers, conventions, and trusted internal/local SSO SDKs (`file:../sdk/...`). Separate intentional bug fixes into a distinct follow-up step (`/shadow-debug`) — never smuggle behavioral changes into a refactor!

---

## 2. 8-Step Characterization & Refactor Playbook
Read [`methodologies/CHARACTERIZATION-AND-SEMANTIC-EQUIVALENCE.md`](methodologies/CHARACTERIZATION-AND-SEMANTIC-EQUIVALENCE.md) and [`playbooks/INVARIANT-LEDGER-AND-ROLLBACK.md`](playbooks/INVARIANT-LEDGER-AND-ROLLBACK.md):
1. **Inventory Patterns:** Record runtime, formatting, naming, error envelope, and test idioms.
2. **Find 1–3 Precedents:** Locate closest comparable modules; match local module style over generic boilerplate.
3. **Declare Invariant Ledger:** Lock API shape, validation thresholds, rounding/error quirks, DB/event side-effect ordering, auth checks, and rollback command.
4. **Capture Characterization Tests:** Record real observable inputs/outputs (`exit 0` BEFORE refactoring).
5. **Design Minimal Reversible Step:** Use pure seam extraction, Branch-by-Abstraction, or strangler seams with default production bindings.
6. **Execute Compact Scoped Diff:** Clean newly orphaned dead code inside modified files only; zero collateral edits to unrelated files; strict typing (`0 any`, `0 as Type`, `0 !`).
7. **Verify Semantic Equivalence:** Re-run characterization tests (`exit 0` AFTER), adjacent contract tests, `refactor_characterization_gate.py`, and `shadow_gate.py`.
8. **Report Proof:** Output Invariant Ledger, diff scope, dead code removed, characterization exit codes, and residual risks.

```powershell
python "shadow-refactor/scripts/refactor_characterization_gate.py" --self-test
python "shadow-refactor/scripts/refactor_characterization_gate.py" --verify-plan path/to/refactor-plan.json
python -m unittest discover -s shadow-refactor/tests -v
```
