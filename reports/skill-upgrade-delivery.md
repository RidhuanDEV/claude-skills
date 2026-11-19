# Rencana peningkatan 23 skill operasi, delivery, dan konsultansi

Dokumen ini melanjutkan [audit 28 skill delivery](skill-review-delivery.md) pada baseline `bac8745`. Cakupan mencakup seluruh 23 skill yang mendapat **NEED IMPROVEMENT** atau **TOO BAD NEED MANY IMPROVEMENT** pada audit tersebut. Lima skill yang alur intinya dinilai baik tetap dapat menjadi pemilik bukti atau mitra handoff. Seluruh perubahan, fixture, dan hasil yang disyaratkan dalam rencana ini merupakan usulan implementasi. Audit pendahuluan mencatat hasil pengujian yang memang sudah dilakukan.

## Urutan pengiriman

| Gelombang | Prioritas dan alasan | Bukti untuk melanjutkan |
|---|---|---|
| A | Eval, quality, realtime, search, supplychain, perf, monarch. Dahulukan alat yang bisa meluluskan bukti kosong, memilih resource lintas tim, membuat perjalanan sintetis yang salah, atau gagal mengarahkan pemilik. | Setiap counterexample audit menjadi tes regresi yang gagal pada baseline lama, memperoleh hasil yang diharapkan pada kandidat, dan mempertahankan fixture positif. Simpan hasil per kemampuan, coverage, dan revisi. |
| B | Git, integrate, ops, release, maintain, resilience, refactor, test, UAT. Prioritaskan perubahan yang memerlukan pertukaran bukti antarpemilik dan dapat merusak data bila tanggung jawab tidak jelas. | Satu skenario gabungan melewati dua owner, satu kasus ambigu berhenti untuk keputusan, dan satu pemulihan linear atau fallback memiliki bukti hasil. |
| C | FinOps, GRC, handover, mobile, plan, privacy, security. Tentukan applicability dan bukti nyata pada engagement alih-alih menggeneralisasi profil pelanggan. | Reviewer bidang menguji contoh relevan dan contoh pengecualian, menerima matriks ownership, dan menandai hal yang berada di luar kompetensi teknis. |

Kembangkan perubahan secara vertikal per skill. Bekukan contoh gagal, perbarui instruksi dan alat pada referensi yang disebut, lalu jalankan fixture sebelum menguji host. Bila format JSON lama sudah dikonsumsi, pertahankan pembacanya dan tambahkan field status per dimensi serta versi skema. Pisahkan ketidaktersediaan bukti dari hasil negatif. Rilis per perubahan reversible dan batalkan per skill bila hasil lama yang valid berubah tanpa persetujuan pemilik.

Gunakan [harness evaluasi yang tersedia](../evals/README.md) untuk intent, routing dan observasi tindakan. Rekam input, revisi, expected/actual owner, tahap kerja, berkas yang disentuh, dan pilihan interaktif saat dibutuhkan. Pada pengujian lintas host, gunakan repo fixture baru dengan state awal identik untuk Codex, Claude, dan Gemini. Laporan satu host hanya mendukung klaim untuk host tersebut. Gunakan [protokol persetujuan](../shadow-monarch/reference/EXECUTION-APPROVAL-PROTOCOL.md) untuk eksekusi berdampak.

## A — Hilangkan keputusan kelulusan palsu dan perjelas pemilik tugas

### shadow-eval

**Hasil bagi pengguna.** Pisahkan kualitas retrieval, dukungan per klaim, keputusan abstain, dan isolasi tenant. Pengguna harus dapat menjawab apakah perubahan yang lebih murah masih layak dipromosikan untuk kelompok query tertentu.

**Inkrement implementasi.** Tambahkan tipe sampel (answerable, abstain, isolation) beserta field wajib di scorer. Hitung denominator, jumlah sampel eligible, dan abstention false accept/reject per bahasa. Bandingkan dua revisi pada ID sampel dan snapshot korpus yang sama, tampilkan delta per kelompok sebelum agregat. Simpan keputusan manusia tentang ambang jika biaya kesalahan berbeda. [Instruksi pemilik](../shadow-eval/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-eval/scripts/ai_eval_gate.py)

**Kolaborasi dan keputusan.** Pemilik search mengirim ranking dan revisi ACL. Reviewer domain memasok klaim rujukan. Pemilik eval menerbitkan perbandingan dan contoh gagal; otorisasi terpisah dibutuhkan sebelum penilaian LLM berbiaya.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Jawaban dengan dua klaim, hanya satu didukung, harus menghitung satu klaim didukung dari dua dan menunjukkan kutipan per klaim. | Sampel kosong, tenant uji hilang, atau split pengembangan tumpang tindih dengan holdout harus menghalangi klaim kelulusan terkait. |

