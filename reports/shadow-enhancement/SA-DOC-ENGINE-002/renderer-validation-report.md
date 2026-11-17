# SA-DOC-ENGINE-002 — Renderer Validation & Diagram Hardening Report (`R06`, `R07`, `H01`)

Generated: 2026-11-17

## 1. Format-Specific Verification (`R06`)
Upgraded `shadow-doc/scripts/v2_renderers.py::verify_rendered_outputs_qa`:
- **PDF (`pypdf.PdfReader`)**: Parses generated PDF, verifies `pdf_pages >= 1`, extracts text across pages, and checks `document_id`, `revision`, and heading strings are extracted cleanly (`T53`, `T56`).
- **DOCX (`zipfile` + `python-docx`)**: Verifies OOXML ZIP structure (`[Content_Types].xml`, `word/document.xml`), `core_properties` metadata, heading styles, table counts (`>= 2`), and content parity (`T25`, `T53`).
- **HTML (`HTMLParser` + escaping)**: Validates `<!DOCTYPE html>`, required semantic tags, expected headings, HTML escaping of `<script>` XSS payloads (`&lt;script&gt;`), and `0` unintended external `http(s)://` URLs (`T26`, `T30`, `T53`).

## 2. Diagram Asset Rendering Boundary (`R07`)
Upgraded `render_diagram_asset(...)`:
- Executes argument arrays (`shell=False`) in isolated temporary directories with bounded timeout (`timeout_sec=10`), validating `.svg` (`<svg`) and `.png` (`\x89PNG`) signatures.
- Explicitly separates `RENDERED`, `RENDER_FAILED`, `RENDER_TIMEOUT`, `CLI_MISSING`, `CLI_DETECTED_NOT_ATTEMPTED`, and `FALLBACK_SOURCE_PRESERVED`.
- `dbml2sql` (SQL transpiler) is never misclassified as a DBML image renderer (`cli_tool: None` for image asset rendering unless a diagram CLI override is supplied).

## 3. Unicode PDF Rendering (`H01`)
- `_discover_unicode_pdf_fonts()` discovers host OS Unicode TTF fonts cleanly at runtime (`arial.ttf`, `segoeui.ttf`, `consola.ttf`, `DejaVuSans.ttf`) without bundling proprietary font binaries into the repository.
- Tested via `T56` (`Bahasa Indonesia`, `€100`, `£80`, `≤`, `±5%`, `α`, `β`, `∑`, `—`) and verified verbatim via `pypdf` extraction (`PASS`).
- Graceful fallback to Helvetica + `_ascii_clean` preserved when a host lacks system TTF fonts.
