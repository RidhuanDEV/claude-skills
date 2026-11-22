# 01 — Scientific Hypothesis Falsification, Fault Trees & Automated `git bisect`

## 1. Purpose & Activation Conditions
Replace intuition-driven "shotgun debugging" with **scientific hypothesis falsification**: separate **Symptom**, **Contributing Factor**, and **Causal Root Cause**, rank `>= 2` competing hypotheses with explicit disconfirming observations, pinpoint regressions in `O(log N)` steps via `git bisect run`, and prove every fix with a **Red-Before (`FAIL`) -> Green-After (`PASS`)** evidence trail validated by `debug_hypothesis_gate.py`. Activate on any non-trivial bug, unexpected `500`, misleading stack trace, or post-commit regression.

## 2. Prerequisites
- Redacted failure artifact (error message, `requestId`/`traceId`, release SHA, or observable misbehavior).
- Read-only (`L0`) repository access and local/sandboxed test execution (`L1`).

## 3. Technical Principles & Constraints
- **Never Stop at the First Plausible Log Line (Confirmation Bias Defense):** Two errors appearing near each other in time are often **coincidental** or **downstream symptoms** (e.g., `HTTP 502 Bad Gateway` is a symptom; upstream OOMKill caused by unbounded PDF buffer allocation is the root cause). Always generate **at least 2 competing hypotheses** and define what observation would **disprove** each one!
- **Separate Three Distinct Layers:**
  1. **Symptom:** What the user or monitor saw (`POST /checkout returned 500`).
  2. **Contributing Factor:** Conditions enabling or amplifying it (missing payload size cap, shared worker pool).
  3. **Root Cause:** Exact causal mechanism whose removal structurally eliminates the failure class.
- **No Silent Band-Aid Suppression:** Never "fix" a crash by slapping `?.` optional chaining defaulting money/auth to `0`/`false`, swallowing exceptions in empty `catch {}`, or adding `sleep(2000)`. Band-aids convert loud crashes into silent data corruption!
- **Automated `git bisect run` For Commit Regressions:** When a working feature broke sometime across the last `N` commits, write a 10-line deterministic repro script (exiting `0` on good, `1` on bad, `125` on unbuildable commit) and let `git bisect run` isolate the exact introducing commit in $\lceil \log_2 N \rceil$ steps!
- **Redacted Evidence Gate:** Scrub every PostgreSQL/MySQL DSN password, `Bearer` token, private key, AWS `AKIA` key, and customer PII/NIK before writing `debug-report.md` or test fixtures.

## 4. Architecture & Implementation

```mermaid
flowchart TD
  S["1. Capture Symptom & Redacted Timeline\n(requestId, SHA, Expected vs Actual)"] --> H["2. Rank >= 2 Competing Hypotheses\n(Each with Disconfirming Observation)"]
  H --> P["3. Execute Cheapest Falsifying Probe\n(Read-Only L0 / Local L1)"]
  P -->|"Refuted"| H2["Prune Hypothesis & Narrow Fault Tree"]
  H2 --> P
  P -->|"Confirmed"| Repro["4. Write Minimal Failing Repro Test\n(phase: before_fix, exit_code != 0)"]
  Repro --> Fix["5. Apply Minimal Behavior-Preserving Fix"]
  Fix --> Verify["6. Re-Run Repro + Adjacent Suite\n(phase: after_fix, exit_code == 0)"]
  Verify --> Gate["7. Validate via debug_hypothesis_gate.py"]
```

### Automated `git bisect run` Template (PowerShell / Bash)
```powershell
# Locate exact introducing commit across 60 commits in <= 6 steps!
git bisect start HEAD v2.4.0
git bisect run python tests/repro_bug_412.py
# Always clean up bisect state after recording the exact bad SHA:
git bisect reset
```

