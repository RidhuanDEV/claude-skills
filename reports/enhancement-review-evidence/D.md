# Grade sheet D: orchestrator, utilities, delivery and consulting skills (14)

Reviewer: strict principal-level, read-only. Repo: `<repo>` @ `1dbe3b5` (clean). Date 2026-11-26.
Scale: 1=BAD, 2=MEDIUM, 3=GOOD, 4=PERFECT. Grade rule follows the rubric (PERFECT avg>=3.6 and no dim<3; GOOD avg>=3.0 and no dim=1; MEDIUM avg>=2.2; BAD avg<2.2 or a critical defect).

## Summary table

| Skill | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|---|
| shadow-monarch | 2 | 3 | 3 | 3 | 2 | 4 | 1 | 1 | 2.38 | MEDIUM |
| context7 | 3 | 2 | 3 | 3 | 1 | 3 | 4 | 2 | 2.63 | MEDIUM |
| handoff | 4 | 3 | 3 | 4 | 3 | 3 | 3 | 2 | 3.13 | GOOD |
| shadow-git | 3 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.88 | MEDIUM |
| shadow-mobile | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | MEDIUM |
| shadow-maintain | 2 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.50 | MEDIUM |
| shadow-handover | 4 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.13 | GOOD |
| shadow-discovery | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.63 | MEDIUM |
| shadow-plan | 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 2.88 | MEDIUM |
| shadow-pmo | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |
| shadow-presales | 3 | 3 | 2 | 3 | 2 | 4 | 3 | 2 | 2.75 | MEDIUM |
| shadow-grc | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |
| shadow-ea | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2.75 | MEDIUM |
| shadow-modernize | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.63 | MEDIUM |

No PERFECT. 4 GOOD, 10 MEDIUM, 0 BAD. D8 (provenance) is 2 or lower everywhere. Across the 11 specialist skills, 0 of 33 reference playbooks has a "last verified" date. The consulting references (pmo, presales, grc, ea, plan, git) contain 0 URLs, including on date-sensitive regulatory claims.

## Shared evidence

### Router generalization probe (fresh, 25 realistic prompts aimed at my 14 skills)
Command: `python shadow-monarch/scripts/skill_router.py --route "<prompt>"`, reading `routing_decision.primary_skill`. Result: **11/25 correct**. The router self-test passes 154/154 (exit 0), so the self-test is overfitted to its own phrasing.

The router sent these prompts to the wrong skill or to none:
- To `shadow-monarch`, meaning no specialist:
  - "our iOS build got rejected with ITMS-91053 missing privacy manifest". The literal error code is in the shadow-mobile reference.
  - "bump android targetSdk to 35 for play store"
  - "context is almost full, save handoff"
  - "what's the correct prisma 6 syntax for relation filters" (should go to context7)
  - "we inherited a 15 year old PHP monolith, should we rewrite it"
  - "set up worktrees so two agents can work in parallel"
  - "requirement says 7 days SLA, clarify"
  - All 4 Indonesian prior-review probes for shadow-ea, shadow-git, shadow-mobile and shadow-modernize.
- To the wrong specialist:
  - "prod is down after deploy, users cannot login" went to `shadow-auth`, not shadow-maintain.
  - Both shadow-plan prompts ("Pecah kebutuhan menjadi backlog...", "break this PRD into sprint stories with DoR DoD") went to `shadow-discovery`.

These prompts routed correctly: postmortem, BAST, PRD+AC, CR defect vs paid, P80 Monte Carlo, bid/no-bid RAB, ISO SoA, POJK 11, SPBE 6 domain, assetlinks.json, and package-lock conflict.

Root cause: `skill_router.py` is a 2,466-line hand-maintained regex include/exclude table (`skill_router.py:28-210+`). It matches literal tokens such as `targetSdkVersion`, not `targetSdk`, so it cannot generalize. `--audit-descriptions` reports `all_passed: true` for 59 skills, but it checks only frontmatter shape (presence of "use when" and length under 500), not whether a skill is selected.

### Description-budget truncation (host-level auto-triggering)
In the observed Claude Code session, 10 skills appeared in the skill listing as bare names with no description: shadow-realtime, -refactor, -release, -resilience, -search, -sec, -seo, -supplychain, -test and -uat. They are the alphabetical tail. This most likely happens because the host caps the total characters of skill descriptions. This suite's descriptions total about 18.9k characters, and `shadow-monarch:shadow-monarch` is also listed a second time as a plugin, which spends more of the budget.

Impact: in Claude Code, auto-triggering depends on the model reading the descriptions. `skill_router.py` runs only if the agent decides to run it. So the security, test, release and UAT owners are effectively invisible for implicit selection and fire only when named with a slash command.

This compounds with shadow-monarch's catch-all description ("Use when implementing, debugging, refactoring, reviewing, designing, or auditing software systems..."). That description wins by default and then delegates to a router that scored 11/25 on these probes. None of my 14 skills were truncated, but the problem is caused by this suite's design and is a cross-cutting HIGH defect.

