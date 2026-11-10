# HYBRID-JSON-MD-SCHEMA — Canonical JSON AST v2.0 & Legacy v1.0 Reference

Adapted from `D:\Pekerjaan-Sistem-Analis\Laporan\Laporan-Generator` and upgraded to **Shadow-Doc v2.0** (`schemas/canonical-document.schema.json`).

---

## 1. Why Hybrid `.json` + `.md`?

| Layer | File Format | Responsibility |
| :--- | :--- | :--- |
| **Blueprint & Templates** | `.md` (`templates/01..20.md`, `POLA-*.md`) | Defines chapter structure, tone of voice (`id-ID` / `en-US`), placeholders (`[ISI ...]`), and formatting standards. |
| **Fast Narrative Authoring** | `.md` (`draft.md`) | Quick authoring format for prose, Mermaid diagrams, and Markdown tables; imported into Canonical AST v2.0 via `doc_scaffold.py import` (or legacy v1 via `md-to-json`). |
| **Canonical Source of Truth (v2.0)** | `.json` (`schemas/canonical-document.schema.json`) | Strictly validated AST with block-level IDs (`FR-001`, `TBL-001`), `trace_ids`, `source_refs`, `history[]`, `signoff_record[]`, and SHA-256 `semantic_hash`. |
| **Compiled Output** | `.docx`, `.pdf`, `.xlsx`, `.csv`, `.zip` | Regenerable binary output. **NEVER edited directly.** |

---

## 2. Canonical Document JSON AST v2.0 (`schema_version: "2.0"`)

```json
{
  "schema_version": "2.0",
  "document_id": "PRJ-SRS-001",
  "project_id": "PRJ-2026",
  "document_type": "SRS",
  "title": "Software Requirements Specification",
  "revision": "0.1-DRAFT",
  "app_version": "1.0.0",
  "status": "DRAFT",
  "language": "id-ID",
  "classification": "INTERNAL",
  "style_profile": "corporate",
  "owner": "Lead System Analyst",
  "reviewers": ["Security Architect"],
  "approvers": ["VP Engineering"],
  "created_at": "2026-11-10T05:00:00Z",
  "updated_at": "2026-11-10T05:00:00Z",
  "supersedes": null,
  "forbidden_terms": ["OtherClientName"],
  "sources": [
    {
      "source_id": "KAK-2026",
      "reference": "docs/KAK-Bab-II.pdf",
      "verified_at": "2026-11-10T05:00:00Z",
      "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "blocks": [
    {
      "id": "SEC-1",
      "kind": "heading",
      "level": 2,
      "title": "1. Kebutuhan Fungsional",
      "body": null,
      "source_refs": ["KAK-2026"],
      "trace_ids": []
    },
    {
      "id": "FR-001",
      "kind": "paragraph",
      "title": "Autentikasi OAuth2 & Passkey",
      "body": "Sistem wajib menyediakan autentikasi OAuth2/OIDC dengan dukungan passkey FIDO2.",
      "source_refs": ["KAK-2026"],
      "trace_ids": ["SDD-001", "TC-001", "UAT-001"],
      "status": "APPROVED"
    }
  ],
  "history": [
    {
      "revision": "0.1-DRAFT",
      "reason": "Initial draft",
      "changed_by": "Lead System Analyst",
      "changed_at": "2026-11-10T05:00:00Z",
      "approval_ref": null
    }
  ],
  "signoff_record": [
    {
      "role": "Approver",
      "identity": null,
      "decision": "PENDING",
      "timestamp": null,
      "evidence_ref": null
    }
  ],
  "unmapped_blocks": []
}
```

---

## 3. Legacy v1.0 JSON Schema (`bagian -> subbagian -> blok`) — Preserved for Backward Compatibility

Legacy v1.0 files (`jenis`, `judul`, `bagian`) remain 100% supported by `doc_scaffold.py check-readiness` and can be migrated to v2.0 at any time using:

```powershell
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" migrate-v1 --in legacy.json --project-id PRJ-2026 --doc-id DOC-001 --out migrated_v2.json
```

(Automatically creates `legacy.v1.bak.json` and preserves the original `bagian` array under `legacy_v1_bagian`).

```json
{
  "jenis": "srs | prd | dokteknis | bulanan | akhir | uat | manual",
  "judul": "Dokumen Spesifikasi Teknis & Arsitektur Sistem",
  "metadata": {
    "instansi": ["KEMENTERIAN PEKERJAAN UMUM"],
    "proyek": "Pengembangan Sistem Informasi Terpadu",
    "istilah_terlarang": ["nama_produk_internal_rahasia"]
  },
  "bagian": [
    {
      "judul": "Pendahuluan",
      "blok": [
        {
          "paragraf": "Dokumen ini menjabarkan arsitektur dan spesifikasi teknis sistem secara menyeluruh.",
          "sumber": "KAK Bab II Ruang Lingkup Pekerjaan"
        }
      ],
      "subbagian": []
    }
  ]
}
```

---

## 4. Multi-Format Rendering & Visual QA Standards (`.docx`, `.pdf`, `.xlsx`, `.csv`, `.md`)

1. **Explicit UTF-8 Everywhere on Windows**:
   - Every file read/write in Python specifies `encoding="utf-8"`.
2. **Word (`.docx`) Pagination & Typography**:
   - Supports `corporate` (`Calibri` 11pt) and `institutional` (`Times New Roman` 12pt) profiles, A4 portrait or landscape (`RTM`), running headers/footers, native Word TOC field (`TOC \o "1-3"`), repeating table headers (`w:tblHeader`), non-splitting rows (`w:cantSplit`), and heading attachment (`keep_with_next = True`).
3. **Excel (`.xlsx`) Register Standards**:
   - Generates 4 standardized worksheets: `README_Metadata`, `Register_Data` (frozen header row `A2`, auto-filter, status dropdown validation), `Traceability_Links`, and `Data_Dictionary`.
4. **PDF (`.pdf`) Standards**:
   - Native offline rendering via `fpdf2` with running headers, page `X/{nb}` footers, PDF section bookmarks/outlines, and wrapped tables.
