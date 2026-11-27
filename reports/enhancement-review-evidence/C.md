# Grades — Group C (15 skills: quality, test, debug, refactor, perf, uat, release, compat, sec, supplychain, privacy, ops, observe, resilience, finops)

Reviewer mode: read-only. Repo: `D:\Ridhuan Ngoding Moment\SKILL` @ 1dbe3b5. Probe scripts: `C:/Users/Ridhuan/AppData/Local/Temp/claude/e80b2dfa48902dc8/c0b822e3-f9e8-41c6-a8c8-050edf286e4e/scratchpad/probeC/p1..p5.py`.

## Summary table

| Skill | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow-quality | 2 | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 2.63 | MEDIUM |
| shadow-test | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 1 | 2.38 | MEDIUM |
| shadow-debug | 4 | 3 | 3 | 4 | 2 | 3 | 3 | 2 | 3.00 | GOOD |
| shadow-refactor | 3 | 3 | 3 | 4 | 2 | 3 | 3 | 2 | 2.88 | MEDIUM |
| shadow-perf | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |
| shadow-uat | 2 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.50 | MEDIUM |
| shadow-release | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | MEDIUM |
| shadow-compat | 3 | 3 | 4 | 3 | 2 | 3 | 3 | 2 | 2.88 | MEDIUM |
| shadow-sec | 3 | 3 | 2 | 3 | 2 | 4 | 3 | 3 | 2.88 | MEDIUM |
| shadow-supplychain | 4 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3.13 | GOOD |
| shadow-privacy | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |
| shadow-ops | 3 | 3 | 3 | 3 | 2 | 3 | 2 | 1 | 2.50 | MEDIUM |
| shadow-observe | 4 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3.00 | GOOD |
| shadow-resilience | 3 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.88 | MEDIUM |
| shadow-finops | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 2.75 | MEDIUM |

No PERFECT. No BAD (no false-PASS critical found in the three re-probed tools; all three prior criticals FIXED).

## Prior-review re-probes (requested)

| Defect (reports/skill-review-delivery.md) | Probe | Observed | Status |
|---|---|---|---|
| shadow-quality Docker cleanup ignores repo/run identity (L153-157) | Legacy mock `gate(cleanup=True)` with two-project `docker ps` rows; plus ledger run where inventory returns a neighbour ID not in ledger; plus ledger `"version":"1"` | `legacy-call: BLOCKED [] ['Provide a repository, run ID and trusted ledger for this job.'] calls= 0`; `neighbour-in-inventory: BLOCKED ['Run inventory has containers missing from its ledger; reconcile ownership before cleanup.'] calls= 1`; `str version: BLOCKED` | **FIXED** (shadow_gate.py:337-386 requires repo+run_id+typed ledger, label-filtered inventory, non-forced `docker rm` after re-inspect) |
| shadow-supplychain accepts `signer_verified="false"` (L209-213) | Original probe; plus same manifest with a valid digest-bound receipt | `status: FAIL ... 'Manifest signer declaration is false or malformed.'`; with good receipt still `FAIL`; clean + good receipt `PASS` | **FIXED** (supplychain_sbom_gate.py:130 `is not True`; receipt bound to `subject_sha256` + 4-tuple policy L141-157) |
| shadow-perf POST-only spec emits /healthz, no POST (L113-117) | `--spec` with only `POST /orders`, `--out` | `status: DRAFT, operations:["POST /orders"], selected: 0`; generated files: `/healthz` count 0; `steps = []`; script `fail('Draft: select and dry-run a journey first')`; status check is `response.status !== step.expect` (exact) | **FIXED** |

Other prior defects touched incidentally: shadow-refactor empty-allowlist PASS -> **FIXED** (`refactor no allowlist: FAIL`); shadow-sec "IDs not resolved to catalog" -> **STILL OPEN** (see below); shadow-resilience pg_restore-as-RTO -> **FIXED** (SKILL.md:36, drill_evidence.py); shadow-release unconditional perf/backup/`/readyz` -> **PARTIAL**; shadow-test universal 8-point HTTP matrix -> **PARTIAL**; shadow-uat 9-state/202 exit gate + absolute file URIs -> **FIXED** (SKILL.md:57, links resolve); shadow-ops identical-version parity -> **FIXED** in SKILL.md:43.

