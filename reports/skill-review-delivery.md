# Audit skill Shadow Army untuk operasi, delivery, dan konsultansi

Audit 28 skill tingkat atas dari `shadow-ea` sampai `shadow-uat` pada revisi `bac8745`. Pengguna laporan ini adalah maintainer yang memutuskan perubahan instruksi, pemeriksaan, dan routing. Label menilai kontrak dan alat yang ditinjau. Contoh usulan dalam setiap entri adalah kriteria penerimaan untuk perbaikan mendatang.

**ALREADY GOOD** berarti alur inti memiliki pembagian tanggung jawab atau bukti yang mendukung penggunaan terfokus. **NEED IMPROVEMENT** menunjukkan batas cakupan, dokumentasi, atau verifikasi yang perlu diperbaiki. **TOO BAD NEED MANY IMPROVEMENT** diberikan jika alat inti dapat menghasilkan keyakinan palsu tentang bukti kosong/tidak sah, cakupan perjalanan pengguna, atau kepemilikan sumber daya lintas pekerjaan. Penilaian ini pada perilaku yang ditunjukkan, bukan sertifikasi produk pengguna. Bukti berupa pembacaan sumber, tes bawaan, dan contoh tandingan lokal. Pengujian di perangkat, CI perusahaan, produksi, dan percakapan live lintas host belum diukur.

## Katalog dan keputusan

### shadow-ea — ALREADY GOOD

Menilai duplikasi aplikasi, kesenjangan kapabilitas, serta kandidat ABB/SBB agar pemilik portofolio dapat memutuskan investasi.

**Dasar klasifikasi.** Profil sektor memang mengubah validasi. Self-test 8/8 mencakup perusahaan umum yang boleh melewati pemeriksaan SPBE dan gap ABB tanpa kandidat yang ditolak. [Instruksi](../shadow-ea/SKILL.md) · [Implementasi](../shadow-ea/scripts/ea_portfolio_engine.py)

**Perbaikan dan cara menguji.** Pertahankan cabang sektor. Minta pemilik integrasi memvalidasi satu dependensi sebelum mengarsipkan aplikasi yang tampak duplikat. Tambahkan contoh permintaan Indonesia tentang portofolio ke router.

### shadow-eval — TOO BAD NEED MANY IMPROVEMENT

Membantu tim retrieval dan tim pembuat jawaban mengevaluasi sitasi, cakupan konteks, dan isolasi tenant secara terpisah.

**Dasar klasifikasi.** Self-test 9/9. Namun satu sampel kosong menghasilkan skor sempurna pada ketiga ukuran dan gate_passed=True. Nilai bawaan untuk komponen yang tidak terukur membuat dataset tanpa bukti tampak lulus. [Instruksi](../shadow-eval/SKILL.md) · [Implementasi](../shadow-eval/scripts/ai_eval_gate.py)

**Perbaikan dan cara menguji.** Wajibkan skema per jenis sampel, hitung cakupan denominator, dan laporkan INSUFFICIENT_EVIDENCE. Simpan evaluasi penolakan jawaban terpisah dari evaluasi retrieval biasa. Tes ulang sampel kosong di bawah.

### shadow-finops — NEED IMPROVEMENT

Menghitung estimasi biaya inferensi, efek cache, dan biaya infrastruktur untuk keputusan pemilik anggaran.

**Dasar klasifikasi.** Self-test 9/9. Instruksi meminta HPA pada setiap Deployment/StatefulSet dan label tenant_tier pada semua resource. Aplikasi tanpa multitenansi atau beban stabil tetap terkena aturan itu. [Instruksi](../shadow-finops/SKILL.md) · [Implementasi](../shadow-finops/scripts/finops_cost_auditor.py)

**Perbaikan dan cara menguji.** Pisahkan pertanyaan biaya token dari audit cluster. Jadikan rekomendasi HPA bersyarat pada pola beban dan model biaya. Uji kasus kalkulasi token tanpa resource Kubernetes.

### shadow-git — NEED IMPROVEMENT

Menjaga kontrak dan kepemilikan berkas saat beberapa orang atau agent berbagi branch dan worktree.

