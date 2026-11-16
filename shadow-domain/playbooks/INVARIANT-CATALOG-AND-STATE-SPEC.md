# Invariant Catalog & State Transition Specification

```yaml
domain_model:
  bounded_context: "OrderFulfillment"
  is_simple_crud: false
  use_full_ddd: true
  aggregates: ["PurchaseOrder"]
  state_transitions:
    DRAFT: ["SUBMITTED", "CANCELLED"]
    SUBMITTED: ["APPROVED", "REJECTED", "CANCELLED"]
    APPROVED: ["COMPLETED"]
    COMPLETED: []   # terminal: reversal requires separate Refund aggregate
  invariants:
    - id: "INV-01"
      rule: "approver_id != requester_id (maker-checker enforced under concurrent transitions)"
    - id: "INV-02"
      rule: "tenant_id immutable and verified on all commands"
  unresolved_policy_conflicts: []
```