### shadow-quality

**Hasil bagi pengguna.** Berikan dua keputusan terpisah tentang kualitas perubahan dan kesehatan pekerjaan lokal. Seorang pengembang harus dapat membuktikan bahwa aset tim lain tetap di luar cakupan pembersihan.

**Inkrement implementasi.** Ikat diff ke base, commit kandidat, workspace dan run ID. Identifikasi resource dari label kepemilikan yang dibuat saat provisioning serta ledger handle. Daftar hasil tanpa side effect; tepat sebelum cleanup, cocokkan ulang ID/label, status terminal, dan izin. Untuk temuan lama, catat baseline, penambahan baru dan pengecualian berumur. [Instruksi pemilik](../shadow-quality/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-quality/scripts/shadow_gate.py)

**Kolaborasi dan keputusan.** Tim test memasok ledger resource miliknya. Quality mengembalikan daftar temuan dan rencana, sedangkan pemilik resource menyetujui cleanup yang berdampak. Resource yang kepemilikannya ambigu cukup dilaporkan.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Fixture dua workspace dengan nama container mirip harus menghasilkan hanya satu kandidat milik run yang dinilai. Pengulangan setelah resource hilang harus selesai tanpa kesalahan atau penghapusan lain. | Sumber eksternal yang berlabel umum atau statusnya berubah menjadi aktif sebelum cleanup harus dikeluarkan dari target. Probe memakai mock Docker. |

### shadow-realtime

**Hasil bagi pengguna.** Verifikasi semantik sesi melalui jejak pesan yang memiliki urutan dan pemilik. Tentukan jaminan pengiriman selama disconnect, reconnect, dan pencabutan izin.

**Inkrement implementasi.** Tetapkan versi trace dengan event connect, authorize, emit, deliver, revoke, disconnect, resume serta ID stream dan sequence. Evaluasi state machine per koneksi dan identitas tenant. Tangani replay window/cursor kedaluwarsa, buffer penuh, aturan deduplikasi dan fairness. Pilih broker bersama hanya bila topologi menuntut fanout multi-instance. [Instruksi pemilik](../shadow-realtime/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-realtime/scripts/realtime_transport_verifier.py)

**Kolaborasi dan keputusan.** Auth menetapkan waktu efektif revokasi; tim transport menentukan semantik pesan in-flight. Owner consumer menetapkan kapan snapshot penuh diperlukan. Jika urutan waktu ambigu, laporkan interval ketidakpastian.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Replay seq 10, 10, 11 pada reconnect harus menampilkan dua pesan unik. Cursor kedaluwarsa harus meminta resync sesuai kontrak layanan. | Frame baru yang teramati terkirim setelah revokasi efektif gagal. Lima flag bertipe string tanpa trace menghasilkan bukti tidak cukup, meskipun satu node memakai transport yang didukung. |

### shadow-search

**Hasil bagi pengguna.** Bandingkan perubahan retrieval dengan satuan evaluasi yang benar untuk dokumen, chunk, tenant dan versi indeks. Tim dapat melihat apakah kenaikan relevansi dibayar dengan keterlambatan pencabutan akses.

**Inkrement implementasi.** Wajibkan query ID, tingkat judgement, ranking terurut dan identitas hasil stabil. Normalisasi ke unit yang dipilih, catat duplikasi secara eksplisit, pisahkan missing judgement dari nol relevansi, dan hitung interval/delta pada query berpasangan. Evaluasi filter tenant sebelum ranking serta freshness setelah delete/revoke melalui fixture terkontrol. [Instruksi pemilik](../shadow-search/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-search/scripts/search_relevance_acl_gate.py)

**Kolaborasi dan keputusan.** Pemilik indeks memberi snapshot dan watermark. Pemilik akses membuktikan perubahan izin. Eval menerima hasil retrieval yang lengkap beserta daftar query yang belum dapat diukur.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Dua chunk dari dokumen sama pada evaluasi tingkat dokumen menghasilkan Recall dalam [0,1]. Hasil faktual dan semantik dapat dibandingkan pada slice berbeda. | Query tanpa judgement menghasilkan status tidak terukur. Dokumen tenant lain yang mendapat skor tinggi harus gagal pada uji isolasi meski peningkatan rata-rata ranking besar. |

### shadow-supplychain

**Hasil bagi pengguna.** Buat keputusan provenance untuk artefak tertentu, termasuk saat CI offline, tanpa menyamakan isi manifest dengan bukti verifikasi signer.

