# Grades: Group A (UI, design, content, docs, browser, email). 15 skills

Reviewer: strict principal-level, read-only. Repo: `D:\Ridhuan Ngoding Moment\SKILL` @ `1dbe3b5` (main, clean). Date 2026-11-26.
Paths below are relative to the repo root. All tests ran offline, each in under 60 s, with `PYTHONDONTWRITEBYTECODE=1`.

**Side-effect disclosure:** `shadow-doc/scripts/doc_scaffold.py --acceptance-suite` writes its reports into `shadow-doc/output/`, which is inside the skill folder and gitignored. It overwrote `acceptance_report_v2.{json,md}`, the handover zip and the `at0x_*` fixtures there. No tracked file changed: `git status` is clean.

## Summary table

| Skill | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|---|
| antislop | 2 | 3 | 2 | 3 | 1 | 3 | 2 | 2 | 2.25 | MEDIUM |
| antislop-code | 2 | 3 | 3 | 3 | 1 | 3 | 4 | 2 | 2.63 | MEDIUM |
| antislop-copywriting | 2 | 3 | 3 | 3 | 1 | 3 | 2 | 2 | 2.38 | MEDIUM |
| antislop-human | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 2.88 | MEDIUM |
| antislop-layoutmobile | 3 | 3 | 3 | 3 | 1 | 3 | 4 | 2 | 2.75 | MEDIUM |
| antislop-ui | 2 | 3 | 3 | 3 | 1 | 3 | 2 | 3 | 2.50 | MEDIUM |
| modern-web-guidance | 3 | 3 | 3 | 2 | 1 | 2 | 4 | 3 | 2.63 | MEDIUM |
| shadow-design | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2.75 | MEDIUM |
| shadow-accessibility | 4 | 3 | 3 | 2 | 3 | 3 | 4 | 3 | 3.13 | GOOD |
| shadow-illustration | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2.75 | MEDIUM |
| shadow-video | 3 | 3 | 3 | 4 | 2 | 2 | 4 | 2 | 2.88 | MEDIUM |
| shadow-seo | 4 | 3 | 3 | 2 | 2 | 3 | 4 | 3 | 3.00 | GOOD (borderline) |
| shadow-doc | 2 | 3 | 3 | 3 | 4 | 3 | 3 | 2 | 2.88 | MEDIUM |
| shadow-browser | 4 | 3 | 3 | 3 | 3 | 4 | 4 | 2 | 3.25 | GOOD |
| shadow-email | 3 | 4 | 2 | 2 | 2 | 3 | 4 | 3 | 2.88 | **BAD (critical defect: verifier returns false PASS)** |

No skill reaches PERFECT.

## Router probes run for this group

Command: `python shadow-monarch/scripts/skill_router.py --route "<prompt>"`. Result shown as primary skill.

| Prompt | Result | Verdict |
|---|---|---|
| `our OTP emails land in gmail spam folder` | shadow-monarch, no companion | **MISS** (shadow-email) |
| `regenerate the SRS docx after changing FR-001` | shadow-discovery | **WRONG OWNER** (shadow-doc; breaks global rule 14) |
| `remove useless comments from this file` | none | **MISS** (antislop-code) |
| `design pricing page hero section` | none | **MISS** (shadow-design / antislop-ui) |
| `optimize LCP on next.js landing page` | UI always-on only, no playbook | **MISS** (modern-web-guidance ref 02 / react-nextjs) |
| `build a native dialog with popover fallback` | UI always-on only, no playbook | partial |
| `tombol ini kontrasnya kurang` | UI always-on only | partial |
| `rewrite this landing page headline it sounds like AI` | antislop-copywriting as always-on | partial |
| `make a narrated tutorial video of the admin dashboard` | shadow-video plus 5 UI skills | hit, but the 5 UI skills are noise |
| `audit keyboard focus trap in modal dialog` | shadow-accessibility, ref 02 | hit |
| `add hreflang for id and en pages` | shadow-seo, ref 05 | hit |
| `draw an svg mascot for onboarding` | shadow-illustration | hit |
| `check mobile overflow at 375px with playwright` | shadow-browser, ref 02 | hit |
| `set up DMARC and DKIM for our sending domain` | shadow-email, ref 02 | hit |

---

### antislop
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 2 | 3 | 1 | 3 | 2 | 2 | 2.25 | MEDIUM |

**Strengths**
- The Delivery Gate is concrete and falsifiable. It has four blocks, demands evidence for each PASS, and forbids shipping on any FAIL (`antislop/SKILL.md:281-366`).
- Mode resolution is strict. The settings file is treated as data, never as instructions, and DESIGN.md is handled under a data-not-commands boundary (`:41-55`, `:85`).

