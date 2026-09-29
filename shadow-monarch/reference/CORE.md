# CORE — Engineering Mindset & Code Quality

Loaded for non-trivial work. It expands the non-negotiables in SKILL.md (not repeated here);
domain and language files add detail.

## 1. Before touching code

Answer internally:
- What problem are we actually solving? What are the functional and non-functional requirements
  (performance, security, availability, maintainability, observability, accessibility, cost, consistency)?
- What assumptions am I making? State the ones that materially change the solution. Do not invent requirements.
- What existing architecture, contracts, naming and dependency choices must be preserved?
- Which invariants must hold? (e.g. balance never negative, an item is never sold twice, email unique,
  approved records are immutable to unauthorized users, payment is never processed twice.)
- Who owns this data? Which layer should enforce this rule? What is the source of truth?
- What can break: edge cases, partial failure, concurrency, retries, deployment, rollback?
- How will it be tested, observed and maintained six months from now?
- Can it be simpler without sacrificing correctness?

## 2. Problem-solving flow (complex tasks)

1. **Understand**: expected vs current behavior, architecture, dependencies.
2. **Locate** the likely layer: UI, client state, API client, controller, service, domain, DB, cache,
   queue, proxy, network, infra, config.
3. **Hypothesize**: several plausible causes; do not lock onto the first.
4. **Gather evidence**: logs, traces, requests, queries, tests, config, runtime behavior.
5. **Root cause**: separate it from symptoms and contributing factors.
6. **Smallest correct fix**, no unnecessary architecture change.
7. **Regression risk**: what existing behavior could break, which consumers are affected.
8. **Verify**: define how the fix is tested.

For larger features, execute roughly: understand current code → affected modules → contract changes →
domain logic → persistence → API → frontend → validation → tests → regression check →
deployment/migration notes. A feature is complete only when implementation, validation, tests,
migration, docs, observability and deploy config are done as far as the scope requires.

## 3. Modifying existing code

- Patch-style thinking: existing behavior → desired behavior → minimal affected area → regression risks → verification.
- Preserve architecture, naming, formatting, API contracts, component patterns and dependencies unless
  there is a strong technical reason; if the architecture is flawed, explain before proposing a refactor.
- Do not delete working configuration to simplify an example. Do not reformat unrelated files.
- Legacy code often encodes undocumented business rules: understand it, document dependencies, add
  regression tests, then migrate incrementally. A clean rewrite that loses business logic is worse than ugly working code.
- Refactor only for measurable value (less duplication, clearer ownership, testability, safety, easier change).
  Protect fragile code with tests first. Incremental over big-bang.

## 4. Code quality order

Correctness > readability > maintainability > simplicity > consistency > performance > cleverness.

Functions:
- One responsibility; the name states the business intent; few, clear parameters; explicit return.
- Split when nesting exceeds ~2 levels, when one function validates + applies business rules + persists + formats,
  when it needs a long comment to be understood, or when it is hard to test without big setup.
- No hidden side effects, no dependence on hidden global state, no boolean flag that switches large behavior.

Naming:
- Names describe intent: `calculateInvoiceTotal`, `findActiveSubscriptionByUserId`, `markOrderAsPaid`, `isPaymentExpired`.
- Avoid `data`, `handleStuff`, `processData`, `doAction`, `temp2`, `manager`, `helper`, and `utils` for business logic.
- Use the business domain vocabulary consistently (Proposal, Reviewer, Approval, Submission, Shipment…).
- Longer and descriptive beats short and ambiguous.

Comments explain **why**: reasons, trade-offs, non-obvious constraints, external quirks. Never restate the code.

Avoid: giant functions, deep nesting, duplicated business logic, magic numbers/strings, stringly-typed domains,
primitive obsession for important values (money, IDs, emails), premature optimization.

## 5. Abstraction discipline

- Abstract when code represents the same **concept** that will evolve together, not because it looks similar.
  Duplication is cheaper than the wrong abstraction.
- Avoid: generic repositories without need, factory layers, wrapper-of-wrapper functions, one-implementation
  interfaces with no seam value, pass-through services, utility dumping grounds, premature microservices.
- SOLID pragmatically: one reason to change; extend without destabilizing; honor contracts; small interfaces;
  depend on abstractions only where it buys real flexibility or testability. Never ceremony.
- YAGNI: no speculative infrastructure. KISS: simple and correct beats complex and elegant (but simple never
  means ignoring requirements). DRY: conceptual duplication matters more than textual duplication.
- Every line has maintenance cost: write less code, remove dead code, isolate side effects, centralize real invariants.

## 6. Null, absence and errors

- Handle absence explicitly: null API fields, not-yet-loaded async data, missing relations, missing optional config.
  Use defaults only when semantically correct; never hide invalid state behind arbitrary fallbacks.
- Errors are design. Distinguish expected (validation, not found, conflict, forbidden) from unexpected (bugs, dependency failure).
- Never swallow errors. Each error is handled, transformed, retried, logged or propagated — by whoever owns that responsibility.
- Internal errors carry context (operation, safe identifiers, cause, retryable or not); user-facing errors never leak internals.
- Always release resources (connections, file handles, streams, timers, subscriptions, temp files) with the language's guaranteed-cleanup construct.

## 7. Code you deliver

- Runnable when practical, complete imports, consistent with the existing stack and style, typed where the language allows,
  secure by default, clear rather than clever.
- No pseudo-code presented as production code; no `// TODO implement` placeholders in delivered code;
  no fictional dependencies. Mark snippets that need adaptation.
- Give file paths for multi-file changes and how to run it when not obvious.
- If context is missing, give a best-effort answer with explicit assumptions rather than stalling — but ask when a wrong guess is costly.
- Distinguish development shortcuts (localhost, verbose logs, self-signed certs) from production recommendations.

## 8. Trade-offs and technology choices

- Significant decisions list options with advantages, disadvantages and when each fits, then recommend based on constraints.
- Never claim a technology is universally better. Evaluate requirements, team expertise, ecosystem, operations,
  maturity, security, cost, performance, maintainability, lock-in. Boring technology is fine when it solves the problem.
- Dependencies cost: check maintenance, security record, size, license, transitive deps, and whether the platform
  already does it. No large dependency for a trivial task. Read release notes for major upgrades.
- A theoretically elegant system nobody can operate is a bad system. Architecture must account for human operators.

## 9. Communication

- Concise, structured, precise, honest about uncertainty. Never hide important risks.
- Explaining code: what it does, why it works, key decisions, failure cases, how to test — not a line-by-line translation.
- Uncertain? "The most likely cause is…", "Based on this stack trace…", "Two plausible scenarios…", then how to verify.

Documentation answers: what is this, why does it exist, how does it work, how do I run, configure, test and deploy it,
what commonly breaks. Useful over exhaustive; keep it in sync with the code. Respect semantic versioning
(MAJOR.MINOR.PATCH) and remember that "minor" upgrades can still break things.

## 10. Final check before answering

Is it correct? Secure? Can it fail partially? Can it run twice? Can two users run it at once?
What if a dependency is down? Can it corrupt or leak data? Does it scale for expected demand?
Can another engineer understand, test and roll it back?
"It compiles" and "the tests I wrote pass" are not the same as "it is correct".
