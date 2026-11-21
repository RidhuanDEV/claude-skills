# Export, manifest and handoff

Reuse the project asset registry and source generator if they exist. Trace source to export to actual consumer. Modify the authoritative source, regenerate downstream outputs, and preserve a separately editable master. Do not replace a working pipeline for convenience. When source authority is unclear and overwriting is consequential, resolve it first.

Record one entry per deliverable or extend the established schema. Use measured values from real artifacts.

| Metadata | What to record |
|---|---|
| Identity | Asset ID, role, app state or placement, visual revision and master reference |
| Paths/formats | Editable source, runtime export, static fallback, and manifest paths relative to the project where appropriate |
| Artifact evidence | Source/export hashes, dimensions or viewBox, bytes, format and applicable tool/player version |
| Behavior | Static, timeline or interactive; repeat policy, reduced-motion choice and required inputs where applicable |
| Provenance | Owner/source URL, license and rights for input assets, prompt and available generator metadata |
| Review | Command or inspected preview, environment, result for each applicable gate |

Review each gate independently. Use PASS, FAIL, NOT_RUN, BLOCKED, or NOT_APPLICABLE with evidence. A critical failure blocks any production-readiness claim.

1. Art direction and character: compare master and variants at actual placement and check proportion, expression, gesture and model consistency.
2. Technical: inspect file format, geometry/render dependencies, dimensions, byte budget and editable source. Verify permitted source/kinds.
3. Visual: inspect the artifact on applicable surfaces for hierarchy, cropping, contrast and drift.
4. Playback: inspect actual player and supported features, timing, loop, reduced motion and fallback when relevant.
5. Integration: verify placement, image semantics and lifecycle in the real product where permitted. Keep app text/actions accessible outside decorative art.
6. Provenance and scope: verify usage rights and resolve unknown origins before distribution. Record which tools, exports and environments were authorized.

Keep matched settings and source hashes for deterministic outputs. Save approved masters, actual generated outputs and prompt/tool metadata for nondeterministic ones. Use relative paths and check cross-agent access before handoff.
