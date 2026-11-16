# Debug Report, Reproduction & Shared Evidence Envelope Template

## `debug-report.md` Structure
```yaml
record_id: "DBG-0001"
task_id: "TASK-001"
repo_ref: "<git-sha>"
symptom: "POST /webhooks/payment returns 500 on concurrent retries"
expected_behavior: "Duplicate webhook returns 200 idempotently without throwing"
observed_behavior: "Unhandled unique constraint violation causes 500"
hypotheses_tested:
  - id: H1
    claim: "DB pool exhausted under burst"
    disconfirming_observation: "Pool active connections stayed at 2/20 during 500s -> REFUTED"
  - id: H2
    claim: "Concurrent requests race past select-then-insert check without ON CONFLICT"
    confirming_probe: "Two parallel requests trigger SQLSTATE 23505 -> CONFIRMED"
evidence:
  - type: "test_result_before_fix"
    command: "pytest tests/test_webhook_race.py"
    exit_code: 1
    observed_at: "2026-11-16T12:00:00+07:00"
  - type: "test_result_after_fix"
    command: "pytest tests/test_webhook_race.py"
    exit_code: 0
    observed_at: "2026-11-16T12:05:00+07:00"
change:
  files: ["src/webhooks/handler.py", "tests/test_webhook_race.py"]
  risk: "low"
verification:
  status: "PASS"
  limitations: ["Tested against local SQLite/Postgres fixture; production spike load not simulated"]
rollback: "git revert <commit>"
```

**Escalation & Rollback:** Always redact `Authorization`, API keys, DSN passwords, and PII before saving debug artifacts.