## Test/self-test runs (all offline, each <25 s)

`python -m unittest discover -s <skill>/tests`: quality 10 OK; test 3 OK; debug 3 OK; refactor 3 OK; uat 1 OK; release 2 OK; compat 5 OK; sec 9 OK (20.7 s); supplychain 6 OK (12.3 s); privacy 2 OK; ops 10 OK; observe 4 OK; resilience 5 OK; finops 1 OK. `node --test shadow-perf/tests/scaffold.test.mjs`: 13/13 pass. `openapi_to_k6_scaffold.mjs --selftest`: SELFTEST_OK. Passing suites are necessary but not sufficient: 6 test files test functions defined inside the test file itself (see cross-cutting).

---

### shadow-quality
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 2.63 | MEDIUM |

Strengths
- Docker ownership gate now fail-closed with repo/run/ledger identity and re-inspection before non-forced removal (scripts/shadow_gate.py:337-386); 10 ownership tests import the real script.
- Honest NOT_RUN when no ledger: SKILL.md:49 "A missing ledger cannot establish zero leaks."
- Review severity taxonomy and L0 read-only review rule (SKILL.md:67-76).

Gaps
- HIGH — Description has no "Do NOT use" and no sibling boundary vs shadow-refactor/shadow-test/engineering:code-review (SKILL.md:3).
- MEDIUM — "7 Mandatory" checks applied universally: 100% parity with `openapi.yaml` + `postman_collection.json` even when a repo has neither (SKILL.md:37); arbitrary "~40-50 lines / nesting > 3" rule without metric tool or threshold source (SKILL.md:26).
- MEDIUM — "Every finding must include ... concrete replacement code" (SKILL.md:73) conflicts with its own L0 read-only review rule and inflates output.
- MEDIUM — Near-zero provenance: 1 URL across SKILL+references, no last-verified dates; no lint/typecheck tool versions.
- LOW — CLAUDE.md promises `--check-docker-leaks` as the VERIFIED-LOCAL gate, but a bare run now always returns NOT_RUN (SKILL.md:49) — consistent, but the global doctrine still implies a pass signal.

Prior-review defect status: FIXED (probe above).

Upgrade actions
1. Add `Do NOT use for ... (shadow-refactor, shadow-test, shadow-sec)` to description.
2. Make checks 4-5 conditional ("if the repo owns an OpenAPI/collection artifact").
3. Replace the line-count heuristic with tool-backed thresholds (ESLint `complexity`, SonarSource Cognitive Complexity whitepaper, ruff `C901`).
4. Add dated sources (typescript-eslint strict config docs, ruff/mypy docs).

Test/self-test run: `python -m unittest discover -s shadow-quality/tests` -> Ran 10, OK; ownership probe p1.py output above.

### shadow-test
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 2 | 2 | 3 | 2 | 1 | 2.38 | MEDIUM |

Strengths
- Clear boundaries vs eval/perf/browser/uat (SKILL.md:3,11); explicit L1 vs L2/L3 (SKILL.md:43).
- Good doctrine: red-before/green-after, fake clocks, port 0, no blind retries (SKILL.md:33-34).

Gaps
- HIGH (licensing) — `references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md` (2159 lines) is the MIT-licensed goldbergyoni/javascript-testing-best-practices README copied without its copyright/permission notice, without commit SHA or date, and not credited in README.md "Credits & Attribution" (README.md:172-185). MIT requires retaining the notice. Not tracked in any UPSTREAM_PROVENANCE file.
- MEDIUM — Vendored file is uncurated: 76 `<img>`/`/assets/` references and 15 broken relative links (translations `readme-zh-CN.md` etc.); SKILL.md:25 calls it "Curated". It also contradicts README's own rule "under about 10k characters" (README.md:185).
- MEDIUM — Routing into vendor is sensible (refs 01/02/05 cite specific sections) but loading the whole 2159-line file for "AAA structure" is token-expensive; no section anchors.
- MEDIUM — `suite_hygiene_verifier.py` trusts self-declared metadata: `uses_fake_timers:"false"` with `waitForTimeout(3000)` -> `[]` (scripts/suite_hygiene_verifier.py:58 `bool(...)`); `--rm shadow.ephemeral=true finally docker rm -f` inside a comment satisfies the Docker check (L82-86) -> `[]`.
- MEDIUM — "Universal 8-Point HTTP Failure Surface" title remains (SKILL.md:35) though body says "applicable"; SKILL.md has no ordered workflow or output contract (D4).
- LOW — 0 external URLs; no dated sources for Vitest/pytest/Pact.

