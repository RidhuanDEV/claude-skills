---
name: shadow-refactor
description: "Behavior-Preserving Codebase Evolution. Use when safely refactoring legacy modules, introducing characterization tests, branch-by-abstraction, or AST-safe incremental cleanup within existing conventions. Do NOT use for enterprise topology redesign (shadow-architect/shadow-ea), migration TCO business cases (shadow-modernize), or root-cause bug hunting (shadow-debug)."
---

# `/shadow-refactor` — Behavior-Preserving Codebase Evolution

- **Owner:** Safe, incremental structural improvements inside existing codebases without changing external contracts or local conventions.
- **Boundaries:** Topology/ADR design (`shadow-architect`), M&A legacy due diligence & 3-5 yr TCO (`shadow-modernize`), bug root-cause diagnosis (`shadow-debug`), static lint/gate (`shadow-quality`).

## 1. Preconditions, Permissions & Failure Handling
- **Default Access:** Read-only repo & precedent discovery first (`read_repository`, `run_local_tests`).
- **Missing Test Suite Rule:** A missing test suite is a **high risk**, NEVER permission for an aggressive rewrite. Capture characterization tests (`golden I/O`) before modifying production paths.
- **Convention Lock:** Never introduce a new architecture layer, library, or pattern without an explicit ADR (`§4.1`).

## 2. 8-Step Characterization & Refactor Playbook
Read [`methodologies/CHARACTERIZATION-AND-SEMANTIC-EQUIVALENCE.md`](methodologies/CHARACTERIZATION-AND-SEMANTIC-EQUIVALENCE.md) and [`playbooks/INVARIANT-LEDGER-AND-ROLLBACK.md`](playbooks/INVARIANT-LEDGER-AND-ROLLBACK.md) for complex extractions:
1. **Inventory Patterns:** Record project runtime, formatting, naming, error envelope, and test idioms.
2. **Find 1–3 Precedents:** Locate closest comparable modules in the repo; follow local module style over generic boilerplate.
3. **Declare Invariant Ledger:** Lock API shape, validation rules, error codes, DB side effects, auth checks, and hidden frontend payload dependencies.
4. **Capture Characterization Tests:** Record real observable inputs/outputs (`PASS` before refactoring).
5. **Design Minimal Reversible Step:** Use Branch-by-Abstraction, module-level Expand-Contract, or seam extraction with explicit rollback instructions.
6. **Execute Compact Diff:** Clean dead code inside modified files only; leave unrelated files untouched.
7. **Verify Semantic Equivalence:** Re-run characterization tests, adjacent consumer/API contract tests, and `shadow_gate.py`.
8. **Report Proof:** Output Invariant Ledger, diff scope, characterization exit codes, and residual risks.

## 3. Examples & Deterministic Gate
- **Happy Path:** Split 400-line controller into service helpers -> precedent matched -> 6 characterization tests green before & after -> zero API/payload changes.
- **Ambiguous Case:** Old module uses mixed CJS/ESM or conflicting validation styles -> document ambiguity in convention report and match target module's local style.
- **Failure / Must-Reject:** Refactor silently changes domain validation threshold or touches unrelated files without characterization proof -> **BLOCKED** by `refactor_characterization_gate.py`.

```powershell
python "shadow-refactor/scripts/refactor_characterization_gate.py" --self-test
python "shadow-refactor/scripts/refactor_characterization_gate.py" --verify-plan path/to/refactor-plan.json
```

## 4. Execution Approval & Intent Boundary (`L0`–`L2`)
- Refactoring inside explicitly requested modules with passing characterization tests is `L1_SAFE_VERIFICATION`. Unrequested refactoring or editing files outside requested modules is **`L2: SCOPE_EXPANSION`** and requires explicit Monarch approval (`shadow-monarch/scripts/execution_approval_gate.py`).
- Preserve existing framework conventions, package managers, and trusted internal/SSO SDKs (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`); never introduce unsolicited dependency swaps during cleanup.

## Reference Guide

| Task / Scenario | Load Reference |
| :--- | :--- |
| Choosing Seam Injection vs Branch-by-Abstraction vs Strangler, Characterization Tests & Side-Effect Ordering | [references/seam-extraction-and-characterization.md](references/seam-extraction-and-characterization.md) |

Do not load unrelated references unnecessarily.