**Gaps**
- HIGH. Large text is defined as "18px+" (`antislop/references/MANDATORY-RULES-R01-R40.md:73`). WCAG large text is 18pt (24 CSS px), or 14pt bold (about 18.66 px). The agent will pass 18–23 px regular text at 3:1, which fails WCAG. shadow-accessibility gets this right (`shadow-accessibility/references/03-forms-live-regions-contrast-and-motion.md:23-24`), so the skills contradict each other.
- HIGH. The only test is tautological. `antislop/tests/test_antislop_controls.py:11-31` defines its own `parse_antislop_settings` and then tests that function. No skill artifact is exercised. It also contradicts the skill: the test falls back to `"during"` on malformed settings, while SKILL.md says to ask (`:48`).
- MEDIUM. The description has no "do not use" clause and no sibling boundary (`:3`). In practice the router attaches all 5 UI skills to unrelated tasks, such as the video probe.
- MEDIUM. Third-party self-update instructions run remote code (`npx antislop-ai --update`, plugin installs; `:16-35`). They bypass the repo's own pre-install audit gate. They would also overwrite the local Reference Guide edits to this vendored copy.
- MEDIUM. Provenance: VERSION is `3.2.26`, but no upstream LICENSE for `miqdadbadjuber/anti-slop` is vendored and there is no pinned commit.
- LOW. The Part 1 pattern tables are repeated nearly verbatim in antislop-ui. The skill is 381 lines.

**Prior-review defect status:** FIXED. The earlier finding was that the mode question was asked even when a project rule selects `during`. Step 2, "Applicable project rule", now exists (`antislop/SKILL.md:46`).

**Upgrade actions**
1. Correct R-25 to WCAG 2.2 SC 1.4.3 "large scale" (18pt / 14pt bold) and cite w3.org/TR/WCAG22.
2. Replace the tautological test with one that parses the real settings path and the real rule file, for example by asserting that the R-25 thresholds match shadow-accessibility.
3. Add "Do NOT use for backend/CLI" plus sibling boundaries to the description.
4. Remove the self-update section, or gate it behind the shadow-sec pre-install audit.
5. Vendor the upstream LICENSE and pin a commit.

**Test run:** `cd antislop && python -m unittest discover -s tests` gave 1 test, OK. It does not prove skill behavior.

### antislop-code
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 1 | 3 | 4 | 2 | 2.63 | MEDIUM |

**Strengths**
- The "Not a Ban" preserve list covers security, concurrency, protocol, workaround and license comments (`antislop-code/SKILL.md:89-113`).
- The scope guardrail allows comment changes only (`:16`). The checklist is lean, and the file is 130 lines.

**Gaps**
- MEDIUM. The skill tells agents to drop issue numbers and version history from workaround comments (`:74-75`). Senior practice keeps a tracker link on workarounds, because it is the removal criterion ("remove when chromium#123 ships"). Following this advice destroys maintainability evidence.
- MEDIUM. There is no verification tooling. `evaluations.md` is checked only structurally (`evals/validate_skill_evaluations.py` counts scenarios). There is no diff-based oracle proving that code tokens are unchanged, even though the scope guardrail would be easy to check with an AST or token diff.
- MEDIUM. The router never selects the skill: `remove useless comments from this file` routes to none. The description has no negative trigger.
- LOW. ASCD-04 (`antislop-code/evaluations.md`) expects the agent to refuse an explicit user request to rename. The right behavior is to do the rename as a separate, declared change, not to refuse it.
- LOW. No language-specific carve-outs: pragmas, `// eslint-disable`, `# type: ignore`, doc generators.

**Prior-review defect status:** STILL OPEN. The prior review asked for pragma and license fixture pairs. There is still no corpus or test.

**Upgrade actions**
1. Add a token-diff checker: strip comments, then assert byte equality of the code.
2. Keep issue links on workarounds.
3. Add pragma and linter-directive preservation rules.
4. Add router probes.

**Test run:** none exist (NOT_RUN).

### antislop-copywriting
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 1 | 3 | 2 | 2 | 2.38 | MEDIUM |

**Strengths**
- "Never invent facts" is enforced in the Draft, Audit, Final loop (`antislop-copywriting/SKILL.md:17`, `:384-390`).
- The "What NOT to flag" and "Signs of human writing" sections curb false positives (`:347-372`).

**Gaps**
- HIGH. The description promises "error messages … in English or Indonesian" (`:3`). The skill contains no Indonesian guidance and no error-message or microcopy anatomy (grep for indonesia/bahasa/error message finds only line 3). An Indonesian UI-copy prompt gets English-only rules.
- MEDIUM. Nearly every pattern cites R-36 as its governing rule (`:300-345`). Rule references stop telling the agent anything.
- MEDIUM. Mechanical bans are presented as hard gates. For example, "Check for em and en dashes one last time (R-02). A hit means the draft is not done" (`:390`) contradicts its own "Em dashes alone… An em dash is evidence only inside a cluster" (`:357`). En-dash ranges such as 2020–2024 are typographically correct.
- MEDIUM. No tooling. A simple lint script for buzzwords and dashes would make the claims falsifiable.
- LOW. 409 lines with no references split.

