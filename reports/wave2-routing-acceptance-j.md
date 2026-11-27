# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is c0ae6a7ba3f197e5e958b791e5b3cd35b5a4ebef076e4f98da279ad05a8f78c4.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-j.json.
Stage-one shortlist covers 352/354 positive owners.
Stage-two selections: accepted 468, accepted_outside_shortlist 4.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 226/472 | 472/472 |
| Primary recall | 42.9% | 100.0% |
| Primary precision | 89.0% | 100.0% |
| Near-misses with the excluded skill inactive | 94.9% | 99.2% |
| Skills meeting all three thresholds | 1 | 58 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 0.0% → 50.0% | FAIL |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-accessibility | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 66.7% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 50.0% → 100.0% | 71.4% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 33.3% → 100.0% | 71.4% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-data | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 66.7% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-design | 66.7% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 33.3% → 100.0% | 50.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 16.7% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 83.3% → 100.0% | 90.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 50.0% → 100.0% | 71.4% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 16.7% → 100.0% | 25.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 100.0% → 100.0% | 75.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-privacy | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 33.3% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 83.3% → 100.0% | 88.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 66.7% → 100.0% | 77.8% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 90/177 | 177/177 |
| id | 62/177 | 177/177 |

## Positive routing diagnostics

- Correct owner selected in 354 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 0 cases.
- Lexical rank one would displace 64 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 94.9% and candidate specificity was 99.2%.


## Reproduction

- wave2-trigger-blind-j.json · 654cbd66e0909e3ffb4ee4ed6bcf14430c1847bc723774ec3fa14420d4bd8e78
- wave2-owner-selection-j.json · 0d7b14dda2729d34b19ceb3256f41ef10f9fc02905a29c8ca4f616ddac5f8943

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate c0ae6a7ba3f197e5e958b791e5b3cd35b5a4ebef076e4f98da279ad05a8f78c4
