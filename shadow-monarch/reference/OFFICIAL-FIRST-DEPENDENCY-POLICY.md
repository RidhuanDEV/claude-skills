# Official-First Project Initialization, Dependency Verification & SDK Preservation Policy

> **Core Governance Mandate:** Conserve output tokens (*Mana Conservation*) and prevent supply-chain or architectural drift by inspecting existing codebases first, scaffolding new projects via **official framework CLI generators** (never hand-writing from-scratch boilerplate when an official generator exists), verifying packages non-destructively before installation, and preserving trusted internal/SSO SDKs.

---

## 1. Seven Core Principles

1. **Discover Before Implementing:** Inspect repo structure, stack versions, lockfiles, conventions, and available SDKs before selecting tools or writing code.
2. **Official-First (Token Efficiency Rule):** Always prefer official framework CLI generators, maintained official SDKs, and current official docs (`/context7`). Never waste output tokens rebuilding standard framework starter files from scratch when a supported CLI generator exists.
3. **Verify Before Adoption:** Registry presence is NOT authenticity or trust. Verify publisher identity, upstream source repository, version compatibility, maintenance status, provenance, and security advisories before installing.
4. **Reuse Before Rebuild:** Prefer an existing trusted SDK, internal package, or established project component over writing duplicate custom code.
5. **Preserve Existing Architecture:** Never swap out established routing, validation, dependency patterns, or auth flows merely due to AI preference.
6. **Custom Implementation Requires Justification:** Custom implementations are allowed only when official options are unavailable, unsuitable, unsupported, or disproportionately complex — document the technical rationale explicitly.
7. **Approval Before Significant Deviation:** Require explicit Monarch approval (`L2`/`L4` under `EXECUTION-APPROVAL-PROTOCOL.md`) before introducing a new framework, replacing a critical SDK/auth flow, changing package managers, or adding unrequested infrastructure (`Docker`, `Redis`, `Kafka`, microservices).

---

## 2. Six-Phase Mandatory Workflow

### Phase 1: Discover
Inspect: repo layout, package manager & lockfile (`package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, `go.sum`, etc.), runtime/framework versions, dependency conventions, internal/local SDKs (`file:../...`), official CLI generators, target deployment environment, and compliance/security constraints.
Classify task as one of: `New project` | `Existing project enhancement` | `Legacy integration` | `SDK/library integration` | `Infrastructure setup`.

### Phase 2: Verify Official Options
Before writing project config manually, check whether the chosen framework provides a supported CLI generator (confirm exact flags & runtime requirements via `/context7` or official docs):
- **React + Vite:** `npm create vite@latest` (resolve exact template & pin versions post-init)
- **Next.js:** `npx create-next-app@<version>`
- **Angular:** `npx @angular/cli@<version> new`
- **Vue:** `npm create vue@<version>`
- **NestJS:** `npx @nestjs/cli@<version> new`
- **Laravel:** `composer create-project laravel/laravel`

*(These are illustrative examples, not forced stack choices.)* Resolve concrete approved versions and pin versions properly in production or regulated environments instead of blindly leaving floating `latest` ranges.

### Phase 3: Verify Dependencies (Non-Destructive Inspection First)
Before adopting any new dependency (especially security-sensitive or foundational packages), inspect metadata **without installing unverified packages first**:
```bash
npm view <package-name> version
npm view <package-name> repository
npm view <package-name> maintainers
npm view <package-name> engines
npm view <package-name> dist-tags
```
Verify: publisher/maintainer identity, authentic upstream repo, release status, peer/runtime compatibility, provenance/signatures, known advisories, license compatibility, and existing approved alternatives. Treat registry output as evidence to review, never automatic trust. Run native audit tools (`npm audit --omit=dev`, `pip-audit`, etc.) on existing dependencies and review findings instead of blindly applying breaking upgrades.

### Phase 4: Select Implementation (5-Tier Decision Hierarchy)
1. **Existing trusted implementation** compatible with requirements.
2. **Official supported SDK** or native framework integration.
3. **Verified mature third-party package**.
4. **Small custom implementation** (only when justified and safe).
5. **New framework / architectural replacement** (explicit Monarch approval required).

*Exception rule:* Never force reuse if an existing component is insecure, obsolete, or incompatible — document and report the flaw transparently.

### Phase 5: Execute Within Approved Scope
- Use official CLI scaffolding workflows for new projects (non-interactive flags where supported).
- Preserve lockfiles and existing project patterns; avoid unnecessary dependencies or unapproved post-install scripts.
- Never substitute an unknown lookalike package or invent unsupported SDK methods/configs.
- Never add unrequested monorepo tooling, microservices, Docker, Redis, or Kafka.

### Phase 6: Report (Mandatory 8-Field Decision Record)
Before implementation, emit this Decision Record (verifiable via `shadow-monarch/scripts/official_first_verifier.py`):

| Field | Required Content |
|---|---|
| `Technology` | Selected framework or package |
| `Source` | Official documentation / verified repository |
| `Version` | Exact resolved/selected version |
| `Trust status` | `Verified` / `Unverified` / `Blocked` |
| `Compatibility` | Runtime, peer dependencies, and existing project compatibility |
| `Existing alternative` | Whether an existing SDK/component can be reused |
| `Decision` | `Reuse` / `Scaffold` / `Install` / `Custom` |
| `Approval` | `Required` / `Not required` |

If package authenticity or compatibility cannot be verified, report uncertainty explicitly (`Unverified` / `Blocked`) rather than guessing.

---

## 3. Special Rule: Authentication, SSO & `ridhuan-sso`

- Inspect any existing local/internal SSO SDK first (identity, exports, supported flow, session/token model, version).
- Never implement a custom replacement login flow or switch auth architecture without explicit Monarch approval.
- Never trust frontend-supplied `username` claims as authentication proof; require verified server-side authenticated claims (verified token signature/introspection/assertion) before local user mapping.
- Never assume similarly named registry packages belong to the same publisher.
- **`ridhuan-sso` (`file:../sdk/sso-client`) Rule:**
  1. Treat the inspected local SDK as the existing authoritative implementation.
  2. Check whether an official registry distribution exists and verify publisher ownership before considering migration.
  3. Preserve `file:../sdk/sso-client` when appropriate; NEVER replace it with an unverified npm lookalike package.
  4. Report packaging/Docker/deployment portability trade-offs separately rather than silently rewriting or swapping the SDK.

---

## 4. Failure Conditions (Enforced by `official_first_verifier.py`)

An agent violates this policy if it:
1. Manually recreates framework starter files from scratch when an official generator exists (wasting output tokens).
2. Installs a package solely by name without publisher/repository verification or installs an unverified package just to inspect it.
3. Claims an npm/registry package is official without verified ownership.
4. Reimplements an available trusted SDK without documented technical justification.
5. Replaces established conventions or auth/SSO SDKs without explicit Monarch approval.
6. Introduces unrequested infrastructure (`Docker`, `Redis`, `Kafka`) or unrelated testing.
7. Treats an unverified dependency as production-ready or trusts unverified frontend `username` fields for auth.
8. Invents non-existent SDK methods, endpoints, or configuration options.