**Dasar klasifikasi.** Contoh detect-strategy --repo . dalam tabel gagal dengan exit 2. Parser mengharapkan opsi global sebelum subcommand. Perintah dengan urutan benar mengenali trunk-based dan main. [Instruksi](../shadow-git/SKILL.md) · [Implementasi](../shadow-git/scripts/git_orchestrator.py)

**Perbaikan dan cara menguji.** Jalankan contoh dokumentasi di tes CLI. Pertahankan scope per worktree. Uji dua pemilik yang berusaha mengubah kontrak bersama dan tampilkan konflik sebelum merge.

### shadow-grc — NEED IMPROVEMENT

Mengubah klaim kontrol menjadi temuan yang dapat ditelusuri ke bukti desain dan bukti operasional.

**Dasar klasifikasi.** Self-test 8/8 termasuk penolakan klaim tinggi dengan bukti hilang. Fungsi validate_audit_findings menggunakan tanggal acuan bawaan tetap 2026-11-16. Tanpa tanggal penugasan, analisis berikutnya dapat memakai konteks waktu yang keliru. [Instruksi](../shadow-grc/SKILL.md) · [Implementasi](../shadow-grc/scripts/grc_assurance_engine.py)

**Perbaikan dan cara menguji.** Jadikan tanggal penugasan dan versi register bagian dari input, serta dokumentasikan pemilik pembaruan. Uji satu kontrol pada dua tanggal efektif. Validitas hukum aktual memerlukan penelaahan tersendiri.

### shadow-handover — NEED IMPROVEMENT

Menyerahkan aset, akses, dokumentasi, dan tanggung jawab pemeliharaan ke pihak penerima melalui BAST.

**Dasar klasifikasi.** Skill membedakan serah terima klien dari handoff sesi dan melarang rahasia plaintext. Bagian inventaris menetapkan tag v1.0.0; kontrak untuk versi lanjutan dapat meminta tag berbeda. [Instruksi](../shadow-handover/SKILL.md)

**Perbaikan dan cara menguji.** Ambil versi dari manifest rilis yang disetujui, tandai serah terima parsial menurut kontrak, lalu minta penerima membuktikan akses. Uji fixture versi 3.2 dan pastikan inventaris merujuk digest sebenarnya.

### shadow-integrate — NEED IMPROVEMENT

Menyusun batas integrasi penyedia eksternal, verifikasi webhook, ledger idempotensi, dan penanganan efek samping.

**Dasar klasifikasi.** Instruksi mewajibkan batas usia lima menit dan Idempotency-Key. Dukungan header serta kebijakan timestamp bergantung pada kontrak penyedia. Header bebas belum membuktikan deduplikasi di sisi penyedia. [Instruksi](../shadow-integrate/SKILL.md)

**Perbaikan dan cara menguji.** Sebelum retry otomatis, catat kemampuan idempotensi, retry window, dan rekonsiliasi penyedia. Uji pembayaran sintetis dengan hasil timeout setelah eksekusi dan provider tanpa dukungan kunci; serahkan status belum pasti ke pemilik rekonsiliasi.

### shadow-maintain — NEED IMPROVEMENT

Mengarahkan triase insiden, pemulihan layanan, RCA tanpa menyalahkan orang, dan tindakan pencegahan dengan pemilik.

**Dasar klasifikasi.** Bagian hotfix meminta rollback segera jika deploy terakhir menyebabkan insiden. Kalimat tersebut mendahului pemeriksaan kompatibilitas data, kewenangan operator, dan ketersediaan target rollback. [Instruksi](../shadow-maintain/SKILL.md)

**Perbaikan dan cara menguji.** Buat percabangan keputusan rollback/forward-fix/isolasi. Dalam tabletop, migration yang tak bisa dibalik harus menghasilkan eskalasi kepada incident commander dan opsi mitigasi yang aman.

### shadow-mobile — NEED IMPROVEMENT

Membantu reviewer Android/iOS membedakan konfigurasi development dan release serta mengumpulkan bukti kesiapan distribusi.

**Dasar klasifikasi.** Self-test 9/9. Fungsi audit_mobile_text menganggap seluruh path berisi kata test sebagai varian uji. File release dalam folder contest kehilangan temuan debuggable yang terdeteksi pada path biasa. [Instruksi](../shadow-mobile/SKILL.md) · [Implementasi](../shadow-mobile/scripts/mobile_release_gate.py)

