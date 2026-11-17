# SA-DOC-ENGINE-002 — Semantic Fidelity & Data Integrity Report (`R03`, `R08`, `H03`, `H04`)

Generated: 2026-11-17

## 1. `MarkdownCompatibilityAdapter` Round-Trip Verification (`R03`)
- Replaced unconditional `lossless_verified: True` with real render + `parse_markdown_into_blocks` verification producing explicit contract:
  - `fidelity_status`: `LOSSLESS_VERIFIED | LOSSY_WITH_WARNINGS | UNVERIFIED | FAILED`
  - `lossless_verified`: `fidelity_status == "LOSSLESS_VERIFIED"`
  - `fidelity_warnings` & `fidelity_failures` listing exact lost/flattened fields.
- Fixed Markdown serialization/parsing round-trip in `v2_renderers.py` & `v2_core.py`:
  - Escaped `\|` pipes inside table cells (`T50` confirmed `"a | b"` -> `"a \\| b"` round-trip).
  - Dynamic backtick fences (`max_backtick_run + 1`) for code blocks containing embedded ```` ``` ```` (`T50` verified ```` ````markdown ````).
- Flattened structures (`finding`, `decision-matrix`, `evidence_refs`, `extensions`, `rendering_hints`) explicitly emit `LOSSY_WITH_WARNINGS` (`T13` confirmed `lossless_verified: False`).

## 2. Domain Adapter Zero-Fabrication Policy (`R08`, `H04`)
- Declared `ADAPTER_CONTRACTS` in `shadow-doc/scripts/domain_adapters.py` across `shadow-grc`, `shadow-presales`, `shadow-handover`, `shadow-pmo`, `shadow-ea`.
- Removed synthetic default rows (`50 RPS`, `4 vCPU`, `16 GB RAM`) and assumed verified sources (`Verified Audit Workpapers`, `Staging UAT Acceptance Evidence`, `Status: Verified`).
- Missing inputs produce explicit `[MISSING]`, `[TBD]`, `[MISSING_EVIDENCE]`, and `source_type: "UNVERIFIED"` recorded inside `extensions["x-shadow:data_integrity"]`.
- `strict=True` raises `ValueError` on missing required inputs, negative metrics (`CPI = -1.5`), or contradictory sizing (`stress.rps < conservative.rps`) (`T55`).
