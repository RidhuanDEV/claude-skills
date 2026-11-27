# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is ed59a7aa8efb087ba62b63011bb595c7aa532b4941f04fc12fcb56943636c3ad.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-g.json.
Stage-one shortlist covers 349/354 positive owners.
Stage-two selections: accepted 466, accepted_outside_shortlist 3, rejected_excluded 3.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 223/472 | 469/472 |
| Primary recall | 44.1% | 99.4% |
| Primary precision | 82.9% | 99.4% |
| Near-misses with the excluded skill inactive | 94.1% | 97.5% |
| Skills meeting all three thresholds | 2 | 55 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 50.0% → 50.0% | FAIL |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 50.0% → 50.0% | FAIL |
| shadow-accessibility | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 83.3% → 100.0% | 90.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 66.7% → 100.0% | 54.5% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 33.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 50.0% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 50.0% → 100.0% | 85.7% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-data | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 33.3% → 100.0% | 37.5% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-design | 50.0% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 50.0% → 66.7% | 46.7% → 100.0% | 50.0% → 100.0% | FAIL |
| shadow-doc | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 33.3% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 83.3% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 83.3% → 100.0% | 72.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 50.0% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 100.0% → 100.0% | 66.7% → 72.7% | 50.0% → 50.0% | FAIL |
| shadow-privacy | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 16.7% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 66.7% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 87/177 | 176/177 |
| id | 69/177 | 176/177 |

## Positive routing diagnostics

- Correct owner selected in 352 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 2 cases.
- Lexical rank one would displace 68 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 94.1% and candidate specificity was 97.5%.


## Reproduction

- wave2-trigger-blind-g.json · 342fd52994458310c855747b900573122cb132db67ec5837f009077d6e317a5d
- wave2-owner-selection-g.json · 56e5e860dce4feb158f4fb2e37b8c619b79acf6054c7844099c7ee1870577250

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate ed59a7aa8efb087ba62b63011bb595c7aa532b4941f04fc12fcb56943636c3ad