**Prior-review defect status:** STILL OPEN. The prior review asked for cross-language fixtures with approved product labels. None exist.

**Upgrade actions**
1. Add an Indonesian section: formal versus informal register (Anda/kamu), terms from KBBI/PUEBI, and calques to avoid ("silakan klik di sini").
2. Add an error-message anatomy: what happened, then whether the user's input is safe, then the next action. Align it with the GOV.UK / NN/g error message guidelines.
3. Reconcile the em-dash rule (`:357` versus `:390`) and exempt en-dash ranges.
4. Add a lint script with precision and recall probes.

**Test run:** none exist (NOT_RUN).

### antislop-human
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 2.88 | MEDIUM |

**Strengths**
- `contrast-check.py` is correct, including the threshold case. `"#777777" "#070707"` returns 4.50 with normal text FAIL, because the comparison uses the unrounded ratio. Bad input exits 2.
- MIT attribution to Addy Osmani's web-quality-skills is present (`LICENSE-web-quality-skills`, reference headers). The interaction-affordance section maps 1:1 to the global UI craft floor.

**Gaps**
- HIGH. Large text is again "(18px+)" (`antislop-human/SKILL.md:26`, `:65`). This is wrong: WCAG 1.4.3 large text is 24 px, or 18.66 px bold. The script output labels "large text" without saying what size qualifies, so the agent applies 3:1 too early.
- MEDIUM. The linearization threshold is `0.03928` (`:63`, `contrast-check.py:54`). WCAG 2.2's relative-luminance definition now notes 0.04045 per sRGB. The difference is immaterial in practice, but the skill cites no source and no version.
- MEDIUM. `contrast-mcp.py` (an MCP server with `PROTOCOL_VERSION = "2024-11-05"`) ships inside the skill with no tests and no install or registration guidance.
- LOW. No hand-off contract to shadow-accessibility for deeper semantic problems. This was the prior review's ask.
- LOW. "One `<h1>`" (`:185`) is presented as a rule. It is a convention, not WCAG.

**Prior-review defect status:** STILL OPEN. There is no evidence form for handing off to shadow-accessibility.

**Upgrade actions**
1. Fix the large-text definition per WCAG 2.2 SC 1.4.3 and print it in the script output.
2. Add a unittest for `contrast-check.py` using the reference table rows.
3. Add a handoff line naming the shadow-accessibility evidence shape.

**Test run:** `python antislop-human/contrast-check.py "#FFFFFF" "#777777"` gave 4.48, normal FAIL, large PASS, as documented. With `"#777777" "#070707"`: 4.50, FAIL (correct). With `fff zzz`: exit 2.

### antislop-layoutmobile
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 1 | 3 | 4 | 2 | 2.75 | MEDIUM |

**Strengths**
- Content-driven breakpoints and three-state reflow are explained with clear mechanics (`antislop-layoutmobile/SKILL.md:27-43`). The fixes are concrete: `dvh`, `minmax`/`auto-fit`, `min-width: 0`.
- Lean at 172 lines, with a clear checklist (`:157-170`).

**Gaps**
- MEDIUM. No mention of WCAG 1.4.10 Reflow at 320 CSS px. The tap-target guidance (44 px, `:113-117`) never states that the WCAG 2.2 AA minimum is 24×24 (SC 2.5.8), while shadow-design and shadow-accessibility do.
- MEDIUM. Missing the iOS input `font-size >= 16px` auto-zoom trap, the viewport meta and `env(safe-area-inset-*)` specifics, and container queries for components.
- MEDIUM. No tooling. The skill could reuse shadow-browser's `scrollWidth` offender finder.
- LOW. No sources cited.

**Prior-review defect status:** N/A. The prior review rated it ALREADY GOOD with no defect.

**Upgrade actions**
1. Add WCAG 2.2 SC 1.4.10 (320 px) and SC 2.5.8 (24 px AA) with links.
2. Add the iOS 16 px input rule.
3. Link to shadow-browser's overflow script as the verification step.

**Test run:** none exist (NOT_RUN).

### antislop-ui
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 1 | 3 | 2 | 3 | 2.50 | MEDIUM |

**Strengths**
- Core Web Vitals thresholds are correct: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 (`antislop-ui/references/CORE-WEB-VITALS.md:22-24`). The honesty rule "never claim without field data" is enforced (`:16`, `SKILL.md:295`).
- The App & Dashboard section (invented stat cards, filler activity feeds) is a useful extension (`SKILL.md:233-277`).

