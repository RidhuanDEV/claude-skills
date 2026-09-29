# Evals — check that the skill works

`evals.json` holds realistic prompts and what a good answer must contain. Use them after installing or editing the skill.

## Manual check (5 minutes)

1. Open a **new** chat (Claude app) or session (Claude Code) with the skill enabled.
2. Paste a prompt from `evals.json`.
3. Check:
   - **Routing**: the tool activity shows `shadow-monarch` being used and the expected reference files being read
     (e.g. eval 2 → CORE, DEBUGGING, BACKEND, DEVOPS, lang-TYPESCRIPT-NODE; eval 7 → no reference files).
   - **Behavior**: tick off each item in `assertions`.
4. For a baseline, turn the skill off and repeat. The skill version should pass clearly more assertions.

| Eval | Tests |
|---|---|
| 1 review-payment-endpoint | severity scale, security + money + idempotency findings |
| 2 nestjs-500-in-docker | evidence-first debugging, container networking/env |
| 3 efcore-add-column-production | safe migrations with rolling deploys |
| 4 go-external-api-client | language idioms (context, timeouts, error wrapping) |
| 5 bahasa-laravel-upload | replies in Bahasa Indonesia, secure uploads, PII |
| 6 rag-fastapi-design | AI-LLM reference: permissions in retrieval, citations, evals |
| 7 simple-question-stays-short | does not over-answer |
| 8 push-back-on-overengineering | peer, not yes-man |

## If something fails

- Skill not used at all → improve the `description` in `SKILL.md` or disable overlapping skills/plugins.
- Wrong files read → adjust the router tables in `SKILL.md`.
- Right files, wrong behavior → the rule is missing or unclear in that reference file; add the reason, not just the rule.

The `assertions` field also works with Anthropic's skill-creator eval tooling for automated with/without-skill comparisons.
