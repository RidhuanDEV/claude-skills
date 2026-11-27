# Shadow Army Skill Enhancement Review (59 skills)

**Date:** 2026-11-26 · **Commit reviewed:** `1dbe3b5` (clean `main`) · **Mode:** read-only review (`L0`) plus bounded offline self-tests and unit tests (`L1`)
**Question:** If an agent loads this skill, will it act and know like a senior professional engineer in that domain?

## 1. Verdict

| Grade | Count | Skills |
|---|---:|---|
| **PERFECT** | 0 | none |
| **GOOD** | 12 | shadow-browser, shadow-accessibility, handoff, shadow-handover, shadow-supplychain, shadow-seo, shadow-debug, shadow-perf, shadow-privacy, shadow-observe, shadow-pmo, shadow-grc |
| **MEDIUM** | 41 | every other skill except the six below |
| **BAD** | 6 | shadow-monarch, shadow-auth, shadow-concurrency, shadow-analytics, shadow-integrate, shadow-email |

The knowledge in the suite is broad and mostly correct. Senior-level depth (D2) averages close to 3 out of 4. The suite fails on three things:

- **Its own verification tooling.** Six verifiers return PASS on unsafe input.
- **Whether the right skill gets selected at all.** Descriptions are dropped from the host's skill listing, and the router misses realistic prompts.
- **Provenance.** Sources have no "last verified" dates, several standards are out of date, and vendored content has no license notices.

None of the six BAD grades comes from weak domain knowledge. Each comes from a critical defect: a shipped gate that says PASS, CONFIRMED or SHIP when it should block. These skills are BAD because the rubric treats a false PASS on a security, money, approval or release gate as critical, whatever the average.

### Fix these five first

| # | Finding | Severity | Evidence (reproduced in this review) |
|---|---|---|---|
| 1 | **Fail-open boolean coercion in gates.** `bool("false") == True` | CRITICAL | `shadow-auth/scripts/auth_policy_verifier.py:88`: privileged `/admin/users` with `"public":"false"` gives `passed: True`. `shadow-monarch/scripts/official_first_verifier.py:135-141`: replacing `file:../sdk/sso-client` with a lookalike gives **PASS** with string `"false"` flags and **BLOCKED** with real `false`. 24 script files use the `bool(x.get(...))` pattern (§4.1). |
| 2 | **Money reconciliation confirms the wrong transaction** | CRITICAL | `shadow-integrate/scripts/reconcile_unknown.py:19-22` returns `RECORD_CONFIRMED` without comparing account, amount, currency or provider transaction ID, although SKILL.md:14 requires that binding. |
| 3 | **Specialist skills are invisible to auto-selection** | HIGH | In this Claude Code session, 10 descriptions were dropped from the skill listing (realtime, refactor, release, resilience, search, sec, seo, supplychain, test, uat). Descriptions total 18,862 characters. Claude Code's budget is 1% of the context window and it drops whole descriptions (see Sources). |
| 4 | **The router is overfitted to its own self-test** | HIGH | `skill_router.py --self-test` passes 154/154. On fresh prompts, routing was correct for 18/25 (orchestrator probe set), 11/25 (grader D set) and about 10/15 (grader A set). |
| 5 | **"Test theater"** | HIGH | 20 test files never import, call or shell out to their skill's scripts (heuristic scan). Graders confirmed at least 13 that check a function defined inside the test. They pass forever and catch nothing. |

## 2. Method and evidence boundary

**Rubric.** Each skill was scored 1–4 on 8 dimensions:

| Dimension | What it measures |
|---|---|
| D1 | Trigger precision |
| D2 | Expert knowledge depth |
| D3 | Correctness and currency (at least 3 claims spot-checked against primary sources) |
| D4 | Procedural operability |
| D5 | Verification tooling (falsifiable oracles, probed with adversarial inputs) |
| D6 | Safety and boundaries |
| D7 | Token efficiency |
| D8 | Provenance and maintainability |

**Grade thresholds:**

| Grade | Condition |
|---|---|
| PERFECT | Average ≥ 3.6 and no dimension below 3 |
| GOOD | Average ≥ 3.0 and no dimension at 1 |
| MEDIUM | Average ≥ 2.2 |
| BAD | Average < 2.2, **or** any critical defect: a false PASS on a security, money, approval or release gate, or wrong security or legal advice |

**Who did what:**
- **Grading.** Four independent graders read SKILL.md, references, scripts, tests and evaluations.md for 15, 15, 15 and 14 skills. Every negative finding cites `file:line`.
- **Research.** A fifth agent fetched primary sources for skill-authoring rules, standards currency and OSS tooling.
- **Calibration.** The orchestrator reproduced each CRITICAL claim before accepting it, and moved two skills to BAD under the same rule: monarch and integrate.

**What was executed:**
- Every `tests/` suite: 46 Python suites OK, plus `shadow-perf` 13/13 under `node --test shadow-perf/tests/scaffold.test.mjs`.
- `evals/` (32 tests OK).
- The router `--self-test` and `--audit-descriptions`. Both pass, and neither measures selection.
- About 65 fresh router probes.
- Adversarial probes against every verifier that prior reviews had flagged, and many new ones.

**Not measured:**
- Live model behaviour with each skill loaded compared with a no-skill baseline, on Claude, Codex or Gemini.
- Trigger rates in the host's own skill selection, beyond the one observed listing truncation.
- `shadow-video`'s self-test, which needs `npm ci` and browsers.
- Real project outcomes.

Grades describe the shipped source and tools, not measured agent output.

> Side effect to note: running `shadow-doc/scripts/doc_scaffold.py --acceptance-suite` regenerated reports under `shadow-doc/output/`. That folder is gitignored, so no tracked file changed, but the tool writes into the skill folder. Upgrade action under shadow-doc.

## 3. Scoreboard (all 59)

Scale 1–4. D1 trigger · D2 depth · D3 correctness · D4 procedure · D5 verification · D6 safety · D7 tokens · D8 provenance.

### 3.1 BAD: fix before relying on the skill

