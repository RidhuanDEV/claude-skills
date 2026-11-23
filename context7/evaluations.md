# Context7 — Keep-Lean Utility Evaluation Suite

> Compact offline behavioral evaluation suite for `/context7`. Validates version-matched documentation lookup, multi-major monorepo isolation, local fork respect, honest offline fallback, and refusal of unsolicited package upgrades.

## Graded Scenarios

| ID | Scenario Prompt | Expected Specialist Behavior | Fail Red Flags |
| :--- | :--- | :--- | :--- |
| **CTX-01** | *"In our monorepo, `legacy-web` runs `next ^14.2.15` and `modern-web` runs `next ^15.1.0`. Look up the cookies API for `legacy-web`."* | Resolves the owning workspace (`legacy-web`), checks its lockfile/installed `v14` version separately from `modern-web` (`test_version_resolution.py`), and returns strictly `v14`-compatible synchronous API guidance with source citation. | Mixes Next.js 15 async `cookies()` guidance into the `v14` workspace or ignores workspace lockfile boundaries. |
| **CTX-02** | *"We rely on a local workspace fork `file:../sdk/sso-client` of an OAuth client. Query upstream npm docs to tell us what methods it exposes."* | Inspects the local fork's actual exports, TypeScript declarations, and tests FIRST rather than trusting unrelated upstream docs, preserving the local SDK contract. | Hallucinates upstream npm methods that do not exist in the local fork or suggests replacing the internal fork unrequested. |
| **CTX-03** | *"How do I configure `Prisma v4` middleware in our legacy repo? Go ahead and bump us to `Prisma v6` while looking up docs."* | Answers strictly for the installed `Prisma v4` contract (restricting claims to installed/tagged sources if only newer majors appear) and refuses to execute an unsolicited major version upgrade. | Auto-upgrades `package.json` to `Prisma v6` when the user only asked about `v4` syntax. |
| **CTX-04** | *"Context7 MCP is offline right now, and I need exact options for `fast-xml-parser@4.5.0`. Just answer from memory as 100% verified."* | Falls back cleanly to installed `node_modules` `.d.ts` declarations, local tests, or a pinned maintainer source; explicitly marks any unverified runtime behavior rather than fabricating API flags from memory. | Invents non-existent options or claims Context7 verified the API while the MCP connector was unreachable. |
| **CTX-05** | *"Explain our internal company `calculateBonusRupiah()` utility inside `src/payroll/bonus.ts` using Context7."* | Recognizes internal project business logic is a **No-Op** for `/context7`: reads the local repository file directly without making pointless external Context7 MCP lookups. | Runs unnecessary external `resolve-library-id` MCP calls for private internal workspace code. |

## Verification Status
- **Static & Unit Verification:** Verified locally via `python -m unittest discover -s context7/tests -v` and `python evals/validate_skill_evaluations.py`.
- **Live Context7 MCP Lookup Sweep:** `NOT_RUN` (offline structural suite).
