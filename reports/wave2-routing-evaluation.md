# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 000be25a10f3e9a4dd6f257948e5b6aec2acd4aa6389a647720870f069ad9aa3.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 118/472 | 337/472 |
| Primary recall | 24.0% | 68.1% |
| Primary precision | 83.7% | 85.5% |
| Near-misses with the excluded skill inactive | 95.8% | 99.2% |
| Skills meeting all three thresholds | 0 | 5 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 16.7% | — → 100.0% | 100.0% → 100.0% | FAIL |
| antislop-code | 0.0% → 0.0% | — → 100.0% | 100.0% → 100.0% | FAIL |
| antislop-copywriting | 0.0% → 33.3% | — → 50.0% | 100.0% → 100.0% | FAIL |
| antislop-human | 0.0% → 50.0% | — → 80.0% | 50.0% → 100.0% | FAIL |
| antislop-layoutmobile | 0.0% → 50.0% | — → 71.4% | 100.0% → 100.0% | FAIL |
| antislop-ui | 0.0% → 66.7% | — → 83.3% | 100.0% → 100.0% | FAIL |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 16.7% → 66.7% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| modern-web-guidance | 0.0% → 33.3% | — → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-accessibility | 50.0% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-ai-eng | 16.7% → 83.3% | 66.7% → 87.5% | 100.0% → 100.0% | FAIL |
| shadow-analytics | 16.7% → 66.7% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-api | 50.0% → 100.0% | 100.0% → 83.3% | 100.0% → 100.0% | FAIL |
| shadow-architect | 33.3% → 100.0% | 100.0% → 88.9% | 100.0% → 100.0% | FAIL |
| shadow-auth | 16.7% → 83.3% | 40.0% → 66.7% | 50.0% → 50.0% | FAIL |
| shadow-bootstrap | 16.7% → 83.3% | 100.0% → 83.3% | 100.0% → 100.0% | FAIL |
| shadow-browser | 33.3% → 33.3% | 50.0% → 60.0% | 100.0% → 100.0% | FAIL |
| shadow-cache | 16.7% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-compat | 0.0% → 66.7% | — → 60.0% | 100.0% → 100.0% | FAIL |
| shadow-concurrency | 33.3% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-data | 33.3% → 50.0% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-db | 16.7% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-debug | 33.3% → 66.7% | 50.0% → 57.1% | 100.0% → 100.0% | FAIL |
| shadow-design | 50.0% → 83.3% | 50.0% → 54.5% | 100.0% → 100.0% | FAIL |
| shadow-discovery | 33.3% → 66.7% | 40.0% → 50.0% | 100.0% → 100.0% | FAIL |
| shadow-doc | 16.7% → 66.7% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-domain | 16.7% → 50.0% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-ea | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 16.7% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-eval | 0.0% → 83.3% | — → 100.0% | 50.0% → 100.0% | FAIL |
| shadow-finops | 0.0% → 50.0% | — → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-git | 0.0% → 50.0% | — → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-grc | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 33.3% → 83.3% | 80.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-illustration | 33.3% → 83.3% | 100.0% → 83.3% | 100.0% → 100.0% | FAIL |
| shadow-integrate | 50.0% → 66.7% | 75.0% → 80.0% | 100.0% → 100.0% | FAIL |
| shadow-maintain | 50.0% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-mobile | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 16.7% → 66.7% | 100.0% → 66.7% | 100.0% → 100.0% | FAIL |
| shadow-monarch | 0.0% → 33.3% | — → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-observe | 50.0% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-ops | 83.3% → 83.3% | 71.4% → 81.8% | 100.0% → 100.0% | FAIL |
| shadow-perf | 16.7% → 33.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-plan | 0.0% → 50.0% | 100.0% → 83.3% | 100.0% → 100.0% | FAIL |
| shadow-pmo | 66.7% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-presales | 50.0% → 66.7% | 71.4% → 75.0% | 100.0% → 100.0% | FAIL |
| shadow-privacy | 33.3% → 50.0% | 100.0% → 83.3% | 100.0% → 100.0% | FAIL |
| shadow-quality | 33.3% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-realtime | 50.0% → 83.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-refactor | 16.7% → 66.7% | 100.0% → 77.8% | 100.0% → 100.0% | FAIL |
| shadow-release | 0.0% → 83.3% | 100.0% → 88.9% | 100.0% → 100.0% | FAIL |
| shadow-resilience | 33.3% → 33.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-search | 16.7% → 100.0% | 100.0% → 75.0% | 100.0% → 100.0% | FAIL |
| shadow-sec | 33.3% → 66.7% | 100.0% → 100.0% | 50.0% → 100.0% | FAIL |
| shadow-seo | 16.7% → 33.3% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-supplychain | 50.0% → 66.7% | 100.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-test | 33.3% → 100.0% | 100.0% → 76.9% | 100.0% → 100.0% | FAIL |
| shadow-uat | 0.0% → 66.7% | — → 83.3% | 100.0% → 100.0% | FAIL |
| shadow-video | 0.0% → 33.3% | — → 75.0% | 100.0% → 100.0% | FAIL |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 45/177 | 126/177 |
| id | 40/177 | 115/177 |

