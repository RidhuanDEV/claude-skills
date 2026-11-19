# Status 78 Improvement Shadow Army (Update Sesi 19 November 2026)

Rekap lanjutan pada cabang `main`, pembanding `bac8745`. Seluruh **78/78 item** (15 awal + 63 lanjutan) kini memiliki implementasi/kontrak dan bukti eksekusi **suite deterministik lokal** (**127/127 Python unittest PASS**, **56/56 Node `node:test` PASS**, **9/9 self-test & gate script PASS**, dan seluruh root `SKILL.md <= 500` baris).

| Kelompok | Total | Terbukti Lokal (Deterministic) | Masih Perlu Uji Live-Host / Eksternal |
|---|---:|---:|---:|
| Infrastruktur bersama (`X01`–`X08`) | 8 | 8 | Live parity Claude/Codex/Gemini/Antigravity & external holdout (`X01`, `X07`, `X08`) |
| Skill inti (`C01`–`C15`) | 15 | 15 | Live browser/DB/staging drills (`C08`, `C12`) |
| Engineering & delivery (`T01`–`T23`) | 23 | 23 | Live multi-turn agent transcripts & operator sign-off (`T05`, `T08`, `T09`, `T23`) |
| Modul desain (`D01`–`D17`) | 17 | 17 | Live workshop/UI human review (`D11`, `D16`) |
| Skenario lintas skill (`E01`–`E15`) | 15 | 15 | End-to-end full testing monorepo (`testing-skills-be-fe-other`) |

Dasar penilaian tersedia di [backlog induk](MASTER-ENHANCEMENT-BACKLOG.md), [pilot](STAGE-B-PILOT.md), dan [bukti implementasi](STAGE-B-TRANSFORMATION.md).

**Tahap berikutnya (Full Live Testing):** Jalankan skenario penuh pada monorepo uji `https://github.com/RidhuanDEV/testing-skills-be-fe-other.git` menggunakan prompt skenario & post-task agent audit prompt untuk menilai `PASS` / `ALMOST PASS` / `FAIL` lintas AI agent secara nyata.

ID terbukti lokal (78/78): X01–X08, C01–C15, T01–T23, D01–D17, E01–E15. **Status readiness: `VERIFIED-LOCAL` untuk deterministic suite; `NOT_MEASURED` untuk live multi-host agent runs & external reviewer holdout.**

## Infrastruktur bersama

### X01 · Baseline dan pembanding atas tindakan nyata

**Bidang F, H, B** · Dependensi — · P0 · Risiko M · 3–5 hari-orang.

**Implementasi dan target.** Bekukan fixture repo, input, hasil minimal, hasil terlarang, trace efek samping dan label reviewer. Sediakan kasus terpisah untuk holdout dan variasi bahasa. [Komponen pemilik](../evals/evals.json)

**Validasi.** Dua reviewer menjalankan fixture sama dan membandingkan keluaran serta kasus yang belum terukur.

**Kriteria penutupan.** Manifest reproduksi menyebut revisi, dependency, host, oracle dan data missing. Holdout tidak terpapar pada tahap tuning.

### X02 · Scope tindakan dan persetujuan interaktif

**Bidang B, E, I, L** · Dependensi — · P0 · Risiko H · 3–5 hari-orang.

**Implementasi dan target.** Propagasikan resource, host, fase, operasi dan keputusan eksplisit ke handoff. Bedakan review, preview, write dan publish. Jika pilihan material belum ditentukan, tanyakan sebelum aksi dependen. [Komponen pemilik](../shadow-monarch/scripts/execution_approval_gate.py)

**Validasi.** Replay review tanpa file write, persetujuan eksplisit satu aksi, dan perubahan target yang harus diputuskan ulang.

**Kriteria penutupan.** Setiap efek samping pada fixture punya otorisasi yang sesuai. Replay jawaban yang sudah jelas menghasilkan nol pertanyaan redundan.

### X03 · Sumber resmi bertanggal dan siklus pembaruan pengetahuan

**Bidang A, J, H** · Dependensi — · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Tambahkan pemilik pembaruan, versi berlaku, tanggal akses, digest, cakupan, alasan pakai dan pemicu revalidasi ke indeks yang sudah ada. Simpan salinan resmi jika hak dan format mengizinkan. [Komponen pemilik](../shadow-doc/scripts/reference_verifier.py)

**Validasi.** Uji versi lama vs baru, sumber offline dan sumber diganti upstream. Uji apakah prinsip/kasus yang terdampak dapat ditelusuri ke sumber.

**Kriteria penutupan.** Referensi yang dikutip resolvable; status stale/unknown terlihat pada keputusan terdampak; perubahan sumber memicu tinjau ulang fixture relevan.

### X04 · Progressive disclosure yang dapat diukur

**Bidang K, H, L** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Gunakan dispatch top-level, pemilihan path menurut concern dan bacaan terbatas pada kasus yang perlu. Ukur jumlah path, karakter/konteks atau token bila tersedia serta temps untuk tugas trivial dan kompleks. [Komponen pemilik](../shadow-monarch/scripts/skill_router.py)

**Validasi.** Pasangkan koreksi ejaan dengan review multi-domain. Bandingkan artefak, bacaan, kualitas serta waktu terhadap baseline.

**Kriteria penutupan.** Tugas kecil tidak menambah bacaan tak relevan dan tugas kompleks tetap mengakses bukti wajib. Ambang biaya disepakati sesudah baseline dicatat.

### X06 · Status dan bukti lintas alat yang kompatibel dengan caller lama

**Bidang D, F, H, I** · Dependensi X01 · P0 · Risiko H · 3–5 hari-orang.

**Implementasi dan target.** Pada dua pilot pertahankan input lama, pisahkan outcome dan completeness, simpan jumlah bukti/unknown dan revision. Uji konsumen lama sebelum memutuskan tipe bersama atau adapter lokal. [Komponen pemilik](../evals/run_evals.py)

**Validasi.** Replay satu payload legacy, satu payload sah lengkap dan satu bukti kosong. Bandingkan perilaku dua caller sebelum menyatukan tipe.

**Kriteria penutupan.** Kasus kosong tidak menjadi verified, caller lama memiliki jalur kompatibel atau migrasi jelas, dan perbedaan semantics tercatat.

### X07 · Kualifikasi lintas host dan pengelolaan variasi model

**Bidang F, I, K, L** · Dependensi X01,X02 · P1 · Risiko M · 3–6 hari-orang.

**Implementasi dan target.** Gunakan fixture awal identik dan catat host/model/versi, jumlah pengulangan, aksi, interaksi, file dan biaya. Nilai keputusan terbuka dengan rubric manusia dan blind holdout. [Komponen pemilik](../evals/README.md)

**Validasi.** Bandingkan set natural language yang sama pada host yang tersedia, lalu uji fallback pada host tanpa UI interaktif.

**Kriteria penutupan.** Klaim paritas hanya mencakup kombinasi yang diuji. Variansi, kegagalan berat dan kondisi belum terukur muncul pada hasil.

### X08 · Promosi, pemantauan regresi dan rollback per unit

**Bidang C, E, G, J** · Dependensi X06,X07 · P1 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** Simpan base/candidate SHA, compatibility matrix serta daftar owner caller. Promosikan batch kecil berdasar kualifikasi, bandingkan fixture lama dan siapkan revert paket yang dapat dilatih di fixture terpisah. [Komponen pemilik](../install.ps1)

**Validasi.** Simulasi dua versi caller, instalasi sebagian dan rollback satu skill pada profil sementara.

**Kriteria penutupan.** Restore menghasilkan kontrak lama yang dapat dipakai; tidak ada dependensi global baru dan setiap pengecualian rollout punya owner.

## Skill inti

### C01 · antislop

