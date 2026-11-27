# Wave 2 Routing Evaluation

**Held-out acceptance gate · FAIL**

Compared 472 prompts across 59 skills. Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.
Baseline commit is 1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857.
Candidate source SHA-256 is 9024658a28f5b90c5a82e447abf3ac53f9aca83ed6a3dcd3c0ba66cbbe6f1308.
Mode is two_stage. Fixtures: evals/fixtures/wave2-trigger-blind-k.json.
Stage-one shortlist covers 350/354 positive owners.
Stage-two selections: accepted 467, accepted_outside_shortlist 4, rejected_fixed_owner 1.

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact primary owner | 207/472 | 471/472 |
| Primary recall | 41.2% | 99.7% |
| Primary precision | 83.1% | 100.0% |
| Near-misses with the excluded skill inactive | 93.2% | 100.0% |
| Skills meeting all three thresholds | 0 | 58 |

The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. Recall uses six positive cases per skill. Precision includes all primary assignments. Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.

| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |
| --- | ---: | ---: | ---: | --- |
| antislop | 0.0% → 100.0% | — → 100.0% | 50.0% → 100.0% | PASS |
| antislop-code | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-copywriting | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-human | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-layoutmobile | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| antislop-ui | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| context7 | 0.0% → 83.3% | — → 100.0% | 100.0% → 100.0% | FAIL |
| handoff | 0.0% → 100.0% | 0.0% → 100.0% | 100.0% → 100.0% | PASS |
| modern-web-guidance | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-accessibility | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ai-eng | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-analytics | 83.3% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-api | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-architect | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-auth | 50.0% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-bootstrap | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-browser | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-cache | 66.7% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-compat | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-concurrency | 50.0% → 100.0% | 66.7% → 100.0% | 0.0% → 100.0% | PASS |
| shadow-data | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-db | 66.7% → 100.0% | 83.3% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-debug | 33.3% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-design | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-discovery | 66.7% → 100.0% | 35.7% → 100.0% | 0.0% → 100.0% | PASS |
| shadow-doc | 0.0% → 100.0% | 66.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-domain | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ea | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-email | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-eval | 16.7% → 100.0% | 100.0% → 100.0% | 50.0% → 100.0% | PASS |
| shadow-finops | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-git | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-grc | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-handover | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-illustration | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-integrate | 83.3% → 100.0% | 80.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-maintain | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-mobile | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-modernize | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-monarch | 0.0% → 100.0% | — → 100.0% | 100.0% → 100.0% | PASS |
| shadow-observe | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-ops | 83.3% → 100.0% | 70.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-perf | 16.7% → 100.0% | 40.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-plan | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-pmo | 66.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-presales | 100.0% → 100.0% | 54.5% → 100.0% | 0.0% → 100.0% | PASS |
| shadow-privacy | 100.0% → 100.0% | 85.7% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-quality | 33.3% → 100.0% | 60.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-realtime | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-refactor | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-release | 16.7% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-resilience | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-search | 50.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-sec | 83.3% → 100.0% | 81.8% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-seo | 83.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-supplychain | 50.0% → 100.0% | 75.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-test | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-uat | 0.0% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |
| shadow-video | 33.3% → 100.0% | 100.0% → 100.0% | 100.0% → 100.0% | PASS |

## Positive recall by language

| Language | Baseline | Candidate |
| --- | ---: | ---: |
| en | 81/177 | 176/177 |
| id | 65/177 | 177/177 |

## Positive routing diagnostics

- Correct owner selected in 353 cases.
- Correct owner missed despite ranking first lexically in 0 cases.
- Correct owner missed with a lower shortlist rank in 0 cases.
- Correct owner absent from the shortlist and selection in 1 cases.
- Lexical rank one would displace 66 correctly routed positives.

## Near-miss adjudication

On the original frozen negatives, baseline specificity was 93.2% and candidate specificity was 100.0%.


## Reproduction

- wave2-trigger-blind-k.json · ebd9e74ea8166fae499cebd5673ede32d54c33cf46517ab07a2d05440a010a39
- wave2-owner-selection-k.json · fb390ffb2e4d4e7480fef0cac04fade4e151b373ee9fd6b06e9a49709bc7dc83

Run the comparison offline with the archived candidate fingerprint.

python -B evals/compare_skill_trigger_routing.py --expect-candidate 9024658a28f5b90c5a82e447abf3ac53f9aca83ed6a3dcd3c0ba66cbbe6f1308
