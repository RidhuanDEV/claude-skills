---
name: shadow-compat
description: "Compatibility & Upgrade Assurance. Use when auditing API/webhook backward compatibility, database schema evolution safety, dependency upgrade breaking changes, or cross-browser/device support matrices."
---

# Shadow Compat (`/shadow-compat`) — API, Dependency & Cross-Browser/Device Compatibility

Use this skill when modifying existing API contracts, upgrading framework/library dependencies, or verifying that web and mobile interfaces work consistently across browsers, operating systems, and client versions.

---

## 1. API & Contract Backward-Compatibility Rules

When mobile apps (which users do not update immediately), partner webhooks, or external systems consume your backend API:

| Change Type | Classification | Safe Evolution Rule |
| :--- | :--- | :--- |
| Adding an **optional** request field or **new** response field | **Non-Breaking (Safe)** | Safe to deploy in minor release (`v1.x`). |
| Adding a **required** request field | **BREAKING** | Make optional with a safe server default, or introduce `/api/v2/...` endpoint. |
| Renaming or removing a response field | **BREAKING** | Keep returning both old and new fields during deprecation window; remove old field only after all clients upgrade. |
| Changing field type (e.g., `number` -> `string` or `object` -> `array`) | **BREAKING** | Never mutate field types in-place on live endpoints. |
| Narrowing an enum in responses (adding a new enum value that old mobile clients don't recognize) | **Potentially Breaking** | Ensure mobile/frontend clients have a safe fallback branch for unknown enum values. |

---

## 2. Dependency & Runtime Upgrade Protocol

When upgrading packages (`package.json`, `requirements.txt`, `composer.json`, `go.mod`):
1. **Audit Breaking Changes First**: Use `/context7` MCP to inspect the official migration guide / changelog between the installed major version and target version.
2. **Incremental Group Upgrades**: Upgrade one ecosystem group at a time (e.g., ORM first -> verify tests -> framework next -> verify tests), never 40 major versions in a single blind commit.
3. **Lockfile & Native Binding Check**: Verify compatibility with the production OS/architecture (`linux/amd64` vs `linux/arm64`, `glibc` vs `musl` Alpine in Docker).

---

## 3. Cross-Browser & Mobile Device Compatibility Checklist

Watch for and eliminate common cross-platform pitfalls:
- **iOS Safari Viewport & Input Quirks**:
  - Use `100dvh` (`min-h-dvh`) instead of `100vh` so the iOS Safari address bar does not clip bottom buttons.
  - Ensure all `<input>`, `<select>`, and `<textarea>` elements have `font-size >= 16px` (`1rem`) on mobile so iOS Safari does not auto-zoom the page on input focus!
  - Respect `env(safe-area-inset-bottom)` on fixed bottom navigation bars and sticky action footers.
- **Date & Timezone Parsing**:
  - Never pass non-standard date strings like `"2026-11-10 14:30:00"` into `new Date(...)` (returns `Invalid Date` in Safari/WebKit!). Always use strict ISO-8601 `"2026-11-10T14:30:00Z"` or explicit date parsers.
- **Windows vs Linux Path & Case-Sensitivity**:
  - Git on Windows is case-insensitive by default (`import './Header'` works locally even if file is `header.tsx`), which breaks immediately on Linux CI/Docker builds! Always verify exact filename casing.

### Schema Evolution Compatibility Matrix & Contract Governance
- **Wire & Schema Evolution Rules**:

| Evolution Mode | Constraint | Safe Deployment Order |
| --- | --- | --- |
| **Backward Compatible** | New consumer/reader reads old producer payloads (`add optional field` with safe default) | Deploy **Consumer first**, then Producer |
| **Forward Compatible** | Old consumer ignores new optional fields (`tolerant reader` + no `additionalProperties: false` breakage) | Deploy **Producer first**, then Consumer |
| **Full Compatible** | Only add/remove fields that both old and new versions default safely; never rename/retype in place | Expand-Contract dual-write / dual-read window (`/shadow-data`) |

- **Semantic API Diff & Consumer-Driven Contract Tests**: Beyond AST/OpenAPI syntactic diffs, audit **semantic breaking changes** (default value flips, keyset/sort order changes, error code remapping, `null` vs omitted field semantics, pagination limit caps). Inventory consumers by version, owner and reachability. Run available clients and replay approved sanitized historical payloads for unreachable clients. Record which behavior replay measures and identify missing evidence (strict decoding, retry semantics, platform support). Route residual risk to the contract owner for an approved staged rollout or defer the breaking change.
- **Deprecation & Sunset Policy**: Annotate deprecated endpoints/fields with RFC 8594/9745 headers (`Deprecation` and `Sunset` timestamps), document migration guides, and verify telemetry shows near-zero legacy traffic before the Contract phase removes the field or route.
- **Version Pinning & Decision Record (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`)**: Resolve peer/runtime `engines` compatibility first and pin approved concrete versions in production/regulated projects instead of leaving floating `latest` ranges.

Run `python -m unittest discover -s tests` from this skill directory for examples of strict decoding, omitted cursors and ordering changes. Capture each real client's decoder/version and business expectations before treating a replay as representative.
