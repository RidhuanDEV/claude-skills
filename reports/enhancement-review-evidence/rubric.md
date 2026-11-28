# Grading rubric (read-only review; do NOT edit any repo file)

Repo root: <repo>. Each skill = <dir>/SKILL.md + references/ + scripts/ + tests/ + evaluations.md.
Question being answered: "If an AI agent loads this skill, will it ACT and KNOW like a senior professional expert engineer in this domain?"

Score each skill 1-4 on 8 dimensions (1=BAD, 2=MEDIUM, 3=GOOD, 4=PERFECT):
D1 Trigger precision - description says when to use AND when not; sibling boundaries; would the right prompts select it?
D2 Expert knowledge depth - covers what a senior practitioner knows: hard edge cases, failure modes, trade-offs, numbers/thresholds, not just buzzwords.
D3 Knowledge correctness & currency - claims match current authoritative sources (spot-check at least 3 concrete claims: standard versions, API names, RFC numbers, thresholds, laws). Flag anything wrong/outdated/unverifiable/hallucination-like.
D4 Procedural operability - clear ordered workflow, decision points, stop/escalate conditions, output/deliverable contract. An agent can follow it without guessing.
D5 Verification tooling - scripts/tests/eval scenarios that actually catch wrong behavior (falsifiable oracles; not just "self-test passes"). Run the skill's self-test / unittest if cheap (bounded L1, offline only, <60s), report result.
D6 Safety & boundaries - approval levels, destructive-action guards, privacy/secrets, scope limits appropriate to domain.
D7 Token efficiency & progressive disclosure - SKILL.md lean, references loaded on demand, no bloat, no slogan/buzzword stuffing, no duplicated content.
D8 Provenance & maintainability - cites primary sources (URLs/standard IDs with versions), dated "last verified", no broken links, internally consistent counts/names.

Overall grade: PERFECT = avg >=3.6 AND no dimension <3; GOOD = avg >=3.0 AND no dimension 1; MEDIUM = avg >=2.2; BAD = avg <2.2 OR any critical defect (wrong security/legal advice, tool that produces false PASS, misleading core claim).
Be strict and evidence-based. PERFECT should be rare. Cite file:line for every negative finding. Do not inflate.

Context (already measured by orchestrator): Router (shadow-monarch/scripts/skill_router.py) self-test 154/154 passes, but fresh probes missed: "migrate column email to NOT NULL in 50M row table"->none, "optimize LCP on next.js landing page"->none, "rotate JWT signing keys"->none, "our redis cache returns other tenant data"->none, "why is this query slow EXPLAIN"->none, "bump react 18 to 19 safely"->none, "design pricing page hero section"->none; "bikin ERD dari database postgres"->shadow-db but playbook RLS; "set up stripe webhook signature check"->integrate playbook 04 not 02. Factor routing into D1 only where relevant.
A prior review exists at reports/skill-review-core.md and reports/skill-review-delivery.md (dated 2026-11-18, older commit). For your skills, check whether the defects it listed are now FIXED or STILL OPEN (verify in code, e.g. rerun its probe).

OUTPUT: write your full result to the file path given in your task (markdown), and return a short summary. Format per skill:
### <skill>
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
Strengths (2-3 bullets, with evidence)
Gaps (3-6 bullets, each with file:line evidence and severity CRITICAL/HIGH/MEDIUM/LOW)
Prior-review defect status: FIXED / STILL OPEN / N/A (with evidence)
Upgrade actions (concrete, ordered; name the authoritative source to align with, e.g. "RFC 9457", "OWASP ASVS 5.0.0", "WCAG 2.2", official doc URL)
Test/self-test run: command + observed result