**Bidang B, K, L** · Dependensi X02 · P2 · Risiko L · 1–2 hari-orang.

**Implementasi dan target.** Perbaiki bagian Two Usage Modes di kontrak. Tambahkan contoh kombinasi sesi, kebijakan proyek, konfigurasi host dan nilai rusak. Di eval percakapan, rekam jumlah pertanyaan serta daftar operasi tulis untuk mode audit. [antislop/SKILL.md](../antislop/SKILL.md)

**Validasi.** Tanpa keputusan yang berlaku, satu pertanyaan lalu tunggu. Instruksi yang disisipkan sebagai nilai settings tidak boleh dijalankan. Reviewer menyimpan asal pilihan dan bukti operasi file dari sandbox.

**Kriteria penutupan.** Preset proyek `during`, settings kosong, audit dialog → temuan di chat, nol pertanyaan mode dan nol file. Pilihan sesi `after` mengubah mode untuk sesi itu saja.

### C02 · context7

**Bidang A, H, J** · Dependensi X03 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Perinci workflow resolver dan query dalam kontrak. Untuk monorepo, pilih manifest pemilik import. Tambahkan alur saat hasil multi-major atau resolver offline, termasuk dokumentasi resmi yang sudah terbundel dan deklarasi tipe lokal sebagai bukti terbatas. [context7/SKILL.md](../context7/SKILL.md)

**Validasi.** Hasil untuk major lain tidak menjadi dasar edit. Jika versi tidak bisa dipastikan, tandai ketidakpastian dan serahkan ke owner dependency bila keputusan migrasi diperlukan. Simpan nama simbol, versi, sumber dan pemeriksaan lokal yang dilakukan.

**Kriteria penutupan.** Fixture dua workspace dengan dua major. Jawaban harus mengaitkan contoh/simbol dengan workspace yang ditanya, versi, dan sumber yang memuatnya.

### C03 · handoff

**Bidang D, G, I** · Dependensi X02,X06 · P1 · Risiko H · 3–5 hari-orang.

**Implementasi dan target.** Hilangkan fallback path per mesin dalam kontrak. Periksa respons save/load/merge pada MCP yang ada, bandingkan Git state saat load dengan keadaan checkout. Tambahkan data opsional yang kompatibel dengan snapshot lama jika identitas saat ini kurang. [handoff/SKILL.md](../handoff/SKILL.md) · [mcp-servers/shadow-handoff-mcp/index.mjs](../mcp-servers/shadow-handoff-mcp/index.mjs)

**Validasi.** Cabang/HEAD berbeda menahan langkah yang menyentuh file terdampak sampai diperiksa. Snapshot lama tanpa metadata harus dapat dibaca dengan status tidak pasti. Serahkan daftar konflik keputusan dan sumber masing-masing kepada agen penerus.

**Kriteria penutupan.** Simpan dua label pada fixture temp, pindahkan checkout, muat snapshot by project/label, lalu gabungkan. Bukti yang belum diuji harus tetap ada dan jejak masing-masing keputusan dapat ditelusuri.

### C04 · shadow-accessibility

**Bidang A, F, L** · Dependensi X01 · P1 · Risiko M · 3–5 hari-orang.

**Implementasi dan target.** Susun ulang pilar formulir di kontrak dengan contoh HTML dan React, termasuk label pembungkus, label eksplisit dan kontrol kustom. Tautkan shadow-browser untuk pengambilan accessibility tree bila host mendukung, lalu dokumentasikan tahapan manual untuk kasus yang tersisa. [shadow-accessibility/SKILL.md](../shadow-accessibility/SKILL.md)

**Validasi.** Placeholder tunggal pada kontrol tanpa nama memicu temuan. Hasil inspeksi tree tanpa screen reader tidak boleh diberi status lulus screen reader. Serahkan elemen, state, urutan tombol, hasil teramati dan dampak ke pemilik komponen.

**Kriteria penutupan.** Dua input dengan nama yang benar melalui teknik native berbeda diterima. Dialog memindahkan dan mengembalikan fokus ke pemicu setelah ditutup.

### C05 · shadow-architect

**Bidang A, B, D** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Beri tiga tingkat keluaran pada kontrak, yaitu konsultasi, desain perubahan lintas modul, dan keputusan sistem. Pakai preseden brownfield dan template ADR yang ada. Dokumentasikan alternatif, pemilik keputusan, bukti, dan pemicu evaluasi ulang. [shadow-architect/SKILL.md](../shadow-architect/SKILL.md)

**Validasi.** Jangan mengusulkan microservice hanya karena ada dua direktori. Penerima handoff harus bisa menyebut kondisi terukur yang akan membatalkan rekomendasi.

**Kriteria penutupan.** Untuk batas validasi lokal, tunjukkan modul pemilik dan invariant tanpa menciptakan diagram sistem baru. Untuk memisahkan deployment, hasil memuat konsekuensi data dan strategi transisi.

### C06 · shadow-auth

**Bidang A, D, E, G** · Dependensi X02 · P0 · Risiko H · 4–7 hari-orang.

**Implementasi dan target.** Perbaiki Policy Test Matrix di kontrak. Mulai dari respons error dan entrypoint server yang dipakai; catat principal/aksi/resource/tenant dan lifecycle sesi. Gunakan shadow-api sebagai owner kontrak HTTP dan shadow-privacy untuk kebijakan log. [shadow-auth/SKILL.md](../shadow-auth/SKILL.md)

**Validasi.** Klaim role dari input tidak memberi akses; log uji tidak menyimpan kredensial atau token. Handoff ke tim API menyertakan tabel policy, status/error yang diharapkan, serta bukti terhadap fixture.

**Kriteria penutupan.** Pada fixture server lokal, tiap identitas yang disiapkan memperoleh respons serta header sesuai kontrak, dan fungsi mutasi hanya dipanggil pada izin yang cocok.

### C07 · shadow-bootstrap

**Bidang C, E, G, H** · Dependensi X02,X03 · P0 · Risiko H · 3–6 hari-orang.

**Implementasi dan target.** Ganti delapan pilar seragam dengan tabel kebutuhan → bukti → kapabilitas → generator resmi → berkas yang diharapkan. Gunakan verifier resmi untuk provenance generator. Buat preview manifest dan jalankan generator hanya di target yang disetujui. Uji pengulangan pada target nonkosong dan kegagalan parsial. [shadow-bootstrap/SKILL.md](../shadow-bootstrap/SKILL.md) · [shadow-monarch/scripts/official_first_verifier.py](../shadow-monarch/scripts/official_first_verifier.py)

**Validasi.** Situs statis tidak memperoleh OpenAPI, ORM, Redis atau Compose tanpa kebutuhan. Target yang berisi file pengguna tidak boleh tertimpa saat retry. Serahkan manifest, versi generator, perintah reproduce dan laporan file yang disentuh.

**Kriteria penutupan.** CLI offline mendapat entrypoint, build/test dan konfigurasi minimum. Layanan ber-DB mendapat migrasi dan readiness sesuai stack. Verifikasi kedua hasil dengan menjalankan entrypoint normal di direktori sementara.

### C08 · shadow-browser

**Bidang C, F, H, L** · Dependensi X02 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Ubah checklist browser menjadi alur siap-fixture → aksi → ekspektasi → observasi → cleanup. Pilih viewport berdasarkan layout dan target tugas. Periksa request terkait dan log dengan redaksi data sensitif. [shadow-browser/SKILL.md](../shadow-browser/SKILL.md)

**Validasi.** 404 pada JS, klik yang tidak berfungsi atau request ke luar host yang disetujui harus terlihat dalam hasil. QA menyerahkan langkah, viewport, URL teredaksi, status aktual dan batas pengujian ke engineer.

**Kriteria penutupan.** Pada fixture login invalid, 401 dan pesan pemulihan tepat dinilai lulus. Jalankan satu alur sukses terpisah.

