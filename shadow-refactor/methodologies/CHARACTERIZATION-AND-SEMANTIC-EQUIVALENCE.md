# Characterization Testing, Semantic Equivalence & Safe Evolution Methodology

## 1. When to Use & When NOT to Use
- **Use when:** Reducing module coupling, eliminating code duplication/dead code within touched paths, extracting seams, or applying Branch-by-Abstraction while preserving behavior.
- **Do NOT use when:** Changing business policy (`shadow-domain`), investigating unknown bugs (`shadow-debug`), or evaluating multi-year platform replacement TCO (`shadow-modernize`).

## 2. Safe Evolution Mechanics
1. **Characterization Tests (Golden Master):** Capture actual current outputs (including edge quirks and error codes) before touching logic; never alter assertions to force a pass.
2. **Branch-by-Abstraction + Feature Flag:** Introduce an interface seam behind existing callers, swap implementations incrementally, run dual-verify if risky, then delete obsolete branch only after validation.
3. **Code Archaeology for Hidden Side Effects:** Audit implicit frontend assumptions (e.g., relying on unsorted array order, nullable string `""` vs `null`, or legacy status strings) and undocumented DB triggers before changing serialization.
4. **Risk-Based Diff Discipline:** Do not bundle formatting sweeps of untouched lines/files with behavioral refactors.
