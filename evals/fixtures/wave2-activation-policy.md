# Activation policies of this skill suite (by design)

A near-miss row says "skill X must stay inactive". It must not contradict these deliberate policies.

1. **Anti-slop rule.** Any request to build, style, or review UI, frontend components, page layout, interaction states or accessibility affordances, UI copy, or code comments automatically activates the UI quality filters: antislop, antislop-ui, antislop-layoutmobile, antislop-human and modern-web-guidance. A near-miss for one of these five skills must therefore involve no UI, frontend, layout, UI-copy or code-comment work. Use backend, data, infrastructure, CLI, process or document tasks instead. Running a linter or a CI job on a frontend package counts as non-UI work.
2. **Fixed co-activation.** These owners always bring helpers:
   - shadow-debug, shadow-refactor, shadow-concurrency and shadow-domain bring shadow-test.
   - shadow-refactor also brings shadow-compat.
   - shadow-search brings shadow-db.
   - shadow-realtime brings shadow-auth and shadow-observe.
   - shadow-pmo brings shadow-architect.
   - shadow-architect brings shadow-sec.

   A near-miss that excludes skill X must not have an owner that brings X.
3. **Risk reviews.** These skills activate as a review whenever their topic appears anywhere in the request:
   - accessibility
   - browser (real-browser or Playwright runs)
   - compatibility and upgrades
   - enterprise portfolio
   - LLM evaluation
   - cloud cost
   - governance and compliance audits
   - client handover
   - observability (metrics, tracing, logging stacks)
   - performance and load testing
   - personal-data privacy
   - code quality and lint
   - release
   - backup and restore
   - security
   - UAT

   A near-miss that excludes one of these skills must not mention that skill's topic at all.
4. **Third-party audits.** Auditing a third-party skill, plugin or MCP server before installing it activates both shadow-sec and shadow-supplychain.
5. **Flaky tests** belong to shadow-test, which has a flaky-test triage playbook.
6. **Session memory and client delivery are separate.**
   - handoff covers AI agent session context only.
   - shadow-handover covers client BAST and delivery.
   - presales covers activity before an award; after an award, requirement work belongs to shadow-discovery.
