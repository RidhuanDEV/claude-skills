# DOCS-PIPELINE — Technical Writing, API Specs & Source-Driven Document Generation

Use when creating, updating, or automating technical documentation, user manuals, SOPs, ADRs, API collections
(OpenAPI/Bruno), or document generation pipelines (`.md` / structured data → `.docx` / `.pdf` / `.xlsx` / `.html`).

## 1. Golden rule: Source-of-Truth document pipeline

- **NEVER directly edit generated output files (`.docx`, `.pdf`, `.xlsx`, compiled `.html`)**.
- All content, structure, styling rules, and data updates **MUST** be made in the **source files** (`.md`, `.json`,
  `.yaml`, templates, or generator scripts) that serve as the single source of truth, and then **regenerated** via the
  project's generator script/pipeline.
- Before updating a document, locate and inspect:
  1. The base source file(s) (`.md`, data manifests, asset folders).
  2. The generator script or build tool (e.g., Python `python-docx`, Node `docx`, Pandoc, Typst, LaTeX, custom CLI).
  3. Formatting mappings (heading styles, table borders, page breaks, numbering, headers/footers, embedded diagrams).
- After editing the source, run the generator command and verify that the output file builds cleanly without broken
  placeholders, corrupted tables, or missing images.

## 2. Technical writing principles

- **Audience-first**: write differently for **End Users** (task-oriented guides, screenshots, plain language),
  **Developers** (architecture, contracts, setup, copy-pasteable commands, edge cases), and **Operations/Support**
  (runbooks, alerts, rollback steps, troubleshooting decision trees).
- **Accuracy & verification**: every command, file path, env var, endpoint, and payload example in documentation must
  be verified against the actual codebase. Outdated documentation is worse than no documentation.
- **Structure for scanning**: clear title, 2-sentence purpose summary, prerequisites, numbered step-by-step procedures,
  tables for reference data, and callout alerts (`NOTE`, `IMPORTANT`, `WARNING`) used sparingly.

## 3. Document types & templates

- **Architecture Decision Record (ADR)**: `Title | Status (Proposed/Accepted/Superseded) | Context & Problem | Options Considered | Decision | Consequences (Trade-offs)`.
- **Runbook / SOP**: `Trigger / Symptom | Impact | Pre-checks | Step-by-Step Resolution Commands | Verification | Rollback / Escalation`.
- **API Documentation (OpenAPI / Bruno / Markdown)**:
  - Keep OpenAPI specs (`.yaml`/`.json`) and Bruno/Postman collections in sync with backend controllers and DTOs.
  - Document authentication headers, rate limits, pagination parameters, realistic request/response examples, and
    exact error envelopes with status codes.
- **Release Notes / Changelog**: group by `Added`, `Changed`, `Fixed`, `Deprecated`, `Removed`, `Security`, and
  highlight **Breaking Changes & Migration Steps** at the top.

## 4. Diagrams as code

- Prefer text-based, version-controlled diagrams (**Mermaid**, PlantUML, D2) inside Markdown sources over static
  uneditable screenshots whenever the pipeline supports them.
- Mermaid syntax discipline:
  - Use supported diagram types (`flowchart TD/LR`, `sequenceDiagram`, `stateDiagram-v2`, `classDiagram`, `erDiagram`).
  - Quote node labels that contain parentheses, brackets, colons, or special characters: `id["Process (Step 1)"]`.
  - Keep diagrams focused (max ~15–20 nodes per diagram; split overview vs detailed sub-flows).
- When generating `.docx`/`.pdf` outputs that require raster/vector images, render diagrams programmatically as part
  of the build pipeline (e.g., `mmdc` / Mermaid CLI or script renderer) rather than manually screenshotting.

## 5. Building maintainable `.docx` / `.pdf` generator scripts

When writing or refactoring document generator scripts (Node `docx`, `python-docx`, Pandoc filters, etc.):
- **Separate content from presentation**: parse structured Markdown/YAML/JSON content into an AST or typed model; keep
  fonts, colors, margins, heading levels, and table styles in a centralized theme/config module.
- **Consistent styling**: define reusable helpers for Title, Heading 1–4, Body Paragraph, Bullet/Numbered Lists, Code
  Blocks (monospace, shaded background), Callout Boxes, and Data Tables (header row shading, repeat header across pages,
  explicit column widths).
- **Idempotent builds**: running the generator twice on the same source must produce a clean overwrite without
  leftover temp files or duplicate sections. Clean up unused helper functions and dead template blocks when refactoring.

## 6. Checklist

Edited source (`.md`/base resource) instead of `.docx` output · generator executed and verified · commands/paths/contracts
verified against repo · diagrams valid and quoted · tables formatted cleanly · audience appropriate · breaking changes
and prerequisites explicit.

## 7. Anti-patterns

Manually editing `.docx` output so the next build overwrites the changes · hardcoding paragraphs inside a 2,000-line
generator script instead of reading `.md` sources · documenting guessed API fields not present in the controller/DTO ·
unquoted special characters breaking Mermaid rendering · walls of prose where a table or sequence diagram is clearer.
