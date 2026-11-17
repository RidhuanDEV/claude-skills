# SA-DOC-ENGINE-002 — Compatibility & Migration Impact Analysis (`G0`)

Generated: 2026-11-17

## 1. Backward Compatibility Guarantees
- **`schema_version` `"2.0"` & `"2.1"` & legacy `v1.0` (`bagian`)**: Preserved cleanly with zero breaking schema removals. All `AT-01..AT-16` acceptance scenarios remain intact.
- **`doc_orchestrator.py` Public Signatures**:
  - `resolve_document_generator(...)`, `assess_generator_compatibility(...)`, `discover_project_generators(...)`, `MarkdownCompatibilityAdapter.adapt(...)` keep existing callers working while enriching return contracts (`fidelity_status`, evidence-backed `criteria_details`, verified `capabilities_evidence`) cleanly.
  - Note on `MarkdownCompatibilityAdapter.adapt`: previously returned `"lossless_verified": True` unconditionally; now returns `"fidelity_status": "LOSSLESS_VERIFIED" | "LOSSY_WITH_WARNINGS" | "UNVERIFIED" | "FAILED"` plus `"lossless_verified": (fidelity_status == "LOSSLESS_VERIFIED")` and `"fidelity_warnings": [...]` so callers inspecting either field get honest, backward-compatible keys!
- **Authorization Gate (`R02`)**:
  - Reuse `shadow-monarch/scripts/execution_approval_gate.py` (`evaluate_execution_request`, `_verify_approval`, `check_subagent_authorization`) directly — **zero** parallel permission system introduced.
  - Safe local read/generate actions to *new* output files inside authorized local workspace (`--env local|development|sandbox` or scoped local destination without overwriting) remain functional; `--overwrite` or protected actions (`init_global_generator`, `change_global_config`, `install_global_dependency`, `replace_existing_generator`, `migrate_pipeline`, `persistent_adapter`, `publish_external`, outside-root writes) require a valid external approval record (`--approval-file` or `approval` dict with matching action/target/project/env/`APPROVED_PENDING` and verified caller binding, refusing self-issued agent tokens!).
- **`domain_adapters.py` (`R08` & `H04`)**:
  - Empty or missing evidence/data NO LONGER fabricates plausible defaults (`50 RPS`, `"Verified Audit Workpapers"`, `["Status", "Verified"]`). Callers passing incomplete payloads receive explicit missing-data markers (`[UNVERIFIED]`, `[MISSING_EVIDENCE]`, `validation_warnings[]` / `strict_errors[]`) and `strict=True` raises `ValueError` clearly on contradictory or empty required inputs!