### C12 · shadow-db

**Bidang A, D, F, H** · Dependensi X06 · P1 · Risiko H · 4–7 hari-orang.

**Implementasi dan target.** Perinci kapabilitas dan bukti per target di kontrak. Pada MCP telusuri detectEngine, mapTypeToTargetEngine dan handler generator. Tambahkan manifest hasil per artefak serta peringatan pemetaan lossy tanpa memecahkan caller lama. [shadow-db/SKILL.md](../shadow-db/SKILL.md) · [mcp-servers/shadow-db-mcp/index.mjs](../mcp-servers/shadow-db-mcp/index.mjs)

**Validasi.** Saat hanya XML dapat diparse, hasil belum membuktikan job Pentaho berjalan. Unknown host tetap tertahan. Serahkan mapping yang perlu keputusan dan selisih rekonsiliasi ke DBA.

**Kriteria penutupan.** Gunakan sumber lokal berisi desimal, dua NULL, timestamp, dan kunci gabungan. Cocokkan jumlah, nilai, key dan hasil replay dua batch di target lokal yang benar-benar tersedia.

### C13 · shadow-design

**Bidang B, I, K, L** · Dependensi X04,X05 · P1 · Risiko M · 3–5 hari-orang.

**Implementasi dan target.** Ganti alamat drive absolut di tabel Foreign-Key Reference Routing dengan referensi portabel. Uji resolusi setelah paket dipindah. Tambahkan kolom owner, event, guard, feedback, recovery dan alasan N/A pada model state. [shadow-design/SKILL.md](../shadow-design/SKILL.md)

**Validasi.** Tolak tautan absolut yang hanya ada di mesin penulis serta state buatan tanpa transisi. Handoff ke frontend/QA menyertakan alur, state yang dicapai dan acceptance yang bisa diuji.

**Kriteria penutupan.** Pada instalasi sementara di root lain, semua tautan lokal yang dipakai dapat dibuka. Untuk fixture alur pengajuan, trace satu user story sampai recovery setelah timeout.

### C14 · shadow-discovery

**Bidang B, I, L** · Dependensi X02 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Tambahkan tiga jalur pada kontrak: klarifikasi satu keputusan, discovery fitur dan discovery proyek. Untuk masing-masing nyatakan minimum input, keluaran, kondisi berhenti dan kriteria eskalasi. Hubungkan PRD penuh hanya dengan kebutuhan yang sesuai. [shadow-discovery/SKILL.md](../shadow-discovery/SKILL.md)

**Validasi.** Jangan mengarang jawaban saat owner belum merespons atau membuat PRD untuk satu pilihan. Handoff mencatat keputusan, siapa yang memutuskan, tanggal dan bagian requirement yang berubah.

**Kriteria penutupan.** Ambiguitas apakah “7 hari” kalender atau kerja memicu satu pertanyaan berpilihan kepada pemilik kebijakan. Setelah jawab, tambahkan contoh sebelum/sesudah tanggal batas ke acceptance.

### C15 · shadow-doc

**Bidang C, D, H, J** · Dependensi X03,X06 · P1 · Risiko M · 3–5 hari-orang.

**Implementasi dan target.** Selaraskan Golden Laws dan urutan pada bagian 3A. Kaitkan resolve, assess_generator_compatibility dan pengujian suite dokumen ke keputusan yang sama. Verifikasi referensi, gambar, font atau diagram sesuai permintaan artefak. [shadow-doc/SKILL.md](../shadow-doc/SKILL.md) · [shadow-doc/scripts/doc_orchestrator.py](../shadow-doc/scripts/doc_orchestrator.py) · [shadow-doc/scripts/doc_engine_test_suite.py](../shadow-doc/scripts/doc_engine_test_suite.py)

**Validasi.** Output yang tidak punya sumber terverifikasi atau dua pipeline tanpa owner menahan penulisan. Handoff berisi lokasi sumber, entrypoint, tipe output, manifest perubahan dan mana yang sudah divalidasi secara visual.

**Kriteria penutupan.** Fixture repo memiliki generator internal, satu sumber editable dan satu output. Perubahan satu paragraf menghasilkan diff di jalur yang diharapkan, tidak menambah pipeline dan dapat dibangun ulang.

## Engineering dan delivery

### T02 · shadow-finops

**Bidang A, B, C, K** · Dependensi X03 · P1 · Risiko M · 3–5 hari-orang.

**Implementasi dan target.** Mulai dari billing export dan struktur alokasi yang ada. Pisahkan committed/minimum, variable, shared, tax/currency dan unallocated. Untuk LLM, parameterkan input/output, cache dan kelas model dari bukti kontrak bertanggal. Identifikasi cost per successful workflow, beri rentang sensitivitas, dan validasi terhadap total invoice serta volume transaksi. [Instruksi pemilik](../shadow-finops/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-finops/scripts/finops_cost_auditor.py)

**Validasi.** Invoice tanpa rincian kategori cache atau model price region tidak boleh menghasilkan penghematan pasti. Untuk layanan non-Kubernetes, laporan tidak merekomendasikan HPA.

**Kriteria penutupan.** Contoh dua tim yang berbagi gateway, satu invoice dan biaya tak teralokasi menghasilkan rekonsiliasi yang menjumlah persis pada total. Bandingkan dua model pada kesuksesan bisnis setara.

### T03 · shadow-git

**Bidang C, D, G, I** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Perbaiki urutan opsi dalam contoh CLI. Tambahkan smoke test dokumentasi terhadap repo sementara. Rekam SHA pangkal, target, rencana write-set dan dependensi handoff. Saat ref target bergerak, invalidate hasil dry-run lama dan jalankan ulang perbandingan. Deteksi benturan kontrak melalui konsumen yang terpengaruh, misalnya migrasi yang dipakai dua branch. [Instruksi pemilik](../shadow-git/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-git/scripts/git_orchestrator.py)

**Validasi.** Dua branch mengubah kontrak produsen/konsumen secara tidak kompatibel pada file berbeda harus ditandai untuk pengujian kontrak walau merge Git bersih.

**Kriteria penutupan.** Dua worktree dengan perubahan terpisah dan base sama menghasilkan preview bersih. Ketika target maju sesudah preview, integrator menghitung ulang sebelum memakai bukti itu.

### T04 · shadow-grc

**Bidang A, B, F, J** · Dependensi X03 · P1 · Risiko H · 3–6 hari-orang.

**Implementasi dan target.** Buat input scope bertanggal dan register sumber resmi yang dimiliki pemilik regulasi. Simpan version/effective interval, kriteria applicability dan mapping many-to-many kontrol. Bentuk catatan bukti yang mencakup periode, populasi, sampling, workpaper dan reviewer. Tandai missing evidence atau conflicting interpretation sebelum menghitung cakupan. [Instruksi pemilik](../shadow-grc/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-grc/scripts/grc_assurance_engine.py)

**Validasi.** Status sertifikasi atau kepatuhan penuh tidak dapat diturunkan dari self-assessment. Rujukan tidak berlaku pada tanggal penilaian harus diblokir atau ditandai perlu verifikasi.

**Kriteria penutupan.** Dokumen kebijakan tersedia sementara sampel transaksi satu kuartal hilang. Desain dapat dinilai, efektivitas operasional harus menunggu bukti. Tanggal berbeda memilih versi register yang sesuai.

### T05 · shadow-handover

**Bidang C, I, L** · Dependensi C03 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Ambil scope dari kontrak, stage dan versi aktual. Buat daftar deliverable dengan owner pengirim/penerima, digest atau location, kriteria penerimaan, status pengecualian dan pertanggungan garansi. Rencanakan walkthrough dan reverse demonstration oleh operator. Credential hanya direferensikan melalui jalur vault atau mekanisme transfer resmi. [Instruksi pemilik](../shadow-handover/SKILL.md)

