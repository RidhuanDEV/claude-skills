# Implementation handoff, traceability, and measurement
## Minimum handoff
Problem and goals; stakeholder decisions; actors and RBAC matrix; user stories/acceptance criteria; map/flow; wireframes with content labels; screen inventory; state and transition table; error messages; data/API assumptions; accessibility requirements; responsive behavior; analytics events; unresolved risks and owners.

## Traceability contract
`US-ID -> FLOW-ID -> SCR-ID / STATE-ID -> AC-ID -> TEST-ID -> METRIC-ID`. Preserve IDs across revisions. Mark requirements with `CONFIRMED`, `PROPOSED`, `UNKNOWN`, or `DEFERRED`. Record changed decisions and rationale; do not overwrite undocumented prior assumptions silently.

## Metrics
Define user-level success before measurement: completion rate, time on task, input error rate, drop-off points, assistance requests, accessibility barriers, and user-reported confidence. For AI products, add correction rate, citation usefulness and uncertainty calibration. Define instrumentation events without collecting sensitive content by default. Segment by role/device/task; avoid optimization that harms vulnerable cohorts.

## Handoff quality
Implementation-ready does not equal implement-now. Explicit user request required before coding. When coding requested, generate small tasks and tests, preserve conventions, verify acceptance against state matrix, and write regression checks.
