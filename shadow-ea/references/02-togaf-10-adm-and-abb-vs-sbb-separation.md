# 02. TOGAF 10 ADM, Capability Mapping & Vendor-Neutral `ABB` vs `SBB` Separation

## 1. Purpose & Activation Conditions
Use this playbook when designing multi-system enterprise blueprints for **Private Enterprises, BUMN, or Banking Groups** under **TOGAF 10 ADM**, mapping Business Capabilities & Value Streams, and enforcing strict separation between vendor-neutral **Architecture Building Blocks (`ABB`)** and concrete product **Solution Building Blocks (`SBB`)** to prevent premature vendor lock-in.

Activate this playbook when:
- Structuring a multi-year enterprise transformation blueprint across Business, Data, Application, and Technology domains (`Preliminary`, `Phases A–H`, `Requirements Management`).
- Defining vendor-neutral `ABB` capability contracts before running commercial vendor comparisons (`/shadow-presales`).
- Reviewing an enterprise blueprint to eliminate hardcoded vendor product names inside architectural capability layers.

## 2. Prerequisites
- Enterprise strategic objectives, multi-system catalog (`>= 3` interacting applications/platforms), and key stakeholder concerns (CIO, Enterprise Architect, Risk/Compliance, Finance).
- Deep companion docs: [`../methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md`](../methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md) & [`../playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md`](../playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md).

## 3. Technical Principles & Constraints
1. **Vendor-Neutral `ABB` Before Concrete `SBB` (Zero Premature Vendor Lock-In)**:
   - **Architecture Building Block (`ABB`)**: Describes a **vendor-neutral required capability, interface standard, NFR, and interoperability contract** (e.g., `ABB-IAM-01: Centralized OIDC/OAuth2 Identity Broker supporting FIDO2 Passkeys, RBAC, and Audit Trails`; `ABB-API-GW-01: Standards-Based API Gateway with Rate Limiting & mTLS`).
   - **Solution Building Block (`SBB`)**: Names concrete evaluated product/implementation candidates mapped to an `ABB` (e.g., `Keycloak HA`, `Auth0`, `Kong`, `Apache APISIX`) evaluated transparently via Multi-Criteria Decision Analysis (`MCDA` — TCO, TKDN/residency, open standards, team capability).
   - **Strict Rule**: NEVER embed proprietary vendor names inside `ABB` definitions! Putting *"Buy Vendor-X ESB"* inside an `ABB` bypasses fair evaluation and causes permanent lock-in.
2. **TOGAF 10 ADM Fit-for-Purpose Tailoring**:
   - Tailor ADM phases (`Preliminary -> A Architecture Vision -> B Business -> C Information Systems [Data + Application] -> D Technology -> E Opportunities & Solutions -> F Migration Planning -> G Implementation Governance -> H Change Management`) proportionally to engagement scope — never generate bloated 300-page shelfware matrices nobody reads!
   - Respect **The Open Group** licensing & copyright boundaries: reference TOGAF 10 concepts, phases, and standard artifacts legitimately without reproducing proprietary full text verbatim.
3. **Business Capability & Value Stream Anchor**:
   - Map applications (`SYS-*`) to stable **Business Capabilities** (what the enterprise does, e.g., *Customer Onboarding*, *Treasury Settlement*, *Claims Processing*) rather than volatile org-chart divisions that reorganize every 18 months.
   - Produce a **Baseline-to-Target Gap Matrix** per domain feeding concrete Transition Architectures (`Plateau 1 -> Plateau 2 -> Target`) directly into `/shadow-pmo` and `/shadow-modernize`.

## 4. Architecture & Implementation
### `ABB` vs `SBB` Enterprise Building-Block Blueprint Table
| ABB-ID | Vendor-Neutral Capability (`ABB`) | Mandatory Standards / NFR Contract | Candidate `SBB` Options (Evaluated Separately) | Target Plateau |
| :--- | :--- | :--- | :--- | :--- |
| `ABB-IAM-01` | Centralized Enterprise IAM & SSO Broker | OIDC 1.0, OAuth2 PKCE, SAML 2.0, FIDO2, JWKS rotation, `99.95%` HA | Keycloak HA (OSS), Auth0, Microsoft Entra ID | Plateau 1 |
| `ABB-API-GW-01` | External & Inter-Agency API Gateway | OpenAPI 3.1, mTLS, Rate Limiting, OTel tracing, SPLP compliant | Kong Gateway, Apache APISIX, Envoy Gateway | Plateau 1 |
| `ABB-EVT-01` | Enterprise Event Streaming & Audit Backbone | At-least-once delivery, schema registry, replay retention `>= 7d` | Apache Kafka / Redpanda, NATS JetStream, RabbitMQ Streams | Plateau 2 |
| `ABB-DWH-01` | Analytical Data Platform & Semantic Layer | SQL/Parquet open formats, RBAC/row-level privacy, lineage | PostgreSQL/ClickHouse, DuckDB + Iceberg, BigQuery | Plateau 2 |