### Test-theater pattern (self-contained tautological unit tests)
These test files define their own function inside the test and assert against it. They never import the skill's script and never exercise agent behavior:
- `context7/tests/test_version_resolution.py:9-20`
- `shadow-mobile/tests/test_mobile_release_canary.py:6-26`
- `shadow-maintain/tests/test_incident_rollback_gate.py:6-20`
- `shadow-discovery/tests/test_ambiguity_single_question.py:6-24`
- `shadow-grc/tests/test_grc_dated_register.py:6-26`
- `shadow-handover/tests/test_partial_handover_cutover.py:7`
- 2 of 3 tests in `shadow-git/tests/test_worktree_semantic_order.py`. One is an off-domain discount-rounding test (`:15`, `:75`).

They all pass and cannot catch a regression in shipped code. The only tests here that exercise real code:
- `shadow-handover/tests/test_receipt.py`, which imports `check_receipt.assess`
- `shadow-plan/tests/test_sprint_dag_verifier.py`
- `mcp-servers/shadow-handoff-mcp/handoff.test.mjs`
- `shadow-monarch/tests/test_resource_cleanup.py`

---

### shadow-monarch
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 2 | 4 | 1 | 1 | 2.38 | MEDIUM |

**Strengths**
- The safety gates are real and tested:
  - `execution_approval_gate.py --self-test`: 16 probes PASS.
  - `official_first_verifier.py`: 12 PASS.
  - `resource_cleanup.py`: 6 PASS, including an orphan flagged without auto-kill.
  - `bounded_exec.py`: 5 PASS.
  - The L0-L4 intent boundary (`GLOBAL.md:36`) is strong governance.
- The sampled reference content is accurate and practitioner-grade:
  - Go 1.22 per-iteration loop vars and method+path mux, `slog` since 1.21 (`lang-GO.md:44,50,68`).
  - RFC 9457 §3.2 (`BACKEND.md:31,58`).
  - OWASP API Top 10 2023 (`SECURITY.md:78`).
  - PPN DPP 11/12 x 12% and PPh 23 2% (`sub-FINTECH-ID-ECOSYSTEM.md:51`), which matches PMK 131/2024.
  - The prefix-cache ordering and native structured-output guidance (`AI-LLM.md:32,44`) is current.
- The Rigor Protocol (`SKILL.md:81-117`) makes the agent state its untested surfaces. This is a good anti-overclaim behavior.

**Gaps**
- HIGH, inconsistent core counts across 3 files:
  - `README.md:3` says "54 skills" and "55 reference modules".
  - `SKILL.md:8` says "58 ... reference generals across 59 skills".
  - `GLOBAL.md:32,56` says 59 skills and 56 references.
  - Actual: 59 skill dirs and 56 files in `reference/`.
  - The README's 33+9+13=55 omits `CROSS-SKILL-OWNERSHIP-MATRIX.md`.
- HIGH, token cost:
  - `SKILL.md` is 39,776 bytes (about 10k tokens) and is triggered by a catch-all description (`SKILL.md:3`), so it loads on nearly every engineering task.
  - `GLOBAL.md` (14.8 KB, about 3.7k tokens) is injected permanently through CLAUDE.md and repeats `SKILL.md` content (Mana doctrine, routing, approval) at both layers.
  - The persona ceremony is mandated on every turn: "Always address the user as Monarch" and phrases like "Shadow Army siap melaksanakan perintah" (`SKILL.md:8-21`). It costs tokens and adds no correctness.
- HIGH, router generalization: 11/25 fresh probes correct, while the self-test passes 154/154. The prior-review defect is still open (see Shared evidence).
- MEDIUM, host-specific tool names in a skill marketed for Claude and Codex: `grep_search`, `find_by_name`, `replace_file_content`, `StartLine–EndLine` (`SKILL.md:29-36`). These are Antigravity tool names. On Claude Code the tools are Grep, Read and Edit, which gives the agent wrong instructions.
- MEDIUM, provenance: 0 of 56 reference modules has a last-verified date. URL counts in the sample: CORE 0, SECURITY 0, AI-LLM 0, lang-TS 0, lang-GO 0, FINTECH 0, BACKEND 1.
- LOW: `SKILL.md:121` says "never load all 59 skills" while the README says 54.

**Prior-review defect status:** STILL OPEN.
- "specialist prompts end at Monarch": the 4 Indonesian prompts from `reports/skill-review-delivery.md:233+` for ea, git, mobile and modernize still return `shadow-monarch`.
- The plan prompt still goes to `shadow-discovery`.

**Upgrade actions (ordered)**
1. Generate every count from the filesystem in CI and fail on drift. Fix README, SKILL.md and GLOBAL.md to 59/56.
2. Cut `SKILL.md` to 8 KB or less (persona in 2 lines, routing table moved to a reference). Narrow the description to orchestration and multi-skill work so specialists win their own prompts.
3. Make `GLOBAL.md` the single source and stop restating it inside `SKILL.md`.
4. Replace or augment the regex router with description-embedding or BM25 retrieval over the SKILL.md descriptions. Add a held-out probe set (Indonesian and English, at least 3 per skill) that is never used to tune the regex, and report recall per skill.
5. Write host-neutral tool names, or a per-host mapping (Claude Code: Grep/Read/Edit; Codex; Antigravity).
6. Add `Last verified: YYYY-MM-DD` and primary URLs to each reference, following `RESEARCH-SOURCE-POLICY.md`, the suite's own rule.

