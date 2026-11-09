# HYBRID-JSON-MD-SCHEMA — Canonical JSON AST & `.md` Importer Specification

Adapted directly from the battle-tested architecture of `D:\Pekerjaan-Sistem-Analis\Laporan\Laporan-Generator`.

---

## 1. Why Hybrid `.json` + `.md`?

| Layer | File Format | Responsibility |
| :--- | :--- | :--- |
| **Blueprint & Style Rules** | `.md` (`POLA-*.md`, `RULES-*.md`) | Defines chapter structure, tone of voice (formal Indonesian PUEBI/EYD), forbidden words, and formatting standards. |
| **Fast Narrative Authoring** | `.md` (`draft.md`) | Optional quick authoring format for prose, Mermaid diagrams, and simple Markdown tables; converted into `.json` via `doc_scaffold.py md-to-json`. |
| **Canonical Source of Truth** | `.json` (`naskah.json`, `dokteknis/*.json`, `uat.json`) | Strictly validated AST with explicit table column widths (`lebar`), cell alignments (`rata`), numbered evidence files (`bukti`), and metric source attribution (`sumber`). |
| **Compiled Output** | `.docx`, `.xlsx`, `.pdf` | Regenerable binary output. **NEVER edited directly.** |

---

## 2. Canonical Document JSON Schema (`naskah.json` / `dokteknis/*.json`)

```json
{
  "jenis": "srs | prd | dokteknis | bulanan | akhir | uat | manual",
  "judul": "Dokumen Spesifikasi Teknis & Arsitektur Sistem",
  "metadata": {
    "instansi": ["KEMENTERIAN PEKERJAAN UMUM", "SEKRETARIAT JENDERAL", "PUSAT DATA DAN TEKNOLOGI INFORMASI"],
    "proyek": "Pengembangan Sistem Informasi Terpadu",
    "periode": "2026-11",
    "tempat": "Jakarta",
    "istilah_terlarang": ["nama_produk_internal_rahasia", "klien_lain"],
    "pejabat": {
      "pengawas": { "jabatan": "Pejabat Pembuat Komitmen", "nama": "Nama Pejabat", "nip": "198001012005011001" }
    }
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
      "subbagian": [
        {
          "judul": "Spesifikasi Komponen Layanan",
          "blok": [
            {
              "daftar": [
                { "judul": "Layanan Autentikasi", "uraian": "Menggunakan protokol OAuth2 dan JWT RS256." },
                { "judul": "Basis Data Utama", "uraian": "PostgreSQL 16 dengan replikasi baca-saja." }
              ]
            },
            {
              "tabel": {
                "keterangan": "Spesifikasi Modul Sistem",
                "kolom": [
                  { "judul": "Kode", "lebar": 8, "rata": "tengah" },
                  { "judul": "Nama Modul", "lebar": 25, "rata": "kiri" },
                  { "judul": "Target SLA", "lebar": 12, "rata": "tengah" }
                ],
                "baris": [
                  ["MOD-01", "Modul Integrasi API Gateway", "99,9%"],
                  ["MOD-02", "Modul Pelaporan Eksekutif", "99,5%"]
                ]
              },
              "sumber": "Dokumen Kontrak Lampiran A"
            },
            {
              "diagram": {
                "mermaid": "flowchart LR\n  Client[\"Aplikasi Web\"] --> GW[\"API Gateway\"]\n  GW --> DB[(\"PostgreSQL 16\")]",
                "keterangan": "Diagram Alur Arsitektur Sistem"
              }
            },
            {
              "kode": {
                "bahasa": "sql",
                "isi": "SELECT id, status FROM orders WHERE created_at >= CURRENT_DATE;"
              }
            },
            {
              "bukti": [
                {
                  "berkas": "bukti/01-dashboard-utama.png",
                  "keterangan": "Tampilan antarmuka halaman pemantauan utama."
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 3. UAT & Test Case Matrix Schema (`uat-matrix.json` -> `.xlsx` & `.docx`)

```json
{
  "jenis": "uat",
  "judul": "Dokumen User Acceptance Testing (UAT)",
  "metadata": {
    "proyek": "Sistem Manajemen Terpadu",
    "versi": "1.0.0",
    "tanggal_uji": "2026-11-09"
  },
  "kasus_uji": [
    {
      "id": "TC-AUTH-001",
      "modul": "Autentikasi & Otorisasi",
      "prioritas": "P0",
      "tipe": "Positive",
      "prasyarat": "Pengguna memiliki akun aktif dengan peran Admin.",
      "langkah": [
        "Buka halaman login aplikasi.",
        "Masukkan email dan kata sandi yang valid, lalu tekan tombol Masuk."
      ],
      "data_uji": "email: admin@instansi.go.id",
      "hasil_diharapkan": "Sistem mengarahkan pengguna ke halaman Dashboard Utama dan mencatat log sesi.",
      "hasil_aktual": "Sesuai harapan.",
      "status": "PASS",
      "bukti_berkas": "bukti/uat-auth-001.png"
    }
  ]
}
```

---

## 4. Word (`.docx`) & Excel (`.xlsx`) Styling Standards

1. **Explicit UTF-8 Everywhere on Windows**:
   - Every file read/write in Python MUST specify `encoding="utf-8"` so Indonesian characters, em-dashes, and symbols are never corrupted by Windows `cp1252`.
2. **Table Formatting Discipline**:
   - Repeat table header rows across page breaks (`w:tblHeader`).
   - Prevent rows from splitting mid-line across pages (`w:cantSplit`).
   - Keep headings attached to the following paragraph (`keep_with_next = True`).
3. **Validation Gate (`check-readiness`) Before Rendering**:
   - Check that every `paragraf` ends with valid terminal punctuation (`.`, `:`, `)`, `"`).
   - Check that every numeric claim with units (`%`, `ms`, `GB`, `request`, `baris`, `rupiah`) has a `"sumber"` field or is flagged as a warning (`PERINGATAN`).
   - Check that every referenced image in `bukti` exists on disk before building `.docx`.