Prior-review defect status: PARTIAL — "applicable" wording added, but "Universal" framing and HTTP-centric matrix remain (SKILL.md:35).

Upgrade actions
1. Add LICENSE notice + upstream commit/date header to the vendor file, add to README credits, track in a provenance lock like `shadow-design/UPSTREAM_PROVENANCE.json`.
2. Trim vendor to the cited sections (AAA, isolation) with anchors, or replace with links.
3. Make the verifier parse booleans strictly (`is True`) and strip comments before Docker regexes; add precision probes.
4. Add an ordered "plan -> red -> green -> scope -> report" section and an applicability table (unit/CLI/event/HTTP/UI).

Test/self-test run: `python -m unittest discover -s shadow-test/tests` -> Ran 3, OK; p4.py: `sleep+strfalse: []`, `docker comment bypass: []`.

### shadow-debug
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 4 | 2 | 3 | 3 | 2 | 3.00 | GOOD |

Strengths
- Precise sibling boundaries (maintain/observe/perf/refactor/test) in description (SKILL.md:3,9).
- Ordered 8-step scientific workflow with >=2 hypotheses + disconfirming observations + red/green evidence (SKILL.md:36-43); anti band-aid rules (SKILL.md:30).

Gaps
- MEDIUM — `debug_hypothesis_gate.py` is a form validator of self-reported fields: `root_cause:"x"`, one hypothesis `{}` and `disconfirming_observation:"."` -> `PASS` (scripts/debug_hypothesis_gate.py:30-46). SKILL.md:48 claims it BLOCKS "root cause from a single coincidental log line" — it cannot detect that.
- MEDIUM — Evidence exit codes are caller-asserted; no link to a command log/hash (L48-56).
- LOW — Only 2 URLs; no dated sources (e.g., `git bisect run` docs, Node `--cpu-prof`).
- LOW — `int(e.get("exit_code"))` on non-numeric input raises instead of reporting (L50).

Prior-review defect status: N/A.

Upgrade actions
1. Require min lengths/distinct hypotheses, >=1 REJECTED hypothesis, and evidence entries pointing to stored log artifacts with sha256.
2. Soften SKILL.md:48 to what the gate actually checks.
3. Add dated citations (git-scm bisect, Node diagnostics guide, py-spy).

Test/self-test run: unittest Ran 3, OK; p4.py `debug rubber: PASS`.

### shadow-refactor
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 4 | 2 | 3 | 3 | 2 | 2.88 | MEDIUM |

Strengths
- Clear 8-step characterization-first workflow, invariant ledger, rollback (SKILL.md:34-43).
- Scope allowlist now enforced even when empty (`refactor no allowlist: FAIL`).

Gaps
- MEDIUM — Truthiness: `precedents_inspected:"false"`, `invariants_locked:"false"` -> `PASS` (scripts/refactor_characterization_gate.py:26-30). Same defect class as the prior supplychain critical.
- MEDIUM — Exit codes and changed_files are caller-asserted; no binding to an actual git diff or revision (L45-51).
- LOW — No external sources (0 URLs) for Feathers characterization tests, Fowler branch-by-abstraction.
- LOW — Description lacks a boundary vs shadow-quality dead-code cleanup (both claim it).

Prior-review defect status: FIXED (empty allowlist) — but truthiness class remains.

Upgrade actions
1. Type-validate inputs (`list[str]` non-empty), derive `changed_files` from `git diff --name-only <base>`.
2. Record before/after test commits SHAs.
3. Cite Feathers (WELC), martinfowler.com/bliki/BranchByAbstraction.html with dates.

Test/self-test run: unittest Ran 3, OK; p3.py `refactor strfalse: PASS`.

### shadow-perf
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |

