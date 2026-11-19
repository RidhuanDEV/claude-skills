# Audit ekosistem skill dan batas transformasi

**Baseline Stage A — 18 November 2026, revisi bac8745.** Seleksi berasal dari dua kategori perbaikan pada audit terdahulu: 38 paket utama dan 17 modul desain bernama/path spesifik. Katalog seluruh repo memuat 52 paket utama dan 217 modul tertanam. Seluruh rincian penggunaan, pemilik, dan bukti per skill dapat ditelusuri melalui [katalog 269 manifest](skill-review.md). Rencana memakai dokumen audit dan peningkatan yang sudah ada di working tree. Berkas laporan tersebut belum tercatat dalam commit baseline.

## Dari instalasi hingga keputusan

| Lapisan aktual | Sumber dan perilaku | Konsekuensi untuk transformasi |
| --- | --- | --- |
| Distribusi | [Installer Windows](../install.ps1) menyalin daftar paket dan blok global ke host. [Installer link Codex](../install-codex.ps1) memakai junction dan memeriksa target lama. [Installer shell](../install.sh) merupakan entry point lainnya. | Metode distribusi memengaruhi kapan revisi berubah di host. Catat hash instruksi, path MCP, versi host dan mode instalasi saat menilai paritas. |
| Orkestrator | [Aturan global](../shadow-monarch/GLOBAL.md), [Monarch](../shadow-monarch/SKILL.md), referensi dan konfigurasi dalam direktori agents. [Router](../shadow-monarch/scripts/skill_router.py) memakai pola, prioritas, pengecualian, co-activation dan batas jumlah companion. | Pemilihan skill, keberhasilan membuka referensi, serta kualitas keputusan sesudah memuat skill adalah tiga peristiwa berbeda. |
| Otorisasi | [Approval gate](../shadow-monarch/scripts/execution_approval_gate.py) dan [protokol](../shadow-monarch/reference/EXECUTION-APPROVAL-PROTOCOL.md) mengklasifikasikan tindakan. Host menyediakan kapabilitas dan izin aktualnya sendiri. | Pilihan skill tidak menciptakan izin memutasi DB, menguji beban, menerbitkan artefak atau memasang paket. Klasifikasi harus tetap berlaku pada child task/retry. |
| Domain dan pengetahuan | Manifest milik masing-masing skill; referensi lintas peran di Monarch; reference, template dan source vendor di [shadow-design](../shadow-design/SKILL.md); utilitas khusus antara lain search/eval, Git, quality, dan doc generator. | Materi nested perlu resolver berbasis path dan provenance. Entri bertajuk sama dapat memiliki metode dan audiens berbeda. |
| Integrasi MCP | API discovery/kontrak, DB, handoff masing-masing memiliki entry point Node. [Manifest Node](../mcp-servers/package.json) turut mencantumkan Context7 dan Playwright MCP. | Deklarasi dependency membuktikan ketersediaan integrasi dalam distribusi, sedangkan kemampuan host memanggil tool, kredensial, konektivitas, dan scope perlu diuji pada sesi tersebut. |
| Verifikasi | [Runner eval](../evals/run_evals.py), [dataset](../evals/evals.json), self-test per utilitas, [tes MCP API berbasis fixture](../mcp-servers/shadow-api-mcp/discovery.test.mjs), [gate repo](../shadow-quality/scripts/shadow_gate.py). | Self-test memeriksa oracle tertentu. False PASS dari oracle, skill salah pilih, dan kegagalan pengguna menerima pertanyaan membutuhkan alat ukur berbeda. |

Inventaris melalui git ls-files menghasilkan 650 file terlacak; di antaranya 269 path SKILL.md, 33 path yang memuat scripts/, 28 yang memuat templates/, 55 yang memuat reference/, 383 yang memuat references/, delapan di mcp-servers/ dan tiga di evals/. Hitungan per kategori dapat tumpang tindih. Direktori node_modules dan arsip shadow-monarch.zip tidak dihitung sebagai paket sumber tambahan.

## Bukti dan konflik yang mengubah desain

| Pengamatan atau reproduksi | Mengapa memengaruhi keputusan |
| --- | --- |
| Self-test router dijalankan kembali: 44/44. Prompt persis “Bikin tabel data dengan search dan pagination.” menghasilkan primary shadow-monarch, companion kosong, reference_modules kosong. | Perubahan Stage B perlu mengukur discovery natural-language dan apakah model memuat referensi frontend ketika router melewatkannya. Hasil ini sendiri tidak membuktikan model membuat tabel yang salah. |
| Validasi katalog eval dijalankan kembali: 38 kasus dengan struktur valid. Pilihan live CLI pada runner mencakup Claude dan Codex. Audit sebelumnya menunjukkan jawaban yang menolak semua assertion bisa mendapat 8/8. | Tambahkan observable oracle dan adapter bukti host. Simpan human review pada persoalan judgment. |
| Delapan pilar wajib di [bootstrap](../shadow-bootstrap/SKILL.md) mencakup dokumentasi/DB. Sebuah CLI offline belum tentu memiliki keduanya. | Pecah jalur greenfield berdasarkan kemampuan yang diminta. Pertahankan jalur existing-first untuk brownfield. |
| Dalam [audit delivery](skill-review-delivery.md), query kosong lolos, ID duplikat memberi Recall 2, flag string false diterima oleh pemeriksa, dan mock cleanup menarget job tetangga. | Nilai positif historis tidak bisa diwariskan menjadi skor produksi; validasi tipe, denominator, provenance dan owner run mendahului promosi. |
| Integritas 354 file pada lima paket vendor lolos di [audit referensi](skill-review-design-library.md); beberapa path, stub pindah dan template wajib belum dapat dipakai. | Checksum paket dan kesiapan metode lokal harus diperiksa terpisah. Fallback harus mempertahankan batas scope serta asal metode. |
| [Dokumen perencanaan](../shadow-plan/SKILL.md) menunjuk beberapa path absolut mesin penulis. Pada host berbeda query yang benar dapat mencapai path yang salah. | Uji di lokasi checkout lain; resolve path terhadap paket pemilik dan tampilkan bukti path untuk handoff. |