**Test/self-test run**
- `python shadow-monarch/scripts/skill_router.py --self-test`: exit 0, 154 passed, 0 failed.
- `--audit-descriptions`: all_passed true, 59 skills.
- The 4 gate scripts with `--self-test`: all exit 0 (16/12/6/5 probes).
- `python -m unittest discover -s shadow-monarch/tests`: 3 tests OK in 10.4s.
- Fresh probes: 11/25.

---

### context7
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 2 | 3 | 3 | 1 | 3 | 4 | 2 | 2.63 | MEDIUM |

**Strengths**
- The version-matched workflow is tight: lockfile or installed version first, record publisher/version/symbol/URL, and treat a migration as old-vs-new contract comparison (`SKILL.md:13-16`).
- It sets a clear negative boundary: a question about an old version does not authorize an upgrade (`SKILL.md:15,19`).
- The file is very lean (15 lines).

**Gaps**
- HIGH: the only test contradicts the skill. `tests/test_version_resolution.py:9-20` resolves the "major" from the `package.json` range (`^14.2.15`), but `SKILL.md:13` says "A manifest range alone leaves the exact version unresolved". The test encodes the anti-pattern and never reads a lockfile.
- MEDIUM: it does not name the actual MCP tool parameters (`resolve-library-id` then `query-docs` with a version-specific library ID such as `/vercel/next.js/v14.x`). It also gives no fallback order when Context7 returns only latest-version docs.
- LOW: the router sends a canonical prompt ("correct prisma 6 syntax for relation filters") to `shadow-monarch`, not context7.
- LOW: no provenance or date for Context7 behavior.

**Prior-review defect status:** FIXED in instructions. The lockfile/installed version, the source identity and the mismatched-major handling are now in `SKILL.md:13-16`. NOT verified by the test (see the HIGH gap above).

**Upgrade actions**
1. Rewrite the test so it reads `package-lock.json`, `pnpm-lock.yaml` or `node_modules/<pkg>/package.json` and asserts UNRESOLVED when only a range exists.
2. Document the versioned library-ID form from the Context7 MCP README (github.com/upstash/context7).
3. Add a probe where docs are available for v15 while v14 is installed. The agent must restrict its claims.

**Test/self-test run:** `python -m unittest discover -s context7/tests`: 1 test OK. It is tautological.

---

### handoff
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 4 | 3 | 3 | 3 | 2 | 3.13 | GOOD |

**Strengths**
- The description gives an explicit negative trigger to `/shadow-handover` (`SKILL.md:3,47`).
- The procedure is precise:
  - `readinessLevel` and `untestedSurfaces` are required (`:24-25`).
  - Resume compares repo, branch and base SHA (`:34`).
  - Merge keeps the lowest readiness, unions untested surfaces, archives rather than deletes, and surfaces warnings (`:39-40`).
- The real MCP tests pass. `node --test handoff.test.mjs`: 2/2, covering branch/HEAD drift, lowest-readiness merge, and the legacy unverified snapshot.

**Gaps**
- MEDIUM: the router returns no specialist for "context is almost full, save handoff". This matters only if the agent relies on the router. The host description is fine.
- MEDIUM: `evaluations.md` marks live MCP round-trip as `NOT_RUN`. The 5 scenarios are not executed against an agent.
- LOW: no guidance on redacting secrets or PII from `completedWork`/`keyDecisions` before persisting them to disk (`SKILL.md:13-27`).
- LOW: hardcoded host list for `sourceAgent` (`:16`).

**Prior-review defect status:** FIXED. The D:-drive fallback path was replaced by "resolve the entry point from host registration" (`SKILL.md:14`), and HEAD validation on resume was added (`:34`).

**Upgrade actions**
1. Add a secret-redaction rule before `save_handoff`, aligned with OWASP Logging Cheat Sheet categories.
2. Run the HNF-01..05 scenarios as an agent-transcript eval.
3. Add "save handoff" and "context penuh" to the router probes.

**Test/self-test run:** `node --test mcp-servers/shadow-handoff-mcp/handoff.test.mjs`: 2 pass, 0 fail (10.7s).

---

### shadow-git
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.88 | MEDIUM |

**Strengths**
- Strong safety: read-only by default, `--approve` is L4, there is a 6-point cleanup gate, and blind `--ours`/`--theirs` is banned (`SKILL.md:13-14,49`).
- Real senior knowledge:
  - It checks semantic risks even when `merge-tree` is clean (parallel migrations, API contract, config, lockfile).
  - It re-resolves SHA freshness immediately before integration (`SKILL.md:47-48`).
  - `git merge-tree --write-tree` is correct for git 2.38 and later.