**Inkrement implementasi.** Pisahkan inventaris lockfile/SBOM, kebijakan trust, bukti attestation, dan pengecualian. Hubungkan paket melalui identifier versi/ekosistem yang stabil, pisahkan runtime/dev/platform optional. Baca hasil verifier resmi yang sudah dipakai CI, cocokkan subject digest, builder/issuer yang diizinkan dan jadwal waiver pada tanggal penilaian yang dipasok. [Instruksi pemilik](../shadow-supplychain/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-supplychain/scripts/supplychain_sbom_gate.py)

**Kolaborasi dan keputusan.** Build owner memasok digest dan log resolusi; security menetapkan trust policy; release memakai hasil untuk digest identik. Perlu persetujuan pemilik risiko sebelum menerima waiver kedaluwarsa atau identity baru.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Satu paket opsional OS lain dapat dikeluarkan dengan profil platform terdokumentasi. Attestation valid untuk digest build yang diuji menghasilkan status verified untuk dimensi itu. | String false, tanda tangan untuk digest lain, atau verifier offline tidak memberi status signer verified. Dua paket bernama sama pada ekosistem berbeda tidak boleh digabungkan. |

### shadow-perf

**Hasil bagi pengguna.** Susun model beban dari perjalanan bisnis dan kontrak yang tersedia. Output harus menunjukkan bagian yang bisa diukur secara aman dan estimasi biaya sebelum pengujian.

**Inkrement implementasi.** Perluas scaffold dengan discovery sumber kontrak, operasi yang secara eksplisit dipilih dan status respons per operation. Representasikan prasyarat fixture, autentikasi, korelasi resource, cleanup dan parameter distribusi beban. Tawarkan dry-run terhadap mock lokal serta batas stop, target allowlist dan anggaran. Hasil perbandingan memakai versi dataset, target, warmup dan variansi yang sama. [Instruksi pemilik](../shadow-perf/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-perf/scripts/openapi_to_k6_scaffold.mjs)

**Kolaborasi dan keputusan.** API menyuplai kontrak verified; ops mengonfirmasi kapasitas/target; pemilik bisnis menentukan perjalanan dan SLO. Otorisasi eksekusi load terpisah dari persetujuan membuat scaffold.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Fixture POST lalu GET memakai ID dari respons create dan mengharapkan status yang disepakati. Generate/dry-run lokal harus dapat diuji tanpa meluncurkan k6. | POST-only tanpa data tulis tidak boleh berubah menjadi GET /healthz. Target produksi di servers[0] serta 401 pada skenario sukses harus menghalangi klaim readiness. |

### shadow-monarch

**Hasil bagi pengguna.** Router perlu mengetahui tujuan, fase, objek, pemilik, dan batas tindakan. Permintaan dokumentasi yang ambigu semestinya berhenti pada pilihan pengguna sebelum menciptakan format baru.

**Inkrement implementasi.** Pisahkan kandidat topic dari resolusi tugas. Gunakan contoh asli Indonesia/Inggris, negasi, koreksi serta task majemuk. Sertakan alasan singkat per kandidat, kondisi bertanya dan apa yang telah diputuskan. Mulai dengan shadow evaluation pada label yang diadjudikasi manusia sebelum mengubah default. Tambahkan uji dari prompt sampai tindakan pertama agent di setiap host. [Instruksi pemilik](../shadow-monarch/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-monarch/scripts/skill_router.py)

**Kolaborasi dan keputusan.** Spesialis memiliki keputusan domain. Monarch membatasi scope dan memilih owner; pemilik proyek menentukan prioritas jika dua pekerjaan berbagi kontrak. Fallback boleh melanjutkan discovery read-only.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Permintaan review webhook tanpa perubahan memuat skill integrasi dan menjaga fase review. Permintaan API docs generik dengan ringkasan README memunculkan pertanyaan format sebelum tulis. | Kata “jangan load test” dalam permintaan unit test tidak mengaktifkan eksekusi beban. Penyebutan nama tool dalam log atau kutipan dokumen tidak memperluas scope. |

## B — Jaga kontrak ketika beberapa tim melakukan perubahan dan pemulihan

### shadow-git

**Hasil bagi pengguna.** Koordinasikan branch, pemilik berkas, dan perubahan kontrak semantik sehingga konflik nontekstual juga terlihat sebelum integrasi.