**Gaps**
- MEDIUM. Large overlap with antislop Part 1, and with modern-web-guidance on Performance and Page Basics. The tables are restated in prose (`SKILL.md:18-213` versus `antislop/SKILL.md:134-196`). The skill is 353 lines.
- MEDIUM. Boundaries with shadow-design and modern-web-guidance are not stated in the description (`:3`). The router misses `design pricing page hero section`.
- MEDIUM. Some purpose-gate "tells" are taste presented as slop, for example "Lucide Icons" (`:152`). It is gated, but with no evidence base.
- MEDIUM. No tooling. Static checks are cheap to build: unsized `<img>`, lazy hero, `cursor` reset.

**Prior-review defect status:** N/A. The prior review rated it ALREADY GOOD.

**Upgrade actions**
1. Deduplicate against the antislop core by referencing it instead of restating.
2. Add boundaries to the description.
3. Add a static HTML/CSS checker for the R-40 items.
4. Cite web.dev/vitals with a date.

**Test run:** none exist (NOT_RUN).

### modern-web-guidance
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 2 | 1 | 2 | 4 | 3 | 2.63 | MEDIUM |

**Strengths**
- The description has explicit "Do NOT use" exclusions and owner/boundary lines (`modern-web-guidance/SKILL.md:3`, `:10-11`). The SKILL.md is very lean at 63 lines.
- Anchor Positioning is gated by `@supports`. `scheduler.yield()` has a `setTimeout` fallback (`references/02-...md:20`, `:53-61`). The CWV honesty rule is present.

**Gaps**
- MEDIUM. The skill tells the agent to run `npx -y modern-web-guidance@1.0.1` (`:28-39`), which downloads and executes a remote package, with no reference to the repo's own pre-install or download audit (global rule 23 and shadow-sec). The pin is also stale: `npm view` shows 1.0.2, modified 2026-11-23. The package and repo do exist and match `GoogleChrome/modern-web-guidance-src`.
- MEDIUM. No procedure. It is a matrix plus references, with no ordered steps, no "check Baseline status first" gate and no deliverable contract.
- MEDIUM. Zero scripts and zero tests (validator: `scripts_count 0, tests_count 0`).
- MEDIUM. Router: `optimize LCP on next.js landing page` and `build a native dialog with popover fallback` return no playbook from this skill.
- LOW. "Bind 100% of custom UI to semantic tokens" duplicates the global rule and antislop-ui.

**Prior-review defect status:** N/A. Not in the prior review.

**Upgrade actions**
1. Gate `npx` behind the shadow-sec pre-install playbook, or vendor a snapshot, and update the pin.
2. Add a 4-step workflow: detect stack, check Baseline status on webstatus.dev, choose native API or fallback, verify.
3. Add a router probe set.
4. Add dated sources (web.dev, WebDX Baseline).

**Test run:** none exist (NOT_RUN).

### shadow-design
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2.75 | MEDIUM |

**Strengths**
- The vendored library is well governed. `skill_vendor_sync.py verify shadow-design` returned `VERIFY PASS: All 354 vendored files across 5 packs … match SHA-256 lockfile`. Four upstreams are pinned to commits, with LICENSE files present (MIT ×3, CC0).
- `resolve_method.py` resolves with checksum provenance and fail-closed statuses. For example, `userflow --flow checkout` returns READY with the sha256 and revision. The prior `file:///` defect is fixed and locked by `tests/test_resolve_method.py:91`.
- The 9-state contract, honesty about async 202 responses, and the evidence labels are expert-grade (`SKILL.md:86-145`).

**Gaps**
- HIGH. Discoverability. `references/methods.json` has 17 entries covering 14 method names, but there are 216 vendored SKILL.md entry points. `resolve_method.py design-token`, `color-system`, `heuristic-evaluation` and `accessibility-audit` all return `UNSUPPORTED`, even though the modules exist (for example `references/external-upstreams/designer-skills/design-systems/skills/design-token/SKILL.md`). Design tokens are the skill's headline trigger (`:3`). The agent must browse READMEs to find modules.
- MEDIUM. Vendored module depth is uneven. The designer-skills modules are generic (design-token is 27 lines, color-system 34), and the core ai-product-designer chapters are about 1.3–2.7 KB each (`06-accessibility-responsive-content.md` is 8 lines). flow-auth (152 lines) is genuinely expert.
- MEDIUM. The primary pack's provenance is `local://` from `C:\Users\Ridhuan\Downloads\…` with license "Vendor-authored" and `last_synced_at: null` per pack (`UPSTREAM_PROVENANCE.json`). There is no license grant for redistribution.
- MEDIUM. The description has no "Do NOT use" clause (`:3`). Router: `design pricing page hero section` returns none.
- LOW. `update-remote` is listed beside read-only commands with no approval gate (`:14`). Two overlapping routing tables (§0 and the Reference Guide) plus the §0b list add about 60 lines of index to SKILL.md.