**Perbaikan dan cara menguji.** Baca source set atau merged release manifest. Tambah uji nama folder contest dan varian debug yang sah. Serahkan bukti perangkat serta hasil build kepada pemilik rilis.

### shadow-modernize — ALREADY GOOD

Membandingkan biaya dan risiko mempertahankan, merapikan, atau mengganti sistem legacy dengan bukti aturan bisnis.

**Dasar klasifikasi.** Self-test 8/8 mencakup komponen TCO yang menjumlah ke total, biaya rewrite yang naik, dan repo yang hilang. Skill memisahkan forensik read-only dari keputusan migrasi. [Instruksi](../shadow-modernize/SKILL.md) · [Implementasi](../shadow-modernize/scripts/modernize_forensics_engine.py)

**Perbaikan dan cara menguji.** Tambahkan sensitivitas biaya downtime dan pasangan opsi dengan selisih kecil. Minta pemilik bisnis mengonfirmasi aturan lama sebelum memasukkan penghematan ke skenario. Perluas kosakata routing Indonesia untuk rewrite/refactor.

### shadow-monarch — NEED IMPROVEMENT

Membatasi scope, memilih pemilik tugas, dan menyambungkan handoff serta persetujuan di seluruh skill.

**Dasar klasifikasi.** Pada prompt umum pemilik default memang sesuai. Akan tetapi beberapa prompt spesialis di tabel berakhir di Monarch. Pencocokan sinyal dan fallback dapat menghapus pemilik spesialis meski kalimat bermakna jelas bagi pengguna. [Instruksi](../shadow-monarch/SKILL.md) · [Implementasi](../shadow-monarch/scripts/skill_router.py)

**Perbaikan dan cara menguji.** Tambahkan pasangan maksud lintas bahasa serta kontrol negatif per owner. Bedakan fallback konsultasi, keputusan pengguna, dan pemilik eksekusi. Ukur recall per bahasa, precision per fase, serta tindakan pertama agen.

### shadow-observe — ALREADY GOOD

Menghubungkan SLI/SLO, burn rate, dan trace lintas komponen sehingga on-call bisa memilih tindakan yang relevan.

**Dasar klasifikasi.** Skill memasangkan paging dengan runbook, melarang label metrik ber-kardinalitas tinggi, dan menyerahkan timeline yang disunting ke debug. Ketiganya memberi batas jelas antara telemetri dan diagnosis. [Instruksi](../shadow-observe/SKILL.md)

**Perbaikan dan cara menguji.** Tambahkan contoh alert tanpa owner dan alert di layanan bertrafik kecil. Evaluasi dengan replay timeline: apakah notifikasi menyebut target, jendela pengamatan, tindakan, pemilik, dan ID penelusuran yang aman?

### shadow-ops — NEED IMPROVEMENT

Memelihara deployment, CI/CD, reverse proxy, infrastruktur, dan konfigurasi operasi sesuai stack aktual.

**Dasar klasifikasi.** Bagian akhir melarang infrastruktur tambahan tanpa permintaan. Bagian parity sekaligus meminta versi DB, Redis, dan topologi proxy identik pada seluruh environment. Syarat analisis berlaku terlalu luas pada platform terkelola. [Instruksi](../shadow-ops/SKILL.md)

**Perbaikan dan cara menguji.** Gunakan profil capability seperti containerized, serverless, atau managed DB. Untuk deployment statis, tes bahwa assessor mencatat N/A untuk Redis/DB serta memeriksa promosi artefak dan rollback yang relevan.

### shadow-perf — TOO BAD NEED MANY IMPROVEMENT

Menyediakan scaffold k6 dan mengarahkan pengukuran baseline sebelum UAT dengan otorisasi terpisah untuk tes beban.

**Dasar klasifikasi.** Probe lokal kontrak berisi POST /orders saja: generator berhasil, memasukkan GET /healthz yang tak tercantum, dan tidak menghasilkan http.post. Pemeriksaan status per operasi memakai <500. Bagian narasi menjanjikan korelasi data tulis. [Instruksi](../shadow-perf/SKILL.md) · [Implementasi](../shadow-perf/scripts/openapi_to_k6_scaffold.mjs)

