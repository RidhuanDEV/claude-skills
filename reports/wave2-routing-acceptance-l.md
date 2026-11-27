# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 23529e8e090559dcdb5b0c2bd9dc9c89932d0ba053f93c811020238f7faa0adc.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-l.json.
Stage-one shortlist covers 350/354 positive owners.
Stage-two selections: accepted 468, accepted_outside_shortlist 4.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 221/472 | 471/472 |
| Primary recall | 42.9% | 99.7% |
| Primary precision | 85.0% | 99.8% |
| Near-misses with the excluded skill inactive | 90.7% | 99.2% |
| Skills meeting all three thresholds | 2 | 57 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 85.7% | 50.0% → 50.0% | FAIL |
| antislop-layoutmobile | 0.0% → 83.3% | — → 100.0% | 100.0% → 100.0% | FAIL |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 0.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-accessibility | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 66.7% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 66.7% → 100.0% | 62.5% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 50.0% → 100.0% | 57.1% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 50.0% → 100.0% | 75.0% → 100.0% | 0.0% → 100.0% | PASS |
| shadow-data | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 50.0% → 100.0% | 80.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-design | 50.0% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 83.3% → 100.0% | 60.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-finops | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 66.7% → 100.0% | 64.7% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-maintain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 83.3% → 100.0% | 90.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 83.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 50.0% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 0.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 83.3% → 100.0% | 50.0% → 100.0% | 0.0% → 100.0% | PASS |
| shadow-privacy | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 87.5% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 66.7% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 89/177 | 177/177 |
| id | 63/177 | 176/177 |

## Positive routing diagnostics

- Correct owner selected in 353 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 1 cases.
- Lexical rank one would displace 60 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 90.7% and candidate specificity was 99.2%.


## Reproduction

- wave2-trigger-blind-l.json · 8557b2919e6647986a8dd71b4c2e0862db56bfa0611b1b7797988ad1053e2915
- wave2-owner-selection-l.json · af7d9200675621e238c90a44aa3004187c7d5b2bf814a252ee5465e2619e6807

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 23529e8e090559dcdb5b0c2bd9dc9c89932d0ba053f93c811020238f7faa0adc