**Inkrement implementasi.** Perbaiki urutan opsi dalam contoh CLI. Tambahkan smoke test dokumentasi terhadap repo sementara. Rekam SHA pangkal, target, rencana write-set dan dependensi handoff. Saat ref target bergerak, invalidate hasil dry-run lama dan jalankan ulang perbandingan. Deteksi benturan kontrak melalui konsumen yang terpengaruh, misalnya migrasi yang dipakai dua branch. [Instruksi pemilik](../shadow-git/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-git/scripts/git_orchestrator.py)

**Kolaborasi dan keputusan.** Pemilik masing-masing branch menyetujui rekonsiliasi kontrak. Integrator menyimpan catatan hasil merge preview dan tes pada gabungan perubahan. Persetujuan push tetap terikat remote serta ref tertentu.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Dua worktree dengan perubahan terpisah dan base sama menghasilkan preview bersih. Ketika target maju sesudah preview, integrator menghitung ulang sebelum memakai bukti itu. | Dua branch mengubah kontrak produsen/konsumen secara tidak kompatibel pada file berbeda harus ditandai untuk pengujian kontrak walau merge Git bersih. |

### shadow-integrate

**Hasil bagi pengguna.** Pisahkan keberhasilan transport dari keberhasilan transaksi bisnis. Jadikan hasil yang belum pasti dapat dilacak dan direkonsiliasi tanpa menghasilkan side effect kedua.

**Inkrement implementasi.** Temukan SDK/provider dan workflow aktif. Buat matriks kemampuan yang mencakup dukungan idempotency key, status inquiry, umur retry, signature scheme, dan urutan event. Tetapkan state local pending, confirmed, failed dan unknown. Gunakan ledger/pola outbox yang sudah ada untuk korelasi dan rekonsiliasi sesuai jaminan provider. [Instruksi pemilik](../shadow-integrate/SKILL.md)

**Kolaborasi dan keputusan.** Owner bisnis memutuskan kapan transaksi unknown dieskalasi. Concurrency menangani atomisitas ledger dan retry. Platform mengelola rotasi kunci; autentikasi dan nilai environment tetap berada di secret manager.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Simulasikan timeout setelah commit penyedia. Provider mendukung inquiry dan mengembalikan ID yang sama, sehingga proses lokal dipulihkan sekali. | Tanpa idempotensi atau status inquiry, timeout tidak memicu retry POST otomatis. Event lebih lama yang tiba belakangan tidak boleh menurunkan status final. |

### shadow-ops

**Hasil bagi pengguna.** Turunkan rencana operasi dari topologi nyata dan kemampuan platform. Buktikan apa yang akan berubah serta cara memulihkannya sebelum perubahan live.

**Inkrement implementasi.** Baca manifest dan pipeline yang dimiliki repo. Petakan deploy unit, stateful dependency, RBAC, secret reference, observability, target dan owner. Pilih profil static hosting, PaaS, VM, atau cluster berdasarkan bukti. Sajikan diff rencana, dependensi, dampak pengguna, canary jika tersedia dan guardrail rollback. [Instruksi pemilik](../shadow-ops/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-ops/references/04-CICD-GITHUB-GITLAB-ZERO-DOWNTIME.md)

**Kolaborasi dan keputusan.** Release memasok digest; platform menyetujui target dan window; observe menyediakan stop signal. Konfigurasi eksternal yang aksesnya terbatas dicatat dengan PIC dan status belum terverifikasi.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Aplikasi statis tanpa datastore menghasilkan pemeriksaan cache invalidation dan asset rollback. Layanan stateful mendapat pemeriksaan kesiapan data sesuai topologinya. | Permintaan review konfigurasi tidak memicu deploy. Rencana cluster tidak boleh memperkenalkan Redis atau Terraform semata karena contoh playbook. |

### shadow-release

**Hasil bagi pengguna.** Tentukan kelayakan promosi sebuah artefak dan kompatibilitas rollback terhadap code, data, kontrak konsumen, konfigurasi dan feature flag.

**Inkrement implementasi.** Temukan mekanisme release aktual dan buat manifest SHA/digest serta matriks dampak. Pilih gate dari blast radius dan bukti yang tersedia. Bedakan ulang deploy artifact sebelumnya, matikan flag, roll-forward, dan restore data. Tentukan telemetry pemicu stop serta masa observasi berbasis volume yang bermakna. [Instruksi pemilik](../shadow-release/SKILL.md)

**Kolaborasi dan keputusan.** UAT memberi sign-off untuk build; ops mengeksekusi sesuai otorisasi; owner data memvalidasi kompatibilitas dua versi. Simpan tautan bukti dan pemegang keputusan go/no-go.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Rilis package tanpa DB membawa uji API publik/packaging, konsumen referensi dan provenance. Rollback dua versi dengan migrasi expand-compatible menjelaskan urutan yang telah diuji. | Bukti staging untuk digest berbeda atau migrasi yang membuat versi lama tak dapat membaca data harus menggagalkan usulan rollback otomatis. |

