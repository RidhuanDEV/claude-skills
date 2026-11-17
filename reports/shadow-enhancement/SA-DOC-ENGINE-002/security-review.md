# SA-DOC-ENGINE-002 — Security & Execution Authorization Review (`R01`, `R02`, `H02`)

Generated: 2026-11-17

## 1. Execution-Boundary Authorization (`R02`)
- **Centralized Gate Integration**: `shadow-doc/scripts/doc_orchestrator.py::enforce_document_execution_authorization` imports and delegates to `shadow-monarch/scripts/execution_approval_gate.py` (`evaluate_execution_request`, `check_subagent_authorization`), avoiding duplicate permission systems.
- **CLI Boundary Enforcement**: `shadow-doc/scripts/doc_scaffold.py` `export` requires `--approval-file` for `overwrite_document` (triggered when any destination file already exists even with `--overwrite`) and for restricted/unknown environments (`--env staging|production|unknown`) or outside-project targets.
- **Bypass Defenses Verified**:
  - Self-issued/untrusted sources (`agent_self_approval`, `self_issued`, `cli_flag_only`, `orchestrator_recommendation`, `subagent`) rejected with `BLOCKED_SELF_ISSUED_OR_UNTRUSTED_APPROVAL`.
  - Expired approvals rejected with `BLOCKED_APPROVAL_EXPIRED`.
  - Action mismatches (`allowed_actions`) rejected with `BLOCKED_APPROVAL_ACTION_MISMATCH`.
  - Path mismatches, project mismatches, and sub-agent scope upgrades rejected via `execution_approval_gate.py`.

## 2. Explicit Generator Verification (`R01`)
- Arbitrary files (`.txt`) and empty directories are classified `capabilities_verified: False` -> **`UNKNOWN`** (`USER_DECISION_REQUIRED`), never synthesized as compatible outputs.
- Outside-project explicit generator paths are isolated with `outside_project_boundary: True` and `USER_DECISION_REQUIRED`.

## 3. Filesystem Containment & Atomic IO (`H02`)
- `validate_safe_path` inspects target AND ancestor chain up to `allowed_root` for symlinks/reparse points (`SYMLINK_TRAVERSAL_BLOCKED`), NUL bytes, and parent escapes (`PATH_TRAVERSAL_BLOCKED`).
- `atomic_write_text` writes via `tempfile.NamedTemporaryFile(..., dir=target.parent, delete=False)` + `os.fsync` + `os.replace` with `finally` cleanup (`0` leftover `.tmp` files verified).