**Prior-review defect status:** FIXED. `file:///` links were replaced with relative links, and a test guards against them.

**Upgrade actions**
1. Generate `methods.json` (or an index) for all 216 entry points, so that `design-token` resolves.
2. Add a "Do NOT use" clause and router probes.
3. Obtain or record a license for the ai-product-designer pack, or mark it internal.
4. Collapse the duplicate routing tables.
5. Mark `update-remote` as L2/L4.

**Test run:** `cd shadow-design && python -m unittest discover -s tests` ran 22 tests, OK (53.2 s). Vendor verify: PASS (354 files).

### shadow-accessibility
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 2 | 3 | 3 | 4 | 3 | 3.13 | GOOD |

**Strengths**
- Thresholds are correct and precise: 24 px / 18.66 px bold for large text, SC 2.5.8 at 24×24, 200% zoom and 320 px reflow (`references/03-...md:23-26`, `SKILL.md:32`). Honest automation limits: axe catches about 35–45% (`references/01-...md:116`, `:124`).
- The verifier handles the prior defect correctly. A wrapping `<label>` passes while a bare input is flagged, along with `div onclick` and a missing alt. A second probe caught a missing `lang`, positive tabindex, a skipped heading level and `outline:none`.

**Gaps**
- MEDIUM. SKILL.md is a list of invariants with no audit procedure: no ordered scope, automated pass, manual keyboard, screen-reader matrix and report steps, and no conformance or report deliverable (VPAT / WCAG-EM) (`SKILL.md:27-44`).
- MEDIUM. The verifier has false negatives. `<button></button>` (no accessible name), `<a>` without href, `role="button"` without tabindex, and `alt="image"` all passed my probe. It is regex-based. The skill should say "smoke linter; does not replace axe".
- MEDIUM. No regulatory context: EN 301 549 / European Accessibility Act (in force June 2025), ADA Title II web rule, Indonesian SPBE obligations. For "public, enterprise, government" scope (`:8`) a senior practitioner would name these.
- LOW. The anecdote "A government procurement portal failed its SPBE accessibility audit on 14 findings in 10 minutes" (`references/01-...md:103`) is unverifiable.
- LOW. "One `<h1>`" is presented as an invariant (`:29`). It is not a WCAG requirement.

**Prior-review defect status:** FIXED. The rule now reads "accept `<label for>`, wrapping `<label>`, or valid ARIA naming" (`SKILL.md:31`), and the verifier behavior confirms it.

**Upgrade actions**
1. Add an ordered audit workflow and report template aligned to W3C WCAG-EM 1.0.
2. Add accessible-name checks for empty buttons and links.
3. Add EN 301 549 v3.2.1 and EAA references.
4. Remove unverifiable anecdotes.

**Test run:** `python -m unittest discover -s tests` ran 5 tests, OK. `--check-html` probes behaved as described (exit 1 on violations).

### shadow-illustration
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2.75 | MEDIUM |

**Strengths**
- The source register is dated ("Reference review date: 2026-11-20"), with license evidence per tool and pinned commits plus tar sha256 for vendored stack-diagram and pixelfx (`references/open-source-source-register.md`).
- Honest verification separation: "A rendered PNG proves only the observed still" (`SKILL.md:58`). The negative fixtures and 10 tests pass.

**Gaps**
- MEDIUM. The SVGO config is for v3 (`references/color-print-and-optimization.md:20-37`): it sets `removeViewBox: false` inside the `preset-default` overrides. SVGO 4.x is current (`npm view svgo` returns 4.1.0), and in v4 `removeViewBox` and `removeTitle` are no longer in preset-default, so the override warns or does nothing. The doc does not pin an SVGO version.
- MEDIUM. The description has no negative trigger (`:3`). "Full-spectrum" overlaps shadow-video (Lottie and motion) and shadow-design (icons).
- MEDIUM. Duplicate routing. The canvas hub appears at `SKILL.md:23`, and its 10 modules are re-listed at `:35-52`.
- LOW. Mojibake in the source register (`â€”`, `Beginnersâ€™`; `open-source-source-register.md:7,8,16`).
- LOW. The SVG 2 "CR snapshot 2026-10-06" citation was not verified in this review.

**Prior-review defect status:** N/A.

**Upgrade actions**
1. Update the SVGO config for v4 (removeViewBox is off by default; use `removeDimensions` carefully) and pin the version.
2. Fix the UTF-8 encoding.
3. Remove the duplicate table.
4. Add a "Do NOT use" clause.

