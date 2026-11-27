# External Research: Skill Authoring, Agent Evaluation, Standards Currency, OSS Tooling

Research date: 2026-11-26. Method: live WebFetch of primary pages where possible. Repo metadata came from GitHub (unauthenticated public API and HTML redirects), the npm registry, PyPI, and the OpenSSF Scorecard API (api.securityscorecards.dev). Web queries contained no personal or repository-identifying information.
Legend: **Fetched = yes** means the primary page was fetched and the claim was read on it. **search** means the claim was confirmed only through search-engine snippets or secondary sources (no primary fetch). **partial** means the primary page was fetched but did not show the exact detail, which came from a secondary source.
Unreviewed arXiv papers are tagged **[PREPRINT]**.

---

## 1. Agent Skills authoring: official guidance

### 1.1 Key facts (highest priority for the review)

**Description and listing budget in Claude Code**
- Claude Code loads a *listing* of every skill name and description into context. The listing always includes every name. When the listing exceeds its character budget, **descriptions are dropped, starting with the least-invoked skills**, which removes the keywords Claude needs to match a request. The budget scales at **1% of the model's context window**. Overflow writes a warning to the debug log (`--debug`). `/doctor` estimates the listing's cost and largest contributors, and `/skill-doctor` finds unused skills. Source: code.claude.com/docs/en/skills, "Skill descriptions are cut short".
- Ways to change the budget: the `skillListingBudgetFraction` setting (e.g. `0.02` = 2%), or the `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var (a fixed character count). `skillOverrides` can set low-priority skills to `"name-only"`.
- **Per-entry cap**: the combined `description` + `when_to_use` text is truncated at **1,536 characters** in the listing, regardless of budget (configurable via `skillListingMaxDescChars`). Docs advice: "Put the key use case first."
- The `/context` Skills row reports the size *after* the budget is applied. Before v2.1.196 it over-reported.
- After compaction, Claude Code re-attaches the most recent invocation of each skill, **keeping the first 5,000 tokens of each**, within a **combined 25,000-token budget** filled from the most recently invoked skill. Implication: put the most important instructions near the top of SKILL.md.
- If frontmatter YAML is malformed, the skill loads with **empty metadata**. `/skill-name` still works, but auto-matching on the description is lost. Detect this with `claude plugin validate .claude/skills` (v2.1.233+).
- Rules that must hold every time belong in **hooks**, not in skill prose ("Claude stops following a skill" troubleshooting).
- Frontmatter controls: `disable-model-invocation`, `user-invocable`, `allowed-tools` (pre-approves tools for that turn only and does not restrict tools), `context: fork` + `agent`, `paths`, `when_to_use`, `argument-hint`. Unknown fields are silently ignored.

**Codex (OpenAI) equivalent**
- The initial skills list uses **at most 2% of the model's context window, or 8,000 characters when the context window is unknown**. It is configurable via `skills.max_context_tokens` (up to 10,000 tokens). With many skills, Codex **shortens descriptions first**, may **omit some skills**, and shows a warning. Skill locations: `.agents/skills` (repo, cwd and parents), `$HOME/.agents/skills`, `/etc/codex/skills`, plus system skills (`skill-creator`, `skill-installer`). Optional `agents/openai.yaml` carries `allow_implicit_invocation` (default true). Note: the old URL developers.openai.com/codex/skills now 308-redirects to learn.chatgpt.com/docs/build-skills.

**Anthropic platform best practices** (platform.claude.com/.../agent-skills/best-practices)
- `name`: max 64 chars, lowercase letters, digits and hyphens only, no XML tags, must not contain the reserved words `anthropic` or `claude`. `description`: non-empty, **max 1,024 chars**, no XML tags, must say *what it does and when to use it*.
- **Write descriptions in the third person**, because the description is injected into the system prompt. Claude chooses from "potentially 100+ available Skills" using the description alone.
- Keep the **SKILL.md body under 500 lines**. Keep references **one level deep** from SKILL.md, because nested references get partially read (e.g. `head -100`). Reference files over **100 lines need a table of contents**.
- "Concise is key": the context window is a public good, and you should only add what Claude doesn't already know. Set degrees of freedom by fragility (high/medium/low). Avoid time-sensitive text (use an "Old patterns" section instead). Use consistent terminology. Use forward-slash paths. Use fully qualified MCP tool names (`Server:tool`). Avoid offering too many options. Scripts should "solve, don't defer" and avoid "voodoo constants". Use plan-validate-execute with verifiable intermediate outputs.
- **Evaluation-driven development**: build evals *before* extensive docs, with at least **three evaluations**, a no-skill baseline, minimal instructions, and iteration. Test with **Haiku, Sonnet and Opus**. Use the Claude A (author) / Claude B (tester) loop. There is no built-in eval runner on the platform.
- Name style: a gerund form is suggested (`processing-pdfs`). Avoid vague names (`helper`, `utils`).

**Open Agent Skills spec** (agentskills.io/specification, repo agentskills/agentskills, Apache-2.0)
- Required fields are `name` and `description`. `name` is 1-64 chars of `[a-z0-9-]`, cannot start or end with a hyphen, has **no consecutive hyphens**, and **must match the parent directory name**. `description` is 1-1024 chars. Optional fields: `license`, `compatibility` (max 500 chars), `metadata` (string to string map), `allowed-tools` (experimental).
- Progressive disclosure budget: metadata **about 100 tokens** per skill, instructions **under 5,000 tokens recommended**, resources on demand. Keep SKILL.md under 500 lines.
- Directories: `scripts/`, `references/`, `assets/`. Validate with `skills-ref validate ./my-skill`.
- **Eval format** (agentskills.io/skill-creation/evaluating-skills): `evals/evals.json` with `{skill_name, evals:[{id, prompt, expected_output, files, assertions}]}`. Run each case **with_skill vs without_skill** (or vs `old_skill` snapshot) in clean contexts. Outputs are `grading.json` (PASS/FAIL **with evidence**), `timing.json` (tokens, duration_ms), `benchmark.json` (mean/stddev pass_rate, time, tokens, delta), and human `feedback.json`. Start with 2-3 cases. Remove assertions that always pass in both configs. Use blind A/B LLM comparison between versions.
- Claude Code docs add: the `skill-creator` plugin (anthropics/claude-plugins-official) automates the loop, including **description tuning** (generates should-trigger and should-not-trigger prompts, measures hit rate, proposes description edits). `claude plugin eval` provides CI-gated evals with a `tool_used: Skill` grader to measure triggering.

**Anthropic Engineering blog** (2025-10-16): describes 3-level progressive disclosure. Security guidance: install skills only from trusted sources, and audit less-trusted ones (scripts, dependencies, instructions that reach external networks).

### 1.2 Implications for a 59-skill suite (analysis, not a quoted claim)
- With 59 skills, at about 1% of a 200K context (about 2,000 tokens, roughly 8K chars) the listing budget gives **about 135 chars per skill on average**. Long "Use when... Do NOT use for..." descriptions (300-600 chars) will make the **least-used skills lose their descriptions entirely**. Measure this with `/context` and `/doctor`. Front-load the key use case in the first sentence. Consider `name-only` overrides for rarely used skills, or consolidating siblings.
- The Codex budget (2% or 8,000 chars) is similar. With 59 skills that averages about 135 chars per description.
- The Anthropic API and agentskills.io cap descriptions at 1,024 chars. Claude Code truncates at 1,536. Any description over 1,024 chars would fail portability.
- A `name` that differs from the directory name, or contains `claude`/`anthropic`, violates the open spec or the platform rules.
- Benchmark evidence (below) shows that description-only routing loses a lot of accuracy. This makes description quality, and trigger evals (should and should-not), the highest-leverage investment.

---

## 2. Research on agent, skill and tool-use evaluation

| Work | Venue / status | Key finding relevant to skills |
|---|---|---|
| SWE-bench (Jimenez et al., arXiv 2310.06770) | **ICLR 2024** | Real GitHub issue resolution benchmark. The standard for coding agents. |
| τ-bench (Yao et al., arXiv 2406.12045) | **ICLR 2025** | Tool-agent-user benchmark. Introduces the **pass^k** reliability metric (consistency over k trials). GPT-4o scored pass^8 below 25% on retail. |
| τ²-bench (arXiv 2506.07982) | [PREPRINT] (search only) | Successor with a dual-control telecom domain. The repo asks users to adopt τ² as the latest version. |
| MetaTool (Huang et al., arXiv 2310.03128) | **ICLR 2024** (search) | Tool-usage awareness and tool **selection**, including the "similar choices" subtask. Directly analogous to sibling-skill disambiguation. |
| BFCL (Patil et al.) | **ICML 2025**, PMLR v267 (search) | Function-calling benchmark with AST-based evaluation. |
| Judging LLM-as-a-Judge (Zheng et al., arXiv 2306.05685) | **NeurIPS 2023 D&B** | GPT-4 judge reaches over 80% agreement with humans. Documents position, verbosity and self-enhancement bias. |
| Who Validates the Validators? (Shankar et al., arXiv 2404.12272) | arXiv page shows no venue. Reportedly UIST 2024, not verified here | **Criteria drift**: evaluation criteria emerge from observing outputs, so judges need human calibration per task. |
| Judging the Judges: position bias (Shi et al., arXiv 2406.07791) | reported AACL-IJCNLP 2025 (search) | 15 judges and more than 150K instances. Position bias is driven by the quality gap between answers. |
| Survey on LLM-as-a-Judge (arXiv 2411.15594) | [PREPRINT] (search) | Taxonomy of judge biases. |
| **SkillsBench** (Li et al., arXiv 2602.12670, v4 2026-06-14) | **[PREPRINT]** | 87 tasks, 8 domains, 18 model-harness configs, with and without skills. Curated skills raise mean pass rate **33.9% to 50.5% (+16.6pp)**, ranging from +4.1 to +25.7pp. **Focused skills with at most 3 modules beat large or exhaustive bundles.** Smaller model plus skills can match a larger model without them. |
| **SkillRouter** (Zheng et al., arXiv 2603.22455, v5 2026-07-20) | **[PREPRINT]** | On about 80K skills, **hiding the skill body (name+description only) costs 37-44pp routing accuracy**. Body-distilled descriptions recover part of the gap but remain 7-21pp below. A 1.2B retrieve+rerank model reaches 74.0% Hit@1. |
| Agentic Skills in the Wild (Liu et al., arXiv 2604.04323) | **[PREPRINT]** | Retrieving from 34K real skills: benefits are "fragile" and approach no-skill baselines in realistic settings. Query-specific refinement recovers part of the loss (Terminal-Bench 2.0: 57.7% to 65.5%). |
| SRA-Bench (2604.24594), SkillTester (2603.28815), SkillSeek (2609.38822), skill-benchmark survey (2606.11435) | **[PREPRINT]** (search only) | Retrieval-pipeline, utility+security and marketplace-scale skill evaluation. Not fetched. |

Takeaways for the review:
- Measure **trigger precision and recall** with should-trigger and should-not-trigger prompts.
- Use **pass^k** instead of single runs.
- Run a **with- and without-skill baseline**.
- **Calibrate** LLM judges against human labels, and use swap or blind ordering to control position bias.
- Prefer **focused** skills over exhaustive ones.

---

## 3. Standards currency (verified 2025-2026)

| Standard | Current status (as of 2026-11-26) | Notes |
|---|---|---|
| OWASP ASVS | **5.0.0**, May 2025 (launched 30 May 2025, Global AppSec EU) | 17 chapters. Cite requirements with a version prefix (`v5.0.0-x.y.z`). |
| OWASP Top 10 (web) | **2025** edition: A01 Broken Access Control, A02 Security Misconfiguration, **A03 Software Supply Chain Failures**, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging & Alerting Failures, **A10 Mishandling of Exceptional Conditions** | SSRF was folded into A01. Announced Nov 2025, with the write-up finalized in early 2026 (secondary sources). |
| OWASP Top 10 for LLM Apps | **2026 edition published 2026-08-04** (announced 2026-09-01): LLM01 Prompt Injection, LLM02 Sensitive Info Disclosure, **LLM03 Excessive Agency**, LLM04 Supply Chain, LLM05 Data & Model Poisoning, LLM06 Unbounded Consumption, LLM07 Misinformation, **LLM08 Hidden Context Exposure**, LLM09 Vector & Embedding Weaknesses, LLM10 Improper Output Handling | **A skill pinned to "OWASP LLM 2025" is one edition behind.** The genai.owasp.org llm-top-10 page still renders the 2025 list. The 2026 list comes from the official GitHub README. A new **Agent Control Standard (ACS)** was donated to the OWASP GenAI project. |
| OWASP Top 10 for Agentic Applications | **"for 2026", published 2025-12-09**: ASI01 Agent Goal Hijack, ASI02 Tool Misuse & Exploitation, ASI03 Identity & Privilege Abuse, ASI04 Agentic Supply Chain, ASI05 Unexpected Code Execution, ASI06 Memory & Context Poisoning, ASI07 Insecure Inter-Agent Communication, ASI08 Cascading Failures, ASI09 Human-Agent Trust Exploitation, ASI10 Rogue Agents | Item titles come from promptfoo docs. The OWASP page has a download only. |
| NIST AI 600-1 | GenAI Profile, **2024-07-26** (DOI 10.6028/NIST.AI.600-1). Page last updated 2026-04-08, with no revision published | |
| NIST SP 800-218 (SSDF) | **v1.1 Final (2022-02-03)**. **SP 800-218 Rev.1 = SSDF v1.2 is an Initial Public Draft (2025-12-17)**, not final | **SP 800-218A** (GenAI/dual-use foundation model community profile) Final 2024-07-26 |
| SLSA | **v1.2 is current (Approved)**, announced Nov 2025. It adds the **Source Track** and is backward-compatible with 1.1 | A working draft exists for further tracks |
| CycloneDX | **v1.7** (2025-10-21). v1.6 = ECMA-424 1st ed. (June 2024). v1.7 targeted for ECMA-424 2nd ed. (Dec 2025, per Ecma listing via search) | v1.7 adds a CBOM algorithm-family registry, citations and patents. CycloneDX 2.0 is announced as upcoming. |
| SPDX | **3.0.1** (Dec 2024) is the latest. spdx.dev lists "3.0" as current. ISO/IEC 5962:2021 still equals SPDX 2.2.1. ISO/IEC DIS 5962 (v3.0) is in progress | |
| WCAG | **WCAG 2.2** remains the standard. It was approved as **ISO/IEC 40500:2025** (W3C news 2025-10-21; ISO text is the Oct-2023 WCAG 2.2). **WCAG 3 is still a Working Draft** (latest drafts Sept 2026), with no completion for "a few more years" | |
| OpenTelemetry GenAI semconv | Moved to the dedicated repo **open-telemetry/semantic-conventions-genai** (Apache-2.0, no releases yet). The status is still **Development** (secondary sources). Covers GenAI client, agent, MCP and provider spans/metrics/events | Use `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` (secondary source) and plan for dual emission |
| MCP specification | **Current = 2026-07-28** (versioning page). Major changes: **stateless** (no `initialize` handshake, no `Mcp-Session-Id`), `server/discover` is mandatory, `subscriptions/listen`, Multi Round-Trip Requests (`input_required`), tasks moved to an extension, `resultType` required, `iss` validation (RFC 9207), **DCR deprecated in favor of Client ID Metadata Documents**, Roots/Sampling/Logging deprecated, 12-month deprecation policy. Previous: 2025-11-25 | Security Best Practices (2026-07-28): confused deputy, token passthrough (**MUST NOT** accept tokens not issued for the server), SSRF in OAuth discovery, **state-handle hijacking** (replaces session hijacking), local server compromise, OAuth URL scheme validation, stdio proxy escalation, mix-up attacks, localhost redirect impersonation, CIMD trust policies, scope minimization |
| RFC 9457 | Problem Details for HTTP APIs, **July 2023**, Standards Track, **obsoletes RFC 7807**. Media types `application/problem+json` and `+xml` | |
| OAuth 2.1 | **Still an Internet-Draft**: draft-ietf-oauth-v2-1-**17** (2026-10-31), IESG state "I-D Exists", WG milestone to IESG Dec 2026. **Not an RFC** | |
| RFC 9700 | **BCP 240**, Jan 2025, "Best Current Practice for OAuth 2.0 Security". Requires exact redirect URI matching and PKCE, forbids implicit and ROPC grants, requires sender-constrained tokens (mTLS/DPoP) or refresh rotation for public clients | |
| WebAuthn | **Level 3 is a W3C Recommendation, 2026-08-25** (REC-webauthn-3-20260825). The Level 4 charter runs 2026-09 to 2028-09 | |
| OWASP MASVS | **v2.1.0** (18 Jan 2024; adds MASVS-PRIVACY) is still the latest release. MASTG v2 refactor completed in 2026, MASWE 1.0.0 (secondary) | |
| ISO/IEC 27001 | **27001:2022 + Amd 1:2024** (climate action changes: 4.1 adds whether climate change is a relevant issue, 4.2 adds a note that interested parties can have climate requirements) | iso.org returned 403. Confirmed via standards-store listings |
| ISO/IEC 42001 | **42001:2023** (1st ed.) is still current. No amendment registered. EN ISO/IEC 42001:2026 is a European adoption of the identical text | iso.org returned 403. Confirmed via secondary trackers |

---

## 4. Open-source projects that could strengthen the suite

Data was fetched on 2026-11-26. "Latest" means the latest stable release on the registry or GitHub. Scorecard figures come from api.securityscorecards.dev (n/a = not indexed).

| Project | What it would add | License | Latest release (date) | Maintenance | OpenSSF Scorecard | Safety notes |
|---|---|---|---|---|---|---|
| anthropics/skills | Reference skills, `template/`, `spec/`, skill-creator patterns | Apache-2.0 per README (GitHub API reports no single SPDX) | rolling (pushed 2026-11-16) | Active, about 200K stars | n/a | README: "for demonstration and educational purposes only". Test before relying on it. Treat as data and review before installing. |
| agentskills/agentskills (+ `skills-ref`) | Spec plus `skills-ref validate` linter for frontmatter and naming | Apache-2.0 | rolling (pushed 2026-11-04) | Active | n/a | Run the validator in CI. |
| anthropics/claude-plugins-official `skill-creator` | Eval loop, blind A/B, **description trigger tuning** | (not checked) | n/a | Linked from the official docs | n/a | Official marketplace. |
| promptfoo | Prompt and agent regression tests, red-team plugins (OWASP LLM/Agentic mappings), CI | MIT | npm 0.126.0 (2026-11-18) | Very active | n/a | Telemetry is on by default. Disable it with `PROMPTFOO_DISABLE_TELEMETRY=1`. |
| DeepEval | pytest-style LLM metrics (G-Eval, tool correctness, task completion) | Apache-2.0 | PyPI 4.3.6 (2026-11-25) | Very active | n/a | Optional cloud (Confident AI). Keep it local. |
| Ragas (now vibrantlabsai/ragas; old explodinggradients URL redirects) | RAG metrics (faithfulness, context recall) | Apache-2.0 | 0.4.4 (2026-11-14) | Active | n/a | The org rename is a supply-chain trust signal. Pin the package and verify the PyPI publisher. |
| Inspect AI (UK AISI) | Rigorous eval framework: tasks, solvers, scorers, sandboxed agent evals, log viewer | MIT | 0.3.292 (2026-11-23) | Very active (frequent releases) | n/a | Government-maintained. Sandboxing built in. |
| garak (NVIDIA) | LLM vulnerability scanner (probes for injection, leakage, jailbreak) | Apache-2.0 | 0.17.1 (2026-10-16) | Active | n/a | Fires adversarial traffic, which is an L3-class run. Use only against your own endpoints. |
| OpenSSF Scorecard | Automated supply-chain posture checks for dependencies and the repo itself | Apache-2.0 | v5.7.0 (2026-11-19) | Active | 8.7 | — |
| Semgrep rules | SAST rule corpus | **Semgrep Rules License v1.0** (not OSI. Restricts use in competing SaaS. Read the license) | rolling | Active | 5.7 | License, not code, is the risk. |
| osv-scanner (Google) | Lockfile vulnerability scan against OSV.dev | Apache-2.0 | v2.7.1 (2026-11-09) | Active | 8.6 | — |
| syft / grype (Anchore) | SBOM generation (CycloneDX/SPDX) and vulnerability scan | Apache-2.0 | syft v1.57.2 (2026-11-16), grype v0.122.1 (2026-11-18) | Active | 8.9 / 8.2 (grype score dated 2026-05) | — |
| cosign (Sigstore) | Artifact signing, attestation, SLSA provenance verification | Apache-2.0 | v3.1.6 (2026-11-25) | Active | 8.6 | — |
| axe-core (Deque) | Automated WCAG 2.x checks | **MPL-2.0** | 4.14.1 (2026-11-16) | Active | 7.1 | Automated checks catch only a subset of WCAG. Pair with manual review. |
| Lighthouse CI | Performance, a11y and SEO budgets in CI | Apache-2.0 | @lhci/cli 0.16.1 (2026-11-11) | Active | 6.6 | — |
| Playwright | Browser E2E, a11y snapshots, trace | Apache-2.0 | 1.65.1 (2026-11-13) | Very active | 6.5 (**score dated 2022-08, stale**) | Install browsers from the official CDN only. |
| k6 (Grafana) | Load and perf testing | **AGPL-3.0** | v2.4.0 (date not fetched) | Active | 7.7 | AGPL: fine as a CLI tool, but check before embedding or redistributing. |
| Pact (pact-js) | Consumer-driven contract tests | MIT (npm) | 17.1.4 (2026-09-07) | Active | 4.2 | Lower Scorecard. Pin versions. |
| StrykerJS / mutmut | Mutation testing (JS/TS, Python) | Apache-2.0 / BSD-3-Clause | 10.1.1 (2026-10-23) / 3.8.1 (2026-10-28) | Active | 3.4 / 5.0 | Low Scorecard. Pin and verify. |
| Schemathesis | Property-based OpenAPI/GraphQL API fuzzing | MIT | 4.34.2 (2026-11-24) | Very active | 6.2 | Fuzzing is resource-intensive. Gate behind approval and use non-prod targets. |
| Spectral (Stoplight) | OpenAPI/AsyncAPI linting (rulesets incl. OWASP API) | Apache-2.0 | spectral-cli 6.17.1 (2026-11-06) | Maintained | 4.8 | — |
| OpenTelemetry Demo | Reference microservice app for observability skills and drills | Apache-2.0 | 3.1.0 (date not fetched) | Active | 7.9 | Heavy (many containers). Ephemeral use only. |
| markdownlint-cli2 | Lints SKILL.md and references | MIT | 0.24.2 (2026-11-20) | Active | 5.4 | — |
| lychee | Fast link checker for references/citations | Apache-2.0 (+MIT) | lychee-v0.24.2 (date not fetched) | Active | 4.7 | Network calls. Rate-limit and cache. |
| Vale (now vale-cli/vale) | Prose linting (terminology consistency, banned phrases, anti-slop rules) | MIT | v3.28.1 (date not fetched) | Active | n/a | The org moved from errata-ai. Verify the source. |

Highest-leverage additions for a skill suite:
1. `skills-ref validate` plus a frontmatter linter in CI. Check name/dir match, description at most 1,024 chars, and no reserved words.
2. A **trigger-eval harness** (skill-creator description tuning or `claude plugin eval` with a `tool_used: Skill` grader) that reports per-skill precision and recall over should-trigger and should-not-trigger prompts.
3. promptfoo or Inspect AI for regression tests across models (Haiku/Sonnet/Opus) with pass^k.
4. Vale + markdownlint + lychee for reference hygiene and terminology consistency.

---

## 5. Citation table

| Claim | URL | Publisher | Version / date | Fetched |
|---|---|---|---|---|
| Skill listing budget = 1% of context window; descriptions dropped from least-invoked first; warning in debug log; `/doctor`, `/skill-doctor` | https://code.claude.com/docs/en/skills | Anthropic (Claude Code docs) | live page, fetched 2026-11-26 | yes |
| `skillListingBudgetFraction`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`, `skillOverrides` name-only, 1,536-char per-entry cap, `skillListingMaxDescChars` | https://code.claude.com/docs/en/skills | Anthropic | fetched 2026-11-26 | yes |
| Compaction re-attach: first 5,000 tokens per skill, 25,000 combined | https://code.claude.com/docs/en/skills | Anthropic | fetched 2026-11-26 | yes |
| Malformed YAML leaves empty metadata; `claude plugin validate` (v2.1.233+) | https://code.claude.com/docs/en/skills | Anthropic | fetched 2026-11-26 | yes |
| Settings keys exist (index) | https://code.claude.com/docs/en/settings-reference | Anthropic | fetched 2026-11-26 | partial (index only) |
| name at most 64, description at most 1,024, third person, SKILL.md under 500 lines, refs one level deep, TOC over 100 lines, at least 3 evals, test Haiku/Sonnet/Opus | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Anthropic | fetched 2026-11-26 | yes |
| Progressive disclosure levels; security: trusted sources only, audit scripts | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Anthropic Engineering | 2025-10-16 | yes |
| Open spec: name rules (no `--`, match dir), description 1-1024, compatibility at most 500, metadata about 100 tokens, body under 5,000 tokens | https://agentskills.io/specification | Agent Skills project (agentskills/agentskills, Apache-2.0) | fetched 2026-11-26 | yes |
| evals.json / grading / benchmark / with-vs-without skill method | https://agentskills.io/skill-creation/evaluating-skills | Agent Skills project | fetched 2026-11-26 | yes |
| Codex: list at most 2% of context or 8,000 chars; `skills.max_context_tokens` up to 10,000; shortens descriptions then omits; `.agents/skills` | https://learn.chatgpt.com/docs/build-skills (redirect from developers.openai.com/codex/skills) | OpenAI | fetched 2026-11-26 | yes |
| SkillsBench +16.6pp, focused skills with at most 3 modules beat exhaustive | https://arxiv.org/abs/2602.12670 | arXiv [PREPRINT] | v4, 2026-06-14 | yes |
| Description-only routing costs 37-44pp | https://arxiv.org/abs/2603.22455 | arXiv [PREPRINT] | v5, 2026-07-20 | yes |
| Skill benefits fragile at 34K-skill scale | https://arxiv.org/abs/2604.04323 | arXiv [PREPRINT] | v1, 2026-04-06 | yes |
| SWE-bench, ICLR 2024 | https://arxiv.org/abs/2310.06770 | arXiv / ICLR | v3 2024-11-11 | yes |
| τ-bench, pass^k, ICLR 2025 | https://arxiv.org/abs/2406.12045 | arXiv / ICLR 2025 | 2024-06-17 | search |
| τ²-bench | https://github.com/sierra-research/tau-bench | Sierra | — | search |
| MetaTool ICLR 2024 | https://arxiv.org/abs/2310.03128 | arXiv / ICLR | — | search |
| BFCL ICML 2025 | https://proceedings.mlr.press/v267/patil25a.html | PMLR | v267 | search |
| LLM-as-a-judge over 80% agreement and biases | https://arxiv.org/abs/2306.05685 | arXiv / NeurIPS 2023 D&B | — | yes |
| Criteria drift | https://arxiv.org/abs/2404.12272 | arXiv | 2024-04-18 | yes |
| Position bias study | https://arxiv.org/abs/2406.07791 | arXiv | v9 | search |
| ASVS 5.0.0 May 2025 | https://github.com/OWASP/ASVS | OWASP | 5.0.0 | search |
| OWASP Top 10:2025 list | https://top10.owasp.org/2025 | OWASP | 2025 | yes |
| OWASP LLM Top 10 2026 list, published 2026-08-04 | https://raw.githubusercontent.com/GenAI-Security-Project/GenAI-LLM-Top10/main/README.md | OWASP GenAI Security Project | 2026 | yes |
| 2026 LLM Top 10 announcement + Agent Control Standard | https://genai.owasp.org/announcement/owasp-genai-security-project-unveils-2026-top-10-for-llm-applications-new-agent-control-standard-and-sponsors-as-community-tops-30000-members/ | OWASP GenAI | 2026-09-01 | yes |
| LLM Top 10 2025 list | https://genai.owasp.org/llm-top-10/ | OWASP GenAI | 2025 | yes |
| Agentic Top 10 published 2025-12-09 | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | OWASP GenAI | 2026 ed. | yes |
| ASI01-ASI10 titles | https://www.promptfoo.dev/docs/red-team/owasp-agentic-ai/ | promptfoo (secondary) | — | yes |
| NIST AI 600-1, 2024-07-26 | https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence | NIST | 2024-07-26 (page upd. 2026-04-08) | yes |
| SSDF 1.1 final, 1.2 draft, 800-218A final | https://csrc.nist.gov/projects/ssdf/publications | NIST CSRC | 1.2 IPD 2025-12-17 | yes |
| SLSA v1.2 current/approved | https://slsa.dev/spec/ | OpenSSF SLSA | v1.2 | yes |
| SLSA v1.2 announcement | https://slsa.dev/blog/2025/11/announce-slsa-v1.2 | OpenSSF SLSA | Nov 2025 | search |
| CycloneDX 1.7 | https://cyclonedx.org/news/cyclonedx-v1.7-released | OWASP CycloneDX | 2025-10-21 | yes |
| ECMA-424 2nd ed. Dec 2025 | https://ecma-international.org/publications-and-standards/standards/ecma-424/ | Ecma International | 2nd ed. | search |
| SPDX 3.0 current; ISO/IEC 5962:2021 | https://spdx.dev/use/specifications/ | Linux Foundation SPDX | 3.0(.1) | yes |
| WCAG 3 still a draft; WCAG 2 current | https://www.w3.org/WAI/WCAG3 | W3C WAI | upd. 2026-11-16 | yes |
| WCAG 2.2 = ISO/IEC 40500:2025 | https://www.w3.org/WAI/news/2025-10-21/wcag22-iso | W3C | 2025-10-21 | search |
| OTel GenAI semconv moved to dedicated repo | https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/ and https://github.com/open-telemetry/semantic-conventions-genai | OpenTelemetry / CNCF | no releases | yes |
| GenAI semconv still Development status | https://dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-not-stable-yet-heres-what-actually-shipped-in-2026-3mke | secondary | 2026 | search |
| MCP current = 2026-07-28 | https://modelcontextprotocol.io/specification/versioning | MCP project (LF) | 2026-07-28 | yes |
| MCP 2026-07-28 changelog (stateless, DCR deprecated, iss validation) | https://modelcontextprotocol.io/specification/2026-07-28/changelog | MCP project | 2026-07-28 | yes |
| MCP security best practices | https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices | MCP project | 2026-07-28 | yes |
| RFC 9457 | https://www.rfc-editor.org/rfc/rfc9457.html | IETF / RFC Editor | July 2023 | yes |
| OAuth 2.1 still a draft (-17) | https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/ | IETF | draft-17, 2026-10-31 | yes |
| RFC 9700 BCP 240 | https://www.rfc-editor.org/rfc/rfc9700.html | IETF / RFC Editor | Jan 2025 | yes |
| WebAuthn L3 Recommendation | https://www.w3.org/news/2026/web-authentication-an-api-for-accessing-public-key-credentials-level-3-is-now-a-w3c-recommendation/ | W3C | 2026-08-25 | yes |
| MASVS v2.1.0 latest | https://github.com/OWASP/masvs/releases | OWASP MAS | v2.1.0 (18 Jan 2024) | yes (year via search) |
| ISO/IEC 27001:2022/Amd 1:2024 | https://www.iso.org/standard/88435.html | ISO/IEC | Feb 2024 | no (403). Search via standards stores |
| ISO/IEC 42001:2023 no amendment | https://www.iso.org/standard/42001 | ISO/IEC | 2023 | no (403). Search via trackers |
| Tool licenses, releases, activity | api.github.com, registry.npmjs.org, pypi.org | GitHub / npm / PyPI | fetched 2026-11-26 | yes |
| Scorecard scores | https://api.securityscorecards.dev/projects/github.com/{org}/{repo} | OpenSSF | dates per row | yes |
| anthropics/skills license and demo-only disclaimer | https://github.com/anthropics/skills | Anthropic | fetched 2026-11-26 | yes |
| Semgrep Rules License v1.0 | https://github.com/semgrep/semgrep-rules | Semgrep | fetched 2026-11-26 | yes (terms not read) |

## 6. Not measured / caveats
- The settings-reference entries (defaults and units for `skillListingMaxDescChars`) were not read in full. Only the index was seen. The skills page states the 1,536 default.
- The exact listing budget in characters depends on the model's context window. The ~135 chars/skill figure is an estimate, not a measurement. Measure it with `/context` in the target environment.
- ISO pages returned 403, so the ISO status comes from secondary sources.
- OTel GenAI "Development" status comes from secondary sources. The repo README did not state it.
- Release dates for k6, lychee, Vale and the OTel Demo were not fetched because of the GitHub API rate limit. Only the tags are known.
- Scorecard is n/a for several AI-eval repos. Playwright's score is from 2022 and stale.
- The Codex docs URL redirects to learn.chatgpt.com. Content was attributed to OpenAI by the page, but the domain change itself was not verified further.
