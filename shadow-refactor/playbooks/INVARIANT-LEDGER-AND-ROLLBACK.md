# Invariant Ledger, Verification & Rollback Playbook

```yaml
record_id: "REF-0001"
precedents_inspected: ["src/billing/invoice.service.ts:12-88"]
invariants_locked:
  - "HTTP 422 envelope shape `{ code, field, message }` unchanged"
  - "Rounding mode HALF_EVEN preserved on IDR/USD invoice totals"
  - "Existing role guard `requireOrgMember` remains on controller boundary"
characterization_suite:
  before_refactor_exit_code: 0
  after_refactor_exit_code: 0
  cases_count: 14
changed_files: ["src/billing/tax-calculator.ts", "tests/billing/tax.char.spec.ts"]
allowed_scope_files: ["src/billing/tax-calculator.ts", "tests/billing/tax.char.spec.ts"]
silent_contract_changes: []
adr_approved_for_new_pattern: true
rollback: "git revert <commit>"
```