### Structured `debug-report.json` Validated by `debug_hypothesis_gate.py`
```json
{
  "record_id": "DBG-2026-412",
  "symptom": "Duplicate invoice PDF email sent when queue worker retries after Redis ack timeout",
  "root_cause": "Outbound SMTP send ran before durable idempotency receipt was committed in PostgreSQL",
  "hypotheses_tested": [
    {
      "id": "H1",
      "claim": "SMTP relay duplicated a single message internally",
      "status": "REFUTED",
      "disconfirming_observation": "Provider logs show two distinct client-generated Message-IDs 31s apart"
    },
    {
      "id": "H2",
      "claim": "Worker redelivery re-executed SMTP send because no idempotency state existed prior to ack",
      "status": "CONFIRMED",
      "disconfirming_observation": "Injected local Redis ack failure after send triggered second SMTP call with same job_id"
    }
  ],
  "evidence": [
    { "phase": "before_fix", "command": "pytest tests/test_email_retry.py", "exit_code": 1 },
    { "phase": "after_fix", "command": "pytest tests/test_email_retry.py", "exit_code": 0 }
  ]
}
```

## 5. Platform/Vendor Variations
- **Binary Search Without Git History (Delta Debugging):** When a bug occurs inside a massive 500-line JSON payload, SQL query, or config file rather than across commits, bisect the **input** (cut payload in half -> test -> keep failing half) to shrink the repro down to the exact minimal failing field in `< 8` steps.
- **Misleading Async Stack Traces (Node/Python/Go):** Async boundaries and minified JS bundles frequently point stack traces at a wrapper middleware or `dist/index.js:1:48120` rather than the caller. Load exact matching source maps (`--enable-source-maps` in Node) or log the caller's span/operation ID before jumping to conclusions.

## 6. Decision Matrix & Trade-Offs

| Investigation Technique | Cost / Risk | Best Trigger | Fails When |
| :--- | :--- | :--- | :--- |
| **Competing Hypothesis Table (`>= 2`)** | Very Low (`L0`) | Every non-trivial bug | Skipped due to "obvious" log line bias |
| **`git bisect run`** | Low (`L1` local) | Known good commit/tag exists | Bug requires external state not reproducible locally |
| **Input Delta Debugging** | Low (`L1` local) | Large failing payload / document / query | Non-deterministic race (stabilize with barrier first) |
| **Targeted Diagnostic Instrumentation** | Low (`L1`) | Missing evidence in existing logs | Forgotten & left noisy in production code (always remove!) |

## 7. Real Production Scenario
Checkout failed with `500 Invalid JSON` right after a release. The top error line in logs was `SyntaxError: Unexpected token '<' in JSON at position 0`, so a developer assumed the JSON serializer was broken and began rewriting response middleware. Applying competing hypotheses (`H1: serializer bug` vs `H2: upstream gateway returning HTML 502 error page parsed as JSON`), checking the raw response `Content-Type` immediately refuted `H1` (`text/html` from Nginx timeout!) and traced the true root cause to a misconfigured upstream `proxy_read_timeout` introduced 3 commits earlier via `git bisect`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Reporting `"root_cause": "Endpoint threw 500 Internal Server Error"` (merely rephrasing the symptom!) or pasting a raw `postgresql://user:pass@host/db` string into `debug-report.md`.
  **RIGHT:** Explain the exact causal mechanism distinct from the symptom, redact all secrets/DSNs/tokens, and validate with `debug_hypothesis_gate.py`.
- **WRONG:** Making 4 simultaneous speculative edits across unrelated files ("maybe this fixes it") without verifying which edit actually changed the failure.
  **RIGHT:** Change ONE variable per probe; once root cause is proven, apply the smallest consistent fix and clean any temporary debug logs.

## 9. Testing & Verification
- Run `python shadow-debug/scripts/debug_hypothesis_gate.py --validate-report path/to/debug-report.json` to mechanically verify `>= 2` hypotheses, disconfirming observation, distinct root cause, red-before/green-after evidence, and zero secret leaks.
- Run `python -m unittest discover -s shadow-debug/tests -v`.

## 10. Operational Considerations
- Keep `debug-report.md` / JSON artifacts free of raw PII/credentials so they can safely be handed off to `/shadow-maintain` blameless postmortems and `/shadow-test` regression suites.

## 11. Authoritative References
- Andreas Zeller — *Why Programs Fail: A Guide to Systematic Debugging* (Delta Debugging & Scientific Method).
- `shadow-debug/methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md` & `playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md`.

## 12. Limitations & When NOT to Use
- Do NOT use `shadow-debug` for post-production SLA/Harwat ticketing processes (`/shadow-maintain`), setting up OTel/Grafana infrastructure (`/shadow-observe`), or broad structural refactoring (`/shadow-refactor`).
- Never access or mutate live production databases without explicit `L4` approval.