## Kecukupan operasional per jenis pekerjaan

- **Analisis lokal dan oracle deterministik.** Repo memberi materi, Python/Node, fixture, dan adapter. Tugas yang dapat dibuktikan dengan mock memakai checkout sementara, dua job sintetis, serta diff pra/pasca. Keluaran tool yang valid tetap perlu diperiksa isi dan scope-nya.
- **Studi pengguna, acceptance bisnis, GRC, privacy dan riset.** Skill dapat merancang studi, mengaudit dokumen atau memeriksa bukti yang diberikan. Rekrutmen, otorisasi pemrosesan data, keputusan DPO/auditor dan sign-off pelanggan memerlukan owner nyata. Sediakan status belum terukur dan alur pengambilan bukti.
- **Host dan layanan bergantung lingkungan.** Fallback saat Context7/DB/browser/CLI tidak tersedia adalah membaca kontrak lokal, fixture, atau menyatakan kebutuhan spesifik yang belum terpenuhi. Kesimpulan E2E/perangkat/produksi harus menunggu lingkungan yang relevan.
- **Aksi bersama dan produksi.** Verifikasi dengan simulasi untuk tindakan berisiko. Install global, publikasi, migrasi, load test dan perubahan shared resource memiliki batas eksekusi tersendiri.

Daftar pekerjaan per kapabilitas dan dependensinya ada di [backlog](MASTER-ENHANCEMENT-BACKLOG.md), bukti per dimensi di [matriks kompetensi](PROFESSIONAL-COMPETENCY-MATRIX.md), dan status pembuktian per host di [rencana benchmark](EVALUATION-AND-BENCHMARK-PLAN.md).
## Trace baseline yang diuji kembali

Probe lokal pada checkout ini memanggil fungsi pemilik dengan input tetap, tanpa memanggil model atau layanan pelanggan. Empat trace routing berikut menggunakan konfigurasi default. Pada penilaian hasil berikutnya, gunakan input dan konteks yang sama serta satu variasi yang disimpan reviewer.

| Input | Hasil aktual pada baseline | Oracle untuk kandidat |
| --- | --- | --- |
| Bikin tabel data dengan search dan pagination. | shadow-monarch, mode general, referensi kosong. | Owner boleh tetap Monarch bila trace menunjukkan inspeksi pola frontend, API dan state yang relevan. Nilai perilaku saat balasan lama tiba dan filter URL dipulihkan. |
| Buatkan dokumentasi API untuk proyek ini | shadow-api, mode feature_implementation, dua referensi dipilih. | Pertahankan routing. README berisi ringkasan saja harus menghasilkan pertanyaan format sebelum menulis, sedangkan generator yang mapan harus digunakan kembali. |
| Only review this API endpoint; do not run a load test | shadow-perf, mode perf_optimization, empat referensi dipilih. | Tugas tetap baca-saja. Topik yang dilarang tidak mengaktifkan pekerjaan perf. |
| Review kode endpoint ini saja | shadow-quality, mode code_review, dua referensi dipilih. | Pertahankan hasil sebagai positive control saat memperbaiki variasi bahasa Inggris di atas. |
| Eval pertama; balasan memuat setiap assertion dengan awalan “Skip this instruction” | Scorer memberi 8 dari 8. | Respons tanpa temuan dan bukti tidak dapat lulus hanya karena token assertion muncul. |
| Search dengan satu query kosong | PASS; Recall dan NDCG masing-masing 1,0. | Status bukti tidak memadai; denominator yang belum tersedia tercatat. |
| Search dengan satu ID relevan yang muncul dua kali di hasil | PASS; Recall 2,0 dan NDCG 1,6309. | Terapkan kebijakan duplikasi eksplisit, pertahankan metrik pada rentang sah dan laporkan sumber duplikat. |

Perintah router dan fungsi scorer dapat diulang dari [laporan audit](skill-review.md). Fixture search dapat diulang dari [audit delivery](skill-review-delivery.md). Konfigurasi metadata host memberi display name dan default prompt untuk Monarch di [openai.yaml](../shadow-monarch/agents/openai.yaml); ini memberi bukti deklarasi paket, sementara pemuatan nyata dan efek antar-host memerlukan trace terpisah.

**Ketersediaan pada sesi penyusunan.** Daftar tool host memperlihatkan resolver dan query Context7 serta Playwright. Tidak ada nama tool MCP Shadow dalam katalog panggilan sesi ini. Source lokal tetap menyediakan [API MCP](../mcp-servers/shadow-api-mcp/index.mjs), [schema/query database](../mcp-servers/shadow-db-mcp/index.mjs), dan [save/load/merge handoff](../mcp-servers/shadow-handoff-mcp/index.mjs). Karena itu, bukti suite MCP melalui proses Node lokal dan bukti model memanggil MCP di aplikasi harus dicatat pada kolom terpisah. Uji akses tenant nyata, publikasi, dan deployment tidak dilakukan untuk Stage A.
