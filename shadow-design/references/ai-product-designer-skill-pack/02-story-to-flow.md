# Story-to-flow traceability
For each user story, create:
| Field | Description |
| ID | Stable US-001 |
| Actor and goal | User role, context, desired outcome |
| Preconditions | Authentication, entitlements, data state, connectivity |
| Trigger | How user enters the flow (including deep link) |
| Happy path | Steps with system feedback and primary action |
| Alternatives | Valid branching and escape/cancel |
| Exceptions | Failure, timeouts, conflicts, invalid state |
| Recovery | Preserve work; retry, undo, support or alternate route |
| Completion | Observable user outcome, not only server response |
| AC | Given/When/Then, including edge-case tests |
| Screen IDs | SCR-001 etc, state IDs if needed |

## Example
US-001: As an editor I can upload a knowledge document.
1. Enter documents page; verify upload capability and constraints.
2. Choose/drop file; show constraints and filename; validate file before request.
3. If invalid, explain specific reason and preserve user's context.
4. Upload with progress; prevent unintended duplicate submissions.
5. If processing is asynchronous, show `received/processing` not `ready`.
6. On success, show searchable document and completion notice; on failure show reason and safe retry.
7. AC includes permissions, oversized/duplicate file, network interruption, page navigation, partial failure, cancellation, and refresh during processing.

## Avoid
Orphan screens, no back path, implicit role assumptions, ambiguous success indicators, 1:1 copy of every user story into a screen, and forced sign-in before its user value is established unless required for safety/security.