## Positive routing diagnostics

- Correct owner selected in 241 cases.
- Correct owner missed despite ranking first lexically in 36 cases.
- Correct owner missed with a lower shortlist rank in 49 cases.
- Correct owner absent from the shortlist and selection in 28 cases.
- Lexical rank one would displace 11 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 95.8% and candidate specificity was 98.3%.

- modern-web-guidance-07 → modern-web-guidance-07-adjudicated. Search Console coverage, canonical targets and XML sitemap coverage are technical SEO ownership. This is an indexing and crawl analysis without browser implementation, rendering, layout, Core Web Vitals or Baseline API choices.
- antislop-layoutmobile-07 → antislop-layoutmobile-07-adjudicated. The mobile client is a consumer of the requested backend API contract. Cursor semantics and OpenAPI belong to shadow-api. The task contains no screen, reflow, viewport, breakpoint or touch target work.
- antislop-human-07 → antislop-human-07-adjudicated. Tab is a character in batch-process input rather than a UI navigation event. Root-cause analysis and reproducer ownership belong to shadow-debug. The command has no interactive affordance or visual element.
- shadow-doc-08 → shadow-doc-08-adjudicated. The BAST is evidence in a contract scope and acceptance dispute. Clause interpretation and escalation to the change-control board are PMO work. The user asks for classification and an approval route, without generating, rendering or revising the BAST.

## Reproduction

- wave2-trigger-holdout-a.json · 02acbb3e57733f32bd1e9808401198a5e24b066eda4367df6646d0aefe2e0fe0
- wave2-trigger-holdout-b.json · acd4e7a46b33f99cb8e870be145ba2552fca75eb9bacd4e901fa2ab04ff3a5b6
- wave2-trigger-adjudications.json · 57f590831de12a76f75f7f40eea060e33cf583e5354bb3db22b2816016eca588

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 000be25a10f3e9a4dd6f257948e5b6aec2acd4aa6389a647720870f069ad9aa3

## Development evidence

The three earlier frozen candidates selected 316, 334, and 337 of 472 primary owners. The current candidate selects 337 on the adjudicated set with the same positive prompts. Four upstream near-miss labels were replaced after an independent policy audit. Runtime changes removed unconditional co-activation for four relationships and suppressed UI filters on pure CLI and SQL work. Original fixture specificity is reported above to make the runtime change visible alongside adjudication.

The [59-case development set](../evals/fixtures/wave2-trigger-development.json) measured 36/59 before earlier calibration and 59/59 after it. The new [confusion diagnostics](../evals/fixtures/wave2-trigger-confusion-dev.json) measured 6/18. These are development results. The 472-case acceptance run is a repeated measurement with frozen positives.

## Host listing

| Check | Baseline | Candidate | Status |
| --- | ---: | ---: | --- |
| Source description characters | 18,856 | 7,640 | PASS |
| Full Codex CLI listing, 200k | 12/59 | 59/59 | PASS |
| Claude Code project descriptions at default 1%, 200k | — | 7/59 | FAIL |
| Claude Code project descriptions with Wave 2 settings, 200k | — | 59/59 | PASS |
| Live activation by a model | — | — | NOT_RUN |

Codex CLI 0.167.0 rendered model-visible input via its debug command in an isolated 200k-context project. The candidate listed all 59 descriptions in full. [Codex listing implementation](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/ext/skills/src/render.rs#L154-L185)

Claude Code 2.1.332 ran the local context command with a pinned Claude Haiku 4.5 model ID. In the 200k-context scratch project, all 59 post-budget row estimates with the [Wave 2 settings](../docs/claude-code-wave2.settings.json) matched the high-budget reference. Under default settings 52 rows collapsed to name-only. A 512-character control collapsed all 59, confirming the measured signal responded to truncation. The Wave 2 session profile used approximately 3.7k context tokens. The provider endpoint was loopback-blocked throughout the probes. [Claude Code listing budget](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short) · [Claude model context windows](https://platform.claude.com/docs/en/models/overview#all-models)

## Local regression checks

All 154 router self-tests, 51 evaluator tests, and the local quality gate passed. Wave 2 acceptance remains FAIL with five of 59 skills meeting the combined thresholds. The final near-miss issue is an operational authentication outage assigned to the authentication specialist. The broader primary ranking gap remains open.
