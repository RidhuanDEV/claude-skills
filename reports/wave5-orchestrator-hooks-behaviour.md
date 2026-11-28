# Wave 5: Orchestrator diet, hooks and behavioural evaluation

27 November 2026 · **Gate: `PASS` for what could be measured on this host** · **Readiness: `VERIFIED-LOCAL`**

| Exit criterion ([enhancement-review §7](enhancement-review.md)) | Result |
| --- | --- |
| Monarch `SKILL.md` ≤ 8 KB, with the non-negotiables in the first 2 KB | **6,850 bytes**, down from 39,989 (−83%). The non-negotiables come straight after the persona line |
| Hard rules enforced by hooks | **Activated 2026-11-28** with the Monarch's approval: a `PreToolUse` hook on `Bash\|PowerShell` in the user settings, plus `skillListingBudgetFraction: 0.02`. Pipe-tested; it takes effect after `/hooks` or a restart |
| Measured uplift per skill against a no-skill baseline | **Published for 57 of 59 skills.** Mean uplift +3.00 (9.51 vs 6.51 out of 10); full passes 44/57 vs 4/57; sign test p ≈ 2.3×10⁻¹⁴ |
| Skills with no uplift are merged or retired | **Not done, deliberately.** 7 skills show no uplift on one scenario each. That is too little evidence to retire a skill, and retiring or merging is a structural decision for the Monarch (`L2`) |
| Cross-model runs (Claude, Codex, Gemini) | **NOT_RUN.** Only Claude subagents are available here |

## 1. Orchestrator diet

All 39,820 bytes of the old body were moved verbatim, not deleted:
- [ROUTING-MATRIX.md](../shadow-monarch/reference/ROUTING-MATRIX.md): role guides with companion skills, sibling boundaries, language and sub-task references, and the 59-skill SDLC matrix.
- [MONARCH-PLAYBOOK.md](../shadow-monarch/reference/MONARCH-PLAYBOOK.md): the full doctrine.

The new `SKILL.md` keeps only what applies every time:
- the seven non-negotiables;
- two-stage routing;
- the 6-step work protocol;
- the rigor rules (now naming the Wave 3/4 gates `facts_registry_check.py` and `mutation_smoke.py`);
- a 59-skill index and links to the detail.

Claude Code keeps only the first 5,000 tokens of a skill after compaction. The whole of the new file now fits in that window.

Routing is unchanged: router self-test 154/154, and the Wave 2 sealed sets M, K and J still pass 59/59 with the current code.

## 2. Shadow guard hook