Strengths
- Strong execution gate (Pre-UAT only, L3/L4) (SKILL.md:8-14); EXPLAIN ANALYZE executes-statement warning (SKILL.md:75) — correct per PostgreSQL docs.
- Compiler now refuses unselected/undocumented operations, required params, auth, and unresolved bodies (openapi_to_k6_scaffold.mjs:42-76); exact-status checks; no derived target or credentials.
- Correct k6 open-model guidance (`constant-arrival-rate`, `preAllocatedVUs`, `dropped_iterations`) (references/01:13,86).

Gaps
- MEDIUM — All three generated profiles are identical (`vus: 1, iterations: 1`) (openapi_to_k6_scaffold.mjs:118); files named `02-load-pre-uat` / `03-stress-spike` contain no load model. Documented at SKILL.md:66 but the naming invites misuse.
- MEDIUM — Generated scripts only accept loopback `BASE_URL` (scaffold L127), so the "Pre-UAT/Staging gate" tool cannot target staging without hand edits; no documented path to the approved staging adapter.
- LOW — Router: "why is this query slow EXPLAIN" -> none (orchestrator data); description competes with shadow-db for EXPLAIN.
- LOW — 1 URL total; references cite "Grafana k6 Documentation" without URL/date (references/01:120).

Prior-review defect status: FIXED (probe above).

Upgrade actions
1. Emit profile-specific `scenarios` (constant/ramping-arrival-rate) gated by `APPROVED_PROFILE`, or rename to `journey-template.k6.js`.
2. Add an allowlisted-staging-origin option bound to an approval record.
3. Link https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/ with last-verified date.

Test/self-test run: `node --test shadow-perf/tests/scaffold.test.mjs` 13/13 pass; `--selftest` SELFTEST_OK; POST-only probe as above.

### shadow-uat
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.50 | MEDIUM |

Strengths
- Sound defect-vs-CR separation and severity-first gate (SKILL.md:41-44,58); honest NOT TESTED labeling (SKILL.md:59; evaluations UAT-02).
- Batch/headless evidence path added (SKILL.md:57).

Gaps
- HIGH — Verification tooling is tautological: no scripts/, and the only test defines `check_query_param_effect` and `reconcile_headless_batch_uat` inside the test file and tests them (tests/test_batch_uat_and_param_drift.py:6-30). Nothing the skill ships is exercised. evaluations.md "Verification Status" overstates this.
- MEDIUM — Description lacks "Do NOT use" and boundary vs shadow-browser/shadow-test/shadow-handover (SKILL.md:3).
- LOW — Header "12-Domain Adversarial Scenarios" lists 4 items (SKILL.md:46-51); reference still says "applicable 9-state UI" (references/02:17,67).
- LOW — Cross-skill links into shadow-design external-upstreams (SKILL.md:47,51) resolve, but couple UAT to another skill's vendored packs.
- LOW — 0 URLs; ISO/IEC/IEEE 29119 or ISTQB acceptance testing not cited.

Prior-review defect status: FIXED (UI/202 now "applicable"; relative links resolve).

Upgrade actions
1. Move the two functions into `scripts/uat_evidence_verifier.py`, import from tests, add RTM coverage checker.
2. Add Do-NOT clause; fix the 12-domain header.
3. Cite ISTQB CTFL acceptance testing / ISO/IEC/IEEE 29119-3 for test documentation.

Test/self-test run: unittest Ran 1, OK (self-contained).

### shadow-release
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | MEDIUM |

Strengths
- Expand-only migration-before-code and N-1 skew safety (SKILL.md:37; references/02); rollback vs forward-fix after destructive DDL (SKILL.md:48).
- Verifier checks SemVer major bump on breaking change, floating tags, destructive DDL ordering, deterministic canary bucketing (release_readiness_verifier.py:54-115).

Gaps
- MEDIUM — Gate 3 in SKILL.md is unconditional ("/shadow-perf baseline and /shadow-uat ... passed", SKILL.md:35) while reference says "where applicable" (references/01:18) — inconsistent; verifier requires `staging_uat_passed` and `backup_or_recovery_point_verified` for every release with no N/A path (scripts/release_readiness_verifier.py:74-85), so a library release cannot pass honestly.
- MEDIUM — Gates are caller-asserted booleans; no evidence references (L84).
- LOW — Smoke still hard-codes `/readyz` (SKILL.md:47; references/03:77).
- LOW — `canary.enabled:"false"` treated as enabled (L104) — fail-safe direction, but sloppy typing.
- LOW — 0 URLs (semver.org 2.0.0 not linked).

