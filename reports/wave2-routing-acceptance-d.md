# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is f1c0c3328d0dcd93cc74c20421d9602f975676f92e956d6883ee964164d790f0.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-d.json.
Stage-one shortlist covers 352/354 positive owners.
Stage-two selections: accepted 466, accepted_no_owner 4, accepted_outside_shortlist 1, rejected_excluded 1.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 215/472 | 471/472 |
| Primary recall | 43.8% | 99.7% |
| Primary precision | 83.5% | 99.8% |
| Near-misses with the excluded skill inactive | 90.7% | 96.6% |
| Skills meeting all three thresholds | 0 | 53 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 50.0% → 50.0% | FAIL |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 50.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 50.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-accessibility | 66.7% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 50.0% → 100.0% | 30.8% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-bootstrap | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 50.0% → 100.0% | 71.4% → 100.0% | 50.0% → 50.0% | FAIL |
| shadow-cache | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 50.0% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-data | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 50.0% → 100.0% | 62.5% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-design | 50.0% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 83.3% → 100.0% | 53.3% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 16.7% → 100.0% | 50.0% → 100.0% | 50.0% → 50.0% | FAIL |
| shadow-ea | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 16.7% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 83.3% → 100.0% | 72.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 66.7% → 100.0% | 100.0% → 100.0% | 50.0% → 50.0% | FAIL |
| shadow-ops | 83.3% → 100.0% | 72.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 66.7% → 83.3% | 75.0% → 100.0% | 100.0% → 100.0% | FAIL |
| shadow-plan | 33.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 83.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-privacy | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 85.7% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-refactor | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 83.3% → 100.0% | 88.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 33.3% → 100.0% | 75.0% → 87.5% | 100.0% → 100.0% | FAIL |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 84/177 | 177/177 |
| id | 71/177 | 176/177 |

## Positive routing diagnostics

- Correct owner selected in 353 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 1 cases.
- Lexical rank one would displace 63 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 90.7% and candidate specificity was 96.6%.


## Reproduction

- wave2-trigger-blind-d.json · f3c1d993ce20415a212105a66450245b3839acffb96a1f6ff346f171b9aabb8e
- wave2-owner-selection-d.json · b4f486de40ef5f87d75d81c96f39ff9217d7d37c7b3789ec277ff5b931283b23

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate f1c0c3328d0dcd93cc74c20421d9602f975676f92e956d6883ee964164d790f0
