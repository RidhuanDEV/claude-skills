# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 6bf295b1a0030cf73fbad316d7e48aa14925a5b0e17f7c632b7e05ee35beaa09.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-e.json.
Stage-one shortlist covers 351/354 positive owners.
Stage-two selections: accepted 460, accepted_no_owner 6, accepted_outside_shortlist 4, rejected_excluded 2.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 215/472 | 470/472 |
| Primary recall | 42.9% | 100.0% |
| Primary precision | 85.0% | 99.6% |
| Near-misses with the excluded skill inactive | 92.4% | 95.8% |
| Skills meeting all three thresholds | 1 | 55 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 0.0% → 0.0% | FAIL |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 50.0% → 50.0% | FAIL |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 50.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-accessibility | 66.7% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 66.7% → 100.0% | 41.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 33.3% → 100.0% | 50.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 33.3% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-data | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 33.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-design | 50.0% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 50.0% → 100.0% | 55.6% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 16.7% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 66.7% → 100.0% | 85.7% → 88.9% | 50.0% → 50.0% | FAIL |
| shadow-illustration | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 100.0% → 100.0% | 76.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 66.7% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 66.7% → 100.0% | 87.5% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 50.0% → 100.0% | 71.4% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 83.3% → 100.0% | 61.5% → 90.0% | 50.0% → 50.0% | FAIL |
| shadow-privacy | 83.3% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 33.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 100.0% → 100.0% | 90.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 66.7% → 100.0% | 72.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 87/177 | 177/177 |
| id | 65/177 | 177/177 |

## Positive routing diagnostics

- Correct owner selected in 354 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 0 cases.
- Lexical rank one would displace 85 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 92.4% and candidate specificity was 95.8%.


## Reproduction

- wave2-trigger-blind-e.json · 32de7a0f926fa17540b1c37c247f000e13e4f540c77e385b9081d614eea0d272
- wave2-owner-selection-e.json · 31145a5f8746617c09189a0de9b7e8d896a1a371fdf48a58d3e791359bb76fdc

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 6bf295b1a0030cf73fbad316d7e48aa14925a5b0e17f7c632b7e05ee35beaa09