**Validasi.** BAST belum ditandatangani, kunci vault tidak dapat diakses penerima, atau digest berbeda harus membuat item pending. Jangan menaruh nilai secret di bukti.

**Kriteria penutupan.** Serah terima parsial untuk rilis 3.2 memakai digest itu, menyertakan pemilik backup; penerima dapat menggunakan akses uji dan menunjukkan prosedur pemulihan dari runbook.

### T06 · shadow-integrate

**Bidang A, C, D, G** · Dependensi X02,C10 · P0 · Risiko H · 4–7 hari-orang.

**Implementasi dan target.** Temukan SDK/provider dan workflow aktif. Buat matriks kemampuan yang mencakup dukungan idempotency key, status inquiry, umur retry, signature scheme, dan urutan event. Tetapkan state local pending, confirmed, failed dan unknown. Gunakan ledger/pola outbox yang sudah ada untuk korelasi dan rekonsiliasi sesuai jaminan provider. [Instruksi pemilik](../shadow-integrate/SKILL.md)

**Validasi.** Tanpa idempotensi atau status inquiry, timeout tidak memicu retry POST otomatis. Event lebih lama yang tiba belakangan tidak boleh menurunkan status final.

**Kriteria penutupan.** Simulasikan timeout setelah commit penyedia. Provider mendukung inquiry dan mengembalikan ID yang sama, sehingga proses lokal dipulihkan sekali.

### T07 · shadow-maintain

**Bidang B, C, G, I** · Dependensi X02 · P1 · Risiko H · 3–5 hari-orang.

**Implementasi dan target.** Tentukan pemilik insiden, tingkat dampak dan jam pembaruan. Bangun timeline perubahan/telemetri dan daftar hipotesis yang masing-masing memiliki bukti penyangkal. Bandingkan isolasi, flag-off, rollback, degradasi dan forward-fix berdasarkan waktu pemulihan, data at risk dan reversibilitas. Kaitkan postmortem ke tindakan berowner, tenggat dan verifikasi pencegahan. [Instruksi pemilik](../shadow-maintain/SKILL.md)

**Validasi.** Insiden setelah migrasi yang tidak kompatibel tidak cukup untuk rollback aplikasi. Jam insiden dan root cause harus dapat ditandai sementara saat bukti kurang.

**Kriteria penutupan.** Setelah flag baru meningkatkan error, tabletop memilih flag-off yang dapat dibalik, lalu memverifikasi pemulihan dari sinyal pengguna.

### T08 · shadow-mobile

**Bidang A, C, F, H** · Dependensi X03 · P1 · Risiko H · 3–6 hari-orang.

**Implementasi dan target.** Temukan flavor, build type, bundle ID/application ID, konfigurasi release efektif dan target distribusi dari project. Normalisasi temuan per target, bedakan source indikatif dari artefak merged/signed terverifikasi. Tambahkan pemeriksaan cold upgrade, offline/low-memory, deep-link intents dan fallback saat device capability tidak tersedia, sesuai fitur terdampak. [Instruksi pemilik](../shadow-mobile/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-mobile/scripts/mobile_release_gate.py)

**Validasi.** Bukti emulator debug untuk klaim signed release atau manifest library yang berbeda dari merged manifest harus diberi status belum cukup. Akses store live membutuhkan keputusan terpisah.

**Kriteria penutupan.** Release di path contest tetap diperiksa; debug source set yang sah tidak dianggap bukti release. Upgrade fixture dari versi lama harus mempertahankan session/migrasi sesuai kontrak.

### T09 · shadow-monarch

**Bidang B, E, I, K, L** · Dependensi X01,X02 · P0 · Risiko H · 4–7 hari-orang.

**Implementasi dan target.** Pisahkan kandidat topic dari resolusi tugas. Gunakan contoh asli Indonesia/Inggris, negasi, koreksi serta task majemuk. Sertakan alasan singkat per kandidat, kondisi bertanya dan apa yang telah diputuskan. Mulai dengan shadow evaluation pada label yang diadjudikasi manusia sebelum mengubah default. Tambahkan uji dari prompt sampai tindakan pertama agent di setiap host. [Instruksi pemilik](../shadow-monarch/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-monarch/scripts/skill_router.py)

**Validasi.** Kata “jangan load test” dalam permintaan unit test tidak mengaktifkan eksekusi beban. Penyebutan nama tool dalam log atau kutipan dokumen tidak memperluas scope.

**Kriteria penutupan.** Permintaan review webhook tanpa perubahan memuat skill integrasi dan menjaga fase review. Permintaan API docs generik dengan ringkasan README memunculkan pertanyaan format sebelum tulis.

### T10 · shadow-ops

**Bidang C, D, E, G** · Dependensi X02 · P1 · Risiko H · 3–5 hari-orang.

**Implementasi dan target.** Baca manifest dan pipeline yang dimiliki repo. Petakan deploy unit, stateful dependency, RBAC, secret reference, observability, target dan owner. Pilih profil static hosting, PaaS, VM, atau cluster berdasarkan bukti. Sajikan diff rencana, dependensi, dampak pengguna, canary jika tersedia dan guardrail rollback. [Instruksi pemilik](../shadow-ops/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-ops/references/04-CICD-GITHUB-GITLAB-ZERO-DOWNTIME.md)

**Validasi.** Permintaan review konfigurasi tidak memicu deploy. Rencana cluster tidak boleh memperkenalkan Redis atau Terraform semata karena contoh playbook.

**Kriteria penutupan.** Aplikasi statis tanpa datastore menghasilkan pemeriksaan cache invalidation dan asset rollback. Layanan stateful mendapat pemeriksaan kesiapan data sesuai topologinya.

### T12 · shadow-plan

**Bidang B, C, I, K** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Temukan outcome, constraint, Definition of Done tim, serta baseline requirement. Untuk tiap work package catat kontrak masuk/keluar, penanggung jawab, predecessor, hal yang bisa dikerjakan paralel, risiko pengulangan dan ukuran selesai. Gunakan spike timeboxed untuk keputusan tidak pasti. Tunjukkan dampak perubahan tanggal/owner atau kontrak bersama terhadap jalur kritis. [Instruksi pemilik](../shadow-plan/SKILL.md)

**Validasi.** Persetujuan desain belum mengotorisasi deploy. Dependensi melingkar atau pekerjaan berisiko tanpa owner tidak boleh disajikan sebagai jadwal final.

**Kriteria penutupan.** Impor batch headless memetakan parsing, rekonsiliasi dan rollback tanpa sembilan state UI. Dua stream yang menyentuh schema sama memerlukan urutan integrasi dan owner yang jelas.

### T16 · shadow-refactor

**Bidang C, D, F, G** · Dependensi X02,C10 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Temukan seam dan konsumen. Peroleh allowed paths dari scope yang disetujui dan changed paths dari Git. Kaitkan tes karakterisasi pada SHA sebelum/sesudah dengan input deterministik. Gunakan differential replay tersunting serta normalisasi field volatil sesuai kontrak. Pisahkan perubahan perilaku yang sengaja diminta ke keputusan tersendiri. [Instruksi pemilik](../shadow-refactor/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-refactor/scripts/refactor_characterization_gate.py)

**Validasi.** Plan tanpa allowed paths, tes pada SHA yang salah, atau event ganda meski output HTTP sama tidak membuktikan ekuivalensi.

**Kriteria penutupan.** Refactor serialisasi yang mempertahankan nullability, status HTTP, dan side effect lulus replay pada dua revisi. Penambahan atribut opsional diberi penilaian eksplisit sesuai konsumen.

### T17 · shadow-release

**Bidang C, D, E, I** · Dependensi C10,T10 · P1 · Risiko H · 3–6 hari-orang.