The decision contract follows the [Claude Code hooks reference](https://code.claude.com/docs/en/hooks), fetched 2026-11-27. `permissionDecision: "ask"` makes the user confirm and shows the reason in the prompt. `"deny"` blocks the call. Silence leaves the normal permission flow in place.

| Decision | Commands |
| --- | --- |
| `ask` | git `commit`, `push`, `merge`, `rebase`, `cherry-pick`, `reset --hard`, `clean -f`, `checkout --`, branch/tag delete, stash drop; recursive deletes; global npm/pnpm/yarn installs; ad-hoc `pip install`; docker prune and volume removal; `terraform apply/destroy`; `kubectl delete/apply`; destructive SQL through a CLI; blanket process kills |
| `deny` | piping a downloaded script into a shell (`curl … \| bash`, `iwr … \| iex`); `rm -rf /` or `~` |
| silent | everything else, including read-only git, `grep 'git push'` and local `npm install` |

The hook splits each command on `&&`, `;` and `|`, and checks only the command word of each part. Tests: 18 commands that must ask, 4 that must be denied, 17 that must stay silent, and malformed payloads ([test_shadow_guard.py](../shadow-monarch/tests/test_shadow_guard.py)). The probes caught one bug before release: `git -C repo rebase` stayed silent until the parser skipped option values.

## 3. Behavioural evaluation

**Method:**
- One graded scenario per skill, taken from that skill's own `evaluations.md`. For shadow-monarch it comes from `evals/evals.json`.
- Every agent got the same prompt and the same 170-word cap:
  - one baseline agent answered all 59 **without access to the repo**;
  - four agents answered after reading the skill's `SKILL.md` and at most 2 of its playbooks.
- Skill names and paths were redacted from both answers before judging: 9 tokens on the skill side, 2 on the baseline side.
- Two independent judges graded **blind**, with answers labelled A or B in random order (seed 20261127). They scored against the pass criteria and red flags and were told to give no credit for length.
- Stored data and the scoring script: [evals/fixtures/wave5-behavioral](../evals/fixtures/wave5-behavioral), [score_behavioral_uplift.py](../evals/score_behavioral_uplift.py). The numbers are locked by [test_behavioral_uplift.py](../evals/test_behavioral_uplift.py).

**Result (57 valid scenarios, k = 1):**

| | With skill | Baseline |
| --- | ---: | ---: |
| Mean score (0–10) | **9.51** | 6.51 |
| Full passes | **44/57** | 4/57 |
| Uplift > 0 / = 0 / < 0 | 50 / 6 / 1 | |

There was no sign of A/B position bias: A won 18 times and B 25, with the skill placed as A in 26 of 59 items.

### Issues found and fixed during the evaluation

| Finding | Root cause | Fix |
| --- | --- | --- |
| 12 scenarios scored as "opaque criteria" ties | My extractor read the *Expected Modules* column (`02`, `04`) instead of *Pass Criteria* | Extraction fixed, and those 12 scenarios re-judged blind. For example, privacy went from a 10/10 tie to 10 vs 5, eval to 10 vs 6, auth and data to 10 vs 7 |
| antislop-copywriting scored 9 vs 10 | The skill did not say what to do with an unsourced number that is already in the draft | Rule added: replace it with a placeholder that names the missing source, or cut it |
| ai-eng TTFT answer missed proxy buffering | Reference 04's TTFT stages covered only server-side spans | Stage 6 `delivery_ms` added (proxy/CDN buffering), linked to the streaming fix in reference 05 |
| shadow-video could not be measured | `evaluations.md` had falsification probes but no graded prompts | Three graded scenarios added (production refusal, source of truth, UI-change sync) |
| shadow-illustration's scenario was not a real prompt | Its table listed capability rows, so prompt and criteria were both "Author SVG and inspect rendered output". The content contract counted any table row | Three graded scenarios added. The contract now counts only rows of a table with a prompt column and a pass/expected column; the old illustration and video files fail it |
| shadow-monarch scenario off-topic | The selected repo eval tested PMO/EVM | Excluded from the statistics; an orchestration scenario should be chosen explicitly next time |

### No measured uplift (candidates, not removals)

| Skill | Skill vs baseline | Reading |
| --- | ---: | --- |
| antislop-copywriting | 9 vs 10 | Gap fixed above; not re-measured |
| shadow-ai-eng | 10 vs 10 | Ceiling tie after the criteria correction; gap fixed above |
| shadow-compat | 10 vs 10 | Ceiling tie: the scenario is too easy to separate expert from generalist |
| shadow-illustration | 10 vs 10 | Invalid scenario (see above); now replaced |
| shadow-domain | 7 vs 7 | Both answers missed the same checkpoint |
| shadow-quality | 8 vs 8 | Both answers missed citing `file:line` |
| shadow-search | 8 vs 8 | Both answers missed analyzer details (ASCII folding, Sastrawi stemming, stopwords) |

## 4. Follow-up: fixing and re-measuring the no-uplift skills (2026-11-28)

Every skill above was fixed where a real gap existed, then re-measured with a fresh blind A/B run ([evals/fixtures/wave5-rerun](../evals/fixtures/wave5-rerun), locked by `BehavioralRerunTests`). Thirteen scenarios: each skill's original failing scenario, a harder one from its own `evaluations.md`, and shadow-video for the first time. Answer length was balanced this time (156 vs 159 words on average), which removes the earlier verbosity confound.

| | With skill | Baseline |
| --- | ---: | ---: |
| Mean score | **9.85** | 6.85 |
| Full passes | **13/13** | 3/13 |
| Uplift > 0 / = 0 / < 0 | 13 / 0 / 0 (sign test p ≈ 1.2×10⁻⁴) | |

| Skill | Gap found | Fix |
| --- | --- | --- |
| shadow-domain | The skill had bounded contexts but did not force a cross-context check | Cross-Context Impact Rule: list the contexts that consumed a settled record, honour closed periods, and correct through audited adjustments. Backdating now loads references 01 and 03. DOMAIN-EVAL-01 went from 7 to 10 |
| shadow-quality | The `file:line` rule was buried at the end | Review Output Contract at the top: read-only, scope triage, anchored findings, verdict. QUALITY-EVAL-01 went from 8 to 10 |
| shadow-search | The analyzer chain was generic; codes such as `PP-27/2022` were not normalized; no stop list kept negations | Exact analyzer chain, `code_normalizer`, curated `id_stop`, and a check for Postgres text search configs. New tested helper [identifier_query_router.py](../shadow-search/scripts/identifier_query_router.py): 18/18 self-test, mutation smoke PASS. Its first pattern failed the precision probes (`tahun 2022` matched, `Perpres` became `erpres`) and was replaced by two probed grammars |
| shadow-compat | Consumer inventory and replay sat under the browser rule | Consumer evidence is now required before any wire or semantic verdict; a consumer that cannot be replayed is `NOT_MEASURED`. CMP-EVAL-03 went from 8 to 10 |
| shadow-illustration | No raster-to-vector tracing guidance | Tracing playbook (reconstruction, auto-trace only as an underlay, overlay diff, a verified-versus-assumed table) plus a routing row. ILLU-EVAL-02 went from 8 to 10 |
| antislop-copywriting, shadow-ai-eng | Fixed earlier in Wave 5 | ASCP-01 9 vs 7, ASCP-05 10 vs 6; AIENG-EVAL-01 10 vs 9, AIENG-EVAL-06 10 vs 5 |
| shadow-video | Not measurable before | VIDEO-EVAL-02 10 vs 4 |

No skill needs retirement or merging: each covers a distinct field, and all seven now show uplift.

## Not measured

- **pass^k:** each skill has one scenario and one run. Repetition is needed before any skill is retired.
- **Other models:** Codex and Gemini; Claude Haiku/Opus at other sizes.
- **Real tasks:** answers are plans with no tool execution, so this measures expert reasoning, not finished code.
- **Judge calibration:** the judges were LLMs. Answer length differed (155 vs 110 words on average); length was instructed out but not controlled for statistically.
- **Hook in a live session:** pipe-tested (`git push` → `ask`, `ls` → silent). A sentinel check inside this session did not fire, because the settings watcher has not reloaded yet; it needs `/hooks` or a restart.
- **Repetition of the follow-up:** k = 1 per scenario. R05 and R12 were judged twice in total (before and after their fix), with the baseline answers reused.

## Verification

| Check | Result |
| --- | --- |
| Skill suites | 538 tests, 0 failures |
| `evals` | 92 OK (adds hook-independent behavioural score locks) |
| Node: perf / video | 13 / 7 |
| `skill_router.py --self-test` | 154/154 |
| `facts_registry_check.py` | PASS, 0 findings |
| Wave 2 sealed sets M, K, J (current code) | PASS 59/59 each |
| Content contracts and coverage (all 59 in the monarch index) | OK |
