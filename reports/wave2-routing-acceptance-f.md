# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 5ace8d48472c6a898244510cab855db9944d9bb0d8d3160deea0ce74c1e3d0dd.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-f.json.
Stage-one shortlist covers 351/354 positive owners.
Stage-two selections: accepted 467, accepted_outside_shortlist 5.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 224/472 | 470/472 |
| Primary recall | 44.9% | 99.7% |
| Primary precision | 84.8% | 99.6% |
| Near-misses with the excluded skill inactive | 94.9% | 98.3% |
| Skills meeting all three thresholds | 1 | 56 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 50.0% → 50.0% | FAIL |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-accessibility | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 83.3% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 66.7% → 100.0% | 70.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 66.7% → 100.0% | 36.4% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 66.7% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 83.3% → 100.0% | 77.8% → 100.0% | 0.0% → 100.0% | PASS |
| shadow-data | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 50.0% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 50.0% → 100.0% | 60.0% → 80.0% | 50.0% → 50.0% | FAIL |
| shadow-design | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 66.7% → 100.0% | 57.1% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 16.7% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 100.0% → 100.0% | 76.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 83.3% → 100.0% | 76.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 66.7% → 100.0% | 50.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 33.3% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 100.0% → 100.0% | 77.8% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-privacy | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 0.0% → 100.0% | 50.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 83.3% → 83.3% | 90.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-uat | 0.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 91/177 | 176/177 |
| id | 68/177 | 177/177 |

## Positive routing diagnostics

- Correct owner selected in 353 cases.
- Correct owner missed despite ranking first lexically in 1 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 0 cases.
- Lexical rank one would displace 70 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 94.9% and candidate specificity was 98.3%.


## Reproduction

- wave2-trigger-blind-f.json · 52b72ba71061c31e3001a05b684772dd1e5812ccd2cf023f5db667fdf4d665fa
- wave2-owner-selection-f.json · 91255fdadc078fc798ae99381d6809dcf904fae9a32ff3cea596764b2237f7d1

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 5ace8d48472c6a898244510cab855db9944d9bb0d8d3160deea0ce74c1e3d0dd