**Gaps**
- MEDIUM: the `--selftest` flag only reports the git version (`{"status":"PASS","git_version":...}`). It runs no orchestrator probes. Every other skill uses `--self-test`, which this script rejects with exit 2, so the naming is inconsistent.
- MEDIUM: `tests/test_worktree_semantic_order.py` drives raw `git` and never imports `git_orchestrator.py`. `:15,:75` is an off-domain discount-rounding test, which looks like copy-paste.
- MEDIUM: the subcommand-local `--repo` is still rejected (`detect-strategy --repo .` exits 2). Docs now show the correct global order, but the CLI stays fragile.
- LOW: "set up worktrees so two agents can work in parallel" and the Indonesian worktree probe both route to `shadow-monarch`.
- LOW: 0 URLs to git-scm docs.

**Prior-review defect status:** FIXED in docs. `SKILL.md:34-41` uses `--repo <path> <subcommand>`, and the verified command `--repo . detect-strategy` exits 0 (trunk-based/main). The underlying parser asymmetry remains.

**Upgrade actions**
1. Make `--self-test` run real probes against a temp repo: dirty-tree stash, shared-branch rebase block, stale SHA invalidation, merge-tree conflict.
2. Accept `--repo` on subparsers.
3. Remove the discount test and import the orchestrator in tests.
4. Cite git-scm.com/docs/git-merge-tree and git-worktree.

**Test/self-test run**
- `python shadow-git/scripts/git_orchestrator.py --selftest`: PASS (version only).
- `python -m unittest discover -s shadow-git/tests`: 3 OK (8.6s).

---

### shadow-mobile
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | MEDIUM |

**Strengths**
- The facts match official sources:
  - MASVS v2.1.0 has 8 groups including PRIVACY.
  - `ITMS-91053` and the 5 Required Reason API categories (`SKILL.md:25`) are correct.
  - Play Integrity replaces SafetyNet.
  - 16 KB alignment with NDK r27+ and AGP 8.5.1+ is correct (`SKILL.md:30`).
  - The reference cites developer.android.com and mas.owasp.org.
- Good operational nuance: "inspect the merged manifest or signed package", upgrade migration from installed data, and old-client compatibility (`SKILL.md:52`).
- The gate script's self-test passes 10/10, and the prior "contest" path bug is fixed.

**Gaps**
- MEDIUM: a dated example. `references/03-android-play-console-16kb-signing-and-integrity.md:41,131` uses `targetSdk = 35`. Google Play has required API 36 for new apps and updates since 31 Aug 2026 (extension form to 1 Nov 2026), per support.google.com/googleplay/android-developer/answer/11926878. The text says "verify active policy" but gives no date anchor.
- MEDIUM: `tests/test_mobile_release_canary.py:6-26` is tautological and does not import `mobile_release_gate.py`.
- LOW: path heuristics remain. `app/src/test/...` and `app/src/debug/...` are suppressed. That is correct for debug, but it shows the scanner is path-based rather than variant-based. The SKILL.md correctly defers to the merged manifest.
- LOW: the router returns no specialist for "ITMS-91053 rejection", "targetSdk 35 bump" and the Indonesian Android release probe.
- LOW: no last-verified dates on store-policy facts, which change every year.

**Prior-review defect status:** FIXED. `audit_mobile_text` on `contest/app/src/main/AndroidManifest.xml` now returns `MASVS_NETWORK_CLEARTEXT_ENABLED` and `MASVS_CODE_DEBUGGABLE_ENABLED`.

**Upgrade actions**
1. Replace the hardcoded API level with a dated table ("as of 2026-08-31: 36; existing apps 35 for visibility") and a last-verified date. Source: Play target API page.
2. Make the unit test import the gate.
3. Add a variant-aware probe: `src/release` vs `src/debug` vs `build.gradle` `debuggable`.
4. Add a Required-Reason table link to the Apple docs URL.

**Test/self-test run**
- `python shadow-mobile/scripts/mobile_release_gate.py --self-test`: exit 0, 10 passed.
- The unittest ran 1 test OK, but it is tautological.
- Contest probe rerun: findings present.

---

### shadow-maintain
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.50 | MEDIUM |

**Strengths**
- The stabilize step is now properly gated:
  - It checks that the last known good artifact can read current writes, schema and queued events.
  - It requires incident commander approval and falls back to a flag or pausing the writer (`SKILL.md:26`).
- It hands causal diagnosis to `/shadow-debug` and requires a red-before/green-after regression test (`:27-30`).
- It has a blameless RCA structure and CAPA with owners (`:36-43`).

**Gaps**
- HIGH, verification: there is no script. The only test (`tests/test_incident_rollback_gate.py:6-20`) defines and checks its own helper, so nothing in the skill is executable.
- MEDIUM: the description has no "Do NOT use" boundary versus shadow-debug, shadow-observe or shadow-resilience (`SKILL.md:3`). The router sent "prod is down after deploy, users cannot login" to `shadow-auth`.
- MEDIUM: the SLA matrix uses fixed targets (`SKILL.md:14-19`) and does not say that the contract or Harwat SLA governs. Agents may quote 15 minutes or 1–2 hours against a contract that says otherwise.
- LOW: no primary sources (Google SRE workbook postmortem chapter, NIST SP 800-61r3 for security incidents) and no breach-notification hook to shadow-privacy (UU PDP 3x24h).