| Skill | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Critical defect |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow-monarch | 2 | 3 | 3 | 3 | **1** | 4 | 1 | 1 | 2.25 | Its SSO-preservation and approval gate passes on string flags. Its routing generalizes poorly. SKILL.md is 39.8 KB. Its own count files disagree (README says 54 skills, SKILL.md says 59, the actual number is 59). |
| shadow-auth | 2 | 3 | 2 | 3 | **1** | 3 | 3 | 2 | 2.38 | `"public":"false"` lets a privileged route pass. The references claim ASVS 5.0 but use 4.0.3 chapter IDs. They present OAuth 2.1 as a standard; it is still a draft (-17). |
| shadow-concurrency | 3 | 3 | 3 | 2 | **1** | 2 | 3 | 2 | 2.38 | All-`"false"` flags give PASS as at-least-once with dedup. The "simulation" only re-reads the declared flags. |
| shadow-integrate | 2 | 3 | 3 | 3 | **1** | 3 | 3 | 2 | 2.50 | UNKNOWN-state reconciliation confirms an inquiry for a different account or amount. |
| shadow-analytics | 3 | 4 | 3 | 3 | **1** | 2 | 3 | 3 | 2.75 | Guardrail `"regressed":"true"` is ignored, giving SHIP_CANDIDATE. `srm_alpha:0` disables the SRM gate. Domain depth is the best in the suite (D2 = 4). |
| shadow-email | 3 | 4 | 2 | 2 | 2 | 3 | 4 | 3 | 2.88 | The DNS checker passes DKIM misaligned under `adkim=s`. It counts only top-level SPF lookups. It cites RFC 7489 and `pct`, but RFC 9989 (May 2026) obsoletes 7489. Its warm-up gates use Postmaster reputation dashboards that were retired in 2025. |

### 3.2 MEDIUM: usable, with material gaps

| Skill | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Top gap |
|---|---|---|---|---|---|---|---|---|---|---|
| antislop | 2 | 3 | 2 | 3 | 1 | 3 | 2 | 2 | 2.25 | "Large text = 18px+" is wrong. WCAG says 18pt ≈ 24px, or 14pt bold ≈ 18.66px. The only test checks itself. |
| shadow-cache | 2 | 3 | 3 | 2 | 2 | 3 | 2 | 1 | 2.25 | `"persistent_structure":"false"` skips the TTL rule. 0 citations. No ordered workflow. |
| antislop-copywriting | 2 | 3 | 3 | 3 | 1 | 3 | 2 | 2 | 2.38 | Promises Indonesian and error-message guidance and contains neither. Its em-dash rules contradict each other (`:357` vs `:390`). |
| shadow-architect | 3 | 3 | 2 | 3 | 1 | 3 | 3 | 1 | 2.38 | Its test checks a function defined inside the test. Topology thresholds are presented as facts. 0 citations. |
| shadow-test | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 1 | 2.38 | Vendors a 2,159-line MIT guide with no notice and 15 broken links. The hygiene checker accepts `"false"` and comments. |
| antislop-ui | 2 | 3 | 3 | 3 | 1 | 3 | 2 | 3 | 2.50 | Repeats antislop core. No description boundary. No checker. |
| shadow-bootstrap | 3 | 2 | 3 | 3 | 2 | 3 | 3 | 1 | 2.50 | The `http` preview omits the config, logging and shutdown that SKILL.md requires. 0 citations. Wrong script path in ref 02. |
| shadow-maintain | 2 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.50 | No script. The test checks itself. The SLA matrix is hard-coded instead of taken from the contract. "Prod down, users cannot login" routes to auth. |
| shadow-ops | 3 | 3 | 3 | 3 | 2 | 3 | 2 | 1 | 2.50 | Vendors 5 OWASP cheat sheets (CC BY-SA 4.0) and 3 H5BP configs (MIT) with no license or attribution, under a repo-wide MIT claim. Long-form compose ports slip past the DB-port check. |
| shadow-uat | 2 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.50 | No scripts. The test checks itself. No "Do NOT use" clause. |
| antislop-code | 2 | 3 | 3 | 3 | 1 | 3 | 4 | 2 | 2.63 | Nothing proves the code is unchanged after comment cleanup. Tells agents to drop issue links from workaround comments. Never routed. |
| context7 | 3 | 2 | 3 | 3 | 1 | 3 | 4 | 2 | 2.63 | Its test resolves the version from a `package.json` range, which its own SKILL.md:13 forbids. |
| modern-web-guidance | 3 | 3 | 3 | 2 | 1 | 2 | 4 | 3 | 2.63 | Runs `npx -y modern-web-guidance@1.0.1` without the repo's own pre-install audit. The pin is stale (1.0.2 exists). |
| shadow-ai-eng | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 2 | 2.63 | No ordered workflow. Checks only declared config. MCP guidance assumes the `initialize` handshake, which the current MCP spec (2026-07-28) removed. |
| shadow-discovery | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.63 | Its single test checks its own regex. SKILL.md presents the full PRD as mandatory; one-question mode exists only in a reference. |
| shadow-modernize | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.63 | On empty input it recommends a strategy at Rp 3.9 B TCO from hidden defaults. SKILL.md says "8 dimensions" and lists 6. |
| shadow-quality | 2 | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 2.63 | The 7 checks apply to every repo, including OpenAPI and Postman parity when neither exists. No "Do NOT use" clause. |
| shadow-api | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | The leak check passes a raw Postgres constraint error and a `node_modules` path inside `detail`. |
| shadow-db | 2 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.75 | `SET NOT NULL` is not flagged. A commented-out `SET lock_timeout` satisfies the check. ERD prompts route to the RLS playbook. |
| shadow-domain | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | Reads `"expected_allowed":"false"` as true. 3 tests. |
| shadow-realtime | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 1 | 2.75 | 0 citations. Trace events marked `blocked` are self-reported by the trace author. |
| shadow-design | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2.75 | The method resolver covers 14 of 216 modules (`design-token` returns UNSUPPORTED). The main pack has no license and comes from a local Downloads folder. |
| shadow-illustration | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2.75 | SVGO config written for v3; v4.1 is current. Duplicate tables. Encoding corruption in the source register. |
| antislop-layoutmobile | 3 | 3 | 3 | 3 | 1 | 3 | 4 | 2 | 2.75 | No 320px reflow rule (SC 1.4.10), no 24px minimum target (SC 2.5.8), no iOS 16px input rule, and no tooling. |
| shadow-mobile | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | Example uses targetSdk 35; Play has required API 36 since 2026-08-31. The test does not import the gate. |
| shadow-presales | 3 | 3 | 2 | 3 | 2 | 4 | 3 | 2 | 2.75 | Perpres 46/2025 thresholds are uncited and could not be corroborated. TKDN tiers are merged. TCO accepts empty input as "reconciled". |
| shadow-ea | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2.75 | Indonesian portfolio prompts route to monarch. No boundary against architect. 0 URLs. |
| shadow-release | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | No NOT_APPLICABLE path: a library release still requires UAT and a backup. SKILL.md and its reference disagree on Gate 3. |
| shadow-finops | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 2.75 | The estimator omits the cache-write premium and accepts a hit rate of 1.5. The test checks itself. |
| antislop-human | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 2.88 | Same large-text error. The contrast script is correct but has no unit test. |
| shadow-video | 3 | 3 | 3 | 4 | 2 | 2 | 4 | 2 | 2.88 | `references/recording-environment.md:28-33` documents getting past Cloudflare Turnstile bot detection. Use Turnstile test sitekeys instead. No offline tests. |
| shadow-doc | 2 | 3 | 3 | 3 | 4 | 3 | 3 | 2 | 2.88 | Strong tests (58/58, 16/16, 14 unit). "Regenerate SRS docx" routes to discovery. Template and test counts disagree. Writes into the skill folder. |
| shadow-data | 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 2.88 | Router misses "NOT NULL on 50M rows". No contract-phase readiness schema. |
| shadow-search | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2.88 | Tenant-only ACL evidence passes with no warning. |
| shadow-eval | 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 2.88 | A dataset of only abstain or isolation samples gives PASS. Cites OWASP LLM **2025**; the 2026 edition is out. No "Do NOT use" clause. |
| shadow-refactor | 3 | 3 | 3 | 4 | 2 | 3 | 3 | 2 | 2.88 | `precedents_inspected:"false"` passes. |
| shadow-compat | 3 | 3 | 4 | 3 | 2 | 3 | 3 | 2 | 2.88 | The cited replay "tool" is a test with its own fixture. Router misses "bump react 18 to 19". |
| shadow-sec | 3 | 3 | 2 | 3 | 2 | 4 | 3 | 3 | 2.88 | A shipped test maps authorization to `ASVS-5.0-V4.1.1`, which in ASVS 5.0 is the Content-Type requirement. The ID check accepts "ASVS 5.0 lol". No OWASP Agentic Top 10. |
| shadow-resilience | 3 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.88 | `drill_evidence.py` never compares the drill result with the RTO/RPO targets. The rehydration test checks itself. |
| shadow-git | 3 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.88 | `--selftest` only reports the git version. Tests never import the orchestrator. One test is an off-domain discount-rounding test. |
| shadow-plan | 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 2.88 | Planning prompts route to discovery. The DoD requires API status-code tests even for batch or copy changes (SKILL.md:61). |