Prior-review defect status: PARTIAL (Gate 4 now allows previous immutable version, SKILL.md:36; perf/UAT/`/readyz` still universal).

Upgrade actions
1. Add release-type profiles (service/static/library) with `NOT_APPLICABLE` + reason per gate.
2. Require `evidence_ref` per gate.
3. Link https://semver.org/spec/v2.0.0.html, Google SRE "Canarying Releases" chapter.

Test/self-test run: unittest Ran 2, OK.

### shadow-compat
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 4 | 3 | 2 | 3 | 3 | 2 | 2.88 | MEDIUM |

Strengths
- Correct deploy order: backward-compatible -> consumers first, forward -> producers first (SKILL.md:30-31), matches Confluent Schema Registry semantics.
- RFC 9745 `Deprecation: @<unix>` Structured Field Date, `rel="deprecation"`, RFC 8594 IMF-fixdate Sunset, 410 after drain (SKILL.md:34; references/02:12-17) — verified correct.
- Semantic-break list (sort flips, null vs omitted, enum exhaustion) beyond AST diff (SKILL.md:32).

Gaps
- MEDIUM — `tests/test_consumer_replay.py` defines and tests its own `read_v1` (L5-11); it is cited in SKILL.md:10 as the skill's "honest consumer payload replay" tool, but no shipped replay tool exists.
- MEDIUM — Router miss: "bump react 18 to 19 safely" -> none (orchestrator), although this is the skill's core upgrade use case.
- LOW — `legacy_route_hits_total{consumer_id}` as a Prometheus label (references/02:79) — acceptable only if consumer set is bounded; say so (conflicts with shadow-observe SKILL.md:46).
- LOW — 2 URLs; no rfc-editor links/dates.

Prior-review defect status: N/A.

Upgrade actions
1. Ship a `consumer_replay.py` that replays stored fixtures against strict/tolerant decoders; test it.
2. Add "upgrade/bump/migrate major version" trigger phrases.
3. Link rfc-editor.org/rfc/rfc9745 and rfc8594.

Test/self-test run: unittest Ran 5, OK.

### shadow-sec
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 3 | 2 | 4 | 3 | 3 | 2.88 | MEDIUM |

Strengths
- Explicit anti-fabrication rule: `v5.0.0-C.S.R` IDs, `UNVERIFIED` fallback (SKILL.md:13); ASVS 5.0 has V1-V17 (correct).
- Strong safety boundaries: DAST/fuzz L3, prod containment L4 (SKILL.md:16); third-party skill pre-install gate with tests.
- Best provenance in group (35 URLs).

Gaps
- HIGH — Shipped test maps tenant-ownership authorization to `ASVS-5.0-V4.1.1` (tests/test_tenant_export_and_controls.py:6,18,22). In ASVS 5.0.0, V4 is "API and Web Service" and 4.1.1 is the Content-Type header requirement (verified on OWASP/ASVS 5.0/en/0x13-V4-API-and-Web-Service.md); authorization is V8 (e.g., v5.0.0-8.2.1). This is exactly the ASVS-4-vs-5 mix-up the skill's own reference warns about (references/02:56).
- HIGH — `check_finding_report` only regex-matches a locator family: `"ASVS 5.0 lol"`, `v5.0.0-99.99.99`, `CWE-0`, `ASVS-5.0-V4.1.1` all pass (scripts/appsec_control_verifier.py:167-169, `CONTROL_ID_RE`). No catalog resolution, so the "Zero Fabricated IDs" promise is not enforced.
- MEDIUM — A clean report with zero findings fails ("must include >= 1 structured finding", L157-159), pushing agents toward manufacturing findings.
- LOW — Description is long and keyword-stuffed (SKILL.md:3); trigger overlap with shadow-auth on CORS/CSRF.

Prior-review defect status: STILL OPEN — IDs not validated against a pinned catalog (probe p3.py output above).

Upgrade actions
1. Vendor the official ASVS 5.0.0 CSV/JSON (github.com/OWASP/ASVS, tag v5.0.0) with sha256 and resolve every `v5.0.0-*` ID; reject unknown IDs.
2. Fix the test to `v5.0.0-8.2.x` (authorization) and add a probe that `v5.0.0-4.1.1` is rejected for authz findings.
3. Allow `findings: []` with `scope` + `methods` evidence -> `PASS_NO_FINDINGS`.