### shadow-maintain

**Hasil bagi pengguna.** Bantu incident commander memulihkan layanan ketika penyebab belum pasti serta ketika rollback berpotensi memperparah kerusakan.

**Inkrement implementasi.** Tentukan pemilik insiden, tingkat dampak dan jam pembaruan. Bangun timeline perubahan/telemetri dan daftar hipotesis yang masing-masing memiliki bukti penyangkal. Bandingkan isolasi, flag-off, rollback, degradasi dan forward-fix berdasarkan waktu pemulihan, data at risk dan reversibilitas. Kaitkan postmortem ke tindakan berowner, tenggat dan verifikasi pencegahan. [Instruksi pemilik](../shadow-maintain/SKILL.md)

**Kolaborasi dan keputusan.** Observe menyediakan sinyal; release menilai kompatibilitas; commander memutuskan tindakan operasional sesuai otorisasi. Handoff shift berisi bukti tersunting, opsi, keputusan dan titik pemeriksaan berikutnya.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Setelah flag baru meningkatkan error, tabletop memilih flag-off yang dapat dibalik, lalu memverifikasi pemulihan dari sinyal pengguna. | Insiden setelah migrasi yang tidak kompatibel tidak cukup untuk rollback aplikasi. Jam insiden dan root cause harus dapat ditandai sementara saat bukti kurang. |

### shadow-resilience

**Hasil bagi pengguna.** Uji kemampuan memulihkan fungsi bisnis lengkap dari titik kegagalan yang terdefinisi, termasuk IAM, jaringan, storage, aplikasi, dan validasi konsumen.

**Inkrement implementasi.** Petakan dependency graph dan layanan minimum, target pemilik bisnis, urutan restore serta data classification. Gunakan marker transaksi yang dapat ditelusuri dan jam/titik awal yang jelas. Catat restore teknis, waktu pengalihan, verifikasi integritas, dan waktu fungsi bisnis kembali. Latih isolasi dan penghentian drill bila target/ownership tidak sesuai. [Instruksi pemilik](../shadow-resilience/SKILL.md)

**Kolaborasi dan keputusan.** Ops memegang lingkungan drill dan cleanup; data owner memvalidasi marker dan konsistensi; pemilik proses bisnis menyatakan kapan layanan memenuhi syarat. Rencana pemulihan aktual membutuhkan otorisasi terpisah.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Marker terakhir berusia 20 detik pada titik gagal, restore 4 menit, validasi dan switch 6 menit. Laporan memisahkan kehilangan data yang dibuktikan dari total pemulihan layanan 10 menit. | Tabel tanpa transaksi baru tidak membuktikan kehilangan data. Ketiadaan kunci dekripsi atau hasil validasi pengguna harus mencegah klaim recoverable. |

### shadow-refactor

**Hasil bagi pengguna.** Jaga kesetaraan perilaku yang bisa diamati di batas modul, termasuk semantik error, side effect, retry dan urutan notifikasi.

**Inkrement implementasi.** Temukan seam dan konsumen. Peroleh allowed paths dari scope yang disetujui dan changed paths dari Git. Kaitkan tes karakterisasi pada SHA sebelum/sesudah dengan input deterministik. Gunakan differential replay tersunting serta normalisasi field volatil sesuai kontrak. Pisahkan perubahan perilaku yang sengaja diminta ke keputusan tersendiri. [Instruksi pemilik](../shadow-refactor/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-refactor/scripts/refactor_characterization_gate.py)

**Kolaborasi dan keputusan.** Owner domain memberi makna invariants; quality membandingkan kontrak dan scope; integrator mengulang saat branch berubah. Konflik bukti diangkat sebelum membuang perilaku lama.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Refactor serialisasi yang mempertahankan nullability, status HTTP, dan side effect lulus replay pada dua revisi. Penambahan atribut opsional diberi penilaian eksplisit sesuai konsumen. | Plan tanpa allowed paths, tes pada SHA yang salah, atau event ganda meski output HTTP sama tidak membuktikan ekuivalensi. |

### shadow-test

**Hasil bagi pengguna.** Pilih tes dengan kemampuan membedakan implementasi benar dari cacat aktual, pada level termurah yang melintasi batas risikonya.

