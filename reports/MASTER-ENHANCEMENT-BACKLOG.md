# Master enhancement backlog

Stage A untuk 38 skill utama dan 17 modul pendukung terpilih. ID D01–D17 mengacu ke [rencana integrasi desain](skill-upgrade-design-library.md); path membedakan modul yang bernama sama. Gunakan [audit](skill-review.md), [engineering](skill-upgrade-core.md), [delivery](skill-upgrade-delivery.md), dan [silabus](skill-upgrade-competencies.md) untuk detail domain.

P0 menangani keyakinan palsu pada gate inti atau dampak tak terotorisasi; P1 membangun kemampuan utama; P2 meningkatkan ketepatan dan pengalaman; P3 untuk eksperimen opsional. Risiko L/M/H adalah dampak salah implementasi. Perkiraan hari-orang per unit mencakup fixture terarah. Dependency adalah prasyarat untuk integrasi. Semua validasi dan definisi selesai adalah kriteria usulan. Baseline setiap unit tetap harus direkam sebelum perubahan.

## Pemetaan bidang A–L

| Bidang | Keputusan yang dinilai | Item contoh |
|---|---|---|
| A · Domain Knowledge | Pilih pengetahuan sesuai produk, sektor dan versi. | C02, T04, T19 |
| B · Professional Reasoning | Bedakan hipotesis, ketidakpastian dan eskalasi. | C05, T07, T09 |
| C · Real-World Workflows | Sesuaikan alur dengan brownfield, greenfield, migrasi, insiden dan rilis. | C07, C11, T17 |
| D · Architecture and Engineering | Pertahankan kontrak, batas sistem dan kompatibilitas. | C10, X06, T15 |
| E · Risk and Safety | Batasi efek samping, hak akses dan cakupan. | X02, T13, T21 |
| F · Quality Engineering | Uji oracle dengan contoh positif, negatif dan regresi. | X01, C04, T22 |
| G · Failure Intelligence | Modelkan kegagalan parsial, state lama, recovery dan retry. | T06, T18, D16 |
| H · Tooling and Automation | Otomatiskan keputusan yang bisa diperiksa dari data aktual. | C12, T11, T14 |
| I · Skill Orchestration | Tetapkan owner, handoff dan resolusi konflik. | C03, T03, D13 |
| J · Knowledge Lifecycle | Kendalikan tanggal, versi, pemilik dan provenance. | X03, X05, T04 |
| K · Efficiency | Ukur biaya konteks dan kerja berulang. | X04, T02, T12 |
| L · User Experience | Berikan keputusan yang jelas dan hormati format keluaran. | C01, D02, D17 |

## Unit bersama

### X01 · Baseline dan pembanding atas tindakan nyata

**Bidang F, H, B** · Dependensi — · P0 · Risiko M · 3–5 hari-orang.

**Masalah.** Tanpa hash, state dan oracle serupa, skor sebelum/sesudah tidak dapat dibandingkan.

**Implementasi dan target.** Bekukan fixture repo, input, hasil minimal, hasil terlarang, trace efek samping dan label reviewer. Sediakan kasus terpisah untuk holdout dan variasi bahasa. [Komponen pemilik](../evals/evals.json)

**Validasi.** Dua reviewer menjalankan fixture sama dan membandingkan keluaran serta kasus yang belum terukur.

**DoD.** Manifest reproduksi menyebut revisi, dependency, host, oracle dan data missing. Holdout tidak terpapar pada tahap tuning.

### X02 · Scope tindakan dan persetujuan interaktif

**Bidang B, E, I, L** · Dependensi — · P0 · Risiko H · 3–5 hari-orang.

**Masalah.** Pengenalan topik dapat disalahartikan sebagai izin mengubah sistem.

**Implementasi dan target.** Propagasikan resource, host, fase, operasi dan keputusan eksplisit ke handoff. Bedakan review, preview, write dan publish. Jika pilihan material belum ditentukan, tanyakan sebelum aksi dependen. [Komponen pemilik](../shadow-monarch/scripts/execution_approval_gate.py)

**Validasi.** Replay review tanpa file write, persetujuan eksplisit satu aksi, dan perubahan target yang harus diputuskan ulang.

**DoD.** Setiap efek samping pada fixture punya otorisasi yang sesuai. Replay jawaban yang sudah jelas menghasilkan nol pertanyaan redundan.

### X03 · Sumber resmi bertanggal dan siklus pembaruan pengetahuan

**Bidang A, J, H** · Dependensi — · P1 · Risiko M · 2–4 hari-orang.

**Masalah.** Referensi lama tetap terlihat sah ketika pemanggil, framework, lisensi atau masa berlaku berubah.

**Implementasi dan target.** Tambahkan pemilik pembaruan, versi berlaku, tanggal akses, digest, cakupan, alasan pakai dan pemicu revalidasi ke indeks yang sudah ada. Simpan salinan resmi jika hak dan format mengizinkan. [Komponen pemilik](../shadow-doc/scripts/reference_verifier.py)

**Validasi.** Uji versi lama vs baru, sumber offline dan sumber diganti upstream. Uji apakah prinsip/kasus yang terdampak dapat ditelusuri ke sumber.

**DoD.** Referensi yang dikutip resolvable; status stale/unknown terlihat pada keputusan terdampak; perubahan sumber memicu tinjau ulang fixture relevan.

### X04 · Progressive disclosure yang dapat diukur

**Bidang K, H, L** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Masalah.** Memuat katalog luas untuk perbaikan kecil menaikkan biaya dan meningkatkan instruksi yang saling berbenturan.

**Implementasi dan target.** Gunakan dispatch top-level, pemilihan path menurut concern dan bacaan terbatas pada kasus yang perlu. Ukur jumlah path, karakter/konteks atau token bila tersedia serta temps untuk tugas trivial dan kompleks. [Komponen pemilik](../shadow-monarch/scripts/skill_router.py)

**Validasi.** Pasangkan koreksi ejaan dengan review multi-domain. Bandingkan artefak, bacaan, kualitas serta waktu terhadap baseline.

**DoD.** Tugas kecil tidak menambah bacaan tak relevan dan tugas kompleks tetap mengakses bukti wajib. Ambang biaya disepakati sesudah baseline dicatat.

### X05 · Kepemilikan adapter vendor dan path stabil

**Bidang D, I, J** · Dependensi X03 · P1 · Risiko M · 2–4 hari-orang.

**Masalah.** Nama modul sama dan tautan mesin asal mengacaukan resolusi setelah upstream berubah.

**Implementasi dan target.** Gunakan provenans dan path relatif penuh untuk identitas. Simpan keputusan serta perbaikan integrasi di owner lokal. Uji revision pin, collision, path relocation dan rollback ke versi adapter sebelumnya. [Komponen pemilik](../shadow-design/UPSTREAM_PROVENANCE.json)

**Validasi.** Pindah working directory, pasang dua modul bernama sama, serta simulasikan penggantian pin.

**DoD.** Semua adapter memilih path yang diverifikasi. Upgrade vendor tidak menghapus logika lokal; konflik pin menjadi status belum diverifikasi.

### X06 · Status dan bukti lintas alat yang kompatibel dengan caller lama

**Bidang D, F, H, I** · Dependensi X01 · P0 · Risiko H · 3–5 hari-orang.

**Masalah.** Sebuah PASS dapat berisi nol observasi dan caller dapat salah menafsirkan perluasan skema sebagai kelulusan.

**Implementasi dan target.** Pada dua pilot pertahankan input lama, pisahkan outcome dan completeness, simpan jumlah bukti/unknown dan revision. Uji konsumen lama sebelum memutuskan tipe bersama atau adapter lokal. [Komponen pemilik](../evals/run_evals.py)

**Validasi.** Replay satu payload legacy, satu payload sah lengkap dan satu bukti kosong. Bandingkan perilaku dua caller sebelum menyatukan tipe.

**DoD.** Kasus kosong tidak menjadi verified, caller lama memiliki jalur kompatibel atau migrasi jelas, dan perbedaan semantics tercatat.

### X07 · Kualifikasi lintas host dan pengelolaan variasi model

**Bidang F, I, K, L** · Dependensi X01,X02 · P1 · Risiko M · 3–6 hari-orang.

**Masalah.** Router deterministik lulus belum membuktikan tindakan awal, pilihan interaktif atau pemuatan instruksi oleh host.

**Implementasi dan target.** Gunakan fixture awal identik dan catat host/model/versi, jumlah pengulangan, aksi, interaksi, file dan biaya. Nilai keputusan terbuka dengan rubric manusia dan blind holdout. [Komponen pemilik](../evals/README.md)

**Validasi.** Bandingkan set natural language yang sama pada host yang tersedia, lalu uji fallback pada host tanpa UI interaktif.

**DoD.** Klaim paritas hanya mencakup kombinasi yang diuji. Variansi, kegagalan berat dan kondisi belum terukur muncul pada hasil.

### X08 · Promosi, pemantauan regresi dan rollback per unit

**Bidang C, E, G, J** · Dependensi X06,X07 · P1 · Risiko H · 2–4 hari-orang.

**Masalah.** Update skill atau referensi dapat mengubah perilaku agent lain yang masih membaca kontrak lama.

**Implementasi dan target.** Simpan base/candidate SHA, compatibility matrix serta daftar owner caller. Promosikan batch kecil berdasar kualifikasi, bandingkan fixture lama dan siapkan revert paket yang dapat dilatih di fixture terpisah. [Komponen pemilik](../install.ps1)

**Validasi.** Simulasi dua versi caller, instalasi sebagian dan rollback satu skill pada profil sementara.

**DoD.** Restore menghasilkan kontrak lama yang dapat dipakai; tidak ada dependensi global baru dan setiap pengecualian rollout punya owner.

## Engineering, desain dan discovery

### C01 · antislop

**Bidang B, K, L** · Dependensi X02 · P2 · Risiko L · 1–2 hari-orang.

**Masalah profesional.** Bagian Two Usage Modes memeriksa sesi dan preferensi lintas proyek. Saat berkas preferensi hilang, proses berhenti untuk menanyakan mode bahkan pada review baca-saja. Instruksi Monarch telah menetapkan `during`.

**Hasil yang dituju.** Pertahankan urutan sumber keputusan yang dapat dijelaskan. Pilihan sesi mengalahkan preferensi dengan cakupan lebih luas. Mode mengatur waktu review, sedangkan izin menulis mengikuti permintaan. Dua dimensi ini harus dihitung terpisah.

