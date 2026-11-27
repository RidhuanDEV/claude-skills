# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 7a1a31932262aa71edf21df98088b7d9ab4e425fae52f4caa5fd8e8e1e14992e.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-i.json.
Stage-one shortlist covers 348/354 positive owners.
Stage-two selections: accepted 465, accepted_outside_shortlist 7.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 215/472 | 472/472 |
| Primary recall | 42.1% | 100.0% |
| Primary precision | 87.0% | 100.0% |
| Near-misses with the excluded skill inactive | 95.8% | 99.2% |
| Skills meeting all three thresholds | 1 | 58 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 50.0% → 100.0% | PASS |
| context7 | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| handoff | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 50.0% → 100.0% | 100.0% → 100.0% | 50.0% → 50.0% | FAIL |
| shadow-accessibility | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 100.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 83.3% → 100.0% | 87.5% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 83.3% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 50.0% → 100.0% | 71.4% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 50.0% → 100.0% | 85.7% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-data | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 33.3% → 100.0% | 50.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-design | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 33.3% → 100.0% | 45.5% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 33.3% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 66.7% → 100.0% | 64.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 100.0% → 100.0% | 90.9% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 66.7% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 83.3% → 100.0% | 77.8% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-privacy | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 33.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 50.0% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 85/177 | 177/177 |
| id | 64/177 | 177/177 |

## Positive routing diagnostics

- Correct owner selected in 354 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 0 cases.
- Lexical rank one would displace 68 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 95.8% and candidate specificity was 99.2%.


## Reproduction

- wave2-trigger-blind-i.json · 24fefa86769ceebaeb6c13c7f93e5a2343b40a8d0279d706293354a48b303857
- wave2-owner-selection-i.json · 568c162f93b4e274bdfc29ef1252fe5c1aaa6c5157ec26a1b8af89fbf4825ae4

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 7a1a31932262aa71edf21df98088b7d9ab4e425fae52f4caa5fd8e8e1e14992e
