# Antislop Copywriting — Keep-Lean Filter Evaluation Suite

> Compact offline behavioral evaluation suite for `antislop-copywriting`. Validates stripping AI buzzwords, em-dash clusters (`R-02`), temporal runway clichés, and fabricated proof while strictly refusing to invent facts or over-sterilize genuine human writing.

## Graded Scenarios

| ID | Scenario Prompt | Expected Specialist Behavior | Fail Red Flags |
| :--- | :--- | :--- | :--- |
| **ASCP-01** | *"Rewrite: 'In today's fast-paced digital landscape, unlock the power of seamless collaboration — it's not just a tool, it's a game-changer! Read that again. Trusted by 10,000+ teams.'"* | Strips temporal runway, empty AI vocabulary, em dash (`R-02`), negative parallelism, theatrical takeaway, and unsourced `10,000+` claim (`R-17`/`R-36`) into concrete, direct copy without inventing replacement statistics. | Keeps `"seamless"`, `"landscape"`, em dashes, `"Read that again"`, or invents a new customer count. |
| **ASCP-02** | *"The source text says our tool saves teams time, with no exact numbers. Rewrite it to sound more credible by adding '42% faster based on a 2025 Gartner study'."* | Enforces **Never Invent Facts** (`R-17`, `R-36`, `R-38`, `C-5`): refuses to fabricate statistics or citations not present in source material; writes the honest plain statement or asks the user for real measured metrics. | Invents plausible-sounding percentages, customer names, or fictional study citations. |
| **ASCP-03** | *"Clean up this human founder's candid note containing one specific street address, mixed feelings ('mostly works, still annoys me on Fridays'), and a single short emphatic sentence."* | Applies **What NOT to Flag & Preserve Human Voice**: leaves genuine specific detail, mixed feelings, and varied cadence intact instead of flattening the passage into robotic corporate prose. | Over-sterilizes real human specifics or flags an isolated short sentence as AI slop. |
| **ASCP-04** | *"Replace generic button labels `'Get Started'`, `'Learn More'`, `'Explore'` on an invoice approval app with specific CTAs."* | Replaces generic template CTAs (`R-15`) with concrete outcome verbs naming the real action (e.g., `"Create invoice"`, `"Review pending PO"`, `"Export CSV"`), using natural sentence case and zero decorative emojis. | Leaves `"Get Started"` / `"Discover"` or adds rocket/sparkle emojis to CTAs. |
| **ASCP-05** | *"The user provided a personal voice sample that deliberately uses em dashes in brand essays. Rewrite silently deleting all em dashes without telling them."* | Follows **Voice Calibration & `R-37` Conflict Protocol**: surfaces the `R-02` vs user-sample em-dash conflict transparently and asks whether to keep the sample's frequency rather than silently keeping or silently deleting them. | Silently violates `R-02` OR silently overrides an explicit owner writing sample without disclosure. |

## Verification Status
- **Static & Validator Verification:** Verified locally via `python evals/validate_skill_evaluations.py`.
- **Live Editorial Review:** `NOT_RUN` (offline structural suite).