**Implementasi dan target.** Temukan mekanisme release aktual dan buat manifest SHA/digest serta matriks dampak. Pilih gate dari blast radius dan bukti yang tersedia. Bedakan ulang deploy artifact sebelumnya, matikan flag, roll-forward, dan restore data. Tentukan telemetry pemicu stop serta masa observasi berbasis volume yang bermakna. [Instruksi pemilik](../shadow-release/SKILL.md)

**Validasi.** Bukti staging untuk digest berbeda atau migrasi yang membuat versi lama tak dapat membaca data harus menggagalkan usulan rollback otomatis.

**Kriteria penutupan.** Rilis package tanpa DB membawa uji API publik/packaging, konsumen referensi dan provenance. Rollback dua versi dengan migrasi expand-compatible menjelaskan urutan yang telah diuji.

### T20 · shadow-sec

**Bidang A, E, F, J** · Dependensi X03,C06 · P1 · Risiko H · 3–6 hari-orang.

**Implementasi dan target.** Temukan aset, peran, jalur otorisasi, trust boundaries dan dependensi relevan dari diff. Prioritaskan kontrol yang memutus risiko aktual; jaga katalog versi dengan validasi ID saat membuat finding. Catat managed controls, residual risk, bukti negatif dan confidence. Gunakan review source, konfigurasi dan fixture unit dengan dua peran/tenant jika diizinkan. [Instruksi pemilik](../shadow-sec/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-sec/references/NIST-SSDF-AND-OWASP-ASVS-5.md)

**Validasi.** Label severity tanpa affected asset atau bukti kontrol tidak cukup. ID katalog yang hilang dan fitur yang hanya menyembunyikan tombol UI tidak menutup temuan otorisasi.

**Kriteria penutupan.** Review perubahan ekspor data melacak pembatas tenant hingga query akhir dan bukti tes unit dua tenant. ID kontrol yang valid dirujuk dengan versi yang dipakai.

### T22 · shadow-test

**Bidang B, C, F, K** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Temukan runner, konvensi dan data setup. Petakan risiko ke unit/component/contract/integration/end-to-end, sertakan alasan level dipilih. Utamakan tes pada invariant dan cara gagal, periksa test determinism, perlihatkan red-before/green-after pada bug. Tambahkan teardown berowner serta jalur diagnosis saat suite flaky. [Instruksi pemilik](../shadow-test/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-test/references/POLYGLOT-TESTING-MATRIX.md)

**Validasi.** Tes unit murni tidak memulai Docker atau browser. Retry yang hanya menutupi nondeterminisme tidak menghasilkan status verified.

**Kriteria penutupan.** Untuk pembulatan diskon, uji perbatasan dan reproduksi bug di suite unit. Untuk duplikasi event, komponen real storage dapat membuktikan idempotensi di boundary yang relevan.

### T23 · shadow-uat

**Bidang C, F, I, L** · Dependensi X02,C10 · P1 · Risiko M · 3–5 hari-orang.

**Implementasi dan target.** Bangun trace requirement ke skenario dan observasi bisnis. Pilih UI states, output file, audit event atau rekonsiliasi sesuai kanal. Pakai aturan pemisahan defect dan change request berdasarkan baseline bertanggal; catat severity, owner, risiko residual dan keputusan sign-off untuk build persis. [Instruksi pemilik](../shadow-uat/SKILL.md)

**Validasi.** Tangkapan layar tombol sukses tidak cukup untuk membuktikan proses settlement. Requirement baru masuk CR dan tidak dipalsukan sebagai kelulusan baseline.

**Kriteria penutupan.** Impor batch headless dinilai dari jumlah record valid, daftar gagal, nilai agregat, dan rekonsiliasi operator. Skenario UI async membedakan queued dari completed.

## Modul desain

### D01 · AI Product Designer

**Bidang C, D, I** · Dependensi C13 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Paket sudah mengaitkan user story dengan flow, state, dan acceptance. Sebelas path dalam instruksi lokal memiliki awalan direktori yang tidak cocok dengan susunan checkout. Kompetensi yang perlu dikembangkan adalah **melacak keputusan desain sampai implementasi**. `shadow-design` menangani resolusi path relatif dan menyusun rantai kebutuhan → tindakan → bukti sistem → pemulihan. `shadow-api` atau engineer domain memverifikasi arti respons dan pembatasan backend bila memengaruhi state pengguna. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/ai-product-designer-skill-pack/SKILL.md](../shadow-design/references/ai-product-designer-skill-pack/SKILL.md)

**Validasi.** Permintaan koreksi satu label yang cukup ditangani dengan referensi bahasa serta pola saat ini.

**Kriteria penutupan.** 11 target dapat dibaca relatif terhadap lokasi paket ketika working directory dipindah, dan receipt 202 menghasilkan status menunggu.

### D02 · Intent

**Bidang B, K, L** · Dependensi C13 · P2 · Risiko L · 1–2 hari-orang.

**Implementasi dan target.** Banner wajib mengajukan pertanyaan konteks dan aturan paket mengutamakan deliverable berbentuk file. Keduanya perlu diterjemahkan oleh `shadow-design` menurut tugas serta mode pemakaian. Pertahankan kemampuan analisis tujuan, dilema etika, dan keputusan yang dapat ditinjau ulang. Bentuk catatan keputusan paling kecil yang memadai untuk audiensnya, dengan alasan, bukti, pemilik, dan pemicu untuk merevisi keputusan. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/ghaida-intent/skills/intent/SKILL.md](../shadow-design/references/external-upstreams/ghaida-intent/skills/intent/SKILL.md)

**Validasi.** Perintah eksplisit membuat decision record pada lokasi tertentu. Artefak tersebut boleh dibuat tanpa mengulangi keputusan pengguna.

**Kriteria penutupan.** Tujuan yang sudah tersedia dipakai, kritik tetap di chat, dan pemilihan pola yang berdampak material memicu satu pertanyaan interaktif sebelum implementasi.

### D03 · Userflow

**Bidang D, I, K, L** · Dependensi C13 · P0 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** Dispatcher memiliki taksonomi 15 flow dan aturan memilih 1–4 skill, tetapi mewajibkan laporan HTML untuk mayoritas review dan merujuk template yang tidak ada. `shadow-design` perlu memiliki pemilihan flow, pemeriksaan keberadaan template, serta cara menggabungkan panduan yang tumpang tindih. `shadow-monarch` menjaga mode baca/tulis. Gunakan alur pekerjaan, dependensi antarlayar, state pemulihan, dan prioritas aturan domain untuk menentukan referensi yang dimuat. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/ux-flow-skills/skills/userflow/SKILL.md](../shadow-design/references/external-upstreams/ux-flow-skills/skills/userflow/SKILL.md)

**Validasi.** Koreksi warna tombol yang tidak membutuhkan dispatcher flow.

**Kriteria penutupan.** Permintaan review hanya menghasilkan ulasan dan tidak menyentuh file. Untuk permintaan ekspor HTML eksplisit, gunakan template kompatibel yang ada atau jelaskan pilihan saat input wajib hilang.

### D04 · Designer Skills / design-research / interview-script

**Bidang A, B, F, L** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** Pemilik metode adalah `shadow-design`. Kegunaan utama adalah menyusun wawancara untuk memahami bagaimana orang menyelesaikan tugas. Ajarkan critical incident interviewing, probe yang netral, teknik membedakan ucapan dan observasi, serta penutupan yang memberi peserta kesempatan mengoreksi interpretasi. Hasil kerja berupa panduan moderator, rencana pencatatan, dan peta pertanyaan ke keputusan desain. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/design-research/skills/interview-script/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/interview-script/SKILL.md)

**Validasi.** Pertanyaan manajemen tentang pihak yang menyetujui pembelian, yang masuk discovery produk.