**Test run:** `python -m unittest discover -s tests` ran 10 tests, OK (17.0 s).

### shadow-video
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 4 | 2 | 2 | 4 | 2 | 2.88 | MEDIUM |

**Strengths**
- A strong gated pipeline: scaffold, readiness, research (`file:line`), script, E2E proof, preview, produce, package. Each step has a stop condition, and E2E runs before recording (`SKILL.md:13-32`).
- Good boundaries: never production, secrets as placeholders, per-project approval for TTS spend and data deletion, owned-process teardown (`:50-70`). It is honest that `verify` does not prove the video is good (`:77`). Engine dependencies are pinned and exist (playwright 1.63.0, typescript 7.0.2, zod 4.6.7).

**Gaps**
- HIGH (safety). `references/recording-environment.md:28-33` is a recipe for evading Cloudflare Turnstile bot detection: real Chrome, no automation flag, and attaching over CDP, because Turnstile "rejects Playwright Chromium". The expert and compliant path is Cloudflare's published Turnstile test sitekeys, or disabling captcha on staging. This conflicts with the no-CAPTCHA-bypass policy.
- MEDIUM. No offline skill-level tests. The validator reports `scripts_count 0, tests_count 0`. The template's `selftest` needs `npm ci` plus browsers, so it is not cheap to run.
- MEDIUM. "Proven on two production projects (government logistics, university research portal)" (`:10-11`) is unverifiable marketing in an instruction file.
- MEDIUM. Weak D8. References cite almost no sources (0–1 URLs per file) and have no last-verified dates. The `edge-tts` "unofficial" caveat is good, but Azure F0 limits are not dated.
- LOW. The description has no negative trigger. The router attaches 5 UI skills to a video task.

**Prior-review defect status:** N/A.

**Upgrade actions**
1. Replace the Turnstile workaround with test sitekeys or staging captcha disablement (Cloudflare Turnstile docs, "Testing").
2. Add offline unit tests for the scene schema, `build-NN.py` narration lint and `scaffold.mjs` refuse-overwrite.
3. Remove the unverifiable claim.
4. Date the TTS and licensing facts.

**Test run:** NOT_RUN. The template self-test requires `npm ci` and Playwright browsers, which is outside the offline <60 s bound.

### shadow-seo
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 2 | 2 | 3 | 4 | 3 | 3.00 | GOOD (borderline) |

**Strengths**
- Precise trigger with boundaries (`SKILL.md:3`). The router hits ref 05 for hreflang. The 12 tiered modules are loaded by symptom.
- Honest GEO and `llms.txt` treatment: experimental, no guarantees. The retrieval-versus-training crawler split is correct (`references/10-...md:10-60`). Sitemap limits (50,000 URLs / 50 MB) are correct (`references/04-...md:13`).

**Gaps**
- MEDIUM. The verifier encodes pseudo-rules as FAIL. A title must be 15–65 characters, a meta description 50–165, exactly one `<h1>`, and every production page must have JSON-LD (`scripts/seo_audit_verifier.py:110-126`). None of these is a Google requirement: multiple h1 and missing structured data are fine. This produces misleading FAILs.
- MEDIUM. Every hreflang page must carry `x-default` (`:71-72`). Google calls x-default recommended, not required, so a valid cluster fails.
- MEDIUM. The verifier checks hand-written JSON descriptors, not real HTML or HTTP responses, so it cannot catch the real SSR or canonical regressions the skill describes.
- MEDIUM. SKILL.md has principles but no ordered audit workflow or deliverable contract (`:10-16`).
- LOW. The "Two-Wave Indexing" framing (`references/03-...md:10`) has been publicly called an oversimplification by Google. There is no FAQ/HowTo rich-result deprecation note, and the AI-crawler list omits Anthropic's bots.

**Prior-review defect status:** N/A.

**Upgrade actions**
1. Downgrade length and h1 checks to WARN. Make x-default a WARN.
2. Add an HTML or HTTP-response mode (parse real `<head>` and `X-Robots-Tag`).
3. Add an ordered audit workflow following the crawl, render, index, rank funnel.
4. Update against Google Search Central (JS SEO basics; structured-data feature deprecations), with a date.

**Test run:** `python -m unittest discover -s tests` ran 3 tests, OK. The verifier code was read for the probes. The x-default behavior is confirmed from the code at `:71`.

### shadow-doc
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 4 | 3 | 3 | 2 | 2.88 | MEDIUM |

**Strengths**
- The strongest tooling in the group. `doc_engine_test_suite.py` reports `SA-DOC-ENGINE-002 Hardened 58-Test Verification Suite` with 58 PASS, 0 FAIL, 0 BLOCKED, 0 NOT_RUN. It covers traversal and symlink containment, XSS escaping, Unicode PDF rendering, and "unknown compat stays UNKNOWN". `--acceptance-suite` passed 16/16. The orchestrator and reference-verifier self-tests pass, and the unittests ran 14, OK.
- Normative anchors are correct: OWASP ASVS 5.0.0, ISO/IEC/IEEE 42010:2022, 29148:2018. Approval separation of duties (owner ≠ approver) and optimistic concurrency are covered (`SKILL.md:20-30`).

