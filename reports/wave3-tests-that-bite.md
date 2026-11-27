# Wave 3: Tests that bite

27 November 2026 · **Gate: `PASS`** · **Readiness: `VERIFIED-LOCAL`**

Wave 3 exit criteria (from [enhancement-review §7](enhancement-review.md)):

1. no test file that never touches shipped code;
2. every skill that ships a Python script has at least one test that fails when that script is mutated.

| Criterion | Before | After | Evidence |
| --- | --- | --- | --- |
| Test files that never touch shipped code (heuristic scan) | 20 | **0** | Each file either imports its skill's script, runs its CLI, or reads the skill's shipped content |
| Skills with a Python script whose tests kill ≥ 1 mutant | not measured (shadow-git 0/8 when first measured) | **50/50** | `shadow-quality/scripts/mutation_smoke.py --all` |
| Unit tests across skill suites | 204 (47 suites) | **526 (53 suites)** | `python -m unittest discover -s <skill>/tests` per skill: 0 failures |
| Repo-level evals | 81 | **86** | `evals/`: OK |
| Node suites | perf 13 | perf 13, **video 7** | `node --test` |

The routing work is unchanged by Wave 3: `skill_router.py --self-test` passes 154/154, and the Wave 2 regression on set M still exits 0.

## What changed

### Tests bound to shipped code

For 14 skills, four agents working in separate folders deleted the logic copied into each test and made the tests exercise the real script. Every gate now has a passing case and at least three adversarial cases: string flags, missing keys, empty input and wrong types. This found and fixed real defects in shipped scripts:

| Skill | Defect fixed |
| --- | --- |
| shadow-auth | Hash and JWT algorithms were checked against a denylist only, so `"true"`, `"false"` and `"rot13"` passed; they are now allowlisted. `access_ttl_sec: true` passed as 1 second |
| shadow-cache | `redis_keys: []` passed vacuously; `redis_commands: "FLUSHDB"` was scanned character by character; `true` and `inf` passed as TTL or jitter |
| shadow-compat | `{"deprecation": "true"}` and specs with neither section returned PASS |
| shadow-accessibility | Non-string colours crashed instead of returning an input error |
| shadow-data | Phase gate flags given as strings (`"true"`, `"false"`) passed; `batch_size` was coerced with `int()` |
| shadow-doc | The R03 round-trip check reported `LOSSLESS_VERIFIED` when a table lost a blank column |
| shadow-finops | Cache hit rate 1.5 was accepted; a directory that does not exist returned PASS with exit code 0 |
| shadow-grc | `True` or a blank string counted as control evidence; `capability_level: True` became level 1 |
| shadow-mobile | An empty or missing scan folder returned PASS |
| shadow-ops | Long-form Compose ports (`target:` / `published:`) exposed database ports unchecked |
| shadow-resilience | Drill results were never compared with the RTO/RPO objectives |
| shadow-sec | `unapproved_live_probing_executed: "true"` passed; octal `0177.0.0.1` bypassed the SSRF block; the test mapped authorization to ASVS V4.1.1 instead of V8 |

### Engines that had no tests

| Skill | Tests | Fail-closed fix |
| --- | ---: | --- |
| shadow-ea | 13 | Missing scores defaulted to 3.0; a SPBE portfolio passed with `data_owner` unassigned |
| shadow-modernize | 17 | Missing cost inputs fell back to hidden Rp defaults and still ranked a strategy; it now returns `INSUFFICIENT_EVIDENCE` |
| shadow-pmo | 17 | `ac=0` / `pv=0` reported CPI/SPI 1.0; boolean, string and NaN inputs were accepted; fewer than 1 Monte Carlo iteration crashed |
| shadow-presales | 17 | Zero, negative or string RPS / CPU demand produced minimum sizing silently |
| shadow-video | 7 (node) | No defect: the scaffold refuses to overwrite, and a dry run changes nothing |

### Logic that existed only inside tests is now shipped

Six skills had decision logic that lived only in their test file, so no agent could use it and no test could catch a regression. Each is now a script with a CLI and `--self-test`, documented in its SKILL.md and tested against the real file:

| Skill | New helper | Defect the move exposed |
| --- | --- | --- |
| shadow-maintain | `rollback_decision.py` | No incident-commander approval gate; flags were not type-checked |
| shadow-uat | `uat_evidence_verifier.py` | An empty RTM was signed off; an empty filtered result counted as verified |
| context7 | `resolve_installed_version.py` | The version was read from the `package.json` range, which the skill itself forbids; it now uses `node_modules` or the lockfile |
| shadow-discovery | `sla_ambiguity.py` | The clarifying question always said "7-day", whatever the stated duration |
| shadow-architect | `topology_decision.py` | Unvalidated driver flags; the thresholds are now labelled heuristics for an ADR |
| antislop | `antislop_settings.py` | A non-string `mode` was accepted |

The following were also fixed:
- **shadow-git:** its tests never touched `git_orchestrator.py` and contained an off-domain discount-rounding test. They now drive real temporary repositories (conflict prediction, semantic migration risk, the cleanup gate, and the 13-scenario acceptance suite). Mutation score: 0/8 → 5/10.
- **shadow-privacy:** only the erasure gate was tested; all four audit rules and `scan_path` are now covered. An empty scan returned PASS and now returns `BLOCKED_NO_FILES_SCANNED`. Mutation score: 1/8 → 6/8.
- **shadow-doc:** source freshness (owner, version, access date, SHA-256) moved from the test into `reference_verifier.evaluate_source_freshness`. It now rejects future or naive timestamps and malformed digests.
- **antislop-human:** `contrast-check.py` had no test. It now has one, built from known WCAG pairs (#767676 on white = 4.54:1 passes, #777777 fails).

### Contracts for skills without code

[test_skill_content_contracts.py](../evals/test_skill_content_contracts.py) covers all 59 skills:
- the frontmatter `name` equals the folder name;
- the description is ≤ 250 characters and has a "Use when" clause;
- every relative link in SKILL.md resolves;
- every helper script SKILL.md names exists;
- every skill has at least 3 graded scenarios with failure signals (shadow-monarch through `evals/evals.json`).

### Mutation smoke

[mutation_smoke.py](../shadow-quality/scripts/mutation_smoke.py) uses only the standard library. It flips one comparison, `and`/`or`, `not` or boolean at a time, reruns the skill's own tests, and restores the file in `try/finally` with a SHA-256 check. Its self-test shows that it separates real tests (mutants killed) from theater (all mutants survive). Across every run, the hashes of all 73 scripts were identical before and after.

| Mutation kill rate | Skills |
| --- | --- |
| 8/8 | ai-eng, architect, auth, browser, cache, data, db, grc, handover, mobile, release, resilience |
| 5–7 of 8 (or ≥ 75%) | design 19/24, antislop, context7, accessibility, api, compat, debug, discovery, domain, ea, finops, git (5/10), integrate, maintain, observe, ops, plan, pmo, presales, privacy, realtime, refactor, search, seo, test, uat |
| ≤ 4 of 8, or a low share of a larger sample | analytics 4/8, bootstrap 4/8, concurrency 4/8, email 4/8, eval 4/8, modernize 4/8, supplychain 4/8, sec 11/16, quality 8/32, illustration 3/22, doc 4/64, monarch 3/58 |

The figures come from a sample of at most 8 mutants per script, so they are indicative.

## Not measured

- **Low kill rates.**
  - shadow-doc (4/64): its 8-module engine is covered mainly by `doc_engine_test_suite.py` (58/58), which runs outside unittest.
  - shadow-monarch (3/58): the router is tested in `evals/`, not in `shadow-monarch/tests`.
  - shadow-illustration (3/22).

  They pass the criterion of at least one kill, but most mutants survive.
- **Behaviours deleted because no shipped code implements them:**
  - mobile canary halt/promote
  - ops profile-cycle detection
  - resilience tombstone replay under legal hold
  - accessibility modal Escape focus stack
  - auth live HTTP RBAC handler
  - browser host allowlist and 401 retry-once
  - compat row-order and strict-additive client checks
- **Stale reference text:**
  - `shadow-auth/references/06-...md:99` and `references/08-...md:76` still describe the removed live-HTTP tests.
  - The finops estimator still leaves out the cache-write premium.
- **Node scripts:** mutation smoke covers Python only.
- **Fixed defects without an independent adversarial review:** readiness is VERIFIED-LOCAL, not REVIEWED.

## Reproduce

```powershell
python -B shadow-quality/scripts/mutation_smoke.py --repo . --all --max-mutants 8
```

```powershell
python -B -m unittest discover -s evals -p "test_*.py"
```
