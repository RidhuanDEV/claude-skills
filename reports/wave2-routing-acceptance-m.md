# Wave 2 Routing Evaluation

**Held-out acceptance gate · PASS**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 83ade33cc21eba9bc2d04ddf43597864c4000e94b63c9357accbe309da582d94.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-m.json.
Stage-one shortlist covers 353/354 positive owners.
Stage-two selections: accepted 471, accepted_outside_shortlist 1.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 221/472 | 472/472 |
| Primary recall | 43.8% | 100.0% |
| Primary precision | 89.8% | 100.0% |
| Near-misses with the excluded skill inactive | 94.9% | 100.0% |
| Skills meeting all three thresholds | 1 | 59 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 50.0% → 100.0% | PASS |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-accessibility | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 66.7% → 100.0% | 63.6% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-data | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-design | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 50.0% → 100.0% | 40.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 16.7% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 100.0% → 100.0% | 81.8% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-maintain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 83.3% → 100.0% | 88.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 66.7% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 83.3% → 100.0% | 72.7% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-privacy | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 33.3% → 100.0% | 80.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 87/177 | 177/177 |
| id | 68/177 | 177/177 |

## Positive routing diagnostics

- Correct owner selected in 354 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 0 cases.
- Lexical rank one would displace 70 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 94.9% and candidate specificity was 100.0%.


## Reproduction

- wave2-trigger-blind-m.json · f48352d9bd4a2151af85be3b2ba393cee739c8c82eb8fd50680f8fa803134e5a
- wave2-owner-selection-m.json · cc222c7d2f7a24b841bb8a649cb03c4d6653b0ba7683949c110d943de811d1ef

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 83ade33cc21eba9bc2d04ddf43597864c4000e94b63c9357accbe309da582d94