### Strict TypeScript `ABB` Purity & `SBB` Traceability Auditor
```typescript
export interface ArchitectureBuildingBlock {
  readonly abbId: string;
  readonly capabilityName: string;
  readonly standardsContract: readonly string[];
  readonly candidateSbbs: readonly string[];
}

const PROPRIETARY_VENDOR_NAMES_RE =
  /\b(?:Oracle\s+Fusion|SAP\s+S\/4HANA|MuleSoft|Salesforce|Microsoft\s+Entra|AWS\s+Cognito|IBM\s+WebSphere|TIBCO)\b/i;

export function auditAbbVendorNeutrality(
  blocks: readonly ArchitectureBuildingBlock[],
): readonly string[] {
  const violations: string[] = [];
  for (const block of blocks) {
    if (PROPRIETARY_VENDOR_NAMES_RE.test(block.capabilityName)) {
      violations.push(
        `${block.abbId}: ABB capabilityName '${block.capabilityName}' leaks proprietary vendor name; move product choices to candidateSbbs.`,
      );
    }
    if (block.standardsContract.length === 0) {
      violations.push(`${block.abbId}: missing open standards / NFR contract.`);
    }
    if (block.candidateSbbs.length < 2) {
      violations.push(
        `${block.abbId}: evaluate >= 2 candidate SBBs (e.g., OSS vs managed) to avoid single-vendor bias.`,
      );
    }
  }
  return violations;
}
```

## 5. Platform / Vendor Variations
- **Indonesian Commercial Banks (`ATI` / `RSTI` under `POJK 11/2022` & `PADK OJK 1/2026`)**: Align TOGAF 10 Target Architecture Plateaus directly to the bank's 3–5 year `RSTI` (Rencana Strategis TI) and cyber-resilience architecture submitted to OJK (`/shadow-grc`).
- **Multi-Subsidiary BUMN Holdings**: Define holding-level shared `ABB`s (IAM, Data Lakehouse, ERP Core Integration Bus) while letting subsidiaries plug standardized `SBB` adapters into shared integration contracts.

## 6. Decision Matrix & Trade-Offs
| Blueprint Modeling Choice | Strengths | Pitfall to Avoid |
| :--- | :--- | :--- |
| **Capability-Driven `ABB -> SBB` Plateaus** | Survives org restructurings; enables fair competitive RFP bidding | Requires executive discipline to resist vendor sales decks skipping `ABB` |
| **Product-First "Buy Tool X" Roadmap** | Fast vendor demos | Creates vendor lock-in, poor cross-system integration, and inflated 5-year TCO |

## 7. Real Production Scenario
**Context:** A BUMN holding company with 6 subsidiaries drafted an Enterprise Blueprint whose Application Architecture stated *"ABB-01: Deploy Vendor-Z Proprietary ESB across all 6 subsidiaries"*—resulting in a `Rp 18B` single-source tender quote with zero open-standards fallback.
**Intervention:** Reframing the blueprint into vendor-neutral `ABB-API-GW-01` (OpenAPI 3.1, mTLS, OTel, horizontal scaling) and evaluating 3 candidate `SBB`s (Kong OSS, Apache APISIX, Managed Cloud API Gateway) via `/shadow-presales` MCDA + TCO reduced 5-year TCO by `61%` while improving cross-subsidiary onboarding speed.

## 8. Failure Modes & Edge Cases
- **WRONG (Writing concrete proprietary products directly as `ABB` requirements or generating 200-page static TOGAF shelfware disconnected from delivery):** Locks the enterprise into overpriced vendors and gathers dust on a shelf.
  **RIGHT:** Keep every `ABB` strictly vendor-neutral with open interface standards, evaluate `>= 2` candidate `SBB`s fairly, and express Target Architecture as funded Transition Plateaus linked to `/shadow-pmo` & `/shadow-presales`.
- **WRONG (Copying proprietary TOGAF specification prose verbatim):** Violates Open Group copyright boundaries.
  **RIGHT:** Apply TOGAF 10 ADM methodology & original project-specific artifacts citing the standard legitimately.

## 9. Testing & Verification
- Run `python shadow-ea/scripts/ea_portfolio_engine.py --analyze-portfolio <portfolio.json>` and verify every `abb_sbb_gaps` entry separates vendor-neutral `abb_id`/`capability` cleanly from `candidate_sbb`.
- Audit all `ABB` tables with `auditAbbVendorNeutrality` before submitting blueprints to Architecture Review Board (`ARB`).

## 10. Operational Considerations
- Hand approved `ABB` standards contracts directly to `/shadow-architect` (for individual system design compliance) and `/shadow-presales` (for competitive RFP/KAK commercial evaluation).

## 11. Authoritative References
- **The Open Group (2022)** — *TOGAF Standard, 10th Edition (ADM, Enterprise Continuum, Architecture vs Solution Building Blocks)*.
- **Shadow EA Methodology** — [`../methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md`](../methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** TOGAF 10 `ABB`/`SBB` ceremonies for a single small startup MVP — use `/shadow-architect` lightweight Modular Monolith & ADR design instead.
- **Do NOT use** 4-domain TOGAF alone for Indonesian government SPBE engagements — enforce all 6 statutory SPBE domains via [`01-indonesia-6domain-spbe-and-satu-data-interoperability.md`](01-indonesia-6domain-spbe-and-satu-data-interoperability.md).
