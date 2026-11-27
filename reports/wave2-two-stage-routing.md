# Wave 2: Two-stage skill routing

27 November 2026 · **Acceptance gate: `PASS`, 59/59 skills on sealed set M** · **Readiness: `VERIFIED-LOCAL`**

The original gate is unchanged: per-skill recall ≥ 90%, precision ≥ 95% and near-miss specificity ≥ 95%. Sealed set M was written by an author who saw only the skill catalog and the activation policies, audited by a second agent before sealing, and opened **once** against the frozen candidate `83ade33c…`. Result: **472/472 exact, recall 100% (EN 177/177, ID 177/177), precision 100%, specificity 100%, 59/59 skills.** The keyword router left by the previous session (baseline `1dbe3b5`) reached 43.8% recall and 1/59 skills on the same set.

## Sealed-set history

Each fix was made after a failure on one set and proven on the **next**, unseen set. No set was re-scored after being used for diagnosis.

| Set | Candidate | Recall | Precision | Specificity | Skills | Status | Root cause found, then fixed |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| D | `f1c0c332` | 99.7% | 99.8% | 96.6% | 53 | FAIL | Fixed companion bundles; uat "Not for" boundary missing |
| E | `6bf295b1` | 100% | 99.6% | 95.8% | 55 | FAIL | "frontend" homograph; labels written without knowledge of rule #17 → policy-aware authoring and audit |
| F | `5ace8d48` | 99.7% | 99.6% | 98.3% | 56 | FAIL | Catalog contradicted itself on flaky tests (debug vs test); "headline" homograph |
| G | `ed59a7aa` | 99.4% | 99.4% | 97.5% | 55 | FAIL | Discovery negative rule excluded "tender" even post-award; "header Cache-Control"; docx styling |
| H | `83957f1d` | 99.7% | 99.6% | 99.2% | 57 | FAIL | Post-award pattern did not allow words between "won" and "tender" |
| I | `7a1a3193` | 100% | 100% | 99.2% | 58 | FAIL | SEO homograph worked in one direction only ("…halaman tidak terindeks") |
| J | `c0ae6a7b` | 100% | 100% | 99.2% | 58 | FAIL | Framework names in infrastructure work → delivery owners treated as non-UI |
| K | `9024658a` | 99.7% | 100% | 100% | 58 | FAIL | "What is…" about a specific library version classed as trivial |
| L | `23529e8e` | 99.7% | 99.8% | 99.2% | 57 | FAIL | Weak UI words ("table") loaded the bundle; human vs layoutmobile overlap on tap targets |
| **M** | `83ade33c` | **100%** | **100%** | **100%** | **59** | **PASS** | — |

Sets D and E used the first protocol and authors without the policy file, so they are not comparable with F–M. Datasets: `evals/fixtures/wave2-trigger-blind-{c..m}.json`. Audit logs: `*-audit.json`. Selections: `wave2-owner-selection-{c..m}.json`.

### Previous results (before the final iterations)

## Root cause of the original FAIL

| Layer | Finding | Evidence |
| --- | --- | --- |
| Candidate generation | The correct owner was already in the candidate pool for **96–97%** of positive prompts | Oracle over lexical top-5 ∪ rules ∪ body top-5: a 175/180, b 167/174 |
| Deterministic selection | Choosing among 5–12 closely related candidates topped out at **about 80%** regardless of tuning | 2-fold cross-validated weight search; kNN on example prompts (worse across authors); body index; blind C: 75.7% → 83.1% |
| Vocabulary | Indonesian requests barely match English skill documents; tokens such as `c4` and `k6` were dropped by the minimum-length filter | Misses such as "beban", "dipulihkan", "basis data", and "C4 container view" routed to container queries |
| Companions | After the owner was correct, fixed bundles kept activating unrelated siblings | D: UI bundle, `CO_ACTIVATION_MAP[shadow-architect]`, request-clause rules |

Conclusion: lexical rules and BM25 are good enough to **narrow the candidates**, but not to **decide** between overlapping specialists. That decision needs semantic understanding, so it is moved to the model, while all safety boundaries stay deterministic.

## Design