Test/self-test run: unittest Ran 9, OK (20.7 s); p3.py outputs listed.

### shadow-supplychain
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3.13 | GOOD |

Strengths
- Consumer trust model: receipt bound to local artifact sha256 and paired (issuer, builder_id, build_type, verifier) tuple (scripts/supplychain_sbom_gate.py:141-157); honest OFFLINE/NOT_RUN -> INCOMPLETE.
- SLSA v1.2 "Verifying artifacts" cited (SKILL.md:58) — verified Approved on slsa.dev and it requires builder id, buildType, subject-digest checks.
- Precise boundaries (SKILL.md:3,9).

Gaps
- MEDIUM — Doc/code mismatch: SKILL.md:58 says waiver `expires_on`; code reads `expires_at` (scripts/supplychain_sbom_gate.py:122). Agents following the doc produce a ValueError.
- MEDIUM — Typosquat heuristic produces false FAIL on legitimate packages: `preact` -> "resembles 'react'" (also `request`/`requests`), with only 8 popular names (POPULAR_ECOSYSTEM_LIBS) — low recall, avoidable false positives, and it is an error not a warning.
- LOW — Receipt authenticity relies on "consumer-controlled CI channel" (SKILL.md:53); no receipt signature/hash pinning.
- LOW — Few dated sources (7 URLs, none with last-verified).

Prior-review defect status: FIXED.

Upgrade actions
1. Align field name (`expires_on` vs `expires_at`) and add a test from the documented example.
2. Downgrade lookalike to `REVIEW` with an allowlist; seed from a maintained top-N list per ecosystem.
3. Add last-verified dates for SLSA v1.2, CycloneDX 1.6/1.7, SPDX 3.0.

Test/self-test run: unittest Ran 6, OK (12.3 s); p2.py outputs above.

### shadow-privacy
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |

Strengths
- UU PDP citations spot-checked correct: Pasal 4(2)/(3) categories, Pasal 20(2) six lawful bases, Pasal 46 3x24h to subject + lembaga, Pasal 56(2)/(3)/(4) cascade, Pasal 57 up to 2% annual revenue (SKILL.md:12-15).
- Explicit legal-escalation boundary (SKILL.md:16); erasure assessor tested via real import (tests/test_erasure.py:5-6) and distinguishes receipts vs pending retention.

Gaps
- MEDIUM — States "mandatory `AES-256-GCM`+KMS column encryption" for Data Spesifik inside a statutory-classification bullet (SKILL.md:12). UU PDP does not mandate a specific algorithm; present as engineering control, not legal requirement.
- MEDIUM — No status note on implementing regulation (RPP PDP) / Lembaga PDP establishment; only a "monitor" line in references/05:88.
- LOW — Description lacks explicit "Do NOT use" vs shadow-sec/shadow-analytics consent (SKILL.md:3).
- LOW — 2 URLs; no link to JDIH UU 27/2022 text or GDPR EUR-Lex, no last-verified dates.

Prior-review defect status: PARTIAL — erasure assessment now separates receipts/process; scanner findings vs controller decisions not yet separated in `--scan` output.

Upgrade actions
1. Reword encryption as recommended control mapped to Pasal 35/39 "security measures".
2. Add dated links: peraturan.bpk.go.id UU 27/2022, eur-lex GDPR 2016/679; note PP status as-of date.
3. Add Do-NOT clause.

Test/self-test run: unittest Ran 2, OK.

### shadow-ops
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 3 | 2 | 1 | 2.50 | MEDIUM |

Strengths
- Correct Docker/ufw port-publishing trap and 127.0.0.1 binding (SKILL.md:46; references/01:62); `ssl_protocols TLSv1.2 TLSv1.3`, `http2 on` (current nginx syntax).
- L0 vs L4 split for plan vs apply / restarts (SKILL.md:11); capability-based parity (SKILL.md:43).
- SKILL.md routes into vendor sheets sensibly: one row per sheet with a "Load When" trigger (SKILL.md:30-35), and playbooks 01/02 point to the matching vendor file.