**Kriteria penutupan.** Path keluarga desain terpilih dan setiap dugaan friksi memperoleh probe non-leading dan tempat mencatat bukti yang menentangnya.

### D05 · PM Skills / pm-product-discovery / interview-script

**Bidang A, B, F, L** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** Pemilik keputusan adalah `shadow-discovery` dengan `shadow-design` menyediakan referensi vendor. Bangun keahlian menyelidiki kejadian pemicu pembelian, alternatif yang telah dicoba, pengambil keputusan, dan biaya berpindah. Output berupa panduan wawancara berbasis keputusan investasi, termasuk apa yang bisa membuat tim menolak hipotesis peluang. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/interview-script/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/interview-script/SKILL.md)

**Validasi.** Uji label tombol dashboard yang harus menuju keluarga desain.

**Kriteria penutupan.** Posisi pembeli tidak disimpulkan dari antusiasme pengguna, calon responden dipisahkan menurut peran, dan path PM terpilih.

### D06 · Designer Skills / design-research / summarize-interview

**Bidang A, B, F, J** · Dependensi D04 · P1 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** `shadow-design` bertanggung jawab atas sintesis perilaku. Metode yang perlu dimiliki adalah coding kejadian, penelusuran kutipan ke segmen transkrip, penandaan inferensi, dan pencatatan kejadian yang menyangkal pola. Desainer menerima daftar friksi per langkah dan pertanyaan validasi. Sertakan identitas pseudonim bila pemilik studi membutuhkannya. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/design-research/skills/summarize-interview/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/summarize-interview/SKILL.md)

**Validasi.** Transkrip tanpa observasi. Laporan tidak boleh menciptakan jumlah kesalahan yang tidak diucapkan atau dicatat.

**Kriteria penutupan.** Pembaca bisa menemukan keduanya, penjelasan penyebab berstatus inferensi, dan identitas pribadi tidak ikut ke handoff.

### D07 · PM Skills / pm-product-discovery / summarize-interview

**Bidang A, B, F, I** · Dependensi D05 · P1 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** `shadow-discovery` memiliki sintesis untuk keputusan produk. Hubungkan kebutuhan, alternatif saat ini, dampak, otoritas membeli, dan bukti yang masih kosong dengan opportunity backlog. Pertahankan level bukti per orang, tanpa menaikkan satu pengalaman menjadi ukuran pasar atau komitmen pembelian. Serahkan pertanyaan prioritas kepada PM. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/summarize-interview/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/summarize-interview/SKILL.md)

**Validasi.** Rangkuman uji kegunaan yang diminta untuk perbaikan field formulir. Rute tersebut memakai D06.

**Kriteria penutupan.** Seorang admin meminta ekspor CSV dan menyebut “mungkin direktur mau bayar”. Ringkasan harus menautkan masalah rekonsiliasi ke kutipan, memisahkan solusi usulan, serta menandai anggaran dan keputusan direktur sebagai belum diketahui.

### D08 · Designer Skills / design-research / survey-design

**Bidang A, B, F, L** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** Pemilik instrumen adalah `shadow-design`. Kembangkan pemilihan skala, konsistensi arah jawaban, pengalaman responden, penanganan data kosong, dan pilot kognitif untuk memeriksa apakah peserta menafsirkan item sesuai tujuan. Hasil berupa kuesioner versi pilot, keputusan desain yang dilayani tiap blok, dan daftar alasan revisi. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/design-research/skills/survey-design/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/survey-design/SKILL.md)

**Validasi.** Fixture yang hendak membandingkan hasil historis. Perubahan skala harus dijelaskan sebagai pemutus keterbandingan sebelum angka digabung.

**Kriteria penutupan.** Tiap konstruk bisa dianalisis terpisah dan responden yang belum mencoba dikeluarkan dari denominator yang relevan.

### D09 · PM Skills / pm-market-research / survey-design

**Bidang A, B, F, J** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** `shadow-discovery` memiliki keputusan pasar dan memakai `shadow-design` untuk akses metode vendor. Kembangkan sampling frame, penentuan populasi target, segmentasi, nonresponse bias, dan kriteria keberhasilan yang ditetapkan sebelum melihat jawaban. Hasil berupa brief keputusan, rencana rekrutmen, instrumen, rancangan tabulasi, serta tindakan bila data tidak konklusif. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-market-research/skills/survey-design/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-market-research/skills/survey-design/SKILL.md)

**Validasi.** Survei pengalaman satu alur pada pengguna yang telah menjalankannya. Rute tersebut memilih D08.

**Kriteria penutupan.** Laporan pilot menyebut sampling frame yang sebenarnya, memisahkan pengguna aktif dari prospek, dan membatasi kesimpulan atau mengusulkan cara merekrut kelompok yang hilang.

### D10 · Doherty Threshold

**Bidang A, F, G, L** · Dependensi C13 · P2 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** `shadow-design` memiliki pengalaman menunggu. Pemilik aplikasi memverifikasi telemetry dan arti hasil operasi. Ajarkan perbedaan waktu ke umpan balik pertama, waktu penyelesaian, dan latensi bagian paling lambat dalam distribusi. Pilih indikator menurut durasi, ketidakpastian, biaya salah klik, dan kebutuhan aksesibilitas. Angka 400 ms dalam referensi perlu status heuristik ketika konteks produk belum diukur. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/interaction-design/skills/doherty-threshold/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/interaction-design/skills/doherty-threshold/SKILL.md)

**Validasi.** Satu trace lambat. Hasilnya tidak cukup untuk mengubah target layanan atau memulai load test.

**Kriteria penutupan.** Fixture cepat tidak menghasilkan kedipan indikator, fixture lambat memberikan state menunggu yang dapat diakses, dan receipt antrean tidak memberi pesan sukses akhir.

### D11 · Critique Visual Hierarchy

**Bidang A, B, F, L** · Dependensi C04,C13 · P2 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** `shadow-design` memiliki kritik tugas pengguna, dibantu `shadow-accessibility` jika fokus keyboard, zoom, atau pembacaan layar ikut memengaruhi navigasi. Ajarkan penilaian entry point, pengelompokan, urutan baca, kepadatan, dan persaingan aksi. Gunakan screenshot untuk observasi, source token untuk nilai teknis, dan bukti tugas untuk dampak. Rasio visual yang disebut sumber dapat menjadi pemicu pemeriksaan. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/visual-critique/skills/critique-visual-hierarchy/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/visual-critique/skills/critique-visual-hierarchy/SKILL.md)

**Validasi.** Layar yang memakai ukuran judul seragam tetapi tugas utama mudah ditemukan. Selisih rasio semata tidak menghasilkan blocker.

**Kriteria penutupan.** Finding dapat ditelusuri ke elemen, viewport, dan tugas yang terganggu.

### D12 · Flow Auth

**Bidang D, E, G, L** · Dependensi C06,C13 · P0 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** `shadow-design` memiliki pengalaman masuk. `shadow-auth` menguasai aturan tenant, identity provider, verifikasi identitas, serta kebijakan pemulihan. Perluas kemampuan menjadi pemodelan state identitas dari bukti yang diizinkan server, termasuk SSO opsional, akun personal, linking, sesi kedaluwarsa, dan provider yang sementara gagal. Tetapkan kontrak data sebelum menetapkan navigasi. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-auth/SKILL.md](../shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-auth/SKILL.md)

**Validasi.** Fixture tenant dengan SSO wajib. Saran UI tidak boleh menambahkan jalur password yang melanggar kebijakannya.

**Kriteria penutupan.** Redirection hanya terjadi untuk hasil resolusi server yang sesuai kebijakan dan akun ambigu mendapat langkah pemulihan yang tidak mengungkap keberadaan akun lain.

### D13 · PM AI Shipping / code-review

