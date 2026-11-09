---
name: shadow-doc
description: Enterprise & Government Document Generator (.docx, .xlsx, .pdf) using a Hybrid Dual-Source architecture (.json Canonical AST + .md Importer & Rules) inspired by Laporan-Generator. Use for PRD, SRS, Technical Docs, UAT/TCM Matrices, BAST, Monthly/Final Progress Reports, and User Manuals. Trigger with /shadow-doc.
---

# Shadow Doc (`/shadow-doc`) — Hybrid `.json` + `.md` Document & Report Pipeline

Use this skill whenever the **Monarch** asks to create, update, convert, validate, or generate formal documents (`.docx`, `.xlsx`, `.pdf`), including:
- **System Analyst & Product Specs**: PRD, SRS, Technical Documentation (`arsitektur`, `api`, `model-data`), ADR.
- **Government / Enterprise Progress Reports**: Laporan Pendahuluan, Laporan Bulanan (`bulanan-N`), Laporan Akhir, BAST, KAK/TOR responses.
- **QA & Handover Artifacts**: Test Case Matrix (TCM `.xlsx`), UAT Scenarios & Sign-Off (`.docx` / `.xlsx`), Data Dictionary (`.xlsx`), User Manual Book, SOP / Runbooks.

---

## 1. Non-Negotiable Golden Rules (Adapted from `Laporan-Generator`)

1. **NEVER Edit Binary Outputs Directly (`.docx`, `.xlsx`, `.pdf`)**:
   - All text, tables, diagrams, and styling changes MUST happen in the source `.json` / `.md` files and generator scripts, then be regenerated.
2. **Hybrid Dual-Source Architecture (`.json` Canonical + `.md` Authoring/Importer)**:
   - **`.json` is the Canonical Source of Truth for Rendering**: Structured documents (`penugasan.json`, `kontrak.json`, `dokteknis/*.json`, `uat-matrix.json`) store content as a typed AST (`bagian -> subbagian -> blok`) so table column widths (`lebar`), alignments (`rata`), image manifests (`bukti`), and cross-client term checks (`FORBIDDEN_TERMS`) are validated deterministically before touching Word/Excel.
   - **`.md` is the Fast Authoring & Pattern Layer**: Rules/blueprints (`POLA-*.md`, `RULES-*.md`) and quick narrative drafts can be written in `.md` and converted into the canonical `.json` AST using [`scripts/doc_scaffold.py`](scripts/doc_scaffold.py) (`md-to-json` mode).
3. **Four Anti-Hallucination & Data-Integrity Laws**:
   - **Every number must have a source (`sumber`)**: Never invent dates, ticket IDs, metrics, or achievements to fill a table. If unrecorded, explicitly mark as unrecorded or ask the Monarch.
   - **Failed/partial generation must NEVER overwrite existing valid drafts**: Write outputs atomically; if readiness validation (`GALAT`) fails, abort rendering and preserve the previous `.docx`/`.json`.
   - **Zero truncated sentences**: Always inspect the end of every narrative block (`_potong_di_kalimat` check) — any paragraph not ending in proper punctuation triggers a warning/error.
   - **Zero cross-client leakage (`FORBIDDEN_TERMS`)**: Check all narrative and table blocks against forbidden internal product names and other client names before rendering.

---

## 2. Standard Directory Layout for Document Projects

When scaffolding a new document pipeline in a project (or `docs/laporan/`), structure it cleanly:

```text
docs/
  pola/
    POLA-DOKUMEN.md          # Structural rules, chapter blueprint, and writing style guide
  input/<profil-atau-proyek>/
    metadata.json            # Document title, client/instansi, contract info, pejabat sign-off, FORBIDDEN_TERMS
    naskah.json              # Canonical JSON AST (or bulanan-1.json, dokteknis/arsitektur.json, uat.json)
    draft.md                 # Optional Markdown draft (converted to naskah.json via doc_scaffold.py md-to-json)
    aset/                    # Official client logos (provided by client — never fabricated)
    bukti/                   # Numbered evidence screenshots (01-..., 02-...)
  output/<profil-atau-proyek>/
    *.docx / *.xlsx          # Generated regenerable artifacts (never edited manually)
```

---

## 3. Workflow Execution Steps

1. **Read Schema Reference**:
   - Load [`references/HYBRID-JSON-MD-SCHEMA.md`](references/HYBRID-JSON-MD-SCHEMA.md) for the exact canonical JSON block schema (`paragraf`, `daftar`, `tabel`, `kode`, `diagram.mermaid`, `bukti`) and `.docx`/`.xlsx` formatting rules.
2. **Choose Input Mode**:
   - **If starting from an existing `.md` file or writing a fast narrative draft**: write/update the `.md` file, then run:
     ```powershell
     python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" md-to-json --input draft.md --output naskah.json --jenis dokteknis --judul "Dokumentasi Teknis Sistem"
     ```
   - **If building structured reports, UAT/TCM tables, or multi-period reports**: edit the canonical `.json` directly following `HYBRID-JSON-MD-SCHEMA.md`.
3. **Run Readiness & Integrity Gate (`check-readiness`)**:
   ```powershell
   python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" check-readiness --input naskah.json
   ```
   - Ensure `GALAT = 0` (no missing evidence images, no truncated sentences, no forbidden terms, no empty table structures).
4. **Generate `.docx` / `.xlsx` Artifact**:
   - If the project already has its own renderer (`src/main.py`, `src/lap_pusdatin.py`, `generate-docx.js`), run the project's native generator.
   - Otherwise, use `doc_scaffold.py` (`render-docx` or `render-xlsx`) to compile the validated `.json` into a styled `.docx` or `.xlsx` file.
   - Remind the Monarch: when opening generated `.docx` in Microsoft Word, press `Ctrl+A` then `F9` to refresh Table of Contents (`TOC`) and `SEQ` numbering fields.