### 3.3 GOOD: path to PERFECT is mostly D5 and D8

| Skill | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | What blocks PERFECT |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow-browser | 4 | 3 | 3 | 3 | 3 | 4 | 4 | 2 | 3.25 | No console or page-error assertion field. Viewports start at 375px, not WCAG's 320px. Undated sources. |
| shadow-accessibility | 4 | 3 | 3 | 2 | 3 | 3 | 4 | 3 | 3.13 | No WCAG-EM ordered audit or report template. Misses empty buttons and links without `href`. |
| handoff | 4 | 3 | 3 | 4 | 3 | 3 | 3 | 2 | 3.13 | No secret or PII redaction before `save_handoff`. Its 5 scenarios have never been run end to end. |
| shadow-handover | 4 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.13 | Names no SBOM standard. The partial-cutover test does not exercise the script. |
| shadow-supplychain | 4 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3.13 | Docs say `expires_on`, code reads `expires_at`. Flags `preact` as a typosquat. |
| shadow-seo | 4 | 3 | 3 | 2 | 2 | 3 | 4 | 3 | 3.00 | False FAILs on rules Google does not have (x-default, length limits, a single h1). Parses JSON descriptions instead of real HTML. |
| shadow-debug | 4 | 3 | 3 | 4 | 2 | 3 | 3 | 2 | 3.00 | The hypothesis gate accepts `root_cause:"x"` with an empty hypothesis. |
| shadow-perf | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | All 3 profiles are 1 VU / 1 iteration. Only a loopback `BASE_URL` is allowed, with no approved staging path. |
| shadow-privacy | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | Presents AES-256-GCM as legally mandatory under UU PDP. No dated legal sources. |
| shadow-observe | 4 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3.00 | The latency SLI mixes up a percentile with a good-events ratio. Free-text NIK and email in logs are not flagged. |
| shadow-pmo | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | No tests/ folder. The shared-dependency CR double-count is still unhandled. No PMI citations. |
| shadow-grc | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | Flags in-flight licensing that the OJK FAQ exempts. Accepts zero findings as valid. |

## 4. Cross-cutting findings

### 4.1 CRITICAL: fail-open truthiness in verifiers (one bug class, repo-wide)

Python `bool("false")` is `True`. Verifiers read agent-authored JSON, so a string flag silently inverts the gate. The prior review (2026-11-18) fixed this in `shadow-realtime` and `shadow-supplychain` only.

**Scope.** 24 script files contain `bool(<dict>.get(...))`:
- analytics, auth, cache ×6, compat ×3, concurrency ×5, doc ×9
- domain, email, grc, modernize, monarch consulting-core
- `execution_approval_gate` ×3, `official_first_verifier` ×9, `skill_router` ×2
- observe, plan, pmo ×6, presales ×3, `shadow_gate` ×3
- release, seo, test

**Direction matters:**
- `execution_approval_gate.py:105,117` coerces `is_mutation` and `is_destructive`. These fail **safe**: more requests are treated as destructive.
- `official_first_verifier.py:114,135,137,141` and `auth_policy_verifier.py:88` fail **open**.

**Confirmed false PASS:**

| Skill | Input | Result |
|---|---|---|
| auth | `"public":"false"` | privileged route passes |
| monarch | SSO lookalike replacement with string `"false"` flags | PASS |
| concurrency | all safety flags `"false"` | PASS as at-least-once with dedup |
| analytics | guardrail `"regressed":"true"` | SHIP_CANDIDATE |
| cache | `"persistent_structure":"false"` | TTL rule skipped |
| domain | `"expected_allowed":"false"` | read as true |
| refactor | `precedents_inspected:"false"` | passes |
| test hygiene | `"false"` or a comment | passes |

**Fix (one change for all of them):**
1. Add a shared `strict_bool(value, field)` helper that raises `INVALID_INPUT` unless `type(value) is bool`.
2. Replace every `bool(x.get(...))` on an evidence field with it.
3. Add a CI meta-test that feeds `"false"`, `"true"`, `0`, `1`, `null` and a missing key to every verifier's self-test fixture. It must assert that none of them yields PASS.

Do not fix this skill by skill again.

### 4.2 HIGH: skill selection fails before any knowledge is used

1. **The host listing budget is exceeded.**
   - Claude Code puts skill names and descriptions in a listing capped at **1% of the context window**. When that overflows, it **drops whole descriptions, starting with the least-invoked skills**. Each entry is also capped at 1,536 characters.
   - Codex caps its skill list at **2% of the context window, or 8,000 characters**. It shortens descriptions first, then omits skills.
   - This suite has 18,862 characters across 59 descriptions, about 320 per skill. On Codex's 8,000-character fallback that is about 135 per skill (estimate).
   - Observed: shadow-sec, shadow-test, shadow-release, shadow-uat and six others appeared with no description, so they fire only when invoked by name.