**Gaps**
- HIGH. Routing. `regenerate the SRS docx after changing FR-001` routes to shadow-discovery, not shadow-doc. That breaks the global "edit source, regenerate via the generator" rule at the moment it matters. The description also lacks "Do NOT use" (e.g. for BAST governance, which belongs to /shadow-handover).
- MEDIUM. Counts are inconsistent. SKILL.md says "Catalog of 20 Standardized SDLC Templates" (`:36`), but `templates/` has 25 plus `registry.json`, and `--selftest` reports `supported_v2_templates: 26`. SKILL.md says "15-test acceptance suite" (`:128`) and the run shows 16. The `doc_engine_test_suite.py` docstring says "44-Test" while it runs 58.
- MEDIUM. `--acceptance-suite` writes into the installed skill's `shadow-doc/output/`, not a temp directory. In a read-only or shared install this is a side effect (it happened in this review; the folder is gitignored).
- LOW. NIST SP 800-61 is cited without a revision (Rev. 3, April 2025), and ISO/IEC 25010 without a year (2023) (`:30`). The `--selftest` dependency report shows `reportlab` and `markdown` MISSING but still exits 0.

**Prior-review defect status:** FIXED. The Golden Law now limits `doc_scaffold.py` to "documents owned by the global engine" and defers to the project generator (`SKILL.md:15-16`). §3A gives a single precedence chain (`:82`).

**Upgrade actions**
1. Add router probes for docx/pdf/xlsx regeneration intents.
2. Reconcile the counts by generating them from `templates/registry.json`.
3. Redirect acceptance outputs to `tempfile` or a `--out-dir`.
4. Version-pin the standards (NIST SP 800-61r3, ISO/IEC 25010:2023).

**Test run:** see Strengths. All suites passed. Commands: `python shadow-doc/scripts/doc_engine_test_suite.py`, `doc_orchestrator.py --self-test`, `reference_verifier.py --self-test`, `doc_scaffold.py --selftest`, `doc_scaffold.py --acceptance-suite`, and `python -m unittest discover -s tests`.

### shadow-browser
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 3 | 3 | 4 | 4 | 2 | 3.25 | GOOD |

**Strengths**
- Oracles are declared before acting. A 401 with the correct error passes, while a 200 with a blank page fails, and an unreachable target is BLOCKED (`SKILL.md:32-34`). This fixes the prior defect.
- `compare_action.py` fails closed. My probe left out the `httpStatus` observation and got `BLOCKED` (exit 2). Identity mismatch or missing reachability evidence also gives BLOCKED, and it never echoes captured data.
- Strong safety: loopback allowlist, L1/L2/L4 split, owned-PID teardown, no blanket kills (`:37-45`).

**Gaps**
- MEDIUM. `compare_action.py` has no console, pageerror or network-error field, although the skill claims a "console/pageerror oracle" (`:3`, `:32`). A run with uncaught errors can PASS the comparator.
- MEDIUM. The viewport matrix starts at 375 (`:29`). WCAG 1.4.10 Reflow requires 320 CSS px. The overflow test uses `innerWidth`, which includes the scrollbar; `clientWidth` is the stricter comparison.
- LOW. Sources are sparse: 0 URLs in refs 02 and 04, and no last-verified dates. "`chrome-devtools-plugin`" (`:8`) is vague.

**Prior-review defect status:** FIXED. There is now a per-scenario oracle, and expected 401s are distinguished from unexpected failures (`SKILL.md:33-34`).

**Upgrade actions**
1. Add a `consoleErrors: 0` / `pageErrors: 0` assertion field.
2. Add a 320 px viewport and use `clientWidth`.
3. Cite playwright.dev and WCAG 1.4.10 with dates.

**Test run:** `python -m unittest discover -s tests` ran 7 tests, OK. The manual comparator probe returned BLOCKED, exit 2, as designed.

### shadow-email
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 4 | 2 | 2 | 2 | 3 | 4 | 3 | 2.88 | **BAD** (critical defect rule) |

**Strengths**
- Deep, practitioner-level content: stream and subdomain isolation, RFC 8058 limited to bulk mail with security mail exempt, a 2-day unsubscribe window, Gmail clipping at 102 KB, complaint target < 0.1% with a 0.3% danger threshold, warm-up ramp, no blind ESP failover after an ambiguous timeout, HMAC tombstones for erasure-safe suppression (`SKILL.md:12-16`, `references/06-...md:11-22`).
- Lean SKILL.md (48 lines) with 11 tiered modules, each with RFC citations.