**Prior-review defect status:** FIXED. The unconditional "rollback immediately" became a compatibility- and authority-gated decision (`SKILL.md:26`).

**Upgrade actions**
1. Say that SLA targets come from the contract and that the table is only a fallback.
2. Add a `rollback_decision.py` with real probes (irreversible migration leads to forward-fix plus escalation).
3. Add Do NOT clauses and incident phrasing to the router.
4. Cite the SRE workbook and NIST SP 800-61r3.

**Test/self-test run:** `python -m unittest discover -s shadow-maintain/tests`: 1 OK. It is tautological. There is no script.

---

### shadow-handover
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.13 | GOOD |

**Strengths**
- It has a clean negative boundary against `/handoff` (`SKILL.md:3,8-11`). The router probe for BAST plus credential transfer routes correctly.
- It enforces zero-plaintext credentials and a credential inventory with a rotation instruction (`:31-32`). It also uses immutable commit and digest provenance, and pending status for any missing signature or digest (`:23`).
- `check_receipt.py` is honest about its limits ("checks the digest and reference presence only", `:59`), and `tests/test_receipt.py` imports the real `assess`.

**Gaps**
- MEDIUM: `tests/test_partial_handover_cutover.py:7` is a self-contained helper and does not exercise the script.
- MEDIUM: "Third-party licenses & SBOM confirming zero prohibited/unlicensed dependencies" (`SKILL.md:28`) names no SBOM format (SPDX 2.3/3.0, CycloneDX 1.6) or license-policy source.
- LOW: running `check_receipt.py --self-test` exits with a usage error. The scripts in this suite do not share a CLI convention.
- LOW: no citation for the BAST legal basis (contract or Perpres procurement acceptance).

**Prior-review defect status:** FIXED. The hardcoded `v1.0.0` tag was removed. The skill now says "Identify the contracted release by immutable commit and artifact digest... Creating tags requires release authorization" (`SKILL.md:23`).

**Upgrade actions**
1. Name the SBOM standards (CycloneDX 1.6 / SPDX).
2. Make the partial-cutover test import `check_receipt`.
3. Add `--self-test` for consistency.

**Test/self-test run:** `python -m unittest discover -s shadow-handover/tests`: 2 OK.

---

### shadow-discovery
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 2.63 | MEDIUM |

**Strengths**
- Epistemic tagging (`[EVIDENCE]`/`[ASSUMPTION]`/`[PROPOSAL]`/`[NEEDS VALIDATION]`) plus "never invent fake user research" (`SKILL.md:15`) is senior-grade.
- It applies the ambiguity stop rule to money, legal, access-control and destructive transitions (`:14`), and requires quantified NFRs with p95, RPO and RTO (`:59-61`).
- A single-question economy mode now exists (`references/01...:25`). The vendored upstream links resolve.

**Gaps**
- HIGH, verification: there is no script. `tests/test_ambiguity_single_question.py:6-24` tests its own regex, not agent behavior or a shipped checker.
- MEDIUM: `SKILL.md` still presents the full deliverable set (stakeholder matrix, FR, NFR, risk matrix, exit gate) as "Mandatory" (`:41-74`). The one-question mode lives only in a reference. An agent loading only `SKILL.md` over-produces for a single local ambiguity.
- LOW: the hardcoded NFR example "p95 < 400ms" and "99.9%" (`:59-61`) can be copied as defaults.
- LOW: the router sends "requirement says 7 days SLA, clarify" to `shadow-monarch`.

**Prior-review defect status:** PARTIALLY FIXED. Single-question economy was added to `references/01:25`, but `SKILL.md` has no mode selector, so the default path is still the full PRD.

**Upgrade actions**
1. Add a 3-mode selector (clarify one decision / feature / project baseline) at the top of `SKILL.md`.
2. Label the NFR numbers as examples.
3. Cite ISO/IEC/IEEE 29148:2018 and ISO/IEC 25010:2023 with dates.

**Test/self-test run:** `python -m unittest discover -s shadow-discovery/tests`: 1 OK. It is tautological.

---

### shadow-plan
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 2.88 | MEDIUM |

**Strengths**
- `sprint_dag_verifier.py` is real: the self-test passes 7/7, and the unit tests import `audit_sprint_plan` (3 OK).
- It tags L2, L3 and L4 tasks `[APPROVAL-REQUIRED]` (`SKILL.md:68`), which separates planning from authorization.
- Traceability IDs are stable from EPIC to METRIC (`:12,24`).