2. **The orchestrator description is a catch-all.** "Use when implementing, debugging, refactoring, reviewing, designing, or auditing…" wins generic prompts, then hands off to a router that generalizes poorly.
3. **The router is overfitted.**
   - `skill_router.py` is a 2,466-line hand-maintained regex table. Its 154 self-test probes were written alongside the patterns.
   - **Fresh probes that returned no specialist:**
     - "migrate column email to NOT NULL in 50M row table" (should be data)
     - "optimize LCP on next.js landing page" (should be modern-web-guidance)
     - "rotate JWT signing keys" (should be auth)
     - "our redis cache returns other tenant data" (should be cache)
     - "why is this query slow EXPLAIN" (should be db)
     - "bump react 18 to 19 safely" (should be compat)
     - "design pricing page hero section" (should be design/antislop)
     - "remove useless comments" (should be antislop-code)
     - "OTP mail in spam" (should be email)
     - "save handoff"
     - "ITMS-91053 privacy manifest" (should be mobile)
     - "Prisma 6 relation filter syntax" (should be context7)
   - **Fresh probes routed to the wrong specialist:**
     - "Pecah kebutuhan menjadi backlog" went to discovery, not plan.
     - "regenerate SRS docx" went to discovery, not doc.
     - "prod down, users cannot login" went to auth, not maintain.
   - **Right skill, wrong playbook:** Stripe webhook signature went to playbook 04, not 02. ERD went to the RLS playbook.
4. **Research agrees.** Routing on name and description alone loses 37–44 points of accuracy compared with seeing the skill body. Focused skills with at most 3 modules beat exhaustive bundles. Both results are [PREPRINT] (SkillRouter, SkillsBench).

**Fix:**
- **Cut descriptions.** Each description goes to ≤ 250 characters, with the trigger phrase first and one "Not for X (→ /sibling)" clause. Target ≤ 9,000 characters in total.
- **Narrow the monarch description** to multi-skill orchestration.
- **Keep rarely used skills off the listing.** Set them to `"name-only"` via `skillOverrides`.
- **Add a held-out trigger eval.** Use at least 3 English and at least 3 Indonesian prompts per skill, plus at least 2 should-not-trigger near-misses. These prompts must never be used to tune the regex. Report per-skill recall and precision.
- **Retrieve before matching.** Add BM25 or embedding retrieval over the descriptions as stage 1, ahead of the regex.
- **Measure host triggering.** Use `claude plugin eval` with a `tool_used: Skill` grader.

### 4.3 HIGH: tests that cannot fail

**Tests never touch shipped code.** 20 test files never import, call or shell out to the skill's scripts:
- antislop, context7, accessibility, architect, auth matrix, browser boundaries
- cache idempotency, compat replay, data backfill, discovery, doc conservation, finops
- grc, handover cutover, maintain, mobile, ops profiles, resilience, sec tenant-export, uat

Some of these simulate behaviour on purpose: data uses SQLite, and cache idempotency is a real simulation. At least 13 define the function under test inside the test file.

**Engines accept empty input and report success:**

| Skill | Empty input result |
|---|---|
| modernize | recommends ENCAPSULATE_RETAIN at Rp 3.9 B |
| presales | TCO of 0 marked "reconciled" |
| grc | zero findings accepted as valid |
| eval | abstain-only dataset gives PASS |

**Skills with no tests at all:** the 5 antislop sub-skills, modern-web-guidance, handoff (its MCP tests live in `mcp-servers/`), ea, modernize, pmo, presales and video.

**Fix:**
- Every test imports the shipped module.
- Every engine refuses empty or default-only input with `INSUFFICIENT_EVIDENCE`.
- Run mutation testing (mutmut) on `scripts/` in CI. A surviving mutant in a gate is a defect.

### 4.4 HIGH: standards drift and missing provenance

**Provenance is missing almost everywhere:**
- 0 of 33 specialist playbooks and 0 of 56 monarch reference modules carry a "last verified" date. Only shadow-illustration and one domain/ai-eng file have one.
- Six skills cite zero URLs: cache, realtime, architect, bootstrap, git and release. Four consulting skills cite zero URLs even for Indonesian law: pmo, presales, grc and ea.
- The same fact differs between skills. Large text is 18px in antislop and 24px in shadow-accessibility.

**Verified drift as of 2026-11-26:**

| Item in suite | Current authoritative state | Affected skills |
|---|---|---|
| OWASP Top 10 for LLM **2025** | **2026 edition** published 2026-08-04 (adds LLM03 Excessive Agency and LLM08 Hidden Context Exposure) | ai-eng (4 files), eval (6), finops, search, monarch, evals/, README |
| OWASP **Agentic** Top 10 | Not covered anywhere. "Top 10 for Agentic Applications for 2026" (ASI01–ASI10) was published 2025-12-09 | ai-eng, eval, sec, monarch AGENTS-MCP |
| MCP: `initialize` handshake, unpinned spec | **MCP 2026-07-28**: stateless, `server/discover`, Dynamic Client Registration deprecated in favour of Client ID Metadata Documents, `iss` validation (RFC 9207) | ai-eng ref 06:90-96, monarch AGENTS-MCP, the repo's own `mcp-servers/` |
| DMARC RFC 7489 with `pct` | **RFC 9989** (Proposed Standard, 2026-05-19) obsoletes 7489 and 9091 and drops `pct`. Reporting moved to RFC 9990/9991 | email |
| Postmaster domain and IP reputation gates | Dashboards retired in 2025; use Postmaster v2 Compliance Status | email |
| OAuth 2.1 presented as a standard | Still **draft-ietf-oauth-v2-1-17** (2026-10-31). Anchor to **RFC 9700** (BCP 240) | auth (3 files), ai-eng, monarch (2) |
| ASVS 5.0 cited with 4.0.3 IDs | ASVS **5.0.0** (May 2025): authorization is V8, V4.1.1 is Content-Type | auth, sec |
| targetSdk 35 | Play requires **API 36** for new apps and updates since 2026-08-31 | mobile |
| SVGO v3 config | SVGO **v4.x** | illustration |
| WebAuthn L2 era guidance | **WebAuthn Level 3** became a W3C Recommendation on 2026-08-25 | auth |
| WCAG large text 18px | WCAG 2.2 SC 1.4.3: 18pt (≈24px) or 14pt bold (≈18.66px). WCAG 2.2 is also ISO/IEC 40500:2025 | antislop, antislop-human |
| NIST SSDF | v1.1 final. **v1.2 (SP 800-218 Rev.1) is still a draft** (2025-12-17). SP 800-218A is final | sec, supplychain: label the draft as a draft |
| SLSA, CycloneDX, SPDX | SLSA **v1.2** (Source Track), CycloneDX **1.7** (ECMA-424 2nd ed.), SPDX **3.0.1** | supplychain, handover |