**Bidang C, D, I, L** · Dependensi C13,T14 · P0 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** `shadow-quality` menjadi pemilik review, dengan `shadow-debug` atau pemilik domain bila diperlukan. Adapter perlu menerjemahkan intent PM menjadi pertanyaan reviewer tentang kontrak publik, caller lama, risiko regresi, dan bukti verifikasi. Hasil berupa temuan berperingkat dengan lokasi, kondisi pemicu, dampak, dan koreksi minimum. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/code-review/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/code-review/SKILL.md)

**Validasi.** Permintaan desain UX untuk halaman review pengguna, yang tidak mengaktifkan code review.

**Kriteria penutupan.** Review read-only menemukan pasangan lokasi kontrak dan konsumen, menjelaskan kondisi gagal, serta memberi PM konsekuensi yang dapat dipahami. Instalasi plugin dan perubahan source harus berjumlah nol.

### D14 · PM AI Shipping / intended-vs-implemented

**Bidang B, C, F, I** · Dependensi C13,C14 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** `shadow-discovery` memiliki rekonsiliasi kebutuhan; `shadow-api`, `shadow-test`, atau pemilik komponen memasok bukti implementasi yang relevan. Ajarkan pembedaan janji publik, rancangan usulan, perilaku sengaja disembunyikan, dan bug yang dapat direproduksi. Artefak berupa matriks klaim, status otoritas, bukti implementasi, dampak, dan pihak yang memutuskan tindak lanjut. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md)

**Validasi.** Ide di backlog yang belum disetujui. Selisih dengan ide tersebut tidak diberi status cacat kontrak.

**Kriteria penutupan.** Reviewer melacak input sampai output, mengidentifikasi selisih, dan mempertahankan kedua bukti ketika belum jelas apakah kontrak atau implementasi yang perlu diubah.

### D15 · PM AI Shipping / shipping-artifacts

**Bidang C, I, J, L** · Dependensi C13,T17 · P1 · Risiko M · 1–3 hari-orang.

**Implementasi dan target.** `shadow-release` memiliki bukti perubahan serta status rilis. `shadow-doc` memiliki penyajian bila pengguna meminta dokumen. Kembangkan kemampuan membedakan kebutuhan operator, pelanggan, dan tim dukungan dengan provenance ke commit, tiket, atau hasil verifikasi. Pilih materi sesuai audiens serta cakupan perubahan. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/shipping-artifacts/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/shipping-artifacts/SKILL.md)

**Validasi.** Permintaan khusus runbook rollback. Handoff beralih ke pemilik release dengan pemicu, prosedur, dan bukti pemulihan yang sesuai.

**Kriteria penutupan.** Draft menyebut status integrasi yang benar, tidak menyatakan fitur sudah tersedia di produksi, serta tidak membuat changelog tambahan, memublikasikan draft, atau memasang plugin.

### D16 · Live Polls

**Bidang E, G, I, L** · Dependensi C13,X02 · P1 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** `shadow-plan` atau fasilitator yang ditunjuk memiliki pertanyaan dan keputusan rapat. `shadow-monarch` menjaga cakupan panggilan eksternal. Ajarkan pemungutan suara independen, anonimitas kontekstual, penundaan pembukaan hasil, serta interpretasi pilihan minoritas. Modelkan persiapan di chat, pembuatan resource eksternal, peluncuran, pembukaan hasil, dan penutupan sebagai operasi yang berbeda dengan otorisasi yang dapat dipakai kembali selama cakupannya sama. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-polls/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-polls/SKILL.md)

**Validasi.** Suara minoritas mengenai risiko serius. Kesimpulan mencatat keberatan dan pemilik tindak lanjut meski mayoritas mendukung.

**Kriteria penutupan.** Draft lokal memakai nol panggilan konektor. Pada fixture yang mengizinkan pembuatan eksternal, retry dengan request ID yang sama setelah timeout hanya membuat satu poll, dan tidak membuka polling sebelum waktu yang disepakati.

## Skenario lintas skill

### E02 · Rekonsiliasi setelah interupsi pemasangan lintas host

**Bidang C, D, G, H** · Dependensi C07,X08 · P1 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** Rancang preflight versi, daftar file yang benar-benar dimiliki installer dan mekanisme resume/revert per host. Batasi setiap percobaan pada profil sementara. [install.ps1](../install.ps1) · [install-codex.ps1](../install-codex.ps1) · [install.sh](../install.sh)

**Validasi.** Simulasikan kegagalan setelah host pertama diperbarui. Jalankan ulang dan bandingkan hash serta file konfigurasi eksternal.

**Kriteria penutupan.** Profil sementara berakhir konsisten pada versi sasaran atau kembali ke baseline; konfigurasi eksternal lainnya terpelihara.

### E03 · Penerimaan semantik saat backend menerima parameter tetapi mengabaikannya

**Bidang B, F, I, L** · Dependensi C10,T23,D14 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Pasangkan sumber kontrak, handler dan consumer lama. Bedakan perubahan dokumentasi tentang perilaku saat ini dari perubahan fungsi produk yang membutuhkan keputusan. [mcp-servers/shadow-api-mcp/discovery.test.mjs](../mcp-servers/shadow-api-mcp/discovery.test.mjs) · [shadow-uat/SKILL.md](../shadow-uat/SKILL.md)

**Validasi.** Uji dua nilai fields dengan subset berbeda pada fixture lokal, lalu ubah baseline requirement dari komitmen menjadi proposal.

**Kriteria penutupan.** Hasil melacak perbedaan ke kontrak/implementasi; perubahan scope dan decision owner dinyatakan; duplikasi dokumen tidak dihasilkan.

### E04 · Idempotensi lintas provider, cache dan recovery sesudah crash

**Bidang A, D, E, G** · Dependensi C09,T06,T18 · P0 · Risiko H · 3–6 hari-orang.

**Implementasi dan target.** Pindahkan oracle dari jumlah HTTP request ke jumlah mutasi bisnis. Modelkan fingerprint per tenant, retry window, durable receipt, antrian event dan rekonsiliasi provider. [shadow-integrate/SKILL.md](../shadow-integrate/SKILL.md) · [shadow-cache/SKILL.md](../shadow-cache/SKILL.md) · [shadow-resilience/SKILL.md](../shadow-resilience/SKILL.md)

**Validasi.** Simulasikan commit remote diikuti timeout dan crash lokal, lalu restart dengan cache kosong dan event duplikat dari waktu lebih lama.

**Kriteria penutupan.** Dampak bisnis tetap tunggal atau status unknown diserahkan untuk inquiry. Hasil dapat dijelaskan dari ledger sintetis.

### E05 · Pelepasan akses dan cutover saat shift operasional berganti

**Bidang C, E, G, I** · Dependensi C03,T05,T07 · P1 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** Replay serah terima dua arah dengan tanda terima per tanggung jawab, role efektif dan pemilik stop decision; verifikasi akses di simulasi dan rencanakan pencabutan sesuai kebijakan. [handoff/SKILL.md](../handoff/SKILL.md) · [shadow-handover/SKILL.md](../shadow-handover/SKILL.md) · [shadow-maintain/SKILL.md](../shadow-maintain/SKILL.md)

**Validasi.** Hentikan latihan saat calon penerima mampu membaca runbook tetapi tidak bisa mengakses dependensi yang dibutuhkan.

**Kriteria penutupan.** Item tertunda memiliki owner dan tenggat. Otorisasi revokasi live ditangani terpisah; tidak ada kredensial di artefak.

### E06 · Canary versi klien dengan distribusi pengguna yang berbeda

**Bidang A, B, F, G** · Dependensi T08,T17,T02 · P1 · Risiko H · 3–5 hari-orang.