**Implementasi dan target.** Perbaiki bagian Two Usage Modes di kontrak. Tambahkan contoh kombinasi sesi, kebijakan proyek, konfigurasi host dan nilai rusak. Di eval percakapan, rekam jumlah pertanyaan serta daftar operasi tulis untuk mode audit. [antislop/SKILL.md](../antislop/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Tanpa keputusan yang berlaku, satu pertanyaan lalu tunggu. Instruksi yang disisipkan sebagai nilai settings tidak boleh dijalankan. Reviewer menyimpan asal pilihan dan bukti operasi file dari sandbox.

**DoD.** Preset proyek `during`, settings kosong, audit dialog → temuan di chat, nol pertanyaan mode dan nol file. Pilihan sesi `after` mengubah mode untuk sesi itu saja.

### C02 · context7

**Bidang A, H, J** · Dependensi X03 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Empat langkah Workflow berakhir dengan penerapan sintaks terkini. Tidak ada langkah eksplisit untuk mengekstrak versi lockfile atau menangani hasil untuk major berbeda.

**Hasil yang dituju.** Kebutuhan menjawab “cara menggunakan versi terpasang” berbeda dari “cara migrasi ke versi baru”. Ambil versi resolved dari lockfile/workspace, bedakan range manifest dari versi aktual, dan pastikan halaman dokumentasi sesuai versi serta penerbitnya.

**Implementasi dan target.** Perinci workflow resolver dan query dalam kontrak. Untuk monorepo, pilih manifest pemilik import. Tambahkan alur saat hasil multi-major atau resolver offline, termasuk dokumentasi resmi yang sudah terbundel dan deklarasi tipe lokal sebagai bukti terbatas. [context7/SKILL.md](../context7/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Hasil untuk major lain tidak menjadi dasar edit. Jika versi tidak bisa dipastikan, tandai ketidakpastian dan serahkan ke owner dependency bila keputusan migrasi diperlukan. Simpan nama simbol, versi, sumber dan pemeriksaan lokal yang dilakukan.

**DoD.** Fixture dua workspace dengan dua major. Jawaban harus mengaitkan contoh/simbol dengan workspace yang ditanya, versi, dan sumber yang memuatnya.

### C03 · handoff

**Bidang D, G, I** · Dependensi X02,X06 · P1 · Risiko H · 3–5 hari-orang.

**Masalah profesional.** Kontrak merge memelihara readiness terendah dan memberi peringatan konflik, tetapi fallback save menyebut path drive D pada mesin penulis.

**Hasil yang dituju.** Pisahkan identitas repo, worktree/cabang, label sesi, dan tingkat kesiapan. Pertahankan history dan warning pada merge. Pilih otomatis hanya jika identitas pekerjaan terverifikasi.

**Implementasi dan target.** Hilangkan fallback path per mesin dalam kontrak. Periksa respons save/load/merge pada MCP yang ada, bandingkan Git state saat load dengan keadaan checkout. Tambahkan data opsional yang kompatibel dengan snapshot lama jika identitas saat ini kurang. [handoff/SKILL.md](../handoff/SKILL.md) · [mcp-servers/shadow-handoff-mcp/index.mjs](../mcp-servers/shadow-handoff-mcp/index.mjs)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Cabang/HEAD berbeda menahan langkah yang menyentuh file terdampak sampai diperiksa. Snapshot lama tanpa metadata harus dapat dibaca dengan status tidak pasti. Serahkan daftar konflik keputusan dan sumber masing-masing kepada agen penerus.

**DoD.** Simpan dua label pada fixture temp, pindahkan checkout, muat snapshot by project/label, lalu gabungkan. Bukti yang belum diuji harus tetap ada dan jejak masing-masing keputusan dapat ditelusuri.

### C04 · shadow-accessibility

**Bidang A, F, L** · Dependensi X01 · P1 · Risiko M · 3–5 hari-orang.

**Masalah profesional.** Pilar formulir mewajibkan `<label htmlFor>` untuk setiap input. Aturan React yang spesifik terlalu sempit untuk kontrol native dengan label pembungkus dan proyek HTML non-React.

**Hasil yang dituju.** Nilai nama, peran, status, urutan fokus dan pemulihan fokus dari hasil render. Pisahkan pemeriksaan otomatis, pengamatan keyboard, dan pengujian assistive technology yang benar-benar tersedia.

**Implementasi dan target.** Susun ulang pilar formulir di kontrak dengan contoh HTML dan React, termasuk label pembungkus, label eksplisit dan kontrol kustom. Tautkan shadow-browser untuk pengambilan accessibility tree bila host mendukung, lalu dokumentasikan tahapan manual untuk kasus yang tersisa. [shadow-accessibility/SKILL.md](../shadow-accessibility/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Placeholder tunggal pada kontrol tanpa nama memicu temuan. Hasil inspeksi tree tanpa screen reader tidak boleh diberi status lulus screen reader. Serahkan elemen, state, urutan tombol, hasil teramati dan dampak ke pemilik komponen.

**DoD.** Dua input dengan nama yang benar melalui teknik native berbeda diterima. Dialog memindahkan dan mengembalikan fokus ke pemicu setelah ditutup.

### C05 · shadow-architect

**Bidang A, B, D** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Persyaratan Mandatory Architecture Deliverables dan gate menuju plan/bootstrap tidak membedakan pertanyaan desain satu modul dari desain aplikasi penuh secara operasional.

**Hasil yang dituju.** Bandingkan biaya koordinasi, coupling data, batas transaksi, failure isolation dan reversibilitas. Rekomendasi lokal cukup ketika keputusan dapat dibalik. ADR dibutuhkan bila kontrak, data owner atau deployment lintas tim berubah.

**Implementasi dan target.** Beri tiga tingkat keluaran pada kontrak, yaitu konsultasi, desain perubahan lintas modul, dan keputusan sistem. Pakai preseden brownfield dan template ADR yang ada. Dokumentasikan alternatif, pemilik keputusan, bukti, dan pemicu evaluasi ulang. [shadow-architect/SKILL.md](../shadow-architect/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Jangan mengusulkan microservice hanya karena ada dua direktori. Penerima handoff harus bisa menyebut kondisi terukur yang akan membatalkan rekomendasi.

**DoD.** Untuk batas validasi lokal, tunjukkan modul pemilik dan invariant tanpa menciptakan diagram sistem baru. Untuk memisahkan deployment, hasil memuat konsekuensi data dan strategi transisi.

### C06 · shadow-auth

**Bidang A, D, E, G** · Dependensi X02 · P0 · Risiko H · 4–7 hari-orang.

**Masalah profesional.** Bagian Policy Test Matrix menyebut 403/404 juga untuk pemanggil tanpa autentikasi. Aturan literal bisa mengubah respons 401 yang sudah menjadi kontrak endpoint.

**Hasil yang dituju.** Pisahkan autentikasi, izin aksi, hak melihat resource dan batas tenant. Untuk sistem SSO, buktikan issuer serta pemetaan principal dari SDK yang dimiliki proyek. Retensi audit dan penyamaran data mengikuti kebutuhan produk dan risiko.

**Implementasi dan target.** Perbaiki Policy Test Matrix di kontrak. Mulai dari respons error dan entrypoint server yang dipakai; catat principal/aksi/resource/tenant dan lifecycle sesi. Gunakan shadow-api sebagai owner kontrak HTTP dan shadow-privacy untuk kebijakan log. [shadow-auth/SKILL.md](../shadow-auth/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Klaim role dari input tidak memberi akses; log uji tidak menyimpan kredensial atau token. Handoff ke tim API menyertakan tabel policy, status/error yang diharapkan, serta bukti terhadap fixture.

**DoD.** Pada fixture server lokal, tiap identitas yang disiapkan memperoleh respons serta header sesuai kontrak, dan fungsi mutasi hanya dipanggil pada izin yang cocok.

### C07 · shadow-bootstrap

**Bidang C, E, G, H** · Dependensi X02,X03 · P0 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Delapan pilar wajib menggabungkan OpenAPI, DB/ORM, health probe DB+Redis, Compose dan struktur direktori tertentu. Proyek CLI offline dan situs statis juga masuk cakupan deskripsi greenfield.

**Hasil yang dituju.** Pisahkan kebutuhan lintas proyek (cara build, test, konfigurasi dasar) dari kapabilitas bersyarat seperti persistensi, queue, HTTP/API docs, telemetry, container dan CI. Gunakan stack yang dipilih. Ketidakjelasan format atau biaya layanan memerlukan pilihan pengguna.

**Implementasi dan target.** Ganti delapan pilar seragam dengan tabel kebutuhan → bukti → kapabilitas → generator resmi → berkas yang diharapkan. Gunakan verifier resmi untuk provenance generator. Buat preview manifest dan jalankan generator hanya di target yang disetujui. Uji pengulangan pada target nonkosong dan kegagalan parsial. [shadow-bootstrap/SKILL.md](../shadow-bootstrap/SKILL.md) · [shadow-monarch/scripts/official_first_verifier.py](../shadow-monarch/scripts/official_first_verifier.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Situs statis tidak memperoleh OpenAPI, ORM, Redis atau Compose tanpa kebutuhan. Target yang berisi file pengguna tidak boleh tertimpa saat retry. Serahkan manifest, versi generator, perintah reproduce dan laporan file yang disentuh.

**DoD.** CLI offline mendapat entrypoint, build/test dan konfigurasi minimum. Layanan ber-DB mendapat migrasi dan readiness sesuai stack. Verifikasi kedua hasil dengan menjalankan entrypoint normal di direktori sementara.

### C08 · shadow-browser

**Bidang C, F, H, L** · Dependensi X02 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Bagian Console & Network meminta pelaporan semua 4xx/5xx. Tanpa oracle per skenario, respons valid pada alur login gagal dapat dibaca sebagai regresi.

**Hasil yang dituju.** Nyatakan oracle untuk tiap aksi melalui status, konten, fokus dan state UI. Saat server tidak dapat dijangkau, bedakan kegagalan lingkungan dari regresi. Batasi pemeriksaan ke rute dan role yang relevan.

**Implementasi dan target.** Ubah checklist browser menjadi alur siap-fixture → aksi → ekspektasi → observasi → cleanup. Pilih viewport berdasarkan layout dan target tugas. Periksa request terkait dan log dengan redaksi data sensitif. [shadow-browser/SKILL.md](../shadow-browser/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. 404 pada JS, klik yang tidak berfungsi atau request ke luar host yang disetujui harus terlihat dalam hasil. QA menyerahkan langkah, viewport, URL teredaksi, status aktual dan batas pengujian ke engineer.

**DoD.** Pada fixture login invalid, 401 dan pesan pemulihan tepat dinilai lulus. Jalankan satu alur sukses terpisah.

### C09 · shadow-cache

**Bidang A, D, E, G** · Dependensi C06 · P1 · Risiko H · 3–5 hari-orang.

**Masalah profesional.** Bagian Idempotency Keys menetapkan TTL 24 jam dan replay respons tersimpan, tetapi contoh rekaman tidak mengikat kunci ke fingerprint payload.

**Hasil yang dituju.** Turunkan scope cache dari tenant, identitas, representasi dan perubahan otorisasi. Untuk idempotensi, sepakati arti kunci, fingerprint, response replay, retensi serta keterkaitan dengan commit durable. Pilih mekanisme yang sesuai jaminan bisnis.

**Implementasi dan target.** Pisahkan bab freshness dan idempotency. Dokumentasikan snapshot waktu yang dapat diterima, pemicu invalidasi dan sumber otoritatif. Arahkan atomicity domain ke shadow-concurrency. Jangan mewajibkan Redis bila uniqueness DB sudah mencukupi. [shadow-cache/SKILL.md](../shadow-cache/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Kunci sama dengan payload berbeda harus mengikuti kebijakan konflik. Tenant berbeda tidak mendapat entri cache tenant pertama. Serahkan skema kunci dan tabel transisi ke owner backend/frontend dengan batas kesegaran yang dipilih.

**DoD.** Model lokal mencakup timeout setelah commit dan replay payload sama, menghasilkan satu perubahan stok. Perubahan akses menghapus keterlihatan data lama dari cache yang relevan.

### C10 · shadow-compat

**Bidang A, D, F, I** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Aturan akhir meminta pengujian terhadap setiap klien aktif sebelum merge. Skill belum menentukan bukti pengganti bila klien eksternal tidak dapat dijalankan tim.

**Hasil yang dituju.** Klasifikasikan kompatibilitas bentuk, makna, perilaku, data dan platform. Bedakan konsumen yang diketahui, dapat diuji, dan belum teramati. Pilih replay fixture, contract test, canary yang disetujui atau eskalasi berdasar risiko.

**Implementasi dan target.** Tambahkan inventaris konsumen dan matriks versi ke kontrak. Gunakan contract/golden replay yang sudah ada. Kaitkan rollout dan rollback ke owner serta versi konsumen, tanpa mewajibkan framework test baru. [shadow-compat/SKILL.md](../shadow-compat/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Jika aplikasi mitra offline, catat bukti yang belum diperoleh. Status semua klien kompatibel harus ditolak. Handoff memuat owner kontak, keputusan release yang tertunda dan batas observabilitas.

**DoD.** Jalankan replay payload lama dan bandingkan jumlah item, cursor serta pemrosesan klien. Temuan menyebut dampak terhadap versi tertentu walau schema diff kosong.

### C11 · shadow-data

**Bidang C, D, G** · Dependensi C10 · P0 · Risiko H · 4–7 hari-orang.

**Masalah profesional.** Playbook fase migrasi dan batas izin tersedia. Keputusan melepas skema lama memerlukan bukti konsumsi lintas layanan serta owner operasional yang spesifik proyek.

**Hasil yang dituju.** Buat keputusan per fase berdasarkan ukuran tabel, pola baca/tulis, indeks, locking, replika dan opsi rollback. Batas batch dan ambang lag diambil dari lingkungan nyata setelah disetujui. Hapus janji universal “zero impact”.

**Implementasi dan target.** Di tabel expand/backfill/switch/contract, tambahkan owner pembaca, penulis, checkpoint, penanganan konflik dan kondisi abort. Uji SQL target pada DB lokal yang seversi bila tersedia. Serahkan kontrak payload lama/baru ke shadow-compat. [shadow-data/SKILL.md](../shadow-data/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Jika consumer lama masih membaca kolom atau ada mismatch yang belum dijelaskan, tahan contract. Handoff menyertakan hasil rekonsiliasi, batas verifikasi lock/lag dan prosedur rollback per fase.

**DoD.** Fixture backfill dihentikan setelah satu batch, dilanjutkan dengan checkpoint sambil ada satu update. Invariant hasil akhir dan jumlah baris terjaga, data lebih baru tetap tersimpan.

### C12 · shadow-db

**Bidang A, D, F, H** · Dependensi X06 · P1 · Risiko H · 4–7 hari-orang.

**Masalah profesional.** Bagian ETL menyebut enam hasil generator production-ready. Bukti bahwa file terbentuk saja belum mengukur keberhasilan transformasi, checkpoint atau rekonsiliasi target.

**Hasil yang dituju.** Pisahkan discovery read-only, pembangkitan desain, validasi sintaks, eksekusi lokal dan rekonsiliasi. Catat kemampuan driver/engine dan perilaku konversi yang hilang. Runtime yang tak tersedia membatasi klaim.

**Implementasi dan target.** Perinci kapabilitas dan bukti per target di kontrak. Pada MCP telusuri detectEngine, mapTypeToTargetEngine dan handler generator. Tambahkan manifest hasil per artefak serta peringatan pemetaan lossy tanpa memecahkan caller lama. [shadow-db/SKILL.md](../shadow-db/SKILL.md) · [mcp-servers/shadow-db-mcp/index.mjs](../mcp-servers/shadow-db-mcp/index.mjs)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Saat hanya XML dapat diparse, hasil belum membuktikan job Pentaho berjalan. Unknown host tetap tertahan. Serahkan mapping yang perlu keputusan dan selisih rekonsiliasi ke DBA.

**DoD.** Gunakan sumber lokal berisi desimal, dua NULL, timestamp, dan kunci gabungan. Cocokkan jumlah, nilai, key dan hasil replay dua batch di target lokal yang benar-benar tersedia.

### C13 · shadow-design

**Bidang B, I, K, L** · Dependensi X04,X05 · P1 · Risiko M · 3–5 hari-orang.

**Masalah profesional.** Blok Foreign-Key Reference Routing menggunakan tautan `<repo>/...` ke checkout penulis. Pemilihan topik bisa benar namun rujukannya gagal dibuka dari instalasi lain.

**Hasil yang dituju.** Gunakan bukti alur dan state yang dapat dicapai, lalu pilih referensi relevan secara relatif terhadap paket terpasang. Bedakan state domain dari status jaringan atau kondisi tampilan; beberapa state hanya berlaku untuk satu komponen.

**Implementasi dan target.** Ganti alamat drive absolut di tabel Foreign-Key Reference Routing dengan referensi portabel. Uji resolusi setelah paket dipindah. Tambahkan kolom owner, event, guard, feedback, recovery dan alasan N/A pada model state. [shadow-design/SKILL.md](../shadow-design/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Tolak tautan absolut yang hanya ada di mesin penulis serta state buatan tanpa transisi. Handoff ke frontend/QA menyertakan alur, state yang dicapai dan acceptance yang bisa diuji.

**DoD.** Pada instalasi sementara di root lain, semua tautan lokal yang dipakai dapat dibuka. Untuk fixture alur pengajuan, trace satu user story sampai recovery setelah timeout.

### C14 · shadow-discovery

**Bidang B, I, L** · Dependensi X02 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Bagian Mandatory Discovery Deliverables dan Stage 1 Exit Gate cocok untuk discovery proyek, namun menambah beban untuk satu ketidakjelasan lokal bila diterapkan sekaligus.

**Hasil yang dituju.** Pilih kedalaman berdasarkan besarnya keputusan, biaya kesalahan dan nilai bukti. Pisahkan fakta dari asumsi dan pihak yang berwenang menyelesaikan konflik. Gunakan interaksi langsung ketika satu jawaban dapat membuka pekerjaan.

**Implementasi dan target.** Tambahkan tiga jalur pada kontrak: klarifikasi satu keputusan, discovery fitur dan discovery proyek. Untuk masing-masing nyatakan minimum input, keluaran, kondisi berhenti dan kriteria eskalasi. Hubungkan PRD penuh hanya dengan kebutuhan yang sesuai. [shadow-discovery/SKILL.md](../shadow-discovery/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Jangan mengarang jawaban saat owner belum merespons atau membuat PRD untuk satu pilihan. Handoff mencatat keputusan, siapa yang memutuskan, tanggal dan bagian requirement yang berubah.

**DoD.** Ambiguitas apakah “7 hari” kalender atau kerja memicu satu pertanyaan berpilihan kepada pemilik kebijakan. Setelah jawab, tambahkan contoh sebelum/sesudah tanggal batas ke acceptance.

### C15 · shadow-doc

**Bidang C, D, H, J** · Dependensi X03,X06 · P1 · Risiko M · 3–5 hari-orang.

**Masalah profesional.** Golden Laws meminta regenerasi lewat doc_scaffold.py, sedangkan bagian 3A memprioritaskan generator lokal dan membatasi AST pada global engine. Urutan baca dapat mengubah tindakan.

**Hasil yang dituju.** Turunkan graf sumber → transformasi → output → validasi dari konfigurasi dan perintah yang didukung. Bila ada dua generator aktif, pisahkan target dan ownership. Dukungan sebagian dapat diselesaikan melalui adapter kecil jika proyek mengizinkan.

**Implementasi dan target.** Selaraskan Golden Laws dan urutan pada bagian 3A. Kaitkan resolve, assess_generator_compatibility dan pengujian suite dokumen ke keputusan yang sama. Verifikasi referensi, gambar, font atau diagram sesuai permintaan artefak. [shadow-doc/SKILL.md](../shadow-doc/SKILL.md) · [shadow-doc/scripts/doc_orchestrator.py](../shadow-doc/scripts/doc_orchestrator.py) · [shadow-doc/scripts/doc_engine_test_suite.py](../shadow-doc/scripts/doc_engine_test_suite.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Output yang tidak punya sumber terverifikasi atau dua pipeline tanpa owner menahan penulisan. Handoff berisi lokasi sumber, entrypoint, tipe output, manifest perubahan dan mana yang sudah divalidasi secara visual.

**DoD.** Fixture repo memiliki generator internal, satu sumber editable dan satu output. Perubahan satu paragraf menghasilkan diff di jalur yang diharapkan, tidak menambah pipeline dan dapat dibangun ulang.

## Delivery, operasi dan assurance

### T01 · shadow-eval

**Bidang A, B, F, H** · Dependensi X01,X06 · P0 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Self-test 9/9. Namun satu sampel kosong menghasilkan skor sempurna pada ketiga ukuran dan gate_passed=True. Nilai bawaan untuk komponen yang tidak terukur membuat dataset tanpa bukti tampak lulus.

**Hasil yang dituju.** Pisahkan kualitas retrieval, dukungan per klaim, keputusan abstain, dan isolasi tenant. Pengguna harus dapat menjawab apakah perubahan yang lebih murah masih layak dipromosikan untuk kelompok query tertentu.

**Implementasi dan target.** Tambahkan tipe sampel (answerable, abstain, isolation) beserta field wajib di scorer. Hitung denominator, jumlah sampel eligible, dan abstention false accept/reject per bahasa. Bandingkan dua revisi pada ID sampel dan snapshot korpus yang sama, tampilkan delta per kelompok sebelum agregat. Simpan keputusan manusia tentang ambang jika biaya kesalahan berbeda. [Instruksi pemilik](../shadow-eval/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-eval/scripts/ai_eval_gate.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Sampel kosong, tenant uji hilang, atau split pengembangan tumpang tindih dengan holdout harus menghalangi klaim kelulusan terkait.

**DoD.** Jawaban dengan dua klaim, hanya satu didukung, harus menghitung satu klaim didukung dari dua dan menunjukkan kutipan per klaim.

### T02 · shadow-finops

**Bidang A, B, C, K** · Dependensi X03 · P1 · Risiko M · 3–5 hari-orang.

**Masalah profesional.** Self-test 9/9. Instruksi meminta HPA pada setiap Deployment/StatefulSet dan label tenant_tier pada semua resource. Aplikasi tanpa multitenansi atau beban stabil tetap terkena aturan itu.

**Hasil yang dituju.** Kaitkan perubahan teknis ke biaya per hasil bisnis dan batas kualitas layanan. Bandingkan estimasi, biaya faktual, dan gejala penghematan semu akibat volume turun.

**Implementasi dan target.** Mulai dari billing export dan struktur alokasi yang ada. Pisahkan committed/minimum, variable, shared, tax/currency dan unallocated. Untuk LLM, parameterkan input/output, cache dan kelas model dari bukti kontrak bertanggal. Identifikasi cost per successful workflow, beri rentang sensitivitas, dan validasi terhadap total invoice serta volume transaksi. [Instruksi pemilik](../shadow-finops/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-finops/scripts/finops_cost_auditor.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Invoice tanpa rincian kategori cache atau model price region tidak boleh menghasilkan penghematan pasti. Untuk layanan non-Kubernetes, laporan tidak merekomendasikan HPA.

**DoD.** Contoh dua tim yang berbagi gateway, satu invoice dan biaya tak teralokasi menghasilkan rekonsiliasi yang menjumlah persis pada total. Bandingkan dua model pada kesuksesan bisnis setara.

### T03 · shadow-git

**Bidang C, D, G, I** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Contoh detect-strategy --repo . dalam tabel gagal dengan exit 2. Parser mengharapkan opsi global sebelum subcommand. Perintah dengan urutan benar mengenali trunk-based dan main.

**Hasil yang dituju.** Koordinasikan branch, pemilik berkas, dan perubahan kontrak semantik sehingga konflik nontekstual juga terlihat sebelum integrasi.

**Implementasi dan target.** Perbaiki urutan opsi dalam contoh CLI. Tambahkan smoke test dokumentasi terhadap repo sementara. Rekam SHA pangkal, target, rencana write-set dan dependensi handoff. Saat ref target bergerak, invalidate hasil dry-run lama dan jalankan ulang perbandingan. Deteksi benturan kontrak melalui konsumen yang terpengaruh, misalnya migrasi yang dipakai dua branch. [Instruksi pemilik](../shadow-git/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-git/scripts/git_orchestrator.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Dua branch mengubah kontrak produsen/konsumen secara tidak kompatibel pada file berbeda harus ditandai untuk pengujian kontrak walau merge Git bersih.

**DoD.** Dua worktree dengan perubahan terpisah dan base sama menghasilkan preview bersih. Ketika target maju sesudah preview, integrator menghitung ulang sebelum memakai bukti itu.

### T04 · shadow-grc

**Bidang A, B, F, J** · Dependensi X03 · P1 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Self-test 8/8 termasuk penolakan klaim tinggi dengan bukti hilang. Fungsi validate_audit_findings menggunakan tanggal acuan bawaan tetap 2026-11-16. Tanpa tanggal penugasan, analisis berikutnya dapat memakai konteks waktu yang keliru.

**Hasil yang dituju.** Hasilkan matriks kewajiban dan kontrol berdasar sektor, yurisdiksi, tanggal penilaian dan periode bukti. Pisahkan desain kontrol dari efektivitas operasional dan opini formal.

**Implementasi dan target.** Buat input scope bertanggal dan register sumber resmi yang dimiliki pemilik regulasi. Simpan version/effective interval, kriteria applicability dan mapping many-to-many kontrol. Bentuk catatan bukti yang mencakup periode, populasi, sampling, workpaper dan reviewer. Tandai missing evidence atau conflicting interpretation sebelum menghitung cakupan. [Instruksi pemilik](../shadow-grc/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-grc/scripts/grc_assurance_engine.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Status sertifikasi atau kepatuhan penuh tidak dapat diturunkan dari self-assessment. Rujukan tidak berlaku pada tanggal penilaian harus diblokir atau ditandai perlu verifikasi.

**DoD.** Dokumen kebijakan tersedia sementara sampel transaksi satu kuartal hilang. Desain dapat dinilai, efektivitas operasional harus menunggu bukti. Tanggal berbeda memilih versi register yang sesuai.

### T05 · shadow-handover

**Bidang C, I, L** · Dependensi C03 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Skill membedakan serah terima klien dari handoff sesi dan melarang rahasia plaintext. Bagian inventaris menetapkan tag v1.0.0; kontrak untuk versi lanjutan dapat meminta tag berbeda.

**Hasil yang dituju.** Ukur kesiapan penerima untuk mengoperasikan rilis yang diserahkan. Hubungkan aset, akses dan keterampilan operator dengan scope kontrak dan proof of receipt.

**Implementasi dan target.** Ambil scope dari kontrak, stage dan versi aktual. Buat daftar deliverable dengan owner pengirim/penerima, digest atau location, kriteria penerimaan, status pengecualian dan pertanggungan garansi. Rencanakan walkthrough dan reverse demonstration oleh operator. Credential hanya direferensikan melalui jalur vault atau mekanisme transfer resmi. [Instruksi pemilik](../shadow-handover/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. BAST belum ditandatangani, kunci vault tidak dapat diakses penerima, atau digest berbeda harus membuat item pending. Jangan menaruh nilai secret di bukti.

**DoD.** Serah terima parsial untuk rilis 3.2 memakai digest itu, menyertakan pemilik backup; penerima dapat menggunakan akses uji dan menunjukkan prosedur pemulihan dari runbook.

### T06 · shadow-integrate

**Bidang A, C, D, G** · Dependensi X02,C10 · P0 · Risiko H · 4–7 hari-orang.

**Masalah profesional.** Instruksi mewajibkan batas usia lima menit dan Idempotency-Key. Dukungan header serta kebijakan timestamp bergantung pada kontrak penyedia. Header bebas belum membuktikan deduplikasi di sisi penyedia.

**Hasil yang dituju.** Pisahkan keberhasilan transport dari keberhasilan transaksi bisnis. Jadikan hasil yang belum pasti dapat dilacak dan direkonsiliasi tanpa menghasilkan side effect kedua.

**Implementasi dan target.** Temukan SDK/provider dan workflow aktif. Buat matriks kemampuan yang mencakup dukungan idempotency key, status inquiry, umur retry, signature scheme, dan urutan event. Tetapkan state local pending, confirmed, failed dan unknown. Gunakan ledger/pola outbox yang sudah ada untuk korelasi dan rekonsiliasi sesuai jaminan provider. [Instruksi pemilik](../shadow-integrate/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Tanpa idempotensi atau status inquiry, timeout tidak memicu retry POST otomatis. Event lebih lama yang tiba belakangan tidak boleh menurunkan status final.

**DoD.** Simulasikan timeout setelah commit penyedia. Provider mendukung inquiry dan mengembalikan ID yang sama, sehingga proses lokal dipulihkan sekali.

### T07 · shadow-maintain

**Bidang B, C, G, I** · Dependensi X02 · P1 · Risiko H · 3–5 hari-orang.

**Masalah profesional.** Bagian hotfix meminta rollback segera jika deploy terakhir menyebabkan insiden. Kalimat tersebut mendahului pemeriksaan kompatibilitas data, kewenangan operator, dan ketersediaan target rollback.

**Hasil yang dituju.** Bantu incident commander memulihkan layanan ketika penyebab belum pasti serta ketika rollback berpotensi memperparah kerusakan.

**Implementasi dan target.** Tentukan pemilik insiden, tingkat dampak dan jam pembaruan. Bangun timeline perubahan/telemetri dan daftar hipotesis yang masing-masing memiliki bukti penyangkal. Bandingkan isolasi, flag-off, rollback, degradasi dan forward-fix berdasarkan waktu pemulihan, data at risk dan reversibilitas. Kaitkan postmortem ke tindakan berowner, tenggat dan verifikasi pencegahan. [Instruksi pemilik](../shadow-maintain/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Insiden setelah migrasi yang tidak kompatibel tidak cukup untuk rollback aplikasi. Jam insiden dan root cause harus dapat ditandai sementara saat bukti kurang.

**DoD.** Setelah flag baru meningkatkan error, tabletop memilih flag-off yang dapat dibalik, lalu memverifikasi pemulihan dari sinyal pengguna.

### T08 · shadow-mobile

**Bidang A, C, F, H** · Dependensi X03 · P1 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Self-test 9/9. Fungsi audit_mobile_text menganggap seluruh path berisi kata test sebagai varian uji. File release dalam folder contest kehilangan temuan debuggable yang terdeteksi pada path biasa.

**Hasil yang dituju.** Nilai artefak distribusi yang benar-benar akan dikirim, termasuk build variant, merged manifest, channel pembaruan, migrasi storage dan interoperabilitas lintas versi aplikasi.

**Implementasi dan target.** Temukan flavor, build type, bundle ID/application ID, konfigurasi release efektif dan target distribusi dari project. Normalisasi temuan per target, bedakan source indikatif dari artefak merged/signed terverifikasi. Tambahkan pemeriksaan cold upgrade, offline/low-memory, deep-link intents dan fallback saat device capability tidak tersedia, sesuai fitur terdampak. [Instruksi pemilik](../shadow-mobile/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-mobile/scripts/mobile_release_gate.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Bukti emulator debug untuk klaim signed release atau manifest library yang berbeda dari merged manifest harus diberi status belum cukup. Akses store live membutuhkan keputusan terpisah.

**DoD.** Release di path contest tetap diperiksa; debug source set yang sah tidak dianggap bukti release. Upgrade fixture dari versi lama harus mempertahankan session/migrasi sesuai kontrak.

### T09 · shadow-monarch

**Bidang B, E, I, K, L** · Dependensi X01,X02 · P0 · Risiko H · 4–7 hari-orang.

**Masalah profesional.** Pada prompt umum pemilik default memang sesuai. Akan tetapi beberapa prompt spesialis di tabel berakhir di Monarch. Pencocokan sinyal dan fallback dapat menghapus pemilik spesialis meski kalimat bermakna jelas bagi pengguna.

**Hasil yang dituju.** Router perlu mengetahui tujuan, fase, objek, pemilik, dan batas tindakan. Permintaan dokumentasi yang ambigu semestinya berhenti pada pilihan pengguna sebelum menciptakan format baru.

**Implementasi dan target.** Pisahkan kandidat topic dari resolusi tugas. Gunakan contoh asli Indonesia/Inggris, negasi, koreksi serta task majemuk. Sertakan alasan singkat per kandidat, kondisi bertanya dan apa yang telah diputuskan. Mulai dengan shadow evaluation pada label yang diadjudikasi manusia sebelum mengubah default. Tambahkan uji dari prompt sampai tindakan pertama agent di setiap host. [Instruksi pemilik](../shadow-monarch/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-monarch/scripts/skill_router.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Kata “jangan load test” dalam permintaan unit test tidak mengaktifkan eksekusi beban. Penyebutan nama tool dalam log atau kutipan dokumen tidak memperluas scope.

**DoD.** Permintaan review webhook tanpa perubahan memuat skill integrasi dan menjaga fase review. Permintaan API docs generik dengan ringkasan README memunculkan pertanyaan format sebelum tulis.

### T10 · shadow-ops

**Bidang C, D, E, G** · Dependensi X02 · P1 · Risiko H · 3–5 hari-orang.

**Masalah profesional.** Bagian akhir melarang infrastruktur tambahan tanpa permintaan. Bagian parity sekaligus meminta versi DB, Redis, dan topologi proxy identik pada seluruh environment. Syarat analisis berlaku terlalu luas pada platform terkelola.

**Hasil yang dituju.** Turunkan rencana operasi dari topologi nyata dan kemampuan platform. Buktikan apa yang akan berubah serta cara memulihkannya sebelum perubahan live.

**Implementasi dan target.** Baca manifest dan pipeline yang dimiliki repo. Petakan deploy unit, stateful dependency, RBAC, secret reference, observability, target dan owner. Pilih profil static hosting, PaaS, VM, atau cluster berdasarkan bukti. Sajikan diff rencana, dependensi, dampak pengguna, canary jika tersedia dan guardrail rollback. [Instruksi pemilik](../shadow-ops/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-ops/references/04-CICD-GITHUB-GITLAB-ZERO-DOWNTIME.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Permintaan review konfigurasi tidak memicu deploy. Rencana cluster tidak boleh memperkenalkan Redis atau Terraform semata karena contoh playbook.

**DoD.** Aplikasi statis tanpa datastore menghasilkan pemeriksaan cache invalidation dan asset rollback. Layanan stateful mendapat pemeriksaan kesiapan data sesuai topologinya.

### T11 · shadow-perf

**Bidang A, C, F, G, H** · Dependensi X02,X06 · P0 · Risiko H · 4–7 hari-orang.

**Masalah profesional.** Probe lokal kontrak berisi POST /orders saja: generator berhasil, memasukkan GET /healthz yang tak tercantum, dan tidak menghasilkan http.post. Pemeriksaan status per operasi memakai <500. Bagian narasi menjanjikan korelasi data tulis.

**Hasil yang dituju.** Susun model beban dari perjalanan bisnis dan kontrak yang tersedia. Output harus menunjukkan bagian yang bisa diukur secara aman dan estimasi biaya sebelum pengujian.

**Implementasi dan target.** Perluas scaffold dengan discovery sumber kontrak, operasi yang secara eksplisit dipilih dan status respons per operation. Representasikan prasyarat fixture, autentikasi, korelasi resource, cleanup dan parameter distribusi beban. Tawarkan dry-run terhadap mock lokal serta batas stop, target allowlist dan anggaran. Hasil perbandingan memakai versi dataset, target, warmup dan variansi yang sama. [Instruksi pemilik](../shadow-perf/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-perf/scripts/openapi_to_k6_scaffold.mjs)

**Validasi.** Jalankan fixture dan periksa pembanding ini. POST-only tanpa data tulis tidak boleh berubah menjadi GET /healthz. Target produksi di servers[0] serta 401 pada skenario sukses harus menghalangi klaim readiness.

**DoD.** Fixture POST lalu GET memakai ID dari respons create dan mengharapkan status yang disepakati. Generate/dry-run lokal harus dapat diuji tanpa meluncurkan k6.

### T12 · shadow-plan

**Bidang B, C, I, K** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** DoR setiap story mensyaratkan sembilan UI states. DoD menyebut openapi.yaml, collection, dan viewport. Story pemrosesan batch internal yang tanpa antarmuka akan memperoleh pekerjaan tambahan.

**Hasil yang dituju.** Hasilkan rencana delivery yang bisa disusun ulang saat asumsi berubah, dengan dependensi, ownership dan bukti penerimaan yang proporsional terhadap jenis pekerjaan.

**Implementasi dan target.** Temukan outcome, constraint, Definition of Done tim, serta baseline requirement. Untuk tiap work package catat kontrak masuk/keluar, penanggung jawab, predecessor, hal yang bisa dikerjakan paralel, risiko pengulangan dan ukuran selesai. Gunakan spike timeboxed untuk keputusan tidak pasti. Tunjukkan dampak perubahan tanggal/owner atau kontrak bersama terhadap jalur kritis. [Instruksi pemilik](../shadow-plan/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Persetujuan desain belum mengotorisasi deploy. Dependensi melingkar atau pekerjaan berisiko tanpa owner tidak boleh disajikan sebagai jadwal final.

**DoD.** Impor batch headless memetakan parsing, rekonsiliasi dan rollback tanpa sembilan state UI. Dua stream yang menyentuh schema sama memerlukan urutan integrasi dan owner yang jelas.

### T13 · shadow-privacy

**Bidang A, E, G, J** · Dependensi X02,X03 · P0 · Risiko H · 4–7 hari-orang.

**Masalah profesional.** Self-test 9/9 untuk auditor berbasis teks. Instruksi laporan meminta kategori data serta rujukan pasal. Jejak pola di file saja tidak membuktikan dasar pemrosesan, kebijakan retensi aktual, atau eksekusi DSAR.

**Hasil yang dituju.** Bangun bukti end-to-end untuk tujuan pemrosesan, retensi, DSAR dan aliran lintas pihak. Pisahkan observasi kode dari validasi organisasi dan keputusan hukum.

**Implementasi dan target.** Temukan data categories, tujuan, owner, lawful basis yang telah diputuskan, sistem hulu/hilir, backup dan processor. Untuk satu permintaan subjek sintetis, telusuri akses/koreksi/penghapusan melalui cache, indeks, analitik dan arsip, termasuk legal hold yang disahkan. Hasilkan status per storage dan daftar keputusan yang membutuhkan pejabat berwenang. [Instruksi pemilik](../shadow-privacy/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-privacy/scripts/privacy_pdp_auditor.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Null result pada pencarian PII di source tidak membuktikan penghapusan dari backup. Ketidakjelasan dasar retensi menghentikan rekomendasi penghapusan live dan dirujuk ke pejabat berwenang.

**DoD.** DSAR sintetis menandai indeks hapus, cache invalidated, arsip masuk retensi sah, dan layanan pihak ketiga masih menunggu konfirmasi. Bukti hanya memuat pengenal tersunting.

### T14 · shadow-quality

**Bidang E, F, G, H** · Dependensi X01,X02 · P0 · Risiko H · 4–6 hari-orang.

**Masalah profesional.** Fungsi inspect_or_cleanup_docker_leaks mengambil seluruh docker ps -a dan memakai nama atau label global. Identitas repo/pekerjaan tidak menjadi input. Pada host bersama, container tugas lain dapat ditandai dan container berhenti dapat menjadi sasaran opsi cleanup.

**Hasil yang dituju.** Berikan dua keputusan terpisah tentang kualitas perubahan dan kesehatan pekerjaan lokal. Seorang pengembang harus dapat membuktikan bahwa aset tim lain tetap di luar cakupan pembersihan.

**Implementasi dan target.** Ikat diff ke base, commit kandidat, workspace dan run ID. Identifikasi resource dari label kepemilikan yang dibuat saat provisioning serta ledger handle. Daftar hasil tanpa side effect; tepat sebelum cleanup, cocokkan ulang ID/label, status terminal, dan izin. Untuk temuan lama, catat baseline, penambahan baru dan pengecualian berumur. [Instruksi pemilik](../shadow-quality/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-quality/scripts/shadow_gate.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Sumber eksternal yang berlabel umum atau statusnya berubah menjadi aktif sebelum cleanup harus dikeluarkan dari target. Probe memakai mock Docker.

**DoD.** Fixture dua workspace dengan nama container mirip harus menghasilkan hanya satu kandidat milik run yang dinilai. Pengulangan setelah resource hilang harus selesai tanpa kesalahan atau penghapusan lain.

### T15 · shadow-realtime

**Bidang A, D, F, G** · Dependensi X06,C06 · P0 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Self-test 6/6. Namun lima flag berupa string false dan tanpa event menghasilkan PASS dengan nol pesan. Truthiness menggantikan validasi boolean; kesimpulan tidak mensyaratkan observasi revokasi.

**Hasil yang dituju.** Verifikasi semantik sesi melalui jejak pesan yang memiliki urutan dan pemilik. Tentukan jaminan pengiriman selama disconnect, reconnect, dan pencabutan izin.

**Implementasi dan target.** Tetapkan versi trace dengan event connect, authorize, emit, deliver, revoke, disconnect, resume serta ID stream dan sequence. Evaluasi state machine per koneksi dan identitas tenant. Tangani replay window/cursor kedaluwarsa, buffer penuh, aturan deduplikasi dan fairness. Pilih broker bersama hanya bila topologi menuntut fanout multi-instance. [Instruksi pemilik](../shadow-realtime/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-realtime/scripts/realtime_transport_verifier.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Frame baru yang teramati terkirim setelah revokasi efektif gagal. Lima flag bertipe string tanpa trace menghasilkan bukti tidak cukup, meskipun satu node memakai transport yang didukung.

**DoD.** Replay seq 10, 10, 11 pada reconnect harus menampilkan dua pesan unik. Cursor kedaluwarsa harus meminta resync sesuai kontrak layanan.

### T16 · shadow-refactor

**Bidang C, D, F, G** · Dependensi X02,C10 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Self-test 6/6. Plan dengan changed_files=['other.py'] dan tanpa allowed_scope_files menghasilkan PASS selama checklist lain terisi. Cabang pemeriksaan selisih menonaktifkan batas jika allowlist kosong.

**Hasil yang dituju.** Jaga kesetaraan perilaku yang bisa diamati di batas modul, termasuk semantik error, side effect, retry dan urutan notifikasi.

**Implementasi dan target.** Temukan seam dan konsumen. Peroleh allowed paths dari scope yang disetujui dan changed paths dari Git. Kaitkan tes karakterisasi pada SHA sebelum/sesudah dengan input deterministik. Gunakan differential replay tersunting serta normalisasi field volatil sesuai kontrak. Pisahkan perubahan perilaku yang sengaja diminta ke keputusan tersendiri. [Instruksi pemilik](../shadow-refactor/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-refactor/scripts/refactor_characterization_gate.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Plan tanpa allowed paths, tes pada SHA yang salah, atau event ganda meski output HTTP sama tidak membuktikan ekuivalensi.

**DoD.** Refactor serialisasi yang mempertahankan nullability, status HTTP, dan side effect lulus replay pada dua revisi. Penambahan atribut opsional diberi penilaian eksplisit sesuai konsumen.

### T17 · shadow-release

**Bidang C, D, E, I** · Dependensi C10,T10 · P1 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Daftar preflight mewajibkan backup produksi dan baseline perf. Smoke mengasumsikan /healthz dan /readyz. Aturan tersebut juga mengenai rilis static web atau pustaka tanpa layanan HTTP.

**Hasil yang dituju.** Tentukan kelayakan promosi sebuah artefak dan kompatibilitas rollback terhadap code, data, kontrak konsumen, konfigurasi dan feature flag.

**Implementasi dan target.** Temukan mekanisme release aktual dan buat manifest SHA/digest serta matriks dampak. Pilih gate dari blast radius dan bukti yang tersedia. Bedakan ulang deploy artifact sebelumnya, matikan flag, roll-forward, dan restore data. Tentukan telemetry pemicu stop serta masa observasi berbasis volume yang bermakna. [Instruksi pemilik](../shadow-release/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Bukti staging untuk digest berbeda atau migrasi yang membuat versi lama tak dapat membaca data harus menggagalkan usulan rollback otomatis.

**DoD.** Rilis package tanpa DB membawa uji API publik/packaging, konsumen referensi dan provenance. Rollback dua versi dengan migrasi expand-compatible menjelaskan urutan yang telah diuji.

### T18 · shadow-resilience

**Bidang A, C, F, G** · Dependensi X02 · P1 · Risiko H · 4–6 hari-orang.

**Masalah profesional.** Instruksi menyebut durasi pg_restore sebagai Actual RTO dan MAX(created_at) sebagai pengukuran kehilangan data. Keduanya melewatkan waktu konfigurasi aplikasi serta keadaan tanpa transaksi baru.

**Hasil yang dituju.** Uji kemampuan memulihkan fungsi bisnis lengkap dari titik kegagalan yang terdefinisi, termasuk IAM, jaringan, storage, aplikasi, dan validasi konsumen.

**Implementasi dan target.** Petakan dependency graph dan layanan minimum, target pemilik bisnis, urutan restore serta data classification. Gunakan marker transaksi yang dapat ditelusuri dan jam/titik awal yang jelas. Catat restore teknis, waktu pengalihan, verifikasi integritas, dan waktu fungsi bisnis kembali. Latih isolasi dan penghentian drill bila target/ownership tidak sesuai. [Instruksi pemilik](../shadow-resilience/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Tabel tanpa transaksi baru tidak membuktikan kehilangan data. Ketiadaan kunci dekripsi atau hasil validasi pengguna harus mencegah klaim recoverable.

**DoD.** Marker terakhir berusia 20 detik pada titik gagal, restore 4 menit, validasi dan switch 6 menit. Laporan memisahkan kehilangan data yang dibuktikan dari total pemulihan layanan 10 menit.

### T19 · shadow-search

**Bidang A, D, F, G** · Dependensi X01,X06 · P0 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Self-test 6/6. Satu query kosong memberi PASS. Duplikasi satu dokumen relevan memberi Recall=2.0 dan NDCG=1.6309. Perhitungan menghitung dokumen yang sama berulang, dan ketiadaan ground truth bernilai sempurna.

**Hasil yang dituju.** Bandingkan perubahan retrieval dengan satuan evaluasi yang benar untuk dokumen, chunk, tenant dan versi indeks. Tim dapat melihat apakah kenaikan relevansi dibayar dengan keterlambatan pencabutan akses.

**Implementasi dan target.** Wajibkan query ID, tingkat judgement, ranking terurut dan identitas hasil stabil. Normalisasi ke unit yang dipilih, catat duplikasi secara eksplisit, pisahkan missing judgement dari nol relevansi, dan hitung interval/delta pada query berpasangan. Evaluasi filter tenant sebelum ranking serta freshness setelah delete/revoke melalui fixture terkontrol. [Instruksi pemilik](../shadow-search/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-search/scripts/search_relevance_acl_gate.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Query tanpa judgement menghasilkan status tidak terukur. Dokumen tenant lain yang mendapat skor tinggi harus gagal pada uji isolasi meski peningkatan rata-rata ranking besar.

**DoD.** Dua chunk dari dokumen sama pada evaluasi tingkat dokumen menghasilkan Recall dalam [0,1]. Hasil faktual dan semantik dapat dibandingkan pada slice berbeda.

### T20 · shadow-sec

**Bidang A, E, F, J** · Dependensi X03,C06 · P1 · Risiko H · 3–6 hari-orang.

**Masalah profesional.** Skill meminta contoh ID ASVS dan laporan per kontrol, serta menyebut ASVS 5.0.0 pada bagian rujukan. Label kategori di checklist ditulis langsung dalam teks. Tidak ada langkah dalam checklist yang memastikan ID yang dipilih teresolusi ke katalog versi audit.

**Hasil yang dituju.** Susun assurance defensif yang mengikuti aliran data dan boundary aktual dari perubahan. Kaitkan kontrol ke sumber, versi, bukti aplikasi, dampak, serta status remediasi.

**Implementasi dan target.** Temukan aset, peran, jalur otorisasi, trust boundaries dan dependensi relevan dari diff. Prioritaskan kontrol yang memutus risiko aktual; jaga katalog versi dengan validasi ID saat membuat finding. Catat managed controls, residual risk, bukti negatif dan confidence. Gunakan review source, konfigurasi dan fixture unit dengan dua peran/tenant jika diizinkan. [Instruksi pemilik](../shadow-sec/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-sec/references/NIST-SSDF-AND-OWASP-ASVS-5.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Label severity tanpa affected asset atau bukti kontrol tidak cukup. ID katalog yang hilang dan fitur yang hanya menyembunyikan tombol UI tidak menutup temuan otorisasi.

**DoD.** Review perubahan ekspor data melacak pembatas tenant hingga query akhir dan bukti tes unit dua tenant. ID kontrol yang valid dirujuk dengan versi yang dipakai.

### T21 · shadow-supplychain

**Bidang D, E, G, J** · Dependensi X03,X06 · P0 · Risiko H · 4–6 hari-orang.

**Masalah profesional.** Self-test 7/7. Manifest dengan komponen identik dan signer_verified berupa string false diterima PASS. Pemeriksa mengandalkan truthiness dan klaim pemanggil. Tanggal waiver juga memiliki nilai bawaan tetap.

**Hasil yang dituju.** Buat keputusan provenance untuk artefak tertentu, termasuk saat CI offline, tanpa menyamakan isi manifest dengan bukti verifikasi signer.

**Implementasi dan target.** Pisahkan inventaris lockfile/SBOM, kebijakan trust, bukti attestation, dan pengecualian. Hubungkan paket melalui identifier versi/ekosistem yang stabil, pisahkan runtime/dev/platform optional. Baca hasil verifier resmi yang sudah dipakai CI, cocokkan subject digest, builder/issuer yang diizinkan dan jadwal waiver pada tanggal penilaian yang dipasok. [Instruksi pemilik](../shadow-supplychain/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-supplychain/scripts/supplychain_sbom_gate.py)

**Validasi.** Jalankan fixture dan periksa pembanding ini. String false, tanda tangan untuk digest lain, atau verifier offline tidak memberi status signer verified. Dua paket bernama sama pada ekosistem berbeda tidak boleh digabungkan.

**DoD.** Satu paket opsional OS lain dapat dikeluarkan dengan profil platform terdokumentasi. Attestation valid untuk digest build yang diuji menghasilkan status verified untuk dimensi itu.

### T22 · shadow-test

**Bidang B, C, F, K** · Dependensi X01 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Bagian regression selection membatasi eksekusi ke modul terdampak. Sementara itu matriks wajib delapan poin berorientasi status HTTP dan kontrak diasumsikan openapi.yaml. Tes unit diskon murni tidak memiliki status HTTP.

**Hasil yang dituju.** Pilih tes dengan kemampuan membedakan implementasi benar dari cacat aktual, pada level termurah yang melintasi batas risikonya.

**Implementasi dan target.** Temukan runner, konvensi dan data setup. Petakan risiko ke unit/component/contract/integration/end-to-end, sertakan alasan level dipilih. Utamakan tes pada invariant dan cara gagal, periksa test determinism, perlihatkan red-before/green-after pada bug. Tambahkan teardown berowner serta jalur diagnosis saat suite flaky. [Instruksi pemilik](../shadow-test/SKILL.md) · [Titik perubahan atau acuan teknis](../shadow-test/references/POLYGLOT-TESTING-MATRIX.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Tes unit murni tidak memulai Docker atau browser. Retry yang hanya menutupi nondeterminisme tidak menghasilkan status verified.

**DoD.** Untuk pembulatan diskon, uji perbatasan dan reproduksi bug di suite unit. Untuk duplikasi event, komponen real storage dapat membuktikan idempotensi di boundary yang relevan.

### T23 · shadow-uat

**Bidang C, F, I, L** · Dependensi X02,C10 · P1 · Risiko M · 3–5 hari-orang.

**Masalah profesional.** Exit gate mewajibkan sembilan state UI dan kontrak HTTP 202. Contoh referensi pengukuran juga memakai URI file absolut mesin pengembang. Acceptance batch tanpa UI akan sulit memenuhi kedua syarat UI.

**Hasil yang dituju.** Buktikan outcome bisnis dan kewenangan penerimaan untuk versi tertentu, termasuk proses asinkron, antarmuka headless, dan jalur manusia.

**Implementasi dan target.** Bangun trace requirement ke skenario dan observasi bisnis. Pilih UI states, output file, audit event atau rekonsiliasi sesuai kanal. Pakai aturan pemisahan defect dan change request berdasarkan baseline bertanggal; catat severity, owner, risiko residual dan keputusan sign-off untuk build persis. [Instruksi pemilik](../shadow-uat/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Tangkapan layar tombol sukses tidak cukup untuk membuktikan proses settlement. Requirement baru masuk CR dan tidak dipalsukan sebagai kelulusan baseline.

**DoD.** Impor batch headless dinilai dari jumlah record valid, daftar gagal, nilai agregat, dan rekonsiliasi operator. Skenario UI async membedakan queued dari completed.

## Referensi integrasi produk dan desain

### D01 · AI Product Designer

**Bidang C, D, I** · Dependensi C13 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Rute file relatif memakai satu tingkat direktori ekstra. Pada checkout ini sebelas dokumen yang dirujuk berada satu direktori dengan skill.

**Hasil yang dituju.** Transform product ideas, user stories, or existing interfaces into evidence-aware product strategy, user journeys, robust UX flows, screen specifications, design-system-compatible wireframes, usability reviews, and engineering handoffs.

**Implementasi dan target.** Paket sudah mengaitkan user story dengan flow, state, dan acceptance. Sebelas path dalam instruksi lokal memiliki awalan direktori yang tidak cocok dengan susunan checkout. Kompetensi yang perlu dikembangkan adalah **melacak keputusan desain sampai implementasi**. `shadow-design` menangani resolusi path relatif dan menyusun rantai kebutuhan → tindakan → bukti sistem → pemulihan. `shadow-api` atau engineer domain memverifikasi arti respons dan pembatasan backend bila memengaruhi state pengguna. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/ai-product-designer-skill-pack/SKILL.md](../shadow-design/references/ai-product-designer-skill-pack/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Permintaan koreksi satu label yang cukup ditangani dengan referensi bahasa serta pola saat ini.

**DoD.** 11 target dapat dibaca relatif terhadap lokasi paket ketika working directory dipindah, dan receipt 202 menghasilkan status menunggu.

### D02 · Intent

**Bidang B, K, L** · Dependensi C13 · P2 · Risiko L · 1–2 hari-orang.

**Masalah profesional.** Banner wajib mendahului semua tool saat dipanggil langsung. Aturan presentasi tersebut mengganggu discovery dan dapat mengulang pertanyaan yang sudah terjawab.

**Hasil yang dituju.** The entry point for Intent, a UX and design strategy system.

**Implementasi dan target.** Banner wajib mengajukan pertanyaan konteks dan aturan paket mengutamakan deliverable berbentuk file. Keduanya perlu diterjemahkan oleh `shadow-design` menurut tugas serta mode pemakaian. Pertahankan kemampuan analisis tujuan, dilema etika, dan keputusan yang dapat ditinjau ulang. Bentuk catatan keputusan paling kecil yang memadai untuk audiensnya, dengan alasan, bukti, pemilik, dan pemicu untuk merevisi keputusan. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/ghaida-intent/skills/intent/SKILL.md](../shadow-design/references/external-upstreams/ghaida-intent/skills/intent/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Perintah eksplisit membuat decision record pada lokasi tertentu. Artefak tersebut boleh dibuat tanpa mengulangi keputusan pengguna.

**DoD.** Tujuan yang sudah tersedia dipakai, kritik tetap di chat, dan pemilihan pola yang berdampak material memicu satu pertanyaan interaktif sebelum implementasi.

### D03 · Userflow

**Bidang D, I, K, L** · Dependensi C13 · P0 · Risiko H · 2–4 hari-orang.

**Masalah profesional.** Dispatch menetapkan laporan HTML sebagai keluaran umum. Template yang menjadi input pembuatan laporan tidak ikut dipaketkan.

**Hasil yang dituju.** Use when the user invokes /userflow, asks which UX flow or layout patterns apply to what they're building, or describes an app, feature, or screen to build or review and wants the right proven flow guidance pulled in automatically.

**Implementasi dan target.** Dispatcher memiliki taksonomi 15 flow dan aturan memilih 1–4 skill, tetapi mewajibkan laporan HTML untuk mayoritas review dan merujuk template yang tidak ada. `shadow-design` perlu memiliki pemilihan flow, pemeriksaan keberadaan template, serta cara menggabungkan panduan yang tumpang tindih. `shadow-monarch` menjaga mode baca/tulis. Gunakan alur pekerjaan, dependensi antarlayar, state pemulihan, dan prioritas aturan domain untuk menentukan referensi yang dimuat. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/ux-flow-skills/skills/userflow/SKILL.md](../shadow-design/references/external-upstreams/ux-flow-skills/skills/userflow/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Koreksi warna tombol yang tidak membutuhkan dispatcher flow.

**DoD.** Permintaan review hanya menghasilkan ulasan dan tidak menyentuh file. Untuk permintaan ekspor HTML eksplisit, gunakan template kompatibel yang ada atau jelaskan pilihan saat input wajib hilang.

### D04 · Designer Skills / design-research / interview-script

**Bidang A, B, F, L** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta.

**Hasil yang dituju.** Write a structured interview guide — warm-up, core exploration, and wrap-up.

**Implementasi dan target.** Pemilik metode adalah `shadow-design`. Kegunaan utama adalah menyusun wawancara untuk memahami bagaimana orang menyelesaikan tugas. Ajarkan critical incident interviewing, probe yang netral, teknik membedakan ucapan dan observasi, serta penutupan yang memberi peserta kesempatan mengoreksi interpretasi. Hasil kerja berupa panduan moderator, rencana pencatatan, dan peta pertanyaan ke keputusan desain. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/design-research/skills/interview-script/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/interview-script/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Pertanyaan manajemen tentang pihak yang menyetujui pembelian, yang masuk discovery produk.

**DoD.** Path keluarga desain terpilih dan setiap dugaan friksi memperoleh probe non-leading dan tempat mencatat bukti yang menentangnya.

### D05 · PM Skills / pm-product-discovery / interview-script

**Bidang A, B, F, L** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta.

**Hasil yang dituju.** Create a structured customer interview script with JTBD probing questions, warm-up, core exploration, and wrap-up sections.

**Implementasi dan target.** Pemilik keputusan adalah `shadow-discovery` dengan `shadow-design` menyediakan referensi vendor. Bangun keahlian menyelidiki kejadian pemicu pembelian, alternatif yang telah dicoba, pengambil keputusan, dan biaya berpindah. Output berupa panduan wawancara berbasis keputusan investasi, termasuk apa yang bisa membuat tim menolak hipotesis peluang. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/interview-script/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/interview-script/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Uji label tombol dashboard yang harus menuju keluarga desain.

**DoD.** Posisi pembeli tidak disimpulkan dari antusiasme pengguna, calon responden dipisahkan menurut peran, dan path PM terpilih.

### D06 · Designer Skills / design-research / summarize-interview

**Bidang A, B, F, J** · Dependensi D04 · P1 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta.

**Hasil yang dituju.** Turn one interview transcript into themes, supporting quotes, and action items.

**Implementasi dan target.** `shadow-design` bertanggung jawab atas sintesis perilaku. Metode yang perlu dimiliki adalah coding kejadian, penelusuran kutipan ke segmen transkrip, penandaan inferensi, dan pencatatan kejadian yang menyangkal pola. Desainer menerima daftar friksi per langkah dan pertanyaan validasi. Sertakan identitas pseudonim bila pemilik studi membutuhkannya. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/design-research/skills/summarize-interview/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/summarize-interview/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Transkrip tanpa observasi. Laporan tidak boleh menciptakan jumlah kesalahan yang tidak diucapkan atau dicatat.

**DoD.** Pembaca bisa menemukan keduanya, penjelasan penyebab berstatus inferensi, dan identitas pribadi tidak ikut ke handoff.

### D07 · PM Skills / pm-product-discovery / summarize-interview

**Bidang A, B, F, I** · Dependensi D05 · P1 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta.

**Hasil yang dituju.** Summarize a customer interview transcript into a structured template with JTBD, satisfaction signals, and action items.

**Implementasi dan target.** `shadow-discovery` memiliki sintesis untuk keputusan produk. Hubungkan kebutuhan, alternatif saat ini, dampak, otoritas membeli, dan bukti yang masih kosong dengan opportunity backlog. Pertahankan level bukti per orang, tanpa menaikkan satu pengalaman menjadi ukuran pasar atau komitmen pembelian. Serahkan pertanyaan prioritas kepada PM. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/summarize-interview/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/summarize-interview/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Rangkuman uji kegunaan yang diminta untuk perbaikan field formulir. Rute tersebut memakai D06.

**DoD.** Seorang admin meminta ekspor CSV dan menyebut “mungkin direktur mau bayar”. Ringkasan harus menautkan masalah rekonsiliasi ke kutipan, memisahkan solusi usulan, serta menandai anggaran dan keputusan direktur sebagai belum diketahui.

### D08 · Designer Skills / design-research / survey-design

**Bidang A, B, F, L** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta.

**Hasil yang dituju.** Design unbiased survey instruments — question wording, scales, and sampling — to measure attitudes at scale.

**Implementasi dan target.** Pemilik instrumen adalah `shadow-design`. Kembangkan pemilihan skala, konsistensi arah jawaban, pengalaman responden, penanganan data kosong, dan pilot kognitif untuk memeriksa apakah peserta menafsirkan item sesuai tujuan. Hasil berupa kuesioner versi pilot, keputusan desain yang dilayani tiap blok, dan daftar alasan revisi. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/design-research/skills/survey-design/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/survey-design/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Fixture yang hendak membandingkan hasil historis. Perubahan skala harus dijelaskan sebagai pemutus keterbandingan sebelum angka digabung.

**DoD.** Tiap konstruk bisa dianalisis terpisah dan responden yang belum mencoba dikeluarkan dari denominator yang relevan.

### D09 · PM Skills / pm-market-research / survey-design

**Bidang A, B, F, J** · Dependensi C13,C14 · P1 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta.

**Hasil yang dituju.** Writing or reviewing a survey or questionnaire: customer feedback, NPS, CSAT, CES, pricing, market research, an in-app survey.

**Implementasi dan target.** `shadow-discovery` memiliki keputusan pasar dan memakai `shadow-design` untuk akses metode vendor. Kembangkan sampling frame, penentuan populasi target, segmentasi, nonresponse bias, dan kriteria keberhasilan yang ditetapkan sebelum melihat jawaban. Hasil berupa brief keputusan, rencana rekrutmen, instrumen, rancangan tabulasi, serta tindakan bila data tidak konklusif. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-market-research/skills/survey-design/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-market-research/skills/survey-design/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Survei pengalaman satu alur pada pengguna yang telah menjalankannya. Rute tersebut memilih D08.

**DoD.** Laporan pilot menyebut sampling frame yang sebenarnya, memisahkan pengguna aktif dari prospek, dan membatasi kesimpulan atau mengusulkan cara merekrut kelompok yang hilang.

### D10 · Doherty Threshold

**Bidang A, F, G, L** · Dependensi C13 · P2 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Bagian aplikasi menetapkan angka waktu tetap untuk feedback. Angka ini dapat berubah menjadi target produk tanpa kaitan dengan latensi dan tugas setempat.

**Hasil yang dituju.** Apply the Doherty Threshold — keep system response under 400ms to preserve user flow.

**Implementasi dan target.** `shadow-design` memiliki pengalaman menunggu. Pemilik aplikasi memverifikasi telemetry dan arti hasil operasi. Ajarkan perbedaan waktu ke umpan balik pertama, waktu penyelesaian, dan latensi bagian paling lambat dalam distribusi. Pilih indikator menurut durasi, ketidakpastian, biaya salah klik, dan kebutuhan aksesibilitas. Angka 400 ms dalam referensi perlu status heuristik ketika konteks produk belum diukur. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/interaction-design/skills/doherty-threshold/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/interaction-design/skills/doherty-threshold/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Satu trace lambat. Hasilnya tidak cukup untuk mengubah target layanan atau memulai load test.

**DoD.** Fixture cepat tidak menghasilkan kedipan indikator, fixture lambat memberikan state menunggu yang dapat diakses, dan receipt antrean tidak memberi pesan sukses akhir.

### D11 · Critique Visual Hierarchy

**Bidang A, B, F, L** · Dependensi C04,C13 · P2 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Pertanyaan pemeriksaan memakai rasio ukuran minimum. Rubrik perlu memisahkan sinyal visual tersebut dari bukti kemampuan pengguna menyelesaikan tugas.

**Hasil yang dituju.** Critique a rendered screen's hierarchy — entry point, eye flow, weight distribution, and emphasis.

**Implementasi dan target.** `shadow-design` memiliki kritik tugas pengguna, dibantu `shadow-accessibility` jika fokus keyboard, zoom, atau pembacaan layar ikut memengaruhi navigasi. Ajarkan penilaian entry point, pengelompokan, urutan baca, kepadatan, dan persaingan aksi. Gunakan screenshot untuk observasi, source token untuk nilai teknis, dan bukti tugas untuk dampak. Rasio visual yang disebut sumber dapat menjadi pemicu pemeriksaan. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/designer-skills/visual-critique/skills/critique-visual-hierarchy/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/visual-critique/skills/critique-visual-hierarchy/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Layar yang memakai ukuran judul seragam tetapi tugas utama mudah ditemukan. Selisih rasio semata tidak menghasilkan blocker.

**DoD.** Finding dapat ditelusuri ke elemen, viewport, dan tugas yang terganggu.

### D12 · Flow Auth

**Bidang D, E, G, L** · Dependensi C06,C13 · P0 · Risiko H · 2–4 hari-orang.

**Masalah profesional.** Anjuran auto-route berdasar domain perusahaan bergantung pada konfigurasi identitas tenant yang perlu diperiksa oleh pemilik layanan.

**Hasil yang dituju.** Use when designing, building, or reviewing any authentication surface — signup, login, logout, magic links, passkeys, OAuth/SSO buttons, password reset, 2FA/MFA, email verification, or session-expiry handling.

**Implementasi dan target.** `shadow-design` memiliki pengalaman masuk. `shadow-auth` menguasai aturan tenant, identity provider, verifikasi identitas, serta kebijakan pemulihan. Perluas kemampuan menjadi pemodelan state identitas dari bukti yang diizinkan server, termasuk SSO opsional, akun personal, linking, sesi kedaluwarsa, dan provider yang sementara gagal. Tetapkan kontrak data sebelum menetapkan navigasi. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-auth/SKILL.md](../shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-auth/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Fixture tenant dengan SSO wajib. Saran UI tidak boleh menambahkan jalur password yang melanggar kebijakannya.

**DoD.** Redirection hanya terjadi untuk hasil resolusi server yang sesuai kebijakan dan akun ambigu mendapat langkah pemulihan yang tidak mengungkap keberadaan akun lain.

### D13 · PM AI Shipping / code-review

**Bidang C, D, I, L** · Dependensi C13,T14 · P0 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Isi lokal adalah pemberitahuan pemindahan dan petunjuk pemasangan. Prosedur kerja inti berada di plugin lain.

**Hasil yang dituju.** Moved to phuryn/product-engineering, where it is maintained in the ai-shipping plugin; this copy says where it went and how to install it.

**Implementasi dan target.** `shadow-quality` menjadi pemilik review, dengan `shadow-debug` atau pemilik domain bila diperlukan. Adapter perlu menerjemahkan intent PM menjadi pertanyaan reviewer tentang kontrak publik, caller lama, risiko regresi, dan bukti verifikasi. Hasil berupa temuan berperingkat dengan lokasi, kondisi pemicu, dampak, dan koreksi minimum. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/code-review/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/code-review/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Permintaan desain UX untuk halaman review pengguna, yang tidak mengaktifkan code review.

**DoD.** Review read-only menemukan pasangan lokasi kontrak dan konsumen, menjelaskan kondisi gagal, serta memberi PM konsekuensi yang dapat dipahami. Instalasi plugin dan perubahan source harus berjumlah nol.

### D14 · PM AI Shipping / intended-vs-implemented

**Bidang B, C, F, I** · Dependensi C13,C14 · P1 · Risiko M · 2–4 hari-orang.

**Masalah profesional.** Isi lokal adalah pemberitahuan pemindahan dan petunjuk pemasangan. Prosedur kerja inti berada di plugin lain.

**Hasil yang dituju.** Moved to phuryn/product-engineering, where it is maintained in the ai-shipping plugin; this copy says where it went and how to install it.

**Implementasi dan target.** `shadow-discovery` memiliki rekonsiliasi kebutuhan; `shadow-api`, `shadow-test`, atau pemilik komponen memasok bukti implementasi yang relevan. Ajarkan pembedaan janji publik, rancangan usulan, perilaku sengaja disembunyikan, dan bug yang dapat direproduksi. Artefak berupa matriks klaim, status otoritas, bukti implementasi, dampak, dan pihak yang memutuskan tindak lanjut. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Ide di backlog yang belum disetujui. Selisih dengan ide tersebut tidak diberi status cacat kontrak.

**DoD.** Reviewer melacak input sampai output, mengidentifikasi selisih, dan mempertahankan kedua bukti ketika belum jelas apakah kontrak atau implementasi yang perlu diubah.

### D15 · PM AI Shipping / shipping-artifacts

**Bidang C, I, J, L** · Dependensi C13,T17 · P1 · Risiko M · 1–3 hari-orang.

**Masalah profesional.** Isi lokal adalah pemberitahuan pemindahan dan petunjuk pemasangan. Prosedur kerja inti berada di plugin lain.

**Hasil yang dituju.** Moved to phuryn/product-engineering, where it is maintained in the ai-shipping plugin; this copy says where it went and how to install it.

**Implementasi dan target.** `shadow-release` memiliki bukti perubahan serta status rilis. `shadow-doc` memiliki penyajian bila pengguna meminta dokumen. Kembangkan kemampuan membedakan kebutuhan operator, pelanggan, dan tim dukungan dengan provenance ke commit, tiket, atau hasil verifikasi. Pilih materi sesuai audiens serta cakupan perubahan. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/shipping-artifacts/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/shipping-artifacts/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Permintaan khusus runbook rollback. Handoff beralih ke pemilik release dengan pemicu, prosedur, dan bukti pemulihan yang sesuai.

**DoD.** Draft menyebut status integrasi yang benar, tidak menyatakan fitur sudah tersedia di produksi, serta tidak membuat changelog tambahan, memublikasikan draft, atau memasang plugin.

### D16 · Live Polls

**Bidang E, G, I, L** · Dependensi C13,X02 · P1 · Risiko H · 2–4 hari-orang.

**Masalah profesional.** Skill membedakan draft dan peluncuran, tetapi persiapan bebas mencakup pembuatan resource pada AskOne. Credential dan otorisasi membuat resource eksternal perlu diperiksa tersendiri.

**Hasil yang dituju.** A poll or vote in a meeting, workshop or training: 'run a quick poll', dot-voting, a confidence vote, a word cloud, a quiz.

**Implementasi dan target.** `shadow-plan` atau fasilitator yang ditunjuk memiliki pertanyaan dan keputusan rapat. `shadow-monarch` menjaga cakupan panggilan eksternal. Ajarkan pemungutan suara independen, anonimitas kontekstual, penundaan pembukaan hasil, serta interpretasi pilihan minoritas. Modelkan persiapan di chat, pembuatan resource eksternal, peluncuran, pembukaan hasil, dan penutupan sebagai operasi yang berbeda dengan otorisasi yang dapat dipakai kembali selama cakupannya sama. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-polls/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-polls/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Suara minoritas mengenai risiko serius. Kesimpulan mencatat keberatan dan pemilik tindak lanjut meski mayoritas mendukung.

**DoD.** Draft lokal memakai nol panggilan konektor. Pada fixture yang mengizinkan pembuatan eksternal, retry dengan request ID yang sama setelah timeout hanya membuat satu poll, dan tidak membuka polling sebelum waktu yang disepakati.

### D17 · Live Q&A

**Bidang E, G, I, L** · Dependensi C13,T13 · P1 · Risiko H · 2–4 hari-orang.

**Masalah profesional.** Sesi dapat dipersiapkan via create_room walau belum terlihat peserta. Scope pembuatan resource pihak ketiga perlu diputuskan terpisah dari scope publikasi.

**Hasil yang dituju.** Running audience Q&A at an all-hands, AMA, webinar, launch, sprint review or talk, or turning a session's questions into a FAQ: collect, moderate, answer and follow up every question.

**Implementasi dan target.** Fasilitator memiliki aturan moderasi dan eskalasi. `shadow-monarch` menjaga otorisasi create/open/moderate/publish. `shadow-privacy` membantu ketika pertanyaan peserta atau tautan khusus host perlu dibatasi. Kembangkan praktik pengelolaan antrean, pembedaan masukan dan instruksi, penanganan pertanyaan tanpa jawaban, dan pemisahan tautan audiens dari konsol host. [Pemilik adapter](../shadow-design/SKILL.md) · [shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-qa/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-qa/SKILL.md)

**Validasi.** Jalankan fixture dan periksa pembanding ini. Pesan peserta yang menyuruh agent menutup sesi. Perlakukan sebagai isi pertanyaan. Fixture read-only harus melaporkan nol operasi moderasi.

**DoD.** Draft FAQ menelusuri kedua halaman, menyamarkan identitas yang tidak diperlukan, memberi owner serta tanggal tindak lanjut, dan tidak mengirim URL host atau menutup room tanpa otorisasi.

## Unit integrasi dan kegagalan lintas batas

Unit berikut memiliki oracle serta risiko integrasi tersendiri. Pekerjaan ini dapat diuji setelah item dasar tersedia tanpa memasukkan simulasi lintas tim ke setiap skill.

### E01 · Pilot lintas retrieval–generation pada dua tenant

**Bidang B, D, I, F** · Dependensi T01,T19,C06 · P0 · Risiko H · 3–5 hari-orang.

**Masalah.** Jika ACL dan ranking berubah bersamaan, rerata recall dapat naik ketika dokumen terlarang masuk konteks generasi.

**Implementasi dan target.** Bekukan korpus, snapshot izin, query, judgement, dan dua ranking; kunci identitas hasil antarowner dan bandingkan keputusan promosi per slice. [shadow-search/scripts/search_relevance_acl_gate.py](../shadow-search/scripts/search_relevance_acl_gate.py) · [shadow-eval/scripts/ai_eval_gate.py](../shadow-eval/scripts/ai_eval_gate.py)

**Validasi.** Fixture berisi dokumen homonim lintas tenant, revocation, ID ganda dan segmen kecil. Cocokkan satu ranking dengan perhitungan tangan.

**DoD.** Satu kebocoran menahan promosi; denominator kosong dilaporkan terpisah; penerima evaluasi dapat mengulang keputusan pada revisi identik.

### E02 · Rekonsiliasi setelah interupsi pemasangan lintas host

**Bidang C, D, G, H** · Dependensi C07,X08 · P1 · Risiko H · 2–4 hari-orang.

**Masalah.** Instalasi yang berhasil sebagian dapat meninggalkan host memakai instruksi baru dan server versi lama.

**Implementasi dan target.** Rancang preflight versi, daftar file yang benar-benar dimiliki installer dan mekanisme resume/revert per host. Batasi setiap percobaan pada profil sementara. [install.ps1](../install.ps1) · [install-codex.ps1](../install-codex.ps1) · [install.sh](../install.sh)

**Validasi.** Simulasikan kegagalan setelah host pertama diperbarui. Jalankan ulang dan bandingkan hash serta file konfigurasi eksternal.

**DoD.** Profil sementara berakhir konsisten pada versi sasaran atau kembali ke baseline; konfigurasi eksternal lainnya terpelihara.

### E03 · Penerimaan semantik saat backend menerima parameter tetapi mengabaikannya

**Bidang B, F, I, L** · Dependensi C10,T23,D14 · P1 · Risiko M · 2–4 hari-orang.

**Masalah.** Pemeriksaan schema yang benar dan UAT berstatus hijau dapat menutupi fitur yang diam-diam diabaikan di mapper.

**Implementasi dan target.** Pasangkan sumber kontrak, handler dan consumer lama. Bedakan perubahan dokumentasi tentang perilaku saat ini dari perubahan fungsi produk yang membutuhkan keputusan. [mcp-servers/shadow-api-mcp/discovery.test.mjs](../mcp-servers/shadow-api-mcp/discovery.test.mjs) · [shadow-uat/SKILL.md](../shadow-uat/SKILL.md)

**Validasi.** Uji dua nilai fields dengan subset berbeda pada fixture lokal, lalu ubah baseline requirement dari komitmen menjadi proposal.

**DoD.** Hasil melacak perbedaan ke kontrak/implementasi; perubahan scope dan decision owner dinyatakan; duplikasi dokumen tidak dihasilkan.

### E04 · Idempotensi lintas provider, cache dan recovery sesudah crash

**Bidang A, D, E, G** · Dependensi C09,T06,T18 · P0 · Risiko H · 3–6 hari-orang.

**Masalah.** Endpoint bisa tampak idempoten pada satu server tetapi debit kedua terjadi setelah crash, eviction, atau replay ledger.

**Implementasi dan target.** Pindahkan oracle dari jumlah HTTP request ke jumlah mutasi bisnis. Modelkan fingerprint per tenant, retry window, durable receipt, antrian event dan rekonsiliasi provider. [shadow-integrate/SKILL.md](../shadow-integrate/SKILL.md) · [shadow-cache/SKILL.md](../shadow-cache/SKILL.md) · [shadow-resilience/SKILL.md](../shadow-resilience/SKILL.md)

**Validasi.** Simulasikan commit remote diikuti timeout dan crash lokal, lalu restart dengan cache kosong dan event duplikat dari waktu lebih lama.

**DoD.** Dampak bisnis tetap tunggal atau status unknown diserahkan untuk inquiry. Hasil dapat dijelaskan dari ledger sintetis.

### E05 · Pelepasan akses dan cutover saat shift operasional berganti

**Bidang C, E, G, I** · Dependensi C03,T05,T07 · P1 · Risiko H · 2–4 hari-orang.

**Masalah.** Tim lama dan baru dapat sama-sama menganggap pihak lain memiliki rollback, vault dan komunikasi insiden.

**Implementasi dan target.** Replay serah terima dua arah dengan tanda terima per tanggung jawab, role efektif dan pemilik stop decision; verifikasi akses di simulasi dan rencanakan pencabutan sesuai kebijakan. [handoff/SKILL.md](../handoff/SKILL.md) · [shadow-handover/SKILL.md](../shadow-handover/SKILL.md) · [shadow-maintain/SKILL.md](../shadow-maintain/SKILL.md)

**Validasi.** Hentikan latihan saat calon penerima mampu membaca runbook tetapi tidak bisa mengakses dependensi yang dibutuhkan.

**DoD.** Item tertunda memiliki owner dan tenggat. Otorisasi revokasi live ditangani terpisah; tidak ada kredensial di artefak.

### E06 · Canary versi klien dengan distribusi pengguna yang berbeda

**Bidang A, B, F, G** · Dependensi T08,T17,T02 · P1 · Risiko H · 3–5 hari-orang.

**Masalah.** Rerata canary tampak sehat karena build lama hanya dipakai kohor kecil; rollback server juga tidak menarik klien yang sudah terpasang.

**Implementasi dan target.** Susun matriks app/API/version/feature flag, bandingkan outcome per kohor dan hitung biaya minimum observasi sebelum memutuskan hold atau perluas. [shadow-mobile/SKILL.md](../shadow-mobile/SKILL.md) · [shadow-release/SKILL.md](../shadow-release/SKILL.md)

**Validasi.** Uji canary sintetis dengan mayoritas OS baru tetapi semua kegagalan terjadi pada OS lama. Ulangi dengan sampel kecil yang belum bisa dibedakan.

**DoD.** Keputusan memuat kohor terdampak, ketidakpastian dan mitigasi client/server yang dapat dilakukan. Klaim global tanpa representasi ditolak.

### E07 · Perubahan harga dan sumber regulasi yang terjadi di tengah penugasan

**Bidang A, B, J, I** · Dependensi X03,T02,T04 · P1 · Risiko H · 2–4 hari-orang.

**Masalah.** Sumber baru dapat mengubah estimasi serta kewajiban, sedangkan laporan lama tetap harus dapat direproduksi.

**Implementasi dan target.** Pertahankan snapshot historis, tanggal efektif dan periode penugasan. Catat artefak terdampak, pilih perhitungan ulang hanya untuk bagian relevan, dan beri notifikasi owner sebagai draft internal. [shadow-finops/SKILL.md](../shadow-finops/SKILL.md) · [shadow-grc/SKILL.md](../shadow-grc/SKILL.md)

**Validasi.** Masukkan kontrak tarif bertanggal baru di tengah periode dan kewajiban yang mulai sesudah periode audit.

**DoD.** Laporan periode lama tetap reproducible. Perubahan biaya dan kontrol terkait punya sumber, tanggal berlaku dan review owner.

### E08 · Rehidrasi data yang sudah dihapus ketika restore backup

**Bidang D, E, G, J** · Dependensi T13,T18,T19 · P0 · Risiko H · 3–5 hari-orang.

**Masalah.** Kebijakan penghapusan dan disaster recovery masing-masing benar tetapi data terhapus dapat kembali ke indeks setelah pemulihan.

**Implementasi dan target.** Tetapkan urutan restore, pemutaran ulang tombstone terversi, invalidasi cache, rebuild index dan pemeriksaan bisnis sebelum membuka akses. [shadow-privacy/SKILL.md](../shadow-privacy/SKILL.md) · [shadow-resilience/SKILL.md](../shadow-resilience/SKILL.md) · [shadow-search/SKILL.md](../shadow-search/SKILL.md)

**Validasi.** Fixture berisi permintaan hapus sesudah snapshot serta record legal hold. Restore pada lingkungan latihan dan periksa masing-masing salinan.

**DoD.** Data yang tidak lagi boleh diakses tidak muncul ke pencarian. Rekaman yang harus ditahan tetap terproteksi dan diketahui owner.

### E09 · Replay order semantik pada refactor lintas branch

**Bidang C, D, G, F** · Dependensi T03,T16,T22 · P1 · Risiko M · 2–4 hari-orang.

**Masalah.** Dua patch yang lolos karakterisasi masing-masing dapat menukar urutan transaksi atau notifikasi setelah integrasi.

**Implementasi dan target.** Ambil event sequence dari base dan candidate merge preview. Normalisasi waktu/ID volatil secara eksplisit dan bandingkan invariant ordering, jumlah serta deduplikasi pada caller lama. [shadow-git/SKILL.md](../shadow-git/SKILL.md) · [shadow-refactor/SKILL.md](../shadow-refactor/SKILL.md) · [shadow-test/SKILL.md](../shadow-test/SKILL.md)

**Validasi.** Branch A memindahkan publikasi event, branch B menambah subscriber yang membaca data committed; merge tekstual berjalan bersih.

**DoD.** Hasil integrasi yang mengirim event sebelum commit gagal; diff sederhana yang mempertahankan ordering tetap lulus.

### E10 · Efisiensi pemuatan saat vendor menambah metode bernama sama

**Bidang D, K, I, H** · Dependensi X04,X05,C13,D04,D05 · P2 · Risiko M · 2–3 hari-orang.

**Masalah.** Dua metode sama-sama relevan pada nama dapat terpilih sekaligus setelah update vendor, menambah konteks dan menggandakan instrumen ke peserta.

**Implementasi dan target.** Jadikan keputusan riset, unit analisis dan sumber path sebagai kunci seleksi; ukur count/bytes loaded serta jumlah dokumen/permintaan kepada peserta sebelum dan sesudah update. [shadow-design/SKILL.md](../shadow-design/SKILL.md) · [shadow-design/UPSTREAM_PROVENANCE.json](../shadow-design/UPSTREAM_PROVENANCE.json)

**Validasi.** Satu wawancara untuk perbaikan form, satu untuk validasi minat produk, dan satu brief campuran dengan satu moderator.

**DoD.** Dua brief pertama memuat metode berbeda secara tepat. Brief campuran menghasilkan satu instrumen dan handoff, serta angka biaya yang teramati.

### E11 · Kalibrasi reviewer untuk temuan UX yang tidak deterministik

**Bidang A, B, F, L** · Dependensi C04,D10,D11,X07 · P2 · Risiko M · 2–4 hari-orang.

**Masalah.** Heuristik visual yang konsisten antarmodel bisa tetap salah jika tidak ada kaitan dengan kegagalan pengguna.

**Implementasi dan target.** Bangun pasangan screenshot/task sintetis, catat viewport, fokus, cara pemulihan dan penjelasan reviewer independen. Pisahkan kesepakatan reviewer dari bukti tugas selesai. [shadow-accessibility/SKILL.md](../shadow-accessibility/SKILL.md) · [shadow-design/SKILL.md](../shadow-design/SKILL.md)

**Validasi.** Bandingkan dashboard kurang kontras dengan dashboard lebih sederhana tetapi status darurat tersembunyi bagi keyboard user.

**DoD.** Setiap finding berat memiliki dampak tugas, kondisi tampilan dan pembanding. Ketidaksepakatan diberi langkah verifikasi, bukan diselesaikan dengan voting otomatis.

### E12 · Simulator keputusan dan retry untuk konektor workshop

**Bidang E, G, L, H** · Dependensi D16,D17 · P1 · Risiko M · 2–4 hari-orang.

**Masalah.** Approval membuat ruang tidak selalu meliputi pembukaan, moderasi atau publikasi hasil. Timeout bisa meninggalkan resource remote yang tidak diketahui agent.

**Implementasi dan target.** Gunakan konektor tiruan stateful untuk menelusuri transisi dan request IDs; pisahkan queue pagination, identitas host, owner jawaban dan rekonsiliasi operasi ambigu. [shadow-design/SKILL.md](../shadow-design/SKILL.md) · [evals/evals.json](../evals/evals.json)

**Validasi.** Simulasikan timeout setelah create dan sisipkan pesan peserta yang tampak seperti perintah moderasi pada halaman kedua.

**DoD.** Tidak terjadi double create, tindakan moderator tanpa izin, atau distribusi URL host. Status unknown dipulihkan atau diserahkan ke fasilitator.

### E13 · Gerbang performa yang membedakan saturasi generator dan layanan

**Bidang A, F, H, K** · Dependensi T11,T10 · P2 · Risiko M · 3–5 hari-orang.

**Masalah.** Skenario HTTP benar masih dapat menyalahkan server apabila generator berbagi CPU atau laju kedatangan aktual tak mencapai target.

**Implementasi dan target.** Jabarkan arrival rate, concurrency, warmup, data cache dan resource generator sebagai bagian laporan. Verifikasi dry-run parser terhadap trace tersimpan sebelum mengusulkan run berbiaya. [shadow-perf/SKILL.md](../shadow-perf/SKILL.md) · [shadow-ops/SKILL.md](../shadow-ops/SKILL.md)

**Validasi.** Bandingkan dua trace sintetis dengan latensi klien tinggi, yang satu memiliki saturasi generator dan yang lain saturasi server.

**DoD.** Kedua hasil memiliki diagnosis yang berbeda, interval bukti jelas dan tidak meluncurkan tes beban tanpa persetujuan.

### E14 · Konservasi informasi saat dokumen resmi dirender ulang

**Bidang D, G, H, J** · Dependensi C15,T05 · P1 · Risiko M · 2–4 hari-orang.

**Masalah.** Dokumen valid secara format dapat kehilangan pemilik risiko, nomor versi, atau catatan pengecualian saat berpindah renderer.

**Implementasi dan target.** Buat invariant semantik yang menghubungkan field sumber ke tabel, lampiran dan hasil render. Prioritaskan struktur yang diperlukan penerima dan gunakan renderer yang sudah disetujui. [shadow-doc/scripts/doc_engine_test_suite.py](../shadow-doc/scripts/doc_engine_test_suite.py) · [shadow-handover/SKILL.md](../shadow-handover/SKILL.md)

**Validasi.** Hapus kolom pengecualian dari template pada fixture, serta ubah redaksi judul tanpa mengubah makna pada kontrol positif.

**DoD.** Regresi makna terdeteksi dengan lokasi field; perubahan visual yang setara tetap lulus. Penerima dapat melacak status item dari dokumen ke sumber.

### E15 · Batas keputusan berurutan ketika scope berubah saat agent aktif

**Bidang B, E, I, L** · Dependensi X07,T09,C03 · P1 · Risiko H · 2–4 hari-orang.

**Masalah.** Izin dari pesan sebelumnya dapat digunakan kembali setelah user mempersempit tugas atau mengganti target; kebalikannya, user dapat ditanya berulang untuk aksi yang sama.

**Implementasi dan target.** Bangun fixture percakapan beberapa giliran: review, persetujuan terbatas, lalu instruksi berhenti atau pindah repo. Rekam state otorisasi sebelum setiap panggilan dan saat handoff. [shadow-monarch/SKILL.md](../shadow-monarch/SKILL.md) · [handoff/SKILL.md](../handoff/SKILL.md)

**Validasi.** Replay pada host ber-UI dan fallback tanpa UI. Sertakan jawaban terlambat untuk pertanyaan yang sudah tidak relevan.

**DoD.** Perubahan scope berlaku sebelum aksi dependen berikutnya, pilihan identik tidak ditanyakan ulang dan handoff memuat batas terakhir yang benar.