**Fix:**
1. Add a single `shadow-monarch/reference/FACTS-REGISTRY.md`, or a JSON file. Each standard, threshold and legal citation gets ID, value, source URL, `last_verified` and `review_by`. Skills reference the entry ID instead of restating the value.
2. Add CI checks. `lychee` checks links. A script fails when `review_by` is in the past, or when the same fact ID has two values across skills.

### 4.5 HIGH: vendored third-party content without license compliance

**What was found:**
- **shadow-test.** `references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md` copies the MIT-licensed guide in full (2,159 lines) with no copyright or license notice.
- **shadow-ops.** `references/vendor/` holds 5 OWASP cheat sheets under **CC BY-SA 4.0** (share-alike) and 3 H5BP nginx configs under MIT. None of them carries a license notice or attribution.
- **Repo license.** The repo-wide MIT claim covers all of these files, which is wrong for the CC BY-SA content.
- **shadow-design.** The main pack has no recorded license.

shadow-design's `UPSTREAM_PROVENANCE.json` and `skill_vendor_sync.py` already solve this; the vendored files above are outside that tracking.

**Fix:**
- Extend that provenance lock to every `vendor/` folder.
- Add `LICENSES.md` per vendor folder, plus a header in each file: source URL, commit, fetch date and modification status.
- Exclude the CC BY-SA files from the MIT claim in the README.
- Trim the copies to the cited sections, or replace them with links.

### 4.6 MEDIUM: orchestrator weight

**Size.** `shadow-monarch/SKILL.md` is 39.8 KB, about 10k tokens, and loads for almost every task. `GLOBAL.md` adds another 14.8 KB. Both restate the same 27 rules and the persona ceremony.

**Agent compatibility.** The skill names Antigravity tools (`grep_search`, `replace_file_content`) that Claude Code does not have.

**Context loss.** Claude Code keeps only the **first 5,000 tokens** of each skill after compaction. Most of the orchestrator's routing and rigor protocol is therefore lost in long sessions.

**Fix:**
1. Bring SKILL.md down to 8 KB or less, with the non-negotiables in the first 2 KB.
2. Move the matrices to references.
3. Make GLOBAL.md the single source.
4. Use tool-neutral wording.
5. Move rules that must hold every time, such as git mutation blocks, into **hooks**. The Claude Code docs recommend hooks over prose for this.

### 4.7 MEDIUM: safety and policy items

- **shadow-video: bot-detection workaround.**
  - Problem: the recording guidance gets past Cloudflare Turnstile by using installed Chrome or a CDP-attached manual session.
  - Fix: use Cloudflare's published Turnstile **test sitekeys** in staging, or disable the captcha in staging.
- **modern-web-guidance: unaudited package execution.**
  - Problem: runs `npx -y` of a third-party package without the suite's own pre-install audit (shadow-sec ref 09).
  - Fix: gate it behind that audit, or vendor a pinned, hashed snapshot.
- **handoff: secrets in saved context.**
  - Problem: no secret or PII redaction before session context is saved.
  - Fix: redact before saving.
- **shadow-doc: writes into the skill folder.**
  - Problem: the acceptance suite writes into the skill folder.
  - Fix: write to a temp directory, or to a directory passed in as `--out-dir`.

## 5. Per-skill upgrade cards

Actions are ordered. The source to align with is in brackets.

### 5.1 BAD → GOOD (do these first)

- **shadow-monarch.**
  1. Make `official_first_verifier.py` and `consulting_core.py` use strict booleans, and add string-flag probes.
  2. Generate all counts from the filesystem and fail CI on drift. The real numbers are 59 skills and 56 reference modules.
  3. Shrink SKILL.md to 8 KB or less and narrow the description.
  4. Add retrieval routing plus a held-out bilingual trigger set with per-skill recall.
  5. Move the hard rules into hooks. [Claude Code skills docs; Anthropic skill best practices]
- **shadow-auth.**
  1. Use strict booleans and add probes.
  2. Remap to ASVS **5.0.0** IDs (V6–V11).
  3. Label OAuth 2.1 as a draft and anchor to **RFC 9700**, RFC 9449 (DPoP) and RFC 7636.
  4. Add WebAuthn L3.
  5. Add router keywords for JWKS, JWT rotation and rate limits. [OWASP ASVS v5.0.0 tag; RFC 9700]
- **shadow-concurrency.**
  1. Use strict booleans.
  2. Replace the declaration "simulation" with a trace-based checker, or a SQLite crash-before-ack fixture like shadow-data's.
  3. Cite with dates: the Postgres `SKIP LOCKED` docs and the Kafka/RabbitMQ delivery semantics.
- **shadow-integrate.**
  1. Bind the inquiry to `account`, `amount_minor`, `currency` and `provider_tx_id`. Any mismatch → MANUAL_RECONCILIATION.
  2. Add a mismatch probe.
  3. Route "webhook signature" to ref 02.
  4. Cite with dates: the SNAP BI version and the Stripe and Midtrans webhook docs.
- **shadow-analytics.**
  1. Use strict booleans.
  2. Clamp `srm_alpha` to [1e-6, 0.01] and require a justification for overrides.
  3. Mark vendor DSAR deletion as L4. [Kohavi et al., *Trustworthy Online Controlled Experiments*]
- **shadow-email.**
  1. Make alignment honour `adkim`/`aspf`: `s` means exact match, `r` means organizational domain via the PSL.
  2. Resolve nested SPF includes from a fixture, or WARN and never PASS without it.
  3. Move to **RFC 9989/9990/9991**: drop `pct`, add `t=` and `np=`.
  4. Replace the Postmaster v1 reputation gates with the v2 Compliance Status view.

### 5.2 MEDIUM → GOOD