1. **Stage 1, deterministic.** `route_prompt` returns `routing_decision.owner_candidates`: up to 10 candidates plus `shadow-monarch` as the orchestrator option. It fuses (RRF, k=60) the evidence-based ranking (rules + lexical index with Indonesian translation) with a BM25 index over the full `SKILL.md` text and reference module titles. Scope blocks, negative boundaries, explicit `/skill` mentions, trivial/typo-only requests and execution-sensitive skills are applied **before** candidates are formed.
2. **Stage 2, the model.** The model picks one owner from the candidates (a skill outside the shortlist is allowed when nothing fits), or `none`. `route_prompt(prompt, selected_owner=X)` validates the pick:
   - `accepted` or `accepted_outside_shortlist`: X becomes the primary (`primary_source = model_selected`). Only prompt-triggered risk reviews are kept. Bundle supporting skills load only when the prompt itself provides evidence for them. Antislop sub-skills do not pull in their siblings.
   - `rejected_excluded`: X is blocked by scope or a negative boundary, for example k6 after "jangan pakai k6". The deterministic owner stays.
   - `rejected_fixed_owner` / `rejected_unknown`: an explicit mention, a trivial request, or an unknown name.
   - `accepted_no_owner`: no specialist is needed.
3. **Deterministic output stays compatible.** Of 1,493 prompts compared with the previous router, primaries and companions are identical. The only intended difference: 12 decisions drop the UI bundle when the owner is browser, illustration or video. `skill_router.py --self-test` passes 154/154.

## Evaluation protocol

- The sets **a/b** (from the previous session) were already used in diagnosis, so they serve only as development data.
- Three new sets were written by **independent authors** who read only the skill catalog, never the router or other fixtures. Each set has 472 rows: per skill, 3 EN + 3 ID positives and 1 EN + 1 ID near-miss.
  - **C** is the check set, used for iteration.
  - **D** and **E** were each sealed, opened **once**, and scored against a frozen fingerprint.
- The stage-2 selector is a subagent that reads only the catalog descriptions and anonymized requests (hashed IDs, no labels). Candidates are shown in alphabetical order to reduce the position bias documented by Zheng et al. (NeurIPS 2023). The first protocol showed the candidates in ranked order; there the first candidate was chosen 85% of the time.

| Set | Status | Candidate | Deterministic recall | Two-stage recall | Precision | Specificity | Skills passing |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| C, first protocol | check | iteration | 75.4% | 99.2% | 98.9% | 94.9% | 49/59 |
| C, v2 protocol | check | iteration | 75.4% | 100% | 99.8% | 98.3% | 57/59 |
| **D** | sealed, once | `f1c0c332…` | 76.3% | 99.7% | 99.8% | 96.6% | 53/59 |
| **E** | sealed, once | `6bf295b1…` | 72.9% | **100%** | **99.6%** | 95.8% | **55/59** |

Stage-1 coverage (the correct owner appears in the candidates) is 351–352/354 on every blind set. Fixes made after D were shaped by D's diagnosis, so the valid proof for those fixes is E.

## Remaining failures

The five failing cases on E:

| Case | Mechanism | Class |
| --- | --- | --- |
| `antislop-e-en-near-01` "Run eslint and tsc --noEmit on the frontend package…" | The always-on UI regex reacts to the word "frontend", which is a homograph here | **Router defect**: not yet fixed, to keep the frozen candidate reproducible |
| `antislop-e-id-near-01` validation with `:user-valid` (owner modern-web-guidance) | The UI bundle loads on frontend form work | **Label conflicts with global rule #17**, which activates antislop automatically on UI/frontend work |
| `antislop-human-e-en-near-01` design tokens (owner shadow-design) | Same UI bundle | Label conflicts with rule #17 |
| `shadow-handover-e-en-near-01` "Save my session context… label it 'bast-prep'" | The selector picked handover because of the word "bast" | **Model selection error** on a bait word |
| `shadow-presales-e-en-near-01` "We won the tender; now run requirement workshops and draft the SRS" | The selector picked presales even though the description now says "Not for post-award PRD/SRS" | **Model selection error**; the same pattern occurred on C |

### Gate property

The gate requires all 59 skills to pass with 6 positives and 2 near-misses each. A single wrong case is enough to fail a skill. In effect, the gate demands **zero errors across 472 cases**. With an independent per-case error rate p, the probability of passing is (1−p)^472:

| Per-case error | Probability that 472 cases are all clean |
| ---: | ---: |
| 0.20% | 38.9% |
| 0.50% | 9.4% |
| 1.06% (observed on E) | 0.7% |