**Gaps**
- HIGH, trigger: both plan probes route to `shadow-discovery`, the Indonesian prior probe and "break this PRD into sprint stories with DoR DoD". The planning owner is not selected even though its own keywords (DoR/DoD) appear.
- MEDIUM: the DoD is still unconditional for every story. It requires tests that are "100% green on happy path, 400/401/403/404/409/422" and documented public endpoints (`SKILL.md:61`). A batch job or copy fix inherits API status-code tests.
- LOW: the fixed 5-wave template (`:41-45`) assumes greenfield. It gives no brownfield or maintenance variant.

**Prior-review defect status:** PARTIALLY FIXED.
- Fixed: the UI states are now conditional ("For user interfaces, applicable...", `SKILL.md:54,62`).
- Still open: the API and status-code DoD is unconditional (`:61`).

**Upgrade actions**
1. Derive the DoD from the change type (UI/API/batch/copy) and record an applicability reason.
2. Fix the router precedence so decomposition verbs (pecah/break into/backlog/sprint) beat discovery.
3. Cite Scrum Guide 2020 for DoD semantics.

**Test/self-test run**
- `python shadow-plan/scripts/sprint_dag_verifier.py --self-test`: exit 0, 7 passed.
- unittest: 3 OK.

---

### shadow-pmo
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |

**Strengths**
- It ranks the contractual hierarchy before classifying Defect vs Paid CR, and any billing impact sets `requires_human_approval` and routes to CCB, counsel or PPK (`SKILL.md:18-21`). This is excellent legal-boundary hygiene.
- The math is correct: PERT E=(O+4M+P)/6, σ=(P−O)/6, CPM floats, seeded Monte Carlo P50/P80/P90, CPI=EV/AC, SPI=EV/PV (`:23-26`).
- The engine fails closed: empty tasks raise `ValueError`, and an empty CR returns `SCOPE_CLARIFICATION_REVIEW`, not a verdict. Self-test passes 8/8. The router handled both probes correctly, including Indonesian "hitung P80".

**Gaps**
- MEDIUM: there is no `tests/` directory. Coverage is the script's self-test only, which is author-written.
- MEDIUM: the description has no "Do NOT use" clause against shadow-plan or shadow-presales (`SKILL.md:3`). Disambiguation relies on sibling descriptions.
- LOW: the prior-review suggestion (two CRs sharing a dependency, double counting) has not been implemented. `grep double` finds nothing.
- LOW: no citations (PMBOK 7 / PMI Practice Standard for EVM, AACE for schedule risk) and no dates.

**Prior-review defect status:** N/A (was ALREADY GOOD). The suggested improvement (shared-dependency CR double count) is STILL OPEN.

**Upgrade actions**
1. Add the shared-dependency CR test and a baseline-date test.
2. Add a Do NOT clause to the description.
3. Cite the PMI Practice Standard for Earned Value Management (2nd ed.) and the PMBOK Guide 7th ed.

**Test/self-test run:** `python shadow-pmo/scripts/pmo_governance_engine.py --self-test`: exit 0, 8 passed. Empty-input probes fail closed.

---

### shadow-presales
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 3 | 2 | 4 | 3 | 2 | 2.75 | MEDIUM |

**Strengths**
- It strictly separates the provider RAB/BoQ from the official HPS, which only a PPK, PA or KPA may set (`SKILL.md:26`). The engine stamps `PROVIDER_COMMERCIAL_RAB_ESTIMATE_NOT_OFFICIAL_PPK_HPS` on its output.
- Capacity sizing uses service demand, not DAU (`:20-22`), with 3 scenarios plus sensitivity. TCO includes FX shock, renewal uplift and PPN.
- The router handled "bid no bid untuk tender KAK pemda, hitung RAB" correctly.

**Gaps**
- HIGH, unverified regulatory specifics, with no pasal cited and no primary URL:
  - "HPS not required for Pagu <= Rp 10 juta, E-purchasing <= Rp 100 juta, or integrated procurement" (`references/03...:19`).
  - "direct construction procurement ceiling raised to Rp 400 juta" (`:22`).
  - The "40% UMKK" figure attributed to Perpres 46/2025 (`SKILL.md:27`). My web check found no corroboration of these thresholds in BPK, DJPB or news summaries.
  - The TKDN tier is condensed into "TKDN+BMP >= 40% with TKDN >= 25%" (`:21`). Reporting describes a tiered priority order under the new Pasal 66, so the two conditions are tiers, not a conjunction. As written, this is misleading.
- MEDIUM: `compute_tco_and_commercial({})` returns a full zero-valued TCO with `"numerical_reconciled": true`. It should reject missing inputs. Contrast `compute_capacity_scenarios({})`, which correctly raises.
- LOW: the prior suggestion (stale supplier quote expiry) has not been implemented. `grep valid_until|expired` finds nothing.
- LOW: 0 URLs. Perpres 46/2025 should link peraturan.bpk.go.id/Details/318647.

**Prior-review defect status:** N/A (was ALREADY GOOD). The quote-expiry suggestion is STILL OPEN.

