# UX quality review and release gates
## Evaluation methods
Walk core jobs end-to-end with representative user context; Nielsen heuristics, cognitive walkthrough, keyboard-only and screen-reader review, accessibility checks, assumption review, design consistency audit, service-state walkthrough, and adversarial edge-case tests. Assess user task success rather than only aesthetic appeal.

## Suggested rubric (internal heuristic, not validated scale)
- Problem and story coverage: 15%
- Main/alternate flows: 20%
- Failures and recovery: 20%
- Navigation and design-system consistency: 15%
- Accessibility and cross-device: 15%
- Handoff and acceptance criteria: 15%
Score each 0–5 and compute weighted total (score/5 * weight). 85/100 suggests ready for stakeholder review only, not automatically production-ready.

## Hard blockers overriding score
Any unmitigated critical issue with privacy/security, irreversible data loss, inaccessible core task, broken essential flow, noncompliant high-stakes interaction, or deceptive success means FAIL irrespective of rubric. Every warning logs owner, evidence, consequence, mitigation, and verification plan.

## Evidence
A rubric is expert judgment. User testing, analytics, and accessibility testing are separate validation activities. Report 'NOT TESTED' where testing was not performed. Never manufacture measured improvements.
