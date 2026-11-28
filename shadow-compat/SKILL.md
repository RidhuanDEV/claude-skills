---
name: shadow-compat
description: "Use when checking backward compatibility, dependency upgrades, consumer replay, Deprecation/Sunset, or breaking API changes."
---

# Shadow Compat (`/shadow-compat`) — API Evolution, RFC 9745/8594 Deprecation, Upgrades & Cross-Platform Compatibility

Use this skill when evolving live API/webhook/event contracts, upgrading framework/runtime dependencies, or verifying that web, mobile, and OS builds work cleanly across versions and platforms.

- **Owner:** Wire & semantic backward/forward/full compatibility, RFC 9745 `Deprecation` + RFC 8594 `Sunset` + `410 Gone` retirement governance, incremental dependency/runtime upgrades, iOS Safari/WebKit & Windows/Linux parity, and honest consumer payload replay (`test_consumer_replay.py`).
- **Boundaries:** Greenfield API authoring & OpenAPI generation (`shadow-api`), SQL Expand-Contract backfill execution (`shadow-data`), SBOM & SLSA provenance verification (`shadow-supplychain`), and full release orchestration (`shadow-release`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active compatibility subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-wire-and-semantic-compatibility-matrix.md](references/01-wire-and-semantic-compatibility-matrix.md) | Backward/Forward/Full deploy order, breaking wire diffs vs 6 semantic breaks (sort order, `null` vs omitted, enum exhaustiveness) | Auditing API, webhook, or event contract changes for existing mobile/partner consumers |
| [02-rfc9745-deprecation-sunset-and-410-gone.md](references/02-rfc9745-deprecation-sunset-and-410-gone.md) | RFC 9745 `@<unix>` `Deprecation`, RFC 8594 IMF-fixdate `Sunset`, `Link` pointers, telemetry drain gate, `410 Gone` | Deprecating or retiring legacy `/v1` endpoints cleanly without breaking integrators |
| [03-dependency-and-runtime-upgrade-assurance.md](references/03-dependency-and-runtime-upgrade-assurance.md) | `/context7` migration audits, incremental single-ecosystem waves, `amd64`/`arm64`/`musl` native checks, zero `--legacy-peer-deps` | Upgrading Node/Python/Go/framework/ORM major versions safely |
| [04-cross-browser-os-and-consumer-replay-qa.md](references/04-cross-browser-os-and-consumer-replay-qa.md) | iOS Safari (`100dvh`, `16px` input zoom, ISO-8601 dates), Windows/Linux casing (`forceConsistentCasingInFileNames`), honest replay | Eliminating Safari/Linux-only bugs or evaluating unreachable external consumer compatibility |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`CMP-EVAL-01..07`) | Auditing breaking diff detection, RFC 9745/8594 headers, upgrade rigor, and replay honesty |

---

## 1. Core Compatibility, Deprecation & Platform Rules

1. **Wire & Semantic Evolution (`01`):**
   - **Backward Compatible** (new reader reads old data): deploy **Consumer first**, then Producer.
   - **Forward Compatible** (old tolerant reader ignores new optional fields; zero `additionalProperties: false` tightening): deploy **Producer first**, then Consumer.
   - **Full Compatible / Rename / Retype:** Use Expand-Contract dual-write/dual-read (`/shadow-data`) or introduce `/api/v2/...`. Audit semantic breaks (sort flips, `null` vs omitted, default changes, pagination cap cuts, enum exhaustion) beyond AST OpenAPI diffs!
   - **Consumer evidence before any verdict:** for every wire or semantic change, list the consumers (client build or SDK release, owner, how many requests still use it, whether you can run their decoder) and replay sanitized recorded traffic per consumer against the new build. A consumer you cannot replay is `NOT_MEASURED`, not compatible. Get the contract owner's sign-off on the deploy order and on any default or ordering change, or keep the old behaviour behind the current version and expose the new one as an explicit parameter or `v2`.
2. **RFC 9745 & RFC 8594 Retirement (`02`):**
   - Emit `Deprecation: @<unix_sec>` (NEVER draft `true`), `Sunset: <IMF-fixdate>` (`Sunset >= Deprecation`), and `Link` (`rel="alternate"`, `rel="deprecation"`). Verify `legacy_route_hits` telemetry drained before enabling **`410 Gone`** (not `404`).
3. **Incremental Dependency Upgrades (`03`):**
   - Inspect changelogs via `/context7`, inspect metadata non-destructively (`npm view`), upgrade one ecosystem group at a time, test native bindings on target Linux/Alpine images, pin resolved versions, and preserve internal/local SDKs (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`).
4. **Cross-Browser, OS & Honest Consumer Replay (`04`):**
   - Enforce `100dvh`, `font-size >= 16px` mobile inputs, `env(safe-area-inset-bottom)`, strict ISO-8601 `"T...Z"` dates, and exact filename casing (`forceConsistentCasingInFileNames: true`).
   - Inventory consumers by version/owner/reachability; replay sanitized historical payloads honestly noting unmeasured strict-decoder and retry risks.

---

## 2. Deterministic Compatibility & Consumer Replay Verification

```powershell
python shadow-compat/scripts/compat_deprecation_verifier.py --self-test
python shadow-compat/scripts/compat_deprecation_verifier.py --check-compat path/to/compat_spec.json
python -m unittest discover -s shadow-compat/tests -v
```
