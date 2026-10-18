# sub-SPECS-DOCX-CODE — Authoring Rules for OpenAPI 3.1, DBML, Strict Mermaid & `.docx` Generators

Use when writing formal technical specifications (OpenAPI, DBML, Mermaid diagrams) or implementing automated
document generator scripts (`python-docx`, Node `docx`, Pandoc) that compile `.md` / data sources into `.docx` / `.pdf`.

## 1. OpenAPI 3.1 (`openapi.yaml`) authoring rules

- **Reusable components**: define shared schemas, error envelopes, pagination metadata, and security schemes under
  `components/schemas`, `components/responses`, and `components/securitySchemes` — never duplicate inline schemas across paths.
- **Exact nullability & constraints**:
  - In OpenAPI 3.1, represent nullable fields as `type: ["string", "null"]`.
  - Always specify `required: [...]` arrays explicitly on every object schema; unstated properties are optional by default.
  - Include `format` (`uuid`, `date-time`, `email`, `int64`), `minimum`/`maximum`, `minLength`/`maxLength`, and `enum` values
    matching the backend DTO validator.
- **Operation completeness**: every path operation defines a unique `operationId`, `tags`, `summary`, `security`, typed
  `requestBody` (with realistic `examples`), `200`/`201`/`204` success schema, and `400`/`401`/`403`/`404`/`409`/`422` error responses.

## 2. DBML (Database Markup Language) authoring rules

When documenting or designing relational schemas in `.dbml`:
- Declare explicit column types (`uuid`, `varchar(255)`, `timestamptz`, `numeric(18,2)`), constraints (`[pk]`, `[not null]`,
  `[unique]`, `[default: `now()`]`), and `[note: '...']` for business invariants.
- Define foreign keys with explicit relationship syntax (`Ref: order_items.order_id > orders.id [delete: restrict]`).
- Include an `Indexes` block inside each `Table` showing single-column, composite, and unique partial indexes.

## 3. Strict Mermaid diagram authoring rules

To prevent syntax and rendering failures across Markdown viewers and `.docx`/`.pdf` pipelines:
- **Only use standard, deterministic diagram headers**: `flowchart TD`, `flowchart LR`, `sequenceDiagram`, `stateDiagram-v2`,
  `classDiagram`, `erDiagram`.
- **Always quote node labels containing special characters**: parentheses `()`, brackets `[]`, braces `{}`, colons `:`,
  slashes `/`, or semicolons `;` MUST be wrapped in double quotes:
  - Good: `API["POST /api/v1/orders (Auth Required)"] --> SVC["OrderService.create()"]`
  - Bad (breaks parser): `API[POST /api/v1/orders (Auth Required)] --> SVC[OrderService.create()]`
- **No raw HTML tags** (`<br/>`, `<b>`) inside labels when targeting multi-renderer pipelines; use newline or concise phrasing.
- **ER Diagram syntax**: declare attribute type, name, key (`PK`, `FK`, `UK`), and quoted comment:
  ```mermaid
  erDiagram
    ORDERS ||--|{ ORDER_ITEMS : "contains"
    ORDERS {
      uuid id PK "Primary key"
      uuid customer_id FK "References customers.id"
      varchar status "DRAFT | PAID | CANCELLED"
      numeric total_amount "Minor units or numeric(18,2)"
    }
  ```

## 4. `python-docx` & Node `docx` generator code rules

Remember the golden rule: **never edit `.docx` output files directly; always update the `.md` / base source and run the generator**.
When writing or maintaining the generator script itself:
- **Architecture**:
  1. **Source Parser**: read the `.md` / YAML / JSON source file(s) with explicit `encoding="utf-8"`.
  2. **Theme / Style Registry**: centralize font family (`Arial` / `Calibri` / `Times New Roman`), font sizes (`Pt`),
     brand hex colors (`RGBColor`), page margins, and line spacing in one configuration constant/module.
  3. **Element Builders**: dedicated, pure helper functions for `add_styled_heading()`, `add_body_paragraph()`,
     `add_bullet_item()`, `add_code_block()`, `add_callout_box()`, and `add_formatted_table()`.
- **Table quality rules in `.docx`**:
  - Always set header row background shading, bold header text, cell padding/margins, explicit column widths, and
    `tblHeader` (repeat header row across page breaks) + `cantSplit` (prevent a single row from splitting awkwardly mid-line).
- **Heading & Page Break discipline**:
  - Set `keep_with_next = True` on all headings so a heading is never stranded alone at the bottom of a page.
  - Clean up any temporary rendered chart/diagram PNGs in a `finally` block or dedicated build cache folder, and remove
    dead helper functions when refactoring the generator.