**Upgrade actions**
1. Re-verify every Perpres 46/2025 threshold against the official text (peraturan.bpk.go.id/Details/318647, JDIH LKPP). Cite the pasal and ayat, and add a last-verified date.
2. Rewrite the TKDN rule as the ordered Pasal 66 priority tiers.
3. Make the TCO engine fail closed on empty or zero cost inputs.
4. Add a `quote_valid_until` field and flag expired evidence.

**Test/self-test run**
- `python shadow-presales/scripts/presales_commercial_engine.py --self-test`: exit 0, 8 passed.
- Empty-input probe: TCO vacuous PASS.

---

### shadow-grc
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 3.00 | GOOD |

**Strengths**
- The regulatory claims are verified correct:
  - PADK OJK No. 1 Tahun 2026 implements POJK 11/POJK.03/2022, is effective 1 March 2026, and revokes SEOJK 21/SEOJK.03/2017. The ojk.go.id regulation page confirms all three.
  - ISO/IEC 27001:2022 has 93 Annex A controls in the 37/8/14/34 split (`SKILL.md:26`).
  - COBIT 2019 rates process capability (0–5) separately from focus-area maturity (`:25`).
- It separates Design from Operating effectiveness with a population and sample per period (`:23,34`). It uses a 6-part finding and never claims certification (`:29-30`).
- The engine requires `as_of_date` (`grc_assurance_engine.py:151`), and `validate_iso27001_soa` rejects missing Clauses 4–10. Self-test passes 10/10.

**Gaps**
- MEDIUM: nuance is missing. The OJK FAQ says licensing processes already in progress before PADK took effect still refer to SEOJK 21/2017. `references/02...:17,63` emits `REVOKED_REGULATION_CITED` unconditionally for dates on or after 2026-03-01, a false positive for in-flight licensing files.
- MEDIUM: `validate_audit_findings([], sector="BANKING", as_of_date=...)` returns `valid: True` with 0 findings, a vacuous pass.
- MEDIUM: `tests/test_grc_dated_register.py:6-26` is tautological.
- LOW: the Indeks KAMI version is given as "e.g., v4.2 / v5.0" (`references/02:25`), with no source and no date. There are no URLs for OJK or BSSN.

**Prior-review defect status:** FIXED. The hardcoded 2026-11-16 default was removed. `as_of_date` is now required and validated (`grc_assurance_engine.py:151-155`), and `SKILL.md:42` documents `--as-of-date`.

**Upgrade actions**
1. Add an in-flight-licensing exception per the OJK FAQ for PADK 1/2026.
2. Return `valid: false` or `NO_FINDINGS_SUBMITTED` on an empty findings list.
3. Make the test import the engine.
4. Cite the ojk.go.id PADK-1-2026 page, the ISO/IEC 27001:2022 catalogue, and ISACA COBIT 2019, with last-verified dates.

**Test/self-test run**
- `python shadow-grc/scripts/grc_assurance_engine.py --self-test`: exit 0, 10 passed.
- unittest: 1 OK (tautological).
- Empty-input probes: SoA rejects, COBIT raises, findings return a vacuous valid.

---

### shadow-ea
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2.75 | MEDIUM |

**Strengths**
- The SPBE 6 domains match Perpres 95/2018 and 132/2022: Proses Bisnis, Data dan Informasi, Infrastruktur, Aplikasi, Keamanan, Layanan (`SKILL.md:20`). Satu Data correctly cites Perpres 39/2019.
- It separates ABB from SBB with concrete examples (`:24`) and uses TIME rationalization with traceable IDs that feed other skills (`:22`).
- The engine fails closed on empty applications. Self-test passes 8/8.

**Gaps**
- HIGH, trigger: the prior Indonesian probe "Petakan portofolio aplikasi dan kapabilitas untuk SPBE" still routes to `shadow-monarch`. Only the literal "arsitektur SPBE 6 domain" hits.
- MEDIUM: the description has no "Do NOT use" clause versus shadow-architect (single system) or shadow-modernize (`SKILL.md:3`).
- LOW: no mention of the Permenpan RB SPBE evaluation and arsitektur guidance (for example PermenPANRB 59/2020 on SPBE monitoring and evaluation), so the government-blueprint practice is thinner than the law citations suggest.
- LOW: 0 URLs. TOGAF 10 has no Open Group link or edition date.

**Prior-review defect status:** N/A (was ALREADY GOOD). The prior suggestion to "add Indonesian portfolio phrasing to the router" is STILL OPEN.

**Upgrade actions**
1. Add router vocabulary for portofolio, kapabilitas and peta aplikasi.
2. Add Do NOT boundaries to the description.
3. Cite the Open Group TOGAF Standard 10th Edition and jdih Perpres 95/2018 and 132/2022, with dates.

**Test/self-test run:** `python shadow-ea/scripts/ea_portfolio_engine.py --self-test`: exit 0, 8 passed.

---

### shadow-modernize
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.63 | MEDIUM |

**Strengths**
- The rule "no tests does not mean FULL_REWRITE" (`SKILL.md:21`), plus characterization tests and Strangler Fig, is the right senior instinct.
- Migration economics include the coexistence, dual-run and reconciliation costs that juniors forget (`:25`). Archaeology covers triggers, cron, stored procedures and incident workarounds (`:23`).
- It does read-only forensics with SHA-256 evidence and records access limitations (`:18`).