Gaps
- HIGH (licensing) — 5 OWASP Cheat Sheets vendored verbatim (`references/vendor/OWASP_*.md`, ~2300 lines) are CC BY-SA 4.0 (verified on github.com/OWASP/CheatSheetSeries). No license text, no attribution block, no source URL/commit, no change notice; repo declares "MIT — copy, fork and adapt freely" (README.md:187-189), which conflicts with share-alike. README credit is one vague line (README.md:176).
- MEDIUM (licensing) — H5BP nginx confs (MIT) vendored without the MIT notice or commit SHA.
- MEDIUM — Vendored sheets are unpinned snapshots of living documents with 28 broken relative links (e.g., `Secrets_Management_Cheat_Sheet.md` from OWASP_CI_CD_Security_Cheat_Sheet.md); no last-fetched date, no update path (skill_vendor_sync.py tracks only shadow-design packs).
- MEDIUM — `ops_hardening_verifier.py` misses long-form compose ports (`- target: 5432 / published: 5432` -> no `PUBLIC_INTERNAL_DB_PORT`) (scripts/ops_hardening_verifier.py:23-26).
- MEDIUM — SKILL.md:43 cites `test_ops_profiles_and_plan.py` as evidence, but that test defines its own `select_ops_profile` (tests/test_ops_profiles_and_plan.py:6-9) — no shipped code is exercised.
- LOW — Router: none of the orchestrator misses directly, but description is generic DevOps keyword list.

Prior-review defect status: FIXED in SKILL.md (capability parity), tooling still unbacked.

Upgrade actions
1. Add `references/vendor/LICENSES.md` (CC BY-SA 4.0 + MIT texts), per-file header with source URL, commit SHA, fetch date, "modified: no"; record in a provenance lock and README credits; mark share-alike scope so the MIT claim excludes those files.
2. Rewrite relative links to absolute cheatsheetseries.owasp.org URLs or trim to cited sections.
3. Parse compose YAML (yaml lib or project parser) instead of line regex; add long-form/IPv6 probes.
4. Move profile logic into a script and test it.

Test/self-test run: unittest Ran 10, OK (6.7 s); p5.py long-form ports -> no DB-port violation.

### shadow-observe
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3.00 | GOOD |

Strengths
- Clear ownership split with shadow-ops/debug/maintain/perf/finops/analytics (SKILL.md:8-11).
- Correct SRE Workbook multi-window burn rates (14.4x 1h/5m, 6x 6h/30m, short window = 1/12) and 99.9%/28d = 40.32 min (SKILL.md:33,38; references/01:15-24).
- Verifier catches nested sensitive field names (`req.headers.authorization` flagged).

Gaps
- MEDIUM — Latency SLI conflates percentile and proportion: "Proportion of requests <= 400ms (`p95`)" (SKILL.md:34). An SLI is a ratio of good events; p95 is a different statistic.
- MEDIUM — Log verifier misses free-text PII: message `"user NIK 3201234567890001 email a@b.co"` -> only the header flagged (scripts/telemetry_hygiene_verifier.py:157-185), though SKILL.md:47 promises `nik` stripping.
- LOW — Workbook burn factors derive from a 30-day window; with 28d, 14.4x = 2.14% per hour, not 2% (references/01:22). Note the derivation.
- LOW — 3 URLs, no last-verified dates (OTel semconv versions move fast).

Prior-review defect status: N/A (prior rated acceptable).

Upgrade actions
1. Rephrase latency SLI as `good = duration <= 400ms` ratio; keep percentiles for dashboards.
2. Add value-pattern scanning (NIK 16-digit, email, JWT) to log sample check with precision probes.
3. Cite sre.google/workbook/alerting-on-slos and OTel semantic-conventions version with date.

Test/self-test run: unittest Ran 4, OK.

### shadow-resilience
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.88 | MEDIUM |

Strengths
- Honest RTO/RPO: business-verified end time and source-timeline checkpoint, "mark RPO unmeasured" (SKILL.md:36); drill_evidence.py uses strict `is True` and offset-aware timestamps (scripts/drill_evidence.py:8-41).
- Isolation rule and erasure-tombstone replay after restore (SKILL.md:30,35) — expert-level and rarely covered.