**Implementasi dan target.** Susun matriks app/API/version/feature flag, bandingkan outcome per kohor dan hitung biaya minimum observasi sebelum memutuskan hold atau perluas. [shadow-mobile/SKILL.md](../shadow-mobile/SKILL.md) · [shadow-release/SKILL.md](../shadow-release/SKILL.md)

**Validasi.** Uji canary sintetis dengan mayoritas OS baru tetapi semua kegagalan terjadi pada OS lama. Ulangi dengan sampel kecil yang belum bisa dibedakan.

**Kriteria penutupan.** Keputusan memuat kohor terdampak, ketidakpastian dan mitigasi client/server yang dapat dilakukan. Klaim global tanpa representasi ditolak.

### E07 · Perubahan harga dan sumber regulasi yang terjadi di tengah penugasan

**Bidang A, B, J, I** · Dependensi X03,T02,T04 · P1 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** Pertahankan snapshot historis, tanggal efektif dan periode penugasan. Catat artefak terdampak, pilih perhitungan ulang hanya untuk bagian relevan, dan beri notifikasi owner sebagai draft internal. [shadow-finops/SKILL.md](../shadow-finops/SKILL.md) · [shadow-grc/SKILL.md](../shadow-grc/SKILL.md)

**Validasi.** Masukkan kontrak tarif bertanggal baru di tengah periode dan kewajiban yang mulai sesudah periode audit.

**Kriteria penutupan.** Laporan periode lama tetap reproducible. Perubahan biaya dan kontrol terkait punya sumber, tanggal berlaku dan review owner.

### E08 · Rehidrasi data yang sudah dihapus ketika restore backup

**Bidang D, E, G, J** · Dependensi T13,T18,T19 · P0 · Risiko H · 3–5 hari-orang.

**Implementasi dan target.** Tetapkan urutan restore, pemutaran ulang tombstone terversi, invalidasi cache, rebuild index dan pemeriksaan bisnis sebelum membuka akses. [shadow-privacy/SKILL.md](../shadow-privacy/SKILL.md) · [shadow-resilience/SKILL.md](../shadow-resilience/SKILL.md) · [shadow-search/SKILL.md](../shadow-search/SKILL.md)

**Validasi.** Fixture berisi permintaan hapus sesudah snapshot serta record legal hold. Restore pada lingkungan latihan dan periksa masing-masing salinan.

**Kriteria penutupan.** Data yang tidak lagi boleh diakses tidak muncul ke pencarian. Rekaman yang harus ditahan tetap terproteksi dan diketahui owner.

### E09 · Replay order semantik pada refactor lintas branch

**Bidang C, D, G, F** · Dependensi T03,T16,T22 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Ambil event sequence dari base dan candidate merge preview. Normalisasi waktu/ID volatil secara eksplisit dan bandingkan invariant ordering, jumlah serta deduplikasi pada caller lama. [shadow-git/SKILL.md](../shadow-git/SKILL.md) · [shadow-refactor/SKILL.md](../shadow-refactor/SKILL.md) · [shadow-test/SKILL.md](../shadow-test/SKILL.md)

**Validasi.** Branch A memindahkan publikasi event, branch B menambah subscriber yang membaca data committed; merge tekstual berjalan bersih.

**Kriteria penutupan.** Hasil integrasi yang mengirim event sebelum commit gagal; diff sederhana yang mempertahankan ordering tetap lulus.

### E10 · Efisiensi pemuatan saat vendor menambah metode bernama sama

**Bidang D, K, I, H** · Dependensi X04,X05,C13,D04,D05 · P2 · Risiko M · 2–3 hari-orang.

**Implementasi dan target.** Jadikan keputusan riset, unit analisis dan sumber path sebagai kunci seleksi; ukur count/bytes loaded serta jumlah dokumen/permintaan kepada peserta sebelum dan sesudah update. [shadow-design/SKILL.md](../shadow-design/SKILL.md) · [shadow-design/UPSTREAM_PROVENANCE.json](../shadow-design/UPSTREAM_PROVENANCE.json)

**Validasi.** Satu wawancara untuk perbaikan form, satu untuk validasi minat produk, dan satu brief campuran dengan satu moderator.

**Kriteria penutupan.** Dua brief pertama memuat metode berbeda secara tepat. Brief campuran menghasilkan satu instrumen dan handoff, serta angka biaya yang teramati.

### E11 · Kalibrasi reviewer untuk temuan UX yang tidak deterministik

**Bidang A, B, F, L** · Dependensi C04,D10,D11,X07 · P2 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Bangun pasangan screenshot/task sintetis, catat viewport, fokus, cara pemulihan dan penjelasan reviewer independen. Pisahkan kesepakatan reviewer dari bukti tugas selesai. [shadow-accessibility/SKILL.md](../shadow-accessibility/SKILL.md) · [shadow-design/SKILL.md](../shadow-design/SKILL.md)

**Validasi.** Bandingkan dashboard kurang kontras dengan dashboard lebih sederhana tetapi status darurat tersembunyi bagi keyboard user.

**Kriteria penutupan.** Setiap finding berat memiliki dampak tugas, kondisi tampilan dan pembanding. Ketidaksepakatan diberi langkah verifikasi, bukan diselesaikan dengan voting otomatis.

### E12 · Simulator keputusan dan retry untuk konektor workshop

**Bidang E, G, L, H** · Dependensi D16,D17 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Gunakan konektor tiruan stateful untuk menelusuri transisi dan request IDs; pisahkan queue pagination, identitas host, owner jawaban dan rekonsiliasi operasi ambigu. [shadow-design/SKILL.md](../shadow-design/SKILL.md) · [evals/evals.json](../evals/evals.json)

**Validasi.** Simulasikan timeout setelah create dan sisipkan pesan peserta yang tampak seperti perintah moderasi pada halaman kedua.

**Kriteria penutupan.** Tidak terjadi double create, tindakan moderator tanpa izin, atau distribusi URL host. Status unknown dipulihkan atau diserahkan ke fasilitator.

### E14 · Konservasi informasi saat dokumen resmi dirender ulang

**Bidang D, G, H, J** · Dependensi C15,T05 · P1 · Risiko M · 2–4 hari-orang.

**Implementasi dan target.** Buat invariant semantik yang menghubungkan field sumber ke tabel, lampiran dan hasil render. Prioritaskan struktur yang diperlukan penerima dan gunakan renderer yang sudah disetujui. [shadow-doc/scripts/doc_engine_test_suite.py](../shadow-doc/scripts/doc_engine_test_suite.py) · [shadow-handover/SKILL.md](../shadow-handover/SKILL.md)

**Validasi.** Hapus kolom pengecualian dari template pada fixture, serta ubah redaksi judul tanpa mengubah makna pada kontrol positif.

**Kriteria penutupan.** Regresi makna terdeteksi dengan lokasi field; perubahan visual yang setara tetap lulus. Penerima dapat melacak status item dari dokumen ke sumber.

### E15 · Batas keputusan berurutan ketika scope berubah saat agent aktif

**Bidang B, E, I, L** · Dependensi X07,T09,C03 · P1 · Risiko H · 2–4 hari-orang.

**Implementasi dan target.** Bangun fixture percakapan beberapa giliran: review, persetujuan terbatas, lalu instruksi berhenti atau pindah repo. Rekam state otorisasi sebelum setiap panggilan dan saat handoff. [shadow-monarch/SKILL.md](../shadow-monarch/SKILL.md) · [handoff/SKILL.md](../handoff/SKILL.md)

**Validasi.** Replay pada host ber-UI dan fallback tanpa UI. Sertakan jawaban terlambat untuk pertanyaan yang sudah tidak relevan.

**Kriteria penutupan.** Perubahan scope berlaku sebelum aksi dependen berikutnya, pilihan identik tidak ditanyakan ulang dan handoff memuat batas terakhir yang benar.