**Perbaikan dan cara menguji.** Hentikan pembuatan perjalanan ketika operasi terpilih belum dapat dihasilkan, atau nyatakan bagian manual. Pilih target eksplisit, status sesuai operation, dan data uji. Untuk fixture POST-only hasil yang benar adalah rencana tertunda atau scaffold POST yang disetujui. Jangan menjalankan k6 untuk menguji generator.

### shadow-plan — NEED IMPROVEMENT

Menguraikan kebutuhan menjadi backlog, dependensi, acceptance criteria, dan tanggung jawab pada jalur kritis.

**Dasar klasifikasi.** DoR setiap story mensyaratkan sembilan UI states. DoD menyebut openapi.yaml, collection, dan viewport. Story pemrosesan batch internal yang tanpa antarmuka akan memperoleh pekerjaan tambahan. [Instruksi](../shadow-plan/SKILL.md)

**Perbaikan dan cara menguji.** Turunkan checklist dari jenis perubahan. Uji story batch tanpa UI, satu perbaikan salinan aplikasi, dan operasi API code-first. Catat alasan applicability serta satu PIC untuk dependensi lintas tim.

### shadow-pmo — ALREADY GOOD

Menguji dampak perubahan kontrak, estimasi jadwal PERT/CPM, biaya, dan otoritas persetujuan.

**Dasar klasifikasi.** Self-test 8/8 mencakup graf dependensi siklik serta estimasi dengan urutan tidak sah. Pemilik kalkulasi dan renderer dokumen formal terpisah secara eksplisit. [Instruksi](../shadow-pmo/SKILL.md) · [Implementasi](../shadow-pmo/scripts/pmo_governance_engine.py)

**Perbaikan dan cara menguji.** Tambahkan simulasi dua change request yang berbagi dependensi untuk menghindari hitung ganda. Uji tanggal baseline dan catat siapa yang dapat menyetujui revisi ruang lingkup.

### shadow-presales — ALREADY GOOD

Membantu tim tender membandingkan kebutuhan wajib, sizing, dan biaya beberapa opsi memakai asumsi yang dapat ditinjau.

**Dasar klasifikasi.** Self-test 8/8 mencakup sensitivitas kapasitas pada tiga skenario dan batas wewenang penetapan HPS. Panduan memberikan template harga dan pemilik keputusan. [Instruksi](../shadow-presales/SKILL.md) · [Implementasi](../shadow-presales/scripts/presales_commercial_engine.py)

**Perbaikan dan cara menguji.** Tambahkan kasus harga supplier kedaluwarsa. Tandai komponen yang memerlukan kutipan baru; izinkan pembahasan teknis yang independen sambil menunggu pemilik komersial.

### shadow-privacy — NEED IMPROVEMENT

Menginventarisasi PII, aliran data, retensi, persetujuan, dan penanggung jawab proses permintaan subjek data.

**Dasar klasifikasi.** Self-test 9/9 untuk auditor berbasis teks. Instruksi laporan meminta kategori data serta rujukan pasal. Jejak pola di file saja tidak membuktikan dasar pemrosesan, kebijakan retensi aktual, atau eksekusi DSAR. [Instruksi](../shadow-privacy/SKILL.md) · [Implementasi](../shadow-privacy/scripts/privacy_pdp_auditor.py)

**Perbaikan dan cara menguji.** Pisahkan temuan kode, bukti proses, dan kebutuhan keputusan controller. Uji dataset sintetis dengan log tersunting tetapi owner retensi belum ada; hasil harus menyatakan bukti proses belum tersedia.

### shadow-quality — TOO BAD NEED MANY IMPROVEMENT

Memberi hasil terstruktur tentang risiko perubahan kode, konvensi yang menyimpang, dan kebersihan lingkungan uji.

**Dasar klasifikasi.** Fungsi inspect_or_cleanup_docker_leaks mengambil seluruh docker ps -a dan memakai nama atau label global. Identitas repo/pekerjaan tidak menjadi input. Pada host bersama, container tugas lain dapat ditandai dan container berhenti dapat menjadi sasaran opsi cleanup. [Instruksi](../shadow-quality/SKILL.md) · [Implementasi](../shadow-quality/scripts/shadow_gate.py)

