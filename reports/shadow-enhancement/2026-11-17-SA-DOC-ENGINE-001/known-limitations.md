# SA-DOC-ENGINE-001 — Known Limitations & Unresolved Issues

1. **PDF Non-ASCII Character Normalization (`fpdf2`)**:
   - The bundled `fpdf2` renderer uses core `Helvetica` / `Courier` fonts with `_ascii_clean`, which strips or normalizes non-ASCII Unicode glyphs (e.g., em-dashes, curly quotes) rather than bundling multi-megabyte TTF Unicode fonts offline. Explicitly disclosed in `RENDERER_CONTRACTS["pdf"]["limitations"]`.
2. **External Diagram Vector Rendering (`mmdc`, `dbml2sql`)**:
   - Mermaid and DBML diagrams are always preserved verbatim in Canonical AST, Markdown, HTML (`<pre class="mermaid|dbml">`), DOCX, and PDF. Native SVG/PNG rasterization depends on external tools (`mmdc` / `@dbml/cli`) if installed in the host environment; when absent, `render_diagram_asset` reports `FALLBACK_SOURCE_PRESERVED` cleanly without corrupting documents.
3. **Microsoft Word Dynamic TOC Page Numbers**:
   - Native OOXML `TOC \o "1-3"` fields embedded in `.docx` output require pressing `Ctrl+A` then `F9` inside Microsoft Word to populate page numbers on first open (documented in `RENDERER_CONTRACTS["docx"]["limitations"]` and `shadow-doc/SKILL.md`).
4. **XLSX Sheet Scope**:
   - `render_v2_to_xlsx` excels at tabular registers (`table` blocks -> `Register_Data`, `Traceability_Links`, `Data_Dictionary`), rather than long-form prose chapters (`docx`/`pdf`/`html`/`md`).
5. **Global Sync & Remote Git Push**:
   - Per User Intent Boundary (`L4`), local repo edits do not modify `~/.claude`, `~/.gemini`, `~/.codex`, or `origin/main` until `./install.ps1` and `git push` are explicitly authorized.