**Gaps**
- CRITICAL. The verifier gives a false PASS on DMARC alignment. Probe: `adkim=s; aspf=s`, From `tx.example.com`, DKIM `d=mail.tx.example.com`, Return-Path `bounce.other.net`. Result: `passed: True`. Strict alignment requires an exact domain match, so real DMARC fails (`scripts/email_deliverability_verifier.py:55-63` ignores `adkim`/`aspf` and uses suffix matching). The reverse case gives a false FAIL: From `tx.example.com` with DKIM `example.com` under relaxed alignment is aligned via the organizational domain, but the script returns `DMARC_ALIGNMENT_FAILED`.
- HIGH. The SPF lookup count covers top-level mechanisms only (`:21`, `:35`). Nested `include:` trees are not expanded, so the skill's own "14 DNS lookups → PermError" incident (`references/02-...md:38`) would PASS. The limitation is undocumented.
- HIGH (currency). DMARC is cited as RFC 7489 (`references/02-...md:12`, `:53`). DMARCbis has been published as RFC 9989, which obsoletes RFC 7489 and RFC 9091; failure reporting is now RFC 9991, and the `pct` tag is removed. The rollout table uses `pct=100` (`:34`), and so does the self-test fixture (`scripts/...py:146`). Separately, Google Postmaster Tools v1 retired the Domain and IP reputation dashboards in 2025, but the warm-up gate says "Verify Postmaster Domain & IP Reputation = Medium/High" (`references/06-...md:22`, also `:40`). Sources: [datatracker dmarcbis](https://datatracker.ietf.org/doc/draft-ietf-dmarc-dmarcbis/), [Valimail RFC update](https://www.valimail.com/?p=12740), [Google support 16594218](https://support.google.com/mail/answer/16594218), [Twilio](https://www.twilio.com/en-us/blog/insights/gmail-postmaster-tools-changes).
- MEDIUM. Router miss: `our OTP emails land in gmail spam folder` routes to shadow-monarch only. This is the skill's flagship incident type.
- MEDIUM. SKILL.md has no ordered incident or setup workflow and no deliverable contract (`:10-16`).

**Prior-review defect status:** N/A.

**Upgrade actions**
1. Fix alignment to honor `adkim`/`aspf` (s means exact, r means organizational domain via the Public Suffix List), with precision and recall probes.
2. Either resolve nested SPF includes from a supplied DNS fixture map, or emit an `SPF_NESTED_UNVERIFIED` WARN and never PASS without it.
3. Update to RFC 9989/9990/9991: drop `pct`, describe `t=` and `np=`.
4. Replace the Postmaster reputation gates with the v2 Compliance Status view plus complaint rate.
5. Add router probes for spam-folder and deliverability incidents.

**Test run:** `python -m unittest discover -s tests` ran 3 tests, OK. The self-tests pass, but they miss both alignment cases above.

---

## Cross-cutting observations
1. **Tools that do exist mostly pass their own self-tests, but miss failures outside their fixtures.** shadow-email's verifier gives a false PASS on strict DMARC alignment and on nested SPF. shadow-seo's verifier fails valid pages on pseudo-rules (x-default, title length, one h1). The antislop test checks a function defined inside the test itself. Only shadow-doc (58/58 adversarial cases) and shadow-browser (fail-closed comparator) show real precision and recall discipline. The antislop family (6 skills) and modern-web-guidance have no behavioral tooling at all. Their `evaluations.md` files are only counted by `validate_skill_evaluations.py`.
2. **Facts drift between skills and are not dated.** WCAG large text is "18px+" in antislop and antislop-human but 24 px / 18.66 px bold in shadow-accessibility. DMARC still cites RFC 7489 and `pct`. Postmaster reputation gates remain after their 2025 retirement. The SVGO config targets v3. Counts in shadow-doc disagree (20/25/26 templates; 15/16/44/58 tests). Only shadow-illustration carries a review date. A shared "facts registry" (thresholds, RFC and spec versions with last-verified dates) consumed by all skills would remove most D3 and D8 losses.
3. **Trigger precision is the weakest dimension.** Seven of 15 descriptions lack a "Do NOT use" clause: all six antislop skills and shadow-design. Fresh router probes miss or misroute flagship intents: OTP mail in spam goes nowhere, SRS docx regeneration goes to shadow-discovery, comment cleanup goes nowhere, the pricing hero goes nowhere, and LCP on Next.js gets no playbook. Meanwhile the 5-skill UI always-on bundle attaches to video and accessibility tasks, spending tokens without improving routing. shadow-design's resolver also covers only 14 of 216 vendored entry points, so design tokens cannot be resolved.