**Perbaikan dan cara menguji.** Jadikan project/run ID serta kepemilikan terverifikasi prasyarat cleanup. Pisahkan status lingkungan bersama dari status perubahan. Uji keluaran docker tiruan berisi dua proyek, termasuk resource berlabel milik tetangga.

### shadow-realtime — TOO BAD NEED MANY IMPROVEMENT

Menguji kontrak reconnect, urutan pesan, backpressure, dan penghentian pengiriman setelah izin berakhir.

**Dasar klasifikasi.** Self-test 6/6. Namun lima flag berupa string false dan tanpa event menghasilkan PASS dengan nol pesan. Truthiness menggantikan validasi boolean; kesimpulan tidak mensyaratkan observasi revokasi. [Instruksi](../shadow-realtime/SKILL.md) · [Implementasi](../shadow-realtime/scripts/realtime_transport_verifier.py)

**Perbaikan dan cara menguji.** Validasi tipe dan syarat minimal trace; pisahkan deklarasi dari hasil simulasi. Untuk fixture kontrol positif, izinkan dua frame normal dan wajibkan satu percobaan setelah revokasi diblokir.

### shadow-refactor — NEED IMPROVEMENT

Melindungi perilaku yang sudah berjalan saat struktur internal diperbaiki dengan tes karakterisasi dan rencana rollback.

**Dasar klasifikasi.** Self-test 6/6. Plan dengan changed_files=['other.py'] dan tanpa allowed_scope_files menghasilkan PASS selama checklist lain terisi. Cabang pemeriksaan selisih menonaktifkan batas jika allowlist kosong. [Instruksi](../shadow-refactor/SKILL.md) · [Implementasi](../shadow-refactor/scripts/refactor_characterization_gate.py)

**Perbaikan dan cara menguji.** Wajibkan scope yang dapat diverifikasi dari permintaan dan diff aktual. Simpan hasil test sebelum/sesudah dengan revisi masing-masing. Fixture tanpa scope harus meminta batas atau melaporkan belum terverifikasi.

### shadow-release — NEED IMPROVEMENT

Membantu tim menyiapkan catatan rilis, manifest, target rollback, dan promosi artefak yang bisa ditelusuri.

**Dasar klasifikasi.** Daftar preflight mewajibkan backup produksi dan baseline perf. Smoke mengasumsikan /healthz dan /readyz. Aturan tersebut juga mengenai rilis static web atau pustaka tanpa layanan HTTP. [Instruksi](../shadow-release/SKILL.md)

**Perbaikan dan cara menguji.** Bangun daftar pemeriksaan dari komponen/dampak rilis, endpoint terdaftar, dan kewenangan operator. Uji rilis pustaka tanpa DB, lalu migrasi expand-only yang memang memerlukan bukti backup.

### shadow-resilience — NEED IMPROVEMENT

Menyusun pemulihan, uji restore terisolasi, serta bukti ketahanan dan kesiapan pemilik layanan.

**Dasar klasifikasi.** Instruksi menyebut durasi pg_restore sebagai Actual RTO dan MAX(created_at) sebagai pengukuran kehilangan data. Keduanya melewatkan waktu konfigurasi aplikasi serta keadaan tanpa transaksi baru. [Instruksi](../shadow-resilience/SKILL.md)

**Perbaikan dan cara menguji.** Gunakan marker transaksi dan waktu terakhir layanan lulus verifikasi bisnis. Dalam tabletop, restore 4 menit, validasi/pengalihan 6 menit, maka total pemulihan 10 menit sejak titik awal drill yang disepakati.

### shadow-search — TOO BAD NEED MANY IMPROVEMENT

Menilai retrieval leksikal/hibrida dan isolasi tenant sebelum hasil diteruskan ke generator jawaban.

**Dasar klasifikasi.** Self-test 6/6. Satu query kosong memberi PASS. Duplikasi satu dokumen relevan memberi Recall=2.0 dan NDCG=1.6309. Perhitungan menghitung dokumen yang sama berulang, dan ketiadaan ground truth bernilai sempurna. [Instruksi](../shadow-search/SKILL.md) · [Implementasi](../shadow-search/scripts/search_relevance_acl_gate.py)