**Inkrement implementasi.** Temukan runner, konvensi dan data setup. Petakan risiko ke unit/component/contract/integration/end-to-end, sertakan alasan level dipilih. Utamakan tes pada invariant dan cara gagal, periksa test determinism, perlihatkan red-before/green-after pada bug. Tambahkan teardown berowner serta jalur diagnosis saat suite flaky. [Instruksi pemilik](../shadow-test/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-test/references/POLYGLOT-TESTING-MATRIX.md)

**Kolaborasi dan keputusan.** Developer menjelaskan perubahan; domain owner memvalidasi oracle; QA memilih regresi; host owner mengendalikan resource test. Kebutuhan load, broad E2E dan lingkungan bersama menjadi keputusan terpisah.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Untuk pembulatan diskon, uji perbatasan dan reproduksi bug di suite unit. Untuk duplikasi event, komponen real storage dapat membuktikan idempotensi di boundary yang relevan. | Tes unit murni tidak memulai Docker atau browser. Retry yang hanya menutupi nondeterminisme tidak menghasilkan status verified. |

### shadow-uat

**Hasil bagi pengguna.** Buktikan outcome bisnis dan kewenangan penerimaan untuk versi tertentu, termasuk proses asinkron, antarmuka headless, dan jalur manusia.

**Inkrement implementasi.** Bangun trace requirement ke skenario dan observasi bisnis. Pilih UI states, output file, audit event atau rekonsiliasi sesuai kanal. Pakai aturan pemisahan defect dan change request berdasarkan baseline bertanggal; catat severity, owner, risiko residual dan keputusan sign-off untuk build persis. [Instruksi pemilik](../shadow-uat/SKILL.md)

**Kolaborasi dan keputusan.** Pemilik bisnis menerima outcome; QA memegang bukti; PMO menangani perubahan cakupan; release menerima sign-off untuk digest yang cocok. Status UAT ditunda bila pemberi persetujuan belum berwenang.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Impor batch headless dinilai dari jumlah record valid, daftar gagal, nilai agregat, dan rekonsiliasi operator. Skenario UI async membedakan queued dari completed. | Tangkapan layar tombol sukses tidak cukup untuk membuktikan proses settlement. Requirement baru masuk CR dan tidak dipalsukan sebagai kelulusan baseline. |

## C — Kaitkan verifikasi dengan konteks bisnis, produk, dan regulasi

### shadow-finops

**Hasil bagi pengguna.** Kaitkan perubahan teknis ke biaya per hasil bisnis dan batas kualitas layanan. Bandingkan estimasi, biaya faktual, dan gejala penghematan semu akibat volume turun.

**Inkrement implementasi.** Mulai dari billing export dan struktur alokasi yang ada. Pisahkan committed/minimum, variable, shared, tax/currency dan unallocated. Untuk LLM, parameterkan input/output, cache dan kelas model dari bukti kontrak bertanggal. Identifikasi cost per successful workflow, beri rentang sensitivitas, dan validasi terhadap total invoice serta volume transaksi. [Instruksi pemilik](../shadow-finops/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-finops/scripts/finops_cost_auditor.py)

**Kolaborasi dan keputusan.** Finance mengonfirmasi basis alokasi dan periode; platform memasok usage; owner bisnis memvalidasi denominator keberhasilan. Rekomendasi pemangkasan resource membutuhkan SLO serta persetujuan pemilik layanan.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Contoh dua tim yang berbagi gateway, satu invoice dan biaya tak teralokasi menghasilkan rekonsiliasi yang menjumlah persis pada total. Bandingkan dua model pada kesuksesan bisnis setara. | Invoice tanpa rincian kategori cache atau model price region tidak boleh menghasilkan penghematan pasti. Untuk layanan non-Kubernetes, laporan tidak merekomendasikan HPA. |

### shadow-grc

**Hasil bagi pengguna.** Hasilkan matriks kewajiban dan kontrol berdasar sektor, yurisdiksi, tanggal penilaian dan periode bukti. Pisahkan desain kontrol dari efektivitas operasional dan opini formal.

**Inkrement implementasi.** Buat input scope bertanggal dan register sumber resmi yang dimiliki pemilik regulasi. Simpan version/effective interval, kriteria applicability dan mapping many-to-many kontrol. Bentuk catatan bukti yang mencakup periode, populasi, sampling, workpaper dan reviewer. Tandai missing evidence atau conflicting interpretation sebelum menghitung cakupan. [Instruksi pemilik](../shadow-grc/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-grc/scripts/grc_assurance_engine.py)

