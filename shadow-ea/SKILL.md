---
name: shadow-ea
description: "Use when mapping enterprise IT portfolios, TOGAF, SPBE, TIME rationalization, or cross-system roadmaps. Not for one app (/shadow-architect)."
---

# `/shadow-ea` — Enterprise Architecture & IT Portfolio Intelligence

Use this skill whenever the **Monarch** invokes `/shadow-ea`, designs multi-system enterprise blueprints, rationalizes redundant application portfolios, constructs **Arsitektur SPBE** (government 6-domain blueprints), or leads Architecture Review Board / Design Authority compliance reviews.

Integrates with [`shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md`](../shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md) and deep methodologies:
- [`methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md`](methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md) — Business Capability & Value Stream Mapping, TIME Application Portfolio Rationalization, Data Ownership & Satu Data Interoperability, ABB vs SBB, and explicit **TOGAF 4-Domain <-> SPBE 6-Domain Crosswalk**.
- [`playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md`](playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md) — Capability Heatmap, Application Portfolio Catalog, Integration Matrix, Baseline-to-Target Gap Matrix, Architecture Compliance Assessment, and Investment Priority Matrix.

---

## 1. Execution Contract

1. **TOGAF <-> SPBE 6-Domain Precision**:
   - In private/BUMN/banking enterprise contexts, apply **TOGAF 10 ADM** (`Preliminary`, `Phase A–H`, `Requirements Management`) across Business, Data, Application, and Technology domains, respecting Open Group licensing boundaries (no verbatim full-text reproduction).
   - In Indonesian Government engagements (**Perpres 95/2018** & **Perpres 132/2022**), ALWAYS explicitly model **all 6 SPBE Architecture Domains**: `1. Proses Bisnis`, `2. Data dan Informasi`, `3. Infrastruktur SPBE`, `4. Aplikasi SPBE`, `5. Keamanan SPBE`, `6. Layanan SPBE`, plus **Satu Data Indonesia (`Perpres 39/2019`)** interoperability.
2. **Portfolio Rationalization (`TIME`) & Duplicate Detection**:
   - Map every application (`SYS-*`) to Business Capabilities & Data Owners, flagging overlapping capabilities (`ELIMINATE`/`MIGRATE` candidates) with traceable IDs feeding `/shadow-modernize`, `/shadow-grc`, `/shadow-presales`, and `/shadow-pmo`.
3. **Architecture Building Blocks (`ABB`) vs Solution Building Blocks (`SBB`)**:
   - Separate vendor-neutral capability requirements (`ABB`, e.g., *Centralized IAM & OIDC Broker*) from concrete chosen products/implementations (`SBB`, e.g., *Keycloak HA Cluster*).

---

## 2. Deterministic EA Portfolio & SPBE Validator

```powershell
python "shadow-ea/scripts/ea_portfolio_engine.py" --self-test
python "shadow-ea/scripts/ea_portfolio_engine.py" --analyze-portfolio path/to/portfolio.json
```

## 3. Document Rendering Boundary (`SA-DOC-ENGINE-001`)

- `/shadow-ea` owns TOGAF 10, 6-Domain SPBE, TIME rationalization, and ABB/SBB modeling; NEVER duplicate document renderers.
- Route formal `ARCHITECTURE_REPORT` blueprints through `shadow-doc/scripts/doc_orchestrator.py` (existing repo generator first, or Global Engine via `domain_adapters.py::adapt_pmo_or_ea_payload`).

## Reference Guide

Load only the specific playbook or methodology matching your active Enterprise Architecture subtask:

| Task / Scenario | Load Reference |
| :--- | :--- |
| Indonesia 6-Domain SPBE (`Perpres 95/2018 & 132/2022`), Satu Data (`Perpres 39/2019`), `Wali Data` & `SPLP` Interoperability | [references/01-indonesia-6domain-spbe-and-satu-data-interoperability.md](references/01-indonesia-6domain-spbe-and-satu-data-interoperability.md) |
| TOGAF 10 ADM Tailoring, Capability Mapping & Strict Vendor-Neutral `ABB` vs Concrete `SBB` Separation | [references/02-togaf-10-adm-and-abb-vs-sbb-separation.md](references/02-togaf-10-adm-and-abb-vs-sbb-separation.md) |
| TIME Portfolio Rationalization, Duplicate Capability Detection (`EA-DUP-*`) & Architecture Review Board (`ARB`) Governance | [references/03-time-portfolio-rationalization-and-arb-governance.md](references/03-time-portfolio-rationalization-and-arb-governance.md) |
| Deep Methodology & EA Templates | [methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md](methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md) & [playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md](playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md) |
| Deterministic EA Portfolio Validator & Specialist Eval Suite | [scripts/ea_portfolio_engine.py](scripts/ea_portfolio_engine.py) & [evaluations.md](evaluations.md) |

Do not load unrelated references unnecessarily.