**Perbaikan dan cara menguji.** Tetapkan unit relevansi unik, aturan duplikasi, dan eligibility query. Data kosong menjadi insufficient evidence. Tambahkan invariant metrik dalam [0,1], laporkan missing tenant saat dataset mengklaim isolasi tenant.

### shadow-sec — NEED IMPROVEMENT

Menghubungkan risiko keamanan di perubahan perangkat lunak dengan pemilik kontrol dan bukti remediasi yang dapat diuji.

**Dasar klasifikasi.** Skill meminta contoh ID ASVS dan laporan per kontrol, serta menyebut ASVS 5.0.0 pada bagian rujukan. Label kategori di checklist ditulis langsung dalam teks. Tidak ada langkah dalam checklist yang memastikan ID yang dipilih teresolusi ke katalog versi audit. [Instruksi](../shadow-sec/SKILL.md)

**Perbaikan dan cara menguji.** Sebelum menerbitkan temuan, validasi ID terhadap katalog terpilih dan informasi versi. Uji satu ID tak terdaftar dan satu kontrol sah pada diff sintetis. Temuan yang gagal pemetaan tetap dapat dilaporkan dengan bukti kode dan status pemetaan tertunda.

### shadow-supplychain — TOO BAD NEED MANY IMPROVEMENT

Membandingkan manifest komponen dengan lockfile, menelaah identitas signer, dan mengumpulkan bukti build reproducible.

**Dasar klasifikasi.** Self-test 7/7. Manifest dengan komponen identik dan signer_verified berupa string false diterima PASS. Pemeriksa mengandalkan truthiness dan klaim pemanggil. Tanggal waiver juga memiliki nilai bawaan tetap. [Instruksi](../shadow-supplychain/SKILL.md) · [Implementasi](../shadow-supplychain/scripts/supplychain_sbom_gate.py)

**Perbaikan dan cara menguji.** Wajibkan boolean tervalidasi dan tautkan hasil verifikasi ke digest/issuer. Bedakan metadata deklaratif dari hasil verifikasi aktual. Gunakan tanggal penilaian eksplisit. Fixture string false harus ditolak.

### shadow-test — NEED IMPROVEMENT

Membantu tim memilih pengujian minimum yang menangkap regresi, mengelola fixture, dan menangani kegagalan flaky.

**Dasar klasifikasi.** Bagian regression selection membatasi eksekusi ke modul terdampak. Sementara itu matriks wajib delapan poin berorientasi status HTTP dan kontrak diasumsikan openapi.yaml. Tes unit diskon murni tidak memiliki status HTTP. [Instruksi](../shadow-test/SKILL.md)

**Perbaikan dan cara menguji.** Nyatakan applicability untuk unit, CLI, event, HTTP, dan UI. Pada rumus diskon, uji rounding, batas dan nilai nol; pastikan tidak ada server, Docker, atau load test terpicu.

### shadow-uat — NEED IMPROVEMENT

Menghubungkan kebutuhan yang disepakati ke bukti penerimaan pengguna, defect/CR, dan penandatangan yang berwenang.

**Dasar klasifikasi.** Exit gate mewajibkan sembilan state UI dan kontrak HTTP 202. Contoh referensi pengukuran juga memakai URI file absolut mesin pengembang. Acceptance batch tanpa UI akan sulit memenuhi kedua syarat UI. [Instruksi](../shadow-uat/SKILL.md)

**Perbaikan dan cara menguji.** Tentukan domain skenario dari kriteria yang ditandatangani. Uji proses impor headless melalui file masuk, audit log, hasil rekonsiliasi, dan konfirmasi operator; beri N/A untuk UI. Ubah rujukan contoh ke path yang portabel.

## Probe pemilihan skill dengan prompt bahasa Indonesia

Setiap baris merupakan eksekusi terpisah pada router yang sama. Pemilik harapan merupakan penilaian manual dari tanggung jawab di atas. Hasil primer sesuai pada 16/28 prompt. Sampel purposif ini menguji satu ungkapan per skill. Keluaran routing hanya memilih instruksi yang akan dibaca. Efektivitas instruksi setelah dibaca memerlukan tes terpisah. Jalankan dari akar repo dengan `python shadow-monarch/scripts/skill_router.py --route "<prompt>"`.

