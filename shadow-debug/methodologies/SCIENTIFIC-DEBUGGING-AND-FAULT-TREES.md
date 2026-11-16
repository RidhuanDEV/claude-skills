# Scientific Debugging, Hypothesis Falsification & Fault-Tree Methodology

## 1. When to Use & When NOT to Use
- **Use when:** Any unexpected runtime failure, regression, race symptom, memory leak, async promise leak, deadlocked query, or environment-only bug requires proven causal root cause.
- **Do NOT use when:** Adding new features (`shadow-api`), restructuring clean code (`shadow-refactor`), or designing alerting dashboards (`shadow-observe`).

## 2. Diagnostic Techniques by Failure Mode

| Failure Class | Primary Diagnostic Signals | Disconfirming Probe / Falsification |
|---|---|---|
| **Misleading Stack Trace** | Wrapped/re-thrown error masks original throw site or async continuation | Inspect `error.cause` / async hooks; trace entry-to-sink data flow rather than trusting top frame |
| **Nondeterministic Flake / Race** | Fails only under parallel CI or repeated runs (`--repeat-each=20`) | Check shared mutable globals, wall-clock timers, unawaited promises, or DB transaction isolation |
| **Environment-Only Drift** | Works locally, fails in Docker/Staging | Diff `node -v`/`python --version`, lockfiles, `TZ`, `LC_ALL`, DNS (`localhost` vs service name), TLS certs, file case-sensitivity |
| **Memory Leak / OOM** | Monotonic RSS climb across requests | Capture 2+ heap snapshots separated by GC + load; diff retained object classes & event listeners |
| **DB Deadlock / Lock Timeout** | SQL `40P01` or `1205` under concurrent transactions | Inspect lock wait graph (`pg_locks` / `SHOW ENGINE INNODB STATUS`), inconsistent lock acquisition order across endpoints |

## 3. Causal vs Correlated Evidence Rules
1. **Five-Whys Limitation:** Linear five-whys often stops at one arbitrary branch; complex failures require a **Fault Tree** separating necessary vs contributing factors.
2. **Bisect Discipline:** When a regression has a known good SHA, run `git bisect` with an automated non-mutating reproduction script.
3. **Mandatory Red-Green Proof:** A regression test that only runs *after* the fix does not prove the fix caused the pass. Record both pre-fix failure and post-fix pass.