So a PASS on a fresh blind set mostly measures luck, not routing quality. Some of the remaining failures also come from labels that conflict with repo policy (rule #17, third-party audits that require shadow-supplychain, shadow-test's flaky-test playbook). Each fix also needs a new blind set before a PASS can be claimed.

## Files changed

- [skill_router.py](../shadow-monarch/scripts/skill_router.py): `owner_candidates`, `selected_owner`, selection statuses, companion trimming on the selection path, the UI bundle off for non-authoring owners, `_owner_score`.
- [skill_retrieval.py](../shadow-monarch/scripts/skill_retrieval.py): optional Indonesian translation per index, `body_index`/`retrieve_body`, specific 2-character digit tokens (`c4`, `k6`).
- [skill_lexicon_id.py](../shadow-monarch/scripts/skill_lexicon_id.py) (new): ID→EN technical glossary, multi-word phrases, affix stripper with nasal assimilation, loanword stems (`direstore`).
- [compare_skill_trigger_routing.py](../evals/compare_skill_trigger_routing.py): `--fixtures`, `--selections` (two-stage mode), shortlist coverage report, fingerprint that includes the lexicon.
- [test_owner_shortlist.py](../evals/test_owner_shortlist.py) (new, 16 tests): safety contract, selection, companions, risk retention, development coverage ≥ 98%, lexicon precision/recall probes.
- Descriptions: [shadow-presales](../shadow-presales/SKILL.md) and [shadow-uat](../shadow-uat/SKILL.md) gained sibling boundaries.
- Fixtures: `wave2-trigger-blind-{c,d,e}.json` (SHA-256 `d99426ea…`, `f3c1d993…`, `32de7a0f…`) and `wave2-owner-selection-{c,d,e}.json`.

## Verification

| Check | Result |
| --- | --- |
| `skill_router.py --self-test` | PASS 154/154 |
| `python -m unittest discover -s evals -p "test_*.py"` | PASS 67 tests |
| `shadow-monarch/tests`, `shadow-quality/tests` | PASS |
| `skill_router.py --audit-descriptions` | PASS (7,729 characters in total, maximum 163) |
| Deterministic diff against the previous router, 1,493 prompts | 0 primary/companion changes; 12 intended UI-bundle drops |
| Lexicon probes | 28/28 precision, 14/14 recall |
| Gate on sealed E | **FAIL**, 55/59 |

Reproduce M (exit code 0 = gate passed):

```powershell
python -B evals/compare_skill_trigger_routing.py --expect-candidate 83ade33cc21eba9bc2d04ddf43597864c4000e94b63c9357accbe309da582d94 --fixtures evals/fixtures/wave2-trigger-blind-m.json --selections evals/fixtures/wave2-owner-selection-m.json
```

## Protocol additions after E

- **Policy-aware dataset.** [policy.md](../evals/fixtures/wave2-activation-policy.md) documents deliberate activation: antislop rule #17, `CO_ACTIVATION_MAP`, the 16 risk-review skills, third-party audits, flaky-test ownership, and session memory vs client delivery. Authors get it so that near-misses do not contradict repo policy.
- **Independent label audit before sealing.** A second agent checks every row against the catalog and the policies, and fixes ambiguous rows before any router run (4–12 rows per set).
- **Stage-2 self-check.** Both the selector and [shadow-monarch SKILL.md](../shadow-monarch/SKILL.md) now require re-reading the chosen skill's "Not for" clause, and judging by the requested task rather than incidental words.
- **CLI.** `skill_router.py --route "<task>" --select-owner <skill|none>` validates the owner choice.

## Not measured

- The real host's skill choice in a live Claude Code/Codex session. Stage 2 was emulated by a subagent reading the catalog descriptions; this is not the host's skill-listing mechanism.
- Host listing on the Monarch's own machine. With Claude Code's default settings, 52 of 59 descriptions collapse to name-only. With [claude-code-wave2.settings.json](../docs/claude-code-wave2.settings.json) (`skillListingBudgetFraction: 0.02`) all 59 are kept. That setting has not been applied, because it changes the Monarch's own configuration.
- Repeatability: pass^1 only. One sealed set passed; nine earlier sealed sets each failed on 1–6 cases, and the defects behind those failures were fixed.
- The variance of the stage-2 selector across repeated runs (pass^k) and across model sizes.
- Latency and memory of the body index on a cold start.