| Pemilik yang diuji | Prompt persis | Primary aktual | Companion aktual |
|---|---|---|---|
| shadow-ea | Petakan portofolio aplikasi dan kapabilitas untuk SPBE | shadow-monarch | — |
| shadow-eval | Ukur apakah jawaban RAG didukung kutipan pada data uji terpisah | shadow-monarch | — |
| shadow-finops | Hitung biaya token LLM bulanan dan penghematan cache | shadow-monarch | — |
| shadow-git | Cek benturan antar worktree tanpa menggabungkan branch | shadow-monarch | — |
| shadow-grc | Audit COBIT dan kecukupan bukti kontrol | shadow-grc | shadow-grc |
| shadow-handover | Siapkan BAST dan inventaris serah terima aplikasi | shadow-handover | shadow-handover |
| shadow-integrate | Hubungkan webhook penyedia pembayaran dan cegah proses ganda | shadow-integrate | shadow-integrate |
| shadow-maintain | Susun laporan pemeliharaan dan postmortem insiden | shadow-maintain | shadow-maintain |
| shadow-mobile | Periksa kesiapan rilis aplikasi Android | shadow-monarch | — |
| shadow-modernize | Bandingkan biaya rewrite dan refactor sistem legacy | shadow-monarch | — |
| shadow-monarch | Saya ingin memahami struktur proyek ini | shadow-monarch | — |
| shadow-observe | Tentukan SLO dan error budget untuk latensi pelanggan | shadow-observe | shadow-observe |
| shadow-ops | Tinjau konfigurasi nginx dan deployment staging | shadow-ops | shadow-ops |
| shadow-perf | Siapkan baseline performa sebelum UAT tanpa menjalankan beban | shadow-monarch | — |
| shadow-plan | Pecah kebutuhan menjadi backlog dengan dependensi dan acceptance criteria | shadow-discovery | shadow-discovery |
| shadow-pmo | Analisis dampak change request ke critical path | shadow-pmo | shadow-pmo · shadow-architect |
| shadow-presales | Susun estimasi kapasitas dan RAB tender | shadow-presales | shadow-presales |
| shadow-privacy | Periksa retensi dan penghapusan data pribadi pelanggan | shadow-privacy | shadow-privacy |
| shadow-quality | Tinjau kualitas kode dan dead code pada perubahan ini | shadow-quality | shadow-quality |
| shadow-realtime | Rancang SSE untuk notifikasi dan reconnect setelah jaringan putus | shadow-realtime | shadow-realtime · shadow-auth · shadow-concurrency · shadow-observe |
| shadow-refactor | Rapikan controller ini sambil mempertahankan perilaku | shadow-monarch | — |
| shadow-release | Siapkan catatan rilis dan rollback untuk versi berikutnya | shadow-monarch | — |
| shadow-resilience | Tinjau rencana restore drill dengan RPO dan RTO | shadow-resilience | shadow-resilience |
| shadow-search | Ukur relevansi BM25 untuk pencarian campuran Bahasa Indonesia | shadow-search | shadow-search · shadow-db · shadow-eval |
| shadow-sec | Tinjau kontrol akses dan pemisahan tenant secara statis | shadow-monarch | — |
| shadow-supplychain | Periksa SBOM dan provenance artefak rilis | shadow-supplychain | shadow-supplychain · shadow-sec · shadow-release |
| shadow-test | Buat unit test untuk perhitungan diskon | shadow-test | shadow-test |
| shadow-uat | Siapkan skenario penerimaan pengguna di staging | shadow-monarch | — |

## Reproduksi bukti

Untuk setiap entri yang menyebut self-test, jalankan `python <path-implementasi> --self-test` dari akar repo dengan Python 3. Ketiga belas suite tersebut berakhir dengan exit code 0. Untuk CLI Git, bandingkan `python shadow-git/scripts/git_orchestrator.py detect-strategy --repo .` (exit 2) dan `python shadow-git/scripts/git_orchestrator.py --repo . detect-strategy` (exit 0). Hasil kedua di checkout audit ini adalah strategi trunk-based dengan target main.

Probe berikut memakai data sintetis serta fungsi publik yang sama seperti pemeriksa lokal. Simpan blok sebagai skrip sementara atau jalankan melalui stdin ke Python di akar repo. Semua nilai aktual di bawah diambil dari eksekusi lokal.

