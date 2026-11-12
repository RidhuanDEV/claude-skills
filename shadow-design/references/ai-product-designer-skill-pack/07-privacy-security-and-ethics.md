# Permission-aware, ethical and privacy-preserving UX
## Authorization
Build role x resource x action x state matrix. Show allowed actions with clarity. Disabled vs hidden vs read-only is a design choice, never an authorization guarantee. Backend must enforce authz for every resource/action; never surface sensitive data merely because route can be guessed. Account for role changes and session expiration mid-task.

## Privacy and safety
Data minimization, consent clarity, safe defaults, masking of sensitive fields, reasonable retention disclosures, device-sharing risks, notification redaction, sensitive export/sharing permissions, accidental destructive operations, and secure link-expiration semantics. Do not request secret tokens/passwords in design documents.

## Ethical guardrails
No dark patterns, fabricated testimonials, coercive permissions, false scarcity, hidden cancellation, confusing opt-outs, misleading success, or emotional manipulation. Consider children/vulnerable users and high-stakes contexts; escalate domain-specific regulatory questions for qualified review.

## Tool and supply-chain safety
External skill repos/MCPs are NOT automatically trusted even if open-source or MIT licensed. Review license, dependencies, install scripts, credential permissions, network endpoints, logging, file-system writes, update practices, and threat model. Pin versions when integrating. Prefer read-only MCP access and local sandbox for initial evaluation. Never run `curl | bash`, arbitrary `npx`, or remote code based solely on a README without user approval and review. MCP plugins that can execute arbitrary scripts inside a design editor require particular care.
