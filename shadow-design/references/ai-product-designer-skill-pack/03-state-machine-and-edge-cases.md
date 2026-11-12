# State machines and adversarial UX edge cases
## Model
Represent transitions as `state + event + guard -> next state / side effect / feedback`. Separate UI state from server truth; document cancellation and retry semantics. For relevant flows define initial, empty, loading, partial, success, error, permission denied, offline, and stale/conflict states. Not every screen needs all nine; mark N/A with reason.

## Edge-case matrix
| Domain | Test | UX mitigation |
|---|---|---|
| Data | zero/large/duplicate/null/long string | useful empty-state guidance, pagination, wrapping, safe defaults |
| Form | invalid, async validation, repeated submit, dirty exit | inline errors, preserve values, idempotence, unsaved-change guard |
| Network | offline, intermittent, timeout, retry | detectable state, retry with guidance, durable draft if feasible |
| Navigation | back/forward, refresh, deep link, multiple tabs | stable URLs, retained context, predictable return |
| Session | expiry during task, role revoked | prompt reauth, preserve non-sensitive draft, safe denied state |
| Concurrency | two edits, stale cache, ETag conflict | conflict comparison, version warning, avoid silent overwrite |
| Async | queued/running/failed/partial/complete | truthful status, background-safe progress, notification strategy |
| Destructive | delete, bulk action, wrong target | contextual preview, confirmation for irreversible actions, undo where feasible |
| International | locale, long text, RTL, date/timezones | adaptable layouts, explicit timezone, locale formats |
| Device | touch, zoom, keyboard, landscape, small viewport | target spacing, content reflow, screen reader focus |
| Privacy | notifications, shared devices, clipboard, screen snapshots | minimize sensitive preview, redaction, logout behavior |
| AI | uncertainty, missing citations, malicious retrieved text, interrupted stream | source labels, caveats, confirmation for high-impact action, recovery |

## Severity
Critical: blocks task completion, creates security/privacy harm, irreversible loss, or prevents access for key users. Major: common failure without adequate recovery. Minor: friction with workaround. Cosmetic: negligible outcome impact. Distinguish likelihood and user impact; log unverified assumptions.

## Acceptance examples
- Given upload received and indexing pending, when HTTP 202 returns, then show Processing rather than Available.
- Given two admins edit record version 3, when second submits against version 4, then offer conflict recovery rather than overwrite silently.
- Given user selects a file and network drops, then preserve metadata, explain what was saved, and offer safe retry.