| Skill | Ordered upgrade actions |
|---|---|
| antislop | Fix large text per WCAG 2.2 SC 1.4.3. Replace the self-test with one that parses the real rule file and asserts parity with shadow-accessibility. Add a "Not for backend/CLI" clause. Gate the self-update behind the shadow-sec audit. |
| antislop-code | Add a token-diff checker: strip comments, then assert the code is byte-identical. Keep issue links on workaround comments. Preserve pragmas and lint directives. Add router probes. |
| antislop-copywriting | Add an Indonesian section (Anda/kamu register, KBBI/PUEBI, calques to avoid). Add an error-message anatomy (GOV.UK / NN/g). Reconcile the em-dash rules. Add a lint script with probes. |
| antislop-human | Fix large text. Add a unittest for `contrast-check.py`. Add the evidence handoff to shadow-accessibility. |
| antislop-layoutmobile | Add SC 1.4.10 (320px) and SC 2.5.8 (24px). Add the iOS 16px input rule. Link shadow-browser's overflow script as the verification step. |
| antislop-ui | Reference antislop core instead of restating it. Add description boundaries. Add a static HTML/CSS checker for R-40. Cite web.dev/vitals with a date. |
| modern-web-guidance | Gate or vendor the `npx` call and update the pin. Add a 4-step workflow (stack → Baseline status on webstatus.dev → native or fallback → verify). Add router probes for LCP/INP/CLS. |
| shadow-design | Generate a method index covering all 216 entry points. Add a "Do NOT use" clause. Record or obtain the license for the ai-product-designer pack. Collapse the duplicate routing tables. |
| shadow-illustration | Port the config to SVGO v4 and pin it. Fix the UTF-8 encoding. Remove the duplicate table. Add a "Do NOT use" clause. |
| shadow-video | Replace the Turnstile workaround with test sitekeys. Add offline tests (scene schema, narration lint, refuse-overwrite). Date the TTS and licensing facts. |
| shadow-doc | Add router probes for docx/pdf/xlsx regeneration. Generate counts from `templates/registry.json`. Write acceptance output to a temp directory or `--out-dir`. Pin NIST SP 800-61r3 and ISO/IEC 25010:2023. |
| shadow-api | Broaden the leak patterns (Postgres, MySQL, Prisma, file paths) with precision and recall probes. Add breaking-diff fixtures (oasdiff rule catalogue). Date the RFC 9457/9745/8594 citations. |
| shadow-cache | Use strict booleans. Cite RFC 9111, RFC 5861, TanStack Query v5 and the Redis eviction docs with dates. Make concurrency the single owner of idempotency. Add a 5-step workflow. |
| shadow-data | Add NOT NULL, rename and type-change router keywords. Add a `contract_readiness` schema. Cite the PostgreSQL ALTER TABLE lock levels with a date. |
| shadow-db | Strip SQL comments before matching. Flag `SET NOT NULL`, `ALTER TYPE` and volatile defaults. Route EXPLAIN and ERD intents to refs 03 and 06. |
| shadow-realtime | Cite RFC 6455, WHATWG SSE, RFC 7692 and MQTT 5.0 with dates. Require an event `source`, and reject `blocked` events that lack a dispatcher source. |
| shadow-search | Emit `acl_evidence: TENANT_ONLY`, as a WARN or INCOMPLETE, when there is no allowed-ID snapshot. Cite `trec_eval` NDCG and the OpenSearch docs with dates. |
| shadow-domain | Use strict booleans. Add an effective-dated policy scenario. Add dated citations. |
| shadow-ai-eng | Add a 5-step workflow. Update to **MCP 2026-07-28** (stateless, discovery, CIMD) and test against it. Add OWASP LLM **2026** and the Agentic Top 10. |
| shadow-eval | Require at least 1 answerable judged sample for PASS. Add a "Do NOT use" clause. Move to OWASP LLM 2026 and the Agentic ASI01–10. Add pass^k reporting (τ-bench). |
| shadow-architect | Ship and test `topology_decision_checker.py`. Label thresholds as heuristics (Team Topologies; Fowler MonolithFirst). |
| shadow-bootstrap | Make the `http` profile include config, logging and shutdown. Detect parent manifests and `.git`. Fix the ref-02 path. Cite the official generator docs. |
| shadow-quality | Add a "Do NOT use" clause. Make the OpenAPI and collection checks conditional on those files existing. Use tool-backed complexity (ESLint `complexity`, ruff `C901`). Make it the home of the repo-wide strict-boolean meta-test. |
| shadow-test | Fix the vendor license and provenance. Trim the vendored guide to cited sections. Use strict booleans. Add an applicability table for unit/CLI/event/HTTP/UI. |
| shadow-refactor | Type-validate inputs. Derive `changed_files` from `git diff --name-only`. Record test SHAs before and after. |
| shadow-uat | Move the logic into `scripts/uat_evidence_verifier.py` and test it. Add an RTM coverage checker. Add a "Do NOT use" clause. Cite ISO/IEC/IEEE 29119-3. |
| shadow-release | Add release-type profiles with NOT_APPLICABLE plus a reason. Require `evidence_ref` per gate. Reconcile Gate 3. |
| shadow-compat | Ship and test `consumer_replay.py`. Add upgrade and bump triggers. Link RFC 9745 and RFC 8594. |
| shadow-sec | Vendor the ASVS 5.0.0 JSON with its sha256 and reject unknown IDs. Fix the V4.1.1 mapping to V8. Add OWASP Top 10:2025 (A03, A10) and the Agentic Top 10. Accept PASS_NO_FINDINGS only with scope and method evidence. |
| shadow-ops | Fix the vendor license and provenance. Parse compose YAML instead of regex. Move the profile logic into a tested script. |
| shadow-resilience | Compare drills with `rto_target_seconds` and `rpo_target_seconds`. Align container labels with the shadow-quality ledger. Cite ISO 22301:2019. |
| shadow-finops | Add the cache-write multiplier and validate 0 ≤ rate ≤ 1. Move reconciliation into the script. Date the price table (FOCUS). |
| context7 | Rewrite the test to resolve from the lockfile or `node_modules` and assert UNRESOLVED on a range-only input. Add an installed-v14 versus docs-v15 probe. |
| shadow-git | Make `--self-test` run real temp-repo probes (dirty stash, rebase block, merge-tree conflict). Delete the discount test. Cite git-scm merge-tree and worktree. |
| shadow-mobile | Replace the hard-coded API level with a dated table (API 36 as of 2026-08-31). Make the test import the gate. Add a variant-aware probe. |
| shadow-maintain | Take SLA targets from the contract, with the table as a fallback. Add a tested `rollback_decision.py`. Add incident phrasing to the router. Cite NIST SP 800-61r3. |
| shadow-discovery | Put a 3-mode selector at the top of SKILL.md. Label NFR numbers as examples. Cite ISO/IEC/IEEE 29148:2018 and ISO/IEC 25010:2023. |
| shadow-plan | Derive the DoD from the change type. Fix the router precedence so decomposition verbs (pecah, break into, backlog, sprint) beat discovery. Cite the Scrum Guide 2020. |
| shadow-presales | Re-verify every Perpres 46/2025 threshold against the official text (JDIH BPK / LKPP), with pasal, ayat and date. Split the TKDN tiers. Make TCO fail closed on empty input. Add `quote_valid_until`. |
| shadow-ea | Add Indonesian portfolio vocabulary to the router. Add a "Do NOT use" clause versus architect. Cite TOGAF 10 and Perpres 95/2018 and 132/2022 with dates. |
| shadow-modernize | Fail closed when evidence is missing or LOW. Fix "8" to "6". Add legacy, rewrite and warisan triggers. Cite Fowler StranglerFig and Feathers. |