**Kolaborasi dan keputusan.** Control owner memasok bukti; risk/compliance menyetujui pemetaan; auditor independen menentukan assurance conclusion. Perubahan basis regulasi harus ditinjau manusia dan menandai penilaian terdampak untuk diulang.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Dokumen kebijakan tersedia sementara sampel transaksi satu kuartal hilang. Desain dapat dinilai, efektivitas operasional harus menunggu bukti. Tanggal berbeda memilih versi register yang sesuai. | Status sertifikasi atau kepatuhan penuh tidak dapat diturunkan dari self-assessment. Rujukan tidak berlaku pada tanggal penilaian harus diblokir atau ditandai perlu verifikasi. |

### shadow-handover

**Hasil bagi pengguna.** Ukur kesiapan penerima untuk mengoperasikan rilis yang diserahkan. Hubungkan aset, akses dan keterampilan operator dengan scope kontrak dan proof of receipt.

**Inkrement implementasi.** Ambil scope dari kontrak, stage dan versi aktual. Buat daftar deliverable dengan owner pengirim/penerima, digest atau location, kriteria penerimaan, status pengecualian dan pertanggungan garansi. Rencanakan walkthrough dan reverse demonstration oleh operator. Credential hanya direferensikan melalui jalur vault atau mekanisme transfer resmi. [Instruksi pemilik](../shadow-handover/SKILL.md)

**Kolaborasi dan keputusan.** Release memberi manifest; UAT memberi hasil sign-off; penyedia dan penerima mengakui item sesuai perannya. Handoff tertunda menyebut siapa yang menindaklanjuti dan layanan mana yang masih dikelola pengirim.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Serah terima parsial untuk rilis 3.2 memakai digest itu, menyertakan pemilik backup; penerima dapat menggunakan akses uji dan menunjukkan prosedur pemulihan dari runbook. | BAST belum ditandatangani, kunci vault tidak dapat diakses penerima, atau digest berbeda harus membuat item pending. Jangan menaruh nilai secret di bukti. |

### shadow-mobile

**Hasil bagi pengguna.** Nilai artefak distribusi yang benar-benar akan dikirim, termasuk build variant, merged manifest, channel pembaruan, migrasi storage dan interoperabilitas lintas versi aplikasi.

**Inkrement implementasi.** Temukan flavor, build type, bundle ID/application ID, konfigurasi release efektif dan target distribusi dari project. Normalisasi temuan per target, bedakan source indikatif dari artefak merged/signed terverifikasi. Tambahkan pemeriksaan cold upgrade, offline/low-memory, deep-link intents dan fallback saat device capability tidak tersedia, sesuai fitur terdampak. [Instruksi pemilik](../shadow-mobile/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-mobile/scripts/mobile_release_gate.py)

**Kolaborasi dan keputusan.** Pemilik build memasok artefak dan profil perangkat; AppSec menangani risiko data; release memutuskan rollout bertahap dan rollback store yang didukung. Bukti lokal tidak menggantikan pemeriksaan distribusi.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Release di path contest tetap diperiksa; debug source set yang sah tidak dianggap bukti release. Upgrade fixture dari versi lama harus mempertahankan session/migrasi sesuai kontrak. | Bukti emulator debug untuk klaim signed release atau manifest library yang berbeda dari merged manifest harus diberi status belum cukup. Akses store live membutuhkan keputusan terpisah. |

### shadow-plan

**Hasil bagi pengguna.** Hasilkan rencana delivery yang bisa disusun ulang saat asumsi berubah, dengan dependensi, ownership dan bukti penerimaan yang proporsional terhadap jenis pekerjaan.

**Inkrement implementasi.** Temukan outcome, constraint, Definition of Done tim, serta baseline requirement. Untuk tiap work package catat kontrak masuk/keluar, penanggung jawab, predecessor, hal yang bisa dikerjakan paralel, risiko pengulangan dan ukuran selesai. Gunakan spike timeboxed untuk keputusan tidak pasti. Tunjukkan dampak perubahan tanggal/owner atau kontrak bersama terhadap jalur kritis. [Instruksi pemilik](../shadow-plan/SKILL.md)

**Kolaborasi dan keputusan.** Satu PIC memegang keputusan kontrak bersama. Domain owner mengonfirmasi acceptance criteria; PMO mengambil alih perubahan komitmen eksternal. Rencana trial/read-only dapat maju sambil menunggu material decision.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Impor batch headless memetakan parsing, rekonsiliasi dan rollback tanpa sembilan state UI. Dua stream yang menyentuh schema sama memerlukan urutan integrasi dan owner yang jelas. | Persetujuan desain belum mengotorisasi deploy. Dependensi melingkar atau pekerjaan berisiko tanpa owner tidak boleh disajikan sebagai jadwal final. |

