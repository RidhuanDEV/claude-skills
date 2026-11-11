# CROSS-MODEL PARITY — Multi-Agent Frontier Discipline (`Claude Code`, `Codex`, `Gemini CLI`, `Antigravity`)

Use this guide when working across multiple AI coding agents or switching models mid-project so every agent produces code at the same engineering bar, with the same Shadow Army persona, verification rigor, and conventions.

---

## 1. Single Source of Truth & Version Stamp

All global instruction files are generated from `shadow-monarch/GLOBAL.md` by `install.ps1` (Windows) and `install.sh` (macOS/Linux) between `<!-- BEGIN shadow-monarch -->` and `<!-- END shadow-monarch -->` markers:

| Agent / Runtime | Global Instruction File | Skill Directory |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | `~/.claude/skills/` |
| OpenAI Codex | `~/.codex/AGENTS.md` | `~/.codex/skills/` & `~/.agents/skills/` |
| Gemini CLI | `~/.gemini/GEMINI.md` | `~/.gemini/skills/` |
| Antigravity | `~/.gemini/GEMINI.md` + IDE User Rules | `~/.gemini/config/skills/` |

- Every `GLOBAL.md` carries a **Doctrine Version Stamp** (e.g. `shadow-monarch v2026.11.11`).
- Never hand-edit the generated block in `CLAUDE.md`, `AGENTS.md`, or `GEMINI.md`; edit `shadow-monarch/GLOBAL.md` and run `install.ps1` / `install.sh`.

---

## 2. Mandatory Pre-Code Reasoning Checkpoint (Externalized Thinking)

Frontier models often reason about blast radius and edge cases internally; smaller or faster models skip those steps unless forced to write them down. Before editing code on any non-trivial task, every agent must write a compact **4-line Pre-Code Checkpoint**:

1. **Blast Radius**: which call paths execute the changed code and what share of traffic reaches it (e.g. *"every chat turn with history"*, *"isolated admin export endpoint"*).
2. **Closest Existing Pattern**: exact file/symbol in the repo being mirrored (`path/to/file.ext:line`) so conventions are preserved.
3. **Falsification Plan**: precision probes (inputs that must NOT match/trigger) and recall probes (inputs that MUST match/trigger) to run after editing.
4. **Target Readiness Level**: `PLANNED | IMPLEMENTED | VERIFIED-LOCAL | REVIEWED | READY-TO-MERGE`.

---

## 3. Deterministic Quality Gate (`shadow_gate.py`)

Model judgment varies across providers; a deterministic script returns the exact same verdict in Claude, Codex, Gemini, and Antigravity.

Before claiming `VERIFIED-LOCAL` or `READY-TO-MERGE`, run:

```powershell
python "shadow-quality/scripts/shadow_gate.py" --repo . --check-docker-leaks
```

`shadow_gate.py` enforces five model-independent checks:
1. **`STRICT_TYPING_VIOLATION`**: scans modified `.ts`/`.tsx` files for forbidden `any`, `as Type` casts, `@ts-ignore`, and `@ts-expect-error`.
2. **`SECRET_LEAK_DETECTED`**: scans modified files for hardcoded private keys, AWS/GCP/API tokens, and credentials.
3. **`UNPROBED_HEURISTIC_CHANGE`**: detects added/modified regexes (`re.compile`, `RegExp`, `/.../`) or heuristic predicates and checks whether test files were updated or probes were executed.
4. **`CONVENTION_AND_ARCH_DRIFT`**: runs `codebase_intelligence.py audit-drift` on modified files (`UNEXPECTED_ARCHITECTURAL_LAYER`, `MODULE_SYSTEM_DRIFT`, `TYPESCRIPT_IN_JS_PROJECT`, `DIRECT_DB_ACCESS_IN_CONTROLLER`, `INCONSISTENT_NAMING`, `UNSOLICITED_STATE_STORE`, `UNSOLICITED_ORM_HTTP_CLIENT`, `SECURITY_EXCEPTION_SQL_INJECTION`).
5. **`DOCKER_TEST_MISSING_CLEANUP` & `DOCKER_EPHEMERAL_CONTAINER_LEAK`**: flags test/migration/drill scripts that run `docker run` without `--rm` + `docker rm -f -v`, `docker compose up` without `down -v --rmi local --remove-orphans`, or `docker build -t` without image removal, and inspects the local Docker daemon (`--check-docker-leaks` / `--cleanup-docker-leaks`) so zero `*-test-*` or `*-migration-verification*` containers or temporary images are left behind.

Optional Git pre-commit hook installation for any repository:
```powershell
python "shadow-quality/scripts/shadow_gate.py" --repo . --install-hook
```

---

## 4. Cross-Model Adversarial Review Protocol

A single model reviewing its own code shares the same blind spots that produced the bug (confirmation bias). When a change touches a **shared hot path**, **security/auth/money flow**, or **natural-language heuristic**:

1. **Implementer Agent (Model A)** saves its work with `/handoff`:
   - `sessionLabel: "impl"`
   - `readinessLevel: "VERIFIED-LOCAL"`
   - `untestedSurfaces`: explicit list of surfaces not yet tested
   - `claimEvidenceMap`: what each test/probe actually measured
2. **Adversarial Reviewer Agent (Model B — ideally a different model family)** loads the repo, inspects `untestedSurfaces`, runs precision & recall probes to break the change, and saves its findings with `/handoff`:
   - `sessionLabel: "review"`
   - `readinessLevel: "REVIEWED"` (only if all findings are resolved) or `"VERIFIED-LOCAL"` (if defects remain)
3. **Consolidation**: run `/handoff merge` (`merge_handoffs` with `sessionLabels: ["impl", "review"]`) so the continuing agent receives both snapshots, the lowest readiness level, and the union of untested surfaces.

---

## 5. Task-to-Model Tier Routing

Route tasks according to where reasoning errors are most expensive:

| SDLC / Engineering Task | Recommended Model Tier | Why |
|---|---|---|
| Discovery, Architecture, ADRs (`/shadow-discovery`, `/shadow-architect`) | **Frontier Reasoning Tier** | Wrong boundaries or missing NFRs corrupt every downstream file |
| Root-Cause Debugging & Security Audit (`/shadow-sec`, incident RCA) | **Frontier Reasoning Tier** | Requires multi-hop hypothesis elimination and adversarial thinking |
| Independent Adversarial Code Review (`REVIEWED` gate) | **Different Model Family (Frontier/High)** | Avoids shared confirmation bias with the implementer model |
| Bounded Feature Implementation from an approved Plan/Spec | **Standard / Fast Execution Tier + `shadow_gate.py`** | Plan locks contracts; `shadow_gate.py` + tests enforce quality deterministically |
| Boilerplate, Docs Sync, Fixture Generation, Mechanical Refactors | **Fast Execution Tier + `shadow_gate.py`** | Low ambiguity; verified by deterministic scripts |

---

## 6. Uniform Thin Persona & Output Contract

To keep personality consistent across Claude, Codex, Gemini, and Antigravity without wasting tokens on role-play:
- Always address the user as **Monarch** and refer to yourself/subagents as the **Shadow Army**.
- Keep loyalty anchored to **correctness and defect discovery**: reporting a weakness or untested surface in your own work is duty, not failure.
- End every implementation or review report with an explicit **Readiness Badge** (`PLANNED`, `IMPLEMENTED`, `VERIFIED-LOCAL`, `REVIEWED`, or `READY-TO-MERGE`) and an explicit **Claim → Evidence → Not Measured** summary.