### 5.3 GOOD → PERFECT

| Skill | Ordered upgrade actions |
|---|---|
| shadow-browser | Add `consoleErrors: 0` and `pageErrors: 0` assertion fields. Add a 320px viewport. Date the Playwright and WCAG sources. |
| shadow-accessibility | Add a WCAG-EM 1.0 ordered audit and report template. Add accessible-name checks. Add EN 301 549 v3.2.1 and the EAA. |
| handoff | Redact secrets and PII before saving. Run HNF-01..05 as a transcript eval. Add router probes. |
| shadow-handover | Name CycloneDX 1.7 or SPDX 3.0.1. Make the cutover test import `check_receipt`. Add `--self-test`. |
| shadow-supplychain | Align `expires_on` and `expires_at`. Downgrade lookalike matches to REVIEW with an allowlist (fixes the `preact` false positive). Date SLSA 1.2, CycloneDX 1.7 and SPDX 3.0.1. |
| shadow-seo | Downgrade non-Google rules to WARN. Add an HTML or HTTP-response mode. Add a crawl → render → index workflow (Google Search Central, dated). |
| shadow-debug | Require at least 2 distinct hypotheses with at least 1 REJECTED, and evidence artifacts with sha256 hashes. |
| shadow-perf | Make profile-specific executors (arrival rate) gated by `APPROVED_PROFILE`. Add an allowlisted staging origin bound to an approval record. |
| shadow-privacy | Reword encryption as a recommended control (Pasal 35/39). Add dated JDIH and EUR-Lex links and the status of the PP (implementing regulation). |
| shadow-observe | Express the latency SLI as a ratio of good events. Scan for NIK, email and JWT values in logs. Cite the SRE workbook and the OTel semconv version. |
| shadow-pmo | Add tests/ (shared-dependency CR, baseline date). Add a "Do NOT use" clause. Cite the PMI EVM Practice Standard and PMBOK 7. |
| shadow-grc | Add the OJK FAQ in-flight exception. Reject empty findings. Make the test import the engine. Cite PADK 1/2026, ISO/IEC 27001:2022 + Amd 1:2024 and COBIT 2019 with dates. |

## 6. Recommended open-source tools and skills

Every tool must pass the suite's own `shadow-sec` ref 09 pre-install audit and be pinned before adoption. Licenses and releases are as fetched on 2026-11-26.

| Tool | Adds | License / latest | Use in | Safety note |
|---|---|---|---|---|
| **agentskills `skills-ref validate`** | Frontmatter and name-equals-directory linting; spec conformance | Apache-2.0, rolling | CI for all 59 | Run read-only in CI |
| **Claude `skill-creator` and `claude plugin eval`** | Description trigger tuning (should and should-not trigger), A/B against a no-skill baseline | Official marketplace | Fixes §4.2 | Measures real host selection |
| **promptfoo** | Agent regression and red-team suites mapped to OWASP LLM and Agentic | MIT, 0.126.0 (2026-11-18) | shadow-eval, ai-eng, trigger evals | Telemetry is on by default: set `PROMPTFOO_DISABLE_TELEMETRY=1` |
| **Inspect AI** (UK AISI) | Sandboxed agent evals with pass^k and a log viewer | MIT, 0.3.292 (2026-11-23) | Cross-model parity (Claude, Codex, Gemini) | Use its built-in sandbox |
| **DeepEval / Ragas** | Tool-correctness, faithfulness and context-recall metrics | Apache-2.0; 4.3.6 / 0.4.4 | shadow-eval, shadow-search | Ragas changed GitHub org: verify the PyPI publisher. Keep DeepEval local. |
| **garak** | LLM vulnerability probes | Apache-2.0, 0.17.1 | shadow-eval red team | An L3 run: only against your own endpoints |
| **mutmut / StrykerJS** | Mutation testing of the verifier scripts. Exposes §4.1 and §4.3. | BSD-3 / Apache-2.0 | shadow-quality, every `scripts/` | Low Scorecard (5.0 / 3.4): pin and verify |
| **lychee + markdownlint-cli2 + Vale** | Link rot, Markdown hygiene, terminology and anti-slop prose rules | Apache/MIT; MIT; MIT | Facts registry CI, antislop-copywriting | Vale moved to `vale-cli`; lychee makes network calls (cache them) |
| **OpenSSF Scorecard, osv-scanner, syft/grype, cosign** | Supply-chain evidence for supplychain, release and handover | Apache-2.0; Scorecard 8.2–8.9 | shadow-supplychain, shadow-release | Strongest trust posture of the set |
| **axe-core + Lighthouse CI** | Automated WCAG and CWV checks behind antislop and accessibility | MPL-2.0 / Apache-2.0 | antislop-*, accessibility, mwg, seo | Automated checks cover only part of WCAG: keep manual WCAG-EM |
| **Schemathesis + Spectral (OWASP ruleset)** | Property-based API fuzzing and OpenAPI linting | MIT / Apache-2.0 | shadow-api, shadow-compat | Fuzzing is L3: non-production only |
| **Pact** | Real consumer-driven contracts, replacing compat's in-test replay | MIT, 17.1.4 | shadow-compat | Scorecard 4.2: pin it |
| **k6** | Already used | **AGPL-3.0** | shadow-perf | Fine as a CLI; do not embed or redistribute |
| **Semgrep rules** | SAST corpus | **Semgrep Rules License v1.0 (not OSI)** | shadow-sec | Read the license before redistributing rules |
| **anthropics/skills** | Reference patterns and templates | Apache-2.0 | Authoring reference only | README says "demonstration and educational purposes only": treat as data |

## 7. Roadmap

Each wave lists its exit criteria, which must hold before moving on.

