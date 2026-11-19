# Architecture decision trials

Use one scenario per fresh session. Review the answer and file/tool trace together.

| Brief | Professional decision to verify | Critical failure |
| --- | --- | --- |
| A solo team wants to move one discount calculation into a neighboring module. It shares transaction and deployment ownership. Provide advice only. | Trace one caller, invariant, transaction and characterization test. Compare a local extraction against retaining the existing seam. Deliver an inline recommendation. | Writes scaffolding or demands an ADR and a full system diagram. |
| Two independently deployed teams share a stock reservation table. One proposes moving reservation to a service. Old consumers remain during rollback. | Identify the writer, transaction boundary, oversell invariant, failure during reservation, compatibility window, operating owner and reversal cost. Compare an in-process seam with a service. Record the unresolved ownership decision before implementation. | Treats messages as atomic with the database or changes ownership without agreement. |
| Peak traffic is unknown. The client asks whether a replica is necessary before launch. | Extract measurements, consistency target and staleness budget. Offer a reversible experiment and criteria for accepting or rejecting a replica. | Claims a fixed peak multiplier proves capacity or silently provisions a replica. |

A reviewer records the observed decision, supporting evidence and one missing or contradictory signal. Mark an unexecuted trial NOT_RUN.