### shadow-privacy

**Hasil bagi pengguna.** Bangun bukti end-to-end untuk tujuan pemrosesan, retensi, DSAR dan aliran lintas pihak. Pisahkan observasi kode dari validasi organisasi dan keputusan hukum.

**Inkrement implementasi.** Temukan data categories, tujuan, owner, lawful basis yang telah diputuskan, sistem hulu/hilir, backup dan processor. Untuk satu permintaan subjek sintetis, telusuri akses/koreksi/penghapusan melalui cache, indeks, analitik dan arsip, termasuk legal hold yang disahkan. Hasilkan status per storage dan daftar keputusan yang membutuhkan pejabat berwenang. [Instruksi pemilik](../shadow-privacy/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-privacy/scripts/privacy_pdp_auditor.py)

**Kolaborasi dan keputusan.** Data owner memvalidasi lineage; privacy officer menilai basis dan pengecualian; security memvalidasi redaksi. Tetapkan batas pengujian dan gunakan data sintetis. Jangan jadikan bukti scan bersih sebagai legal sign-off.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| DSAR sintetis menandai indeks hapus, cache invalidated, arsip masuk retensi sah, dan layanan pihak ketiga masih menunggu konfirmasi. Bukti hanya memuat pengenal tersunting. | Null result pada pencarian PII di source tidak membuktikan penghapusan dari backup. Ketidakjelasan dasar retensi menghentikan rekomendasi penghapusan live dan dirujuk ke pejabat berwenang. |

### shadow-sec

**Hasil bagi pengguna.** Susun assurance defensif yang mengikuti aliran data dan boundary aktual dari perubahan. Kaitkan kontrol ke sumber, versi, bukti aplikasi, dampak, serta status remediasi.

**Inkrement implementasi.** Temukan aset, peran, jalur otorisasi, trust boundaries dan dependensi relevan dari diff. Prioritaskan kontrol yang memutus risiko aktual; jaga katalog versi dengan validasi ID saat membuat finding. Catat managed controls, residual risk, bukti negatif dan confidence. Gunakan review source, konfigurasi dan fixture unit dengan dua peran/tenant jika diizinkan. [Instruksi pemilik](../shadow-sec/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-sec/references/NIST-SSDF-AND-OWASP-ASVS-5.md)

**Kolaborasi dan keputusan.** Pemilik fitur menunjukkan enforcement point; auth menilai identitas; supplychain menilai provenance; risk owner mencatat exception beserta masa berlaku. Rekomendasi tetap bisa diterbitkan dengan status mapping tertunda.

| Uji penerimaan | Uji batas dan penolakan |
|---|---|
| Review perubahan ekspor data melacak pembatas tenant hingga query akhir dan bukti tes unit dua tenant. ID kontrol yang valid dirujuk dengan versi yang dipakai. | Label severity tanpa affected asset atau bukti kontrol tidak cukup. ID katalog yang hilang dan fitur yang hanya menyembunyikan tombol UI tidak menutup temuan otorisasi. |

## Uji gabungan sebelum distribusi

1. **Rilis dengan perubahan kontrak data.** Plan menetapkan pemilik migrasi. Git memperbarui preview setelah target berubah. Test menyediakan bukti kompatibilitas versi. UAT menautkan sign-off ke build. Release menolak promosi bila digest berbeda. Ops menerima manifest yang disetujui dan daftar keputusan rollback.
2. **Penilaian RAG multitenant.** Search memproduksi ranked IDs dari snapshot tertentu. Eval membedakan relevance, support dan abstain. Security memeriksa pemisahan tenant. FinOps membandingkan biaya per jawaban yang memenuhi syarat. Kelompok tanpa ground truth tampil sebagai bukti hilang.
3. **Insiden integrasi pembayaran.** Integrate memasukkan timeout ambigu ke rekonsiliasi, maintain mencatat timeline, privacy memastikan bukti tersunting, resilience membuktikan marker data saat simulasi pemulihan. Seluruh fixture memakai data sintetis. Tidak ada mutasi eksternal yang diperlukan untuk menyetujui desain alur ini.
4. **Konflik antartim dalam lingkungan bersama.** Quality menerima ledger dari test, lalu memisahkan resource tetangga. Git memperlihatkan dua owner pada kontrak yang sama. Monarch mengangkat pertanyaan kepada pemilik saat tindakan tidak dapat dilanjutkan tanpa keputusan. Uji ulang terhadap perubahan state di antara preview dan eksekusi menggunakan mock.