| Wave | Scope | Exit criteria |
|---|---|---|
| **W1: Stop false PASS** (about 2 days) | Shared `strict_bool`, applied to the 24 files. Bind the integrate reconciliation fields. Fix email alignment and SPF. Clamp analytics `srm_alpha`. Require at least one answerable sample in eval. Empty-input refusal in modernize, presales and grc. | String-flag meta-test green across all verifiers. Every probe in §4.1 and §5.1 returns FAIL or INVALID_INPUT. Mutation score on gate functions ≥ 80%. |
| **W2: Get selected** (about 3 days) | Descriptions ≤ 250 characters, total ≤ 9k. Narrow the monarch trigger. `skillOverrides` name-only for rare skills. Held-out bilingual trigger set. Retrieval stage 1 in the router. | No description dropped in `/context` on a 200k-token model. Held-out primary-skill recall ≥ 90% and should-not-trigger precision ≥ 95%, per skill, reported. |
| **W3: Tests that bite** (about 3 days) | All 20 self-contained tests import shipped code. Add tests to the 12 untested skills. mutmut and Stryker in CI. | 0 test files without a script import (heuristic scan). Every skill has at least 1 test that fails when its main script is mutated. |
| **W4: Facts and license hygiene** (about 3 days) | FACTS-REGISTRY with dates. Fix every row in §4.4. Vendor LICENSES and provenance lock. lychee, Vale and markdownlint CI. | 0 broken links. 0 overdue `review_by` entries. 0 conflicting fact values. Every vendored file has a license header. |
| **W5: Orchestrator diet and behavioural evals** (about 1 week) | Monarch SKILL.md ≤ 8 KB. Hooks for the hard rules. Inspect AI or promptfoo with-skill versus no-skill runs at pass^k for each domain on Claude, Codex and Gemini. | A measured uplift per skill against baseline is published. Any skill with no uplift is merged or retired (SkillsBench: focused beats exhaustive). |

After W1–W4, roughly 30 of the 41 MEDIUM skills should reach GOOD, because most of them are held back by D5 and D8. PERFECT requires W5 evidence of measured behavioural uplift; no skill can honestly be graded PERFECT on source review alone.

## 8. Prior review (2026-11-18): status of its defects

| Status | Items |
|---|---|
| **FIXED** (re-probed) | eval empty sample → perfect score · search duplicate IDs → Recall 2.0 · realtime string flags and empty events · bootstrap forced pillars on CLI · quality Docker cleanup ownership · supplychain `signer_verified="false"` · perf POST-only spec / `/healthz` · refactor empty allowlist · auth 401 vs 403 · cache idempotency fingerprint · db ETL honesty · architect ADR by scope · resilience pg_restore-as-RTO · mobile manifest path · git argument order · grc assessment date · handover hard-coded tag · maintain rollback gate · handoff drive path and SHA check · antislop mode precedence · design `file:///` links · accessibility wrapping labels · browser expected-outcome · doc generator precedence |
| **PARTIAL** | discovery mode selector (not in SKILL.md) · plan unconditional API DoD · release unconditional gates · test universal 8-point matrix · context7 (instructions fixed, test contradicts them) |
| **STILL OPEN** | monarch routing for the Indonesian ea, git, mobile, modernize and plan prompts · sec control IDs not resolved against the catalog · antislop-code pragma fixtures · antislop-copywriting cross-language fixtures · antislop-human handoff to accessibility · pmo shared-dependency double count |

The 2026-11-18 fixes were applied to the skill named in each finding, not to the bug class. That is why §4.1 reappears in eight more skills.

## 9. Sources

**Skill authoring and selection**
- Claude Code: Skills (listing budget 1% of context; whole descriptions dropped; 1,536-character entry cap; 5,000-token post-compaction keep). https://code.claude.com/docs/en/skills (fetched 2026-11-26)
- Anthropic: Agent Skills best practices (description ≤ 1,024 characters, third person, body < 500 lines, at least 3 evals, test across models). https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Anthropic Engineering: Equipping agents for the real world with Agent Skills (2025-10-16). https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Agent Skills specification and evaluation guide. https://agentskills.io/specification · https://agentskills.io/skill-creation/evaluating-skills
- OpenAI Codex: Build skills (2% of context or 8,000 characters). https://learn.chatgpt.com/docs/build-skills

**Agent and skill evaluation research**
- SkillsBench [PREPRINT]. https://arxiv.org/abs/2602.12670
- SkillRouter [PREPRINT]. https://arxiv.org/abs/2603.22455
- Agentic Skills in the Wild [PREPRINT]. https://arxiv.org/abs/2604.04323
- τ-bench / pass^k (ICLR 2025). https://arxiv.org/abs/2406.12045
- SWE-bench (ICLR 2024). https://arxiv.org/abs/2310.06770
- MetaTool (ICLR 2024). https://arxiv.org/abs/2310.03128
- Judging LLM-as-a-Judge (NeurIPS 2023). https://arxiv.org/abs/2306.05685
- Who Validates the Validators? https://arxiv.org/abs/2404.12272

**Standards**
- OWASP ASVS 5.0.0. https://github.com/OWASP/ASVS
- OWASP Top 10:2025. https://top10.owasp.org/2025
- OWASP Top 10 for LLM 2026. https://genai.owasp.org/announcement/owasp-genai-security-project-unveils-2026-top-10-for-llm-applications-new-agent-control-standard-and-sponsors-as-community-tops-30000-members/
- OWASP Top 10 for Agentic Applications. https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- MCP 2026-07-28 changelog. https://modelcontextprotocol.io/specification/2026-07-28/changelog
- MCP security best practices. https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices
- RFC 9989 DMARC (2026-05-19). https://www.rfc-editor.org/rfc/rfc9989.html
- RFC 9700 (OAuth 2.0 Security BCP). https://www.rfc-editor.org/rfc/rfc9700.html
- OAuth 2.1 draft-17. https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/
- RFC 9457 (Problem Details). https://www.rfc-editor.org/rfc/rfc9457.html
- WebAuthn L3 Recommendation. https://www.w3.org/news/2026/web-authentication-an-api-for-accessing-public-key-credentials-level-3-is-now-a-w3c-recommendation/
- WCAG 3 status. https://www.w3.org/WAI/WCAG3
- WCAG 2.2 as ISO/IEC 40500:2025. https://www.w3.org/WAI/news/2025-10-21/wcag22-iso
- NIST SSDF publications. https://csrc.nist.gov/projects/ssdf/publications
- NIST AI 600-1. https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- SLSA. https://slsa.dev/spec/
- CycloneDX 1.7. https://cyclonedx.org/news/cyclonedx-v1.7-released
- SPDX. https://spdx.dev/use/specifications/
- OWASP MASVS. https://github.com/OWASP/masvs/releases

**Verification notes.** Grader evidence sheets with `file:line` citations and probe outputs are in [enhancement-review-evidence/](enhancement-review-evidence/): `A.md` through `D.md` (one per grader), `research.md` (the full citation table), `rubric.md` and `tests.txt`. They are not committed. ISO pages returned 403, so the ISO 27001 Amd 1:2024 and ISO 42001 status rest on secondary sources. The figure of about 135 characters per skill on Codex is an estimate.