Gaps
- MEDIUM — `test_restore_rehydration.py` simulates with in-test dicts (L8-30); no shipped replay tool or check that tombstones were replayed before traffic.
- MEDIUM — drill_evidence.py reports measured RTO/RPO but never compares against the contractual target or flags breach (L18-42).
- LOW — `docker rm -f -v` cleanup (SKILL.md:37) vs shadow-quality's ownership-ledger model — not cross-referenced (no `shadow.repo`/`shadow.run` labels).
- LOW — 0 URLs (ISO 22301, AWS/Google DR guides not linked).

Prior-review defect status: FIXED.

Upgrade actions
1. Add `rto_target_seconds`/`rpo_target_seconds` and a `tombstones_replayed_before_traffic` receipt to drill_evidence.py.
2. Align container labels with shadow-quality ledger contract.
3. Cite ISO 22301:2019 and dated vendor DR docs.

Test/self-test run: unittest Ran 5, OK.

### shadow-finops
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 2.75 | MEDIUM |

Strengths
- FinOps Framework phases (Inform/Optimize/Operate) and current 4 domains, FOCUS `BilledCost`/`EffectiveCost`/`ChargeCategory`/`PricingCategory` correct (SKILL.md:11-12,20); OWASP LLM10:2025 = Unbounded Consumption correct.
- Thinking tokens billed as output — estimator math verified (24,570 / 38,250 USD for the documented example).

Gaps
- MEDIUM — Description has no "Do NOT use" and overlaps shadow-ai-eng (prefix caching) (SKILL.md:3).
- MEDIUM — Estimator omits cache-write premium (e.g., 1.25x/2x input on Anthropic cache writes) so savings are overstated (scripts/finops_cost_auditor.py:113-125); no input validation: `--cache-hit-rate 1.5` accepted and reports 121.5 USD "savings" on 135 USD.
- MEDIUM — `tests/test_finops_reconciliation.py` defines and tests its own `reconcile_invoice_allocation` (L7-25); the shipped auditor is not unit-tested there.
- LOW — "75%-95% cached input discounts" (SKILL.md:23) is provider-specific; OpenAI tiers have been 50-90%. Needs dated provider table.

Prior-review defect status: N/A.

Upgrade actions
1. Add `--cache-write-multiplier`, validate 0<=rate<=1, add precision probes.
2. Move reconciliation into the script and import it in tests.
3. Add Do-NOT clause; provider price table with last-verified date (finops.org/framework, focus.finops.org v1.2).

Test/self-test run: unittest Ran 1, OK; estimator probes as above.

---

## Cross-cutting observations

1. **Self-contained "tautological" tests inflate verification evidence.** Six test files test functions defined inside the test itself, not shipped code: shadow-uat/tests/test_batch_uat_and_param_drift.py:6-30, shadow-finops/tests/test_finops_reconciliation.py:7, shadow-ops/tests/test_ops_profiles_and_plan.py:6, shadow-compat/tests/test_consumer_replay.py:5, shadow-resilience/tests/test_restore_rehydration.py, shadow-sec/tests/test_tenant_export_and_controls.py:11. SKILL.md files then cite these as tooling (ops SKILL.md:43, compat SKILL.md:10, resilience SKILL.md:35). The sec one also ships a wrong ASVS 5.0 mapping (V4.1.1 for authorization).
2. **Truthiness / self-assertion validators persist outside the three fixed tools.** Supplychain/quality/perf were fixed, but the same class remains: refactor (`"false"` -> PASS), test hygiene (`uses_fake_timers:"false"` -> clean; comment satisfies Docker check), debug gate (`root_cause:"x"` -> PASS), sec control_id regex (`"ASVS 5.0 lol"` passes). Apply the supplychain pattern repo-wide: strict typing (`is True`), evidence references bound to hashes/commits, catalog resolution.
3. **Provenance and licensing are the weakest dimension.** 14/15 skills have zero "last verified" dates; 7 have <=2 URLs. Vendored third-party content in shadow-ops (OWASP CC BY-SA 4.0, H5BP MIT) and shadow-test (Goldberg MIT) has no license notice, source commit, or fetch date, is outside the `UPSTREAM_PROVENANCE.json` + `skill_vendor_sync.py` mechanism used for shadow-design, carries 43 broken relative links, and sits under a repo-wide "MIT — copy, fork and adapt freely" claim that conflicts with share-alike. Also 4 of 15 descriptions lack "Do NOT use" clauses (quality, uat, privacy, finops).
