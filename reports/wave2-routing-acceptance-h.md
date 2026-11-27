# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 83957f1daf339030c0f09a4c61280c52678c5b0398146cb6f0fc38871a3c40e1.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-h.json.
Stage-one shortlist covers 351/354 positive owners.
Stage-two selections: accepted 464, accepted_outside_shortlist 6, rejected_excluded 2.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 210/472 | 470/472 |
| Primary recall | 44.1% | 99.7% |
| Primary precision | 81.1% | 99.6% |
| Near-misses with the excluded skill inactive | 94.1% | 99.2% |
| Skills meeting all three thresholds | 2 | 57 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-accessibility | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 83.3% → 100.0% | 43.8% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-bootstrap | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 33.3% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 33.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 50.0% → 100.0% | 71.4% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-data | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 50.0% → 100.0% | 50.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-design | 83.3% → 100.0% | 71.4% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-discovery | 66.7% → 83.3% | 53.8% → 100.0% | 50.0% → 100.0% | FAIL |
| shadow-doc | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 16.7% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 83.3% → 100.0% | 69.2% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 83.3% → 100.0% | 66.7% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-perf | 66.7% → 100.0% | 50.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 83.3% → 100.0% | 63.6% → 80.0% | 50.0% → 50.0% | FAIL |
| shadow-privacy | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 33.3% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 66.7% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 66.7% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 66.7% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 81/177 | 176/177 |
| id | 75/177 | 177/177 |

## Positive routing diagnostics

- Correct owner selected in 353 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 1 cases.
- Lexical rank one would displace 59 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 94.1% and candidate specificity was 99.2%.


## Reproduction

- wave2-trigger-blind-h.json · b7810031d0211d897d3efd37351f9058a22b1a63755996940ca6dbd358c31c68
- wave2-owner-selection-h.json · bf5a9d2f5ff0be2595f4cc914d393efeb4fa2251eadcb079060ce6f358671d5d

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 83957f1daf339030c0f09a4c61280c52678c5b0398146cb6f0fc38871a3c40e1