**Gaps**
- HIGH, false confidence: `evaluate_modernization_options({})` with no input recommends `ENCAPSULATE_RETAIN` with a ranked total TCO of Rp 3.9B. All 6 dimensions default to score 3.0 with LOW confidence, and the costs come from hidden defaults. A tool for "evidence-based due diligence" should refuse or return `INSUFFICIENT_EVIDENCE` here.
- MEDIUM: an internal contradiction. `SKILL.md:20` says "Score 8 dimensions separately" but lists 6. The reference title says "6-Axis" (`:45`), and the engine self-test asserts `len(risk_vector) == 6` (`modernize_forensics_engine.py:194-197`).
- MEDIUM, trigger: "we inherited a 15 year old PHP monolith, should we rewrite it" and the Indonesian rewrite-vs-refactor probe both route to `shadow-monarch`.
- LOW: no `tests/` directory. Prior suggestions (downtime-cost sensitivity, near-tie options) have not been implemented.

**Prior-review defect status:** N/A (was ALREADY GOOD). The suggested sensitivity and router-vocabulary work is STILL OPEN.

**Upgrade actions**
1. Make the engine fail closed when required dimensions or cost inputs are missing, or when all evidence is LOW.
2. Fix "8" to "6".
3. Add router phrasing (inherited / legacy / rewrite / warisan).
4. Cite Fowler's StranglerFigApplication and Feathers' *Working Effectively with Legacy Code* for characterization tests.

**Test/self-test run**
- `python shadow-modernize/scripts/modernize_forensics_engine.py --self-test`: exit 0, 8 passed.
- Empty-input probe: a recommendation was emitted (defect).

---

## Cross-cutting observations (ranked)
1. **Routing is the system's weakest link, and the safety net is overfitted.** Host description budgets silently dropped 10 skill descriptions, including shadow-sec and shadow-test, and the catch-all shadow-monarch description absorbs generic prompts. The fallback regex router scores 154/154 on its own probes but only 11/25 on fresh realistic prompts for these 14 skills. All prior-review Indonesian misroutes for ea, git, mobile, modernize and plan are still open. Fixes:
   - Shorten all descriptions to about 250 characters or less and drop the duplicate plugin listing.
   - Narrow shadow-monarch's trigger.
   - Evaluate the router on a held-out bilingual set.
2. **Verification theater.** Seven test files across 7 skills (one of them shadow-git) are self-contained tautologies that never import shipped code. context7's test contradicts its own SKILL.md. Several consulting engines also pass vacuously or invent confident outputs on empty input:
   - modernize recommends a strategy with Rp 3.9B TCO.
   - presales returns a zero TCO marked "reconciled".
   - grc accepts 0 findings as valid.
   Fix: make every test import the script, and add fail-closed empty-input probes as the minimum oracle.
3. **Provenance and consistency debt.**
   - 0 of 33 specialist playbooks and 0 of 56 monarch references have a last-verified date.
   - The consulting references contain 0 URLs, even for date-sensitive Indonesian law.
   - Counts disagree across README, SKILL.md and GLOBAL.md (54/55 vs 58/59 vs 59/56).
   - Content drift is already visible: targetSdk 35 is past its deadline, Perpres 46/2025 thresholds are uncorroborated, and modernize says "8 vs 6" dimensions.
   - One regulatory claim checked out fully: PADK OJK 1/2026. The process gives no way to tell verified claims from unverified ones.

## Spot-check sources
- [PADK 1 Tahun 2026 — OJK](https://ojk.go.id/id/regulasi/Pages/PADK-1-Tahun-2026-Penyelenggaraan-Teknologi-Informasi-oleh-Bank-Umum.aspx) and its FAQ (in-flight licensing exception)
- [Perpres 46/2025 — BPK](https://peraturan.bpk.go.id/Details/318647); [DJPB comparison article](https://djpb.kemenkeu.go.id/kppn/gunungsitoli/id/data-publikasi/artikel/2982-perbandingan-pengadaan-langsung-dalam-perpres-12-tahun-2021-dan-perpres-46-tahun-2025-perubahan-batas-nilai,-definisi,-dan-penguatan-digitalisasi.html) (no thresholds found); [Bisnis — TKDN min 25%](https://ekonomi.bisnis.com/read/20250507/257/1875038/prabowo-revisi-aturan-tkdn-untuk-belanja-pemerintahbumn-jadi-minimal-25)
- [Google Play target API requirement](https://support.google.com/googleplay/android-developer/answer/11926878); [developer.android.com target-sdk](https://developer.android.com/google/play/requirements/target-sdk)
- Checked from memory, with no fetch: ISO/IEC 27001:2022 Annex A 93 (37/8/14/34), MASVS 2.1.0 categories, Apple ITMS-91053 and the Required Reason API categories, SPBE 6 domains, Go 1.22 loopvar, RFC 9457.