```python
from pathlib import Path
from runpy import run_path

def module(skill, script):
    return run_path(str(Path("shadow-" + skill, "scripts", script + ".py")))

search = module("search", "search_relevance_acl_gate")["evaluate_search_dataset"]
print(search({"queries": [{}]}))    # PASS, recall=1, MRR=0, NDCG=1
sample = {"tenant_id": "a", "relevance_grades": {"d": 1},
          "retrieved": [{"id": "d", "tenant_id": "a"}] * 2}
print(search({"queries": [sample]}))    # PASS, Recall=2, NDCG=1.6309

rag = module("eval", "ai_eval_gate")["score_rag_dataset"]
print(rag([{}]))    # gate_passed=True, ketiga skor 1.0

realtime = module("realtime", "realtime_transport_verifier")["verify_realtime_session"]
flags = ("supports_cursor_resume enforces_token_revocation_mid_stream "
         "has_bounded_slow_consumer_queue uses_shared_pubsub_broker reconnect_backoff_has_jitter")
print(realtime(dict.fromkeys(flags.split(), "false")))    # PASS, 0 events

refactor = module("refactor", "refactor_characterization_gate")["verify_refactor_plan"]
print(refactor(dict(precedents_inspected=["a"], invariants_locked=["a"],
                    characterization_suite=dict(cases_count=1, before_refactor_exit_code=0,
                                                after_refactor_exit_code=0),
                    changed_files=["other.py"], rollback="revert")))    # PASS

supply = module("supplychain", "supplychain_sbom_gate")["verify_supplychain_manifest"]
components = [dict(name="pkg", version="1")]
print(supply(dict(lockfile_synced=True, lockfile_packages=components,
                  sbom_components=components, provenance=dict(signer_verified="false"))))    # PASS

mobile = module("mobile", "mobile_release_gate")["audit_mobile_text"]
for loc in ("app/src/main/AndroidManifest.xml", "contest/app/src/main/AndroidManifest.xml"):
    print(loc, [item["rule_id"] for item in mobile('<application android:debuggable="true" />', loc)])
# MASVS_CODE_DEBUGGABLE_ENABLED pada path pertama, hasil kosong pada path kedua
```

Untuk mengulangi probe scaffold tanpa mengirim traffic, jalankan blok Python berikut. Kontrak sengaja hanya memuat POST agar operasi tambahan mudah dideteksi.

```python
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory() as directory:
    spec = Path(directory, "spec.json")
    spec.write_text(json.dumps({"openapi": "3.1.0", "info": {"title": "X", "version": "1"},
        "paths": {"/orders": {"post": {"responses": {"201": {"description": "OK"}}}}}}))
    result = subprocess.run(["node", "shadow-perf/scripts/openapi_to_k6_scaffold.mjs",
                             "--spec", str(spec), "--out", directory], capture_output=True)
    js = next(Path(directory).glob("*.js")).read_text()
    print(result.returncode, "/healthz" in js, "http.post(" in js, "status < 500" in js)
    # 0 True False True
```

Untuk memeriksa batas kepemilikan Docker, ganti seluruh proses eksternal dengan mock. Dua baris mewakili layanan tim A yang masih aktif dan resource tim B yang sudah berhenti. Tidak ada daemon atau container nyata yang diakses.

```python
from runpy import run_path
from subprocess import CompletedProcess
from unittest.mock import patch

gate = run_path("shadow-quality/scripts/shadow_gate.py")["inspect_or_cleanup_docker_leaks"]
rows = ("aaa\tproject-a-sandbox\tpostgres\tUp 3 minutes\ttrue\n"
        "bbb\tproject-b-sandbox\tpostgres\tExited (0)\ttrue\n")
effects = [CompletedProcess([], 0, rows, ""), CompletedProcess([], 0, "", "")]
with patch("subprocess.run", side_effect=effects) as fake:
    result = gate(cleanup=True)
    print(result["leaked_count"], result["cleaned_containers"])
    print(fake.call_args_list[-1].args[0])
# 2 ['project-b-sandbox']
# ['docker', 'rm', '-v', 'bbb']   (hanya tercatat oleh mock)
```
