# Rencana peningkatan 15 skill inti

Rencana ini menindaklanjuti 14 skill berstatus **NEED IMPROVEMENT** dan satu berstatus **TOO BAD NEED MANY IMPROVEMENT** dalam [audit inti](skill-review-core.md). Bukti sumbernya adalah kontrak dan implementasi lokal. Semua skenario penerimaan di bawah adalah tugas implementasi mendatang. Perintah, hasil uji dan kesiapan yang tercatat dalam audit sebelumnya tetap terpisah.

## Urutan implementasi dan pembagian keputusan

1. **Mulai dengan bootstrap, auth, data dan DB.** Keputusan pada empat skill ini dapat memasang dependensi, mengubah kontrak identitas atau menyentuh data. Uji batas negatif pada fixture lokal sebelum memakai sistem bersama.
2. **Perbaiki handoff, context7, doc dan design.** Buat bukti sumber, resolusi versi, dan portabilitas dapat diteruskan dari satu host ke host lain. Mulai dari data lama agar konsumen existing tetap dapat melanjutkan pekerjaan.
3. **Perjelas kolaborasi pada discovery, architect, compat dan cache.** Lacak pemilik keputusan, invariant dan konsumen yang terdampak. Mulai dari satu perubahan brownfield yang dapat dibalik.
4. **Perbaiki kualitas interaksi pada antislop, accessibility dan browser.** Uji kasus benar dan salah secara berdampingan. Periksa bukti perilaku dalam host hanya bila tersedia.

Setiap increment mengubah instruksi dalam skill pemilik terlebih dulu. Gunakan [eval percakapan](../evals/evals.json) untuk pemilihan tindakan dan harness lokal yang sudah dimiliki tiap skill untuk perilaku program. Satu skenario harus merekam input, target, tindakan/penolakan, efek samping dan bukti yang belum diukur. Perubahan kode MCP hanya diperlukan jika hasil yang dibutuhkan tidak dapat dibuktikan dari kontrak dan data saat ini. Hak eksekusi tetap berasal dari [protokol otorisasi](../shadow-monarch/reference/EXECUTION-APPROVAL-PROTOCOL.md).

## antislop

**Kasus tim.** Seorang reviewer meminta audit baca-saja atas satu dialog, sementara AGENTS proyek memilih `during`. Keputusan mode yang sudah diberikan harus bertahan saat agen lain mengambil pekerjaan.

**Keputusan desain.** Pertahankan urutan sumber keputusan yang dapat dijelaskan. Pilihan sesi mengalahkan preferensi dengan cakupan lebih luas. Mode mengatur waktu review, sedangkan izin menulis mengikuti permintaan. Dua dimensi ini harus dihitung terpisah.

**Increment dan pemilik.** Perbaiki bagian Two Usage Modes di kontrak. Tambahkan contoh kombinasi sesi, kebijakan proyek, konfigurasi host dan nilai rusak. Di eval percakapan, rekam jumlah pertanyaan serta daftar operasi tulis untuk mode audit. [antislop/SKILL.md](../antislop/SKILL.md)

**Penerimaan positif.** Preset proyek `during`, settings kosong, audit dialog → temuan di chat, nol pertanyaan mode dan nol file. Pilihan sesi `after` mengubah mode untuk sesi itu saja.

**Penerimaan negatif dan handoff.** Tanpa keputusan yang berlaku, satu pertanyaan lalu tunggu. Instruksi yang disisipkan sebagai nilai settings tidak boleh dijalankan. Reviewer menyimpan asal pilihan dan bukti operasi file dari sandbox.

## context7

**Kasus tim.** Engineer merawat aplikasi di major lama sebuah ORM. Cuplikan terbaru dapat memuat opsi konfigurasi yang belum tersedia.

**Keputusan desain.** Kebutuhan menjawab “cara menggunakan versi terpasang” berbeda dari “cara migrasi ke versi baru”. Ambil versi resolved dari lockfile/workspace, bedakan range manifest dari versi aktual, dan pastikan halaman dokumentasi sesuai versi serta penerbitnya.

**Increment dan pemilik.** Perinci workflow resolver dan query dalam kontrak. Untuk monorepo, pilih manifest pemilik import. Tambahkan alur saat hasil multi-major atau resolver offline, termasuk dokumentasi resmi yang sudah terbundel dan deklarasi tipe lokal sebagai bukti terbatas. [context7/SKILL.md](../context7/SKILL.md)

**Penerimaan positif.** Fixture dua workspace dengan dua major. Jawaban harus mengaitkan contoh/simbol dengan workspace yang ditanya, versi, dan sumber yang memuatnya.

**Penerimaan negatif dan handoff.** Hasil untuk major lain tidak menjadi dasar edit. Jika versi tidak bisa dipastikan, tandai ketidakpastian dan serahkan ke owner dependency bila keputusan migrasi diperlukan. Simpan nama simbol, versi, sumber dan pemeriksaan lokal yang dilakukan.

## handoff

**Kasus tim.** Dua agen bekerja di cabang berbeda dan meneruskan satu pekerjaan ke checkout pada drive lain. Langkah berikut dalam snapshot mungkin mengacu ke file yang sudah dipindah.

**Keputusan desain.** Pisahkan identitas repo, worktree/cabang, label sesi, dan tingkat kesiapan. Pertahankan history dan warning pada merge. Pilih otomatis hanya jika identitas pekerjaan terverifikasi.

**Increment dan pemilik.** Hilangkan fallback path per mesin dalam kontrak. Periksa respons save/load/merge pada MCP yang ada, bandingkan Git state saat load dengan keadaan checkout. Tambahkan data opsional yang kompatibel dengan snapshot lama jika identitas saat ini kurang. [handoff/SKILL.md](../handoff/SKILL.md) · [mcp-servers/shadow-handoff-mcp/index.mjs](../mcp-servers/shadow-handoff-mcp/index.mjs)

**Penerimaan positif.** Simpan dua label pada fixture temp, pindahkan checkout, muat snapshot by project/label, lalu gabungkan. Bukti yang belum diuji harus tetap ada dan jejak masing-masing keputusan dapat ditelusuri.

**Penerimaan negatif dan handoff.** Cabang/HEAD berbeda menahan langkah yang menyentuh file terdampak sampai diperiksa. Snapshot lama tanpa metadata harus dapat dibaca dengan status tidak pasti. Serahkan daftar konflik keputusan dan sumber masing-masing kepada agen penerus.

## shadow-accessibility

**Kasus tim.** Formulir pembayaran memakai label native terbungkus pada desktop dan komponen kustom dalam dialog mobile. Pemeriksaan lint berbasis sintaks JSX akan melewatkan perilaku nyata.

**Keputusan desain.** Nilai nama, peran, status, urutan fokus dan pemulihan fokus dari hasil render. Pisahkan pemeriksaan otomatis, pengamatan keyboard, dan pengujian assistive technology yang benar-benar tersedia.

**Increment dan pemilik.** Susun ulang pilar formulir di kontrak dengan contoh HTML dan React, termasuk label pembungkus, label eksplisit dan kontrol kustom. Tautkan shadow-browser untuk pengambilan accessibility tree bila host mendukung, lalu dokumentasikan tahapan manual untuk kasus yang tersisa. [shadow-accessibility/SKILL.md](../shadow-accessibility/SKILL.md)

**Penerimaan positif.** Dua input dengan nama yang benar melalui teknik native berbeda diterima. Dialog memindahkan dan mengembalikan fokus ke pemicu setelah ditutup.

**Penerimaan negatif dan handoff.** Placeholder tunggal pada kontrol tanpa nama memicu temuan. Hasil inspeksi tree tanpa screen reader tidak boleh diberi status lulus screen reader. Serahkan elemen, state, urutan tombol, hasil teramati dan dampak ke pemilik komponen.

## shadow-architect

**Kasus tim.** Tim meminta satu batas modul billing dalam monolit yang telah berjalan, lalu mempertimbangkan pemisahan deployment jika dua tim benar-benar perlu rilis independen.

**Keputusan desain.** Bandingkan biaya koordinasi, coupling data, batas transaksi, failure isolation dan reversibilitas. Rekomendasi lokal cukup ketika keputusan dapat dibalik. ADR dibutuhkan bila kontrak, data owner atau deployment lintas tim berubah.

**Increment dan pemilik.** Beri tiga tingkat keluaran pada kontrak, yaitu konsultasi, desain perubahan lintas modul, dan keputusan sistem. Pakai preseden brownfield dan template ADR yang ada. Dokumentasikan alternatif, pemilik keputusan, bukti, dan pemicu evaluasi ulang. [shadow-architect/SKILL.md](../shadow-architect/SKILL.md)

**Penerimaan positif.** Untuk batas validasi lokal, tunjukkan modul pemilik dan invariant tanpa menciptakan diagram sistem baru. Untuk memisahkan deployment, hasil memuat konsekuensi data dan strategi transisi.

**Penerimaan negatif dan handoff.** Jangan mengusulkan microservice hanya karena ada dua direktori. Penerima handoff harus bisa menyebut kondisi terukur yang akan membatalkan rekomendasi.

## shadow-auth

**Kasus tim.** Satu API mengembalikan 401 pada permintaan anonim, 403 untuk peran tidak cukup dan 404 pada visibilitas resource tertentu. Tim ingin memperbaiki satu policy tanpa mengubah kontrak klien.

**Keputusan desain.** Pisahkan autentikasi, izin aksi, hak melihat resource dan batas tenant. Untuk sistem SSO, buktikan issuer serta pemetaan principal dari SDK yang dimiliki proyek. Retensi audit dan penyamaran data mengikuti kebutuhan produk dan risiko.

**Increment dan pemilik.** Perbaiki Policy Test Matrix di kontrak. Mulai dari respons error dan entrypoint server yang dipakai; catat principal/aksi/resource/tenant dan lifecycle sesi. Gunakan shadow-api sebagai owner kontrak HTTP dan shadow-privacy untuk kebijakan log. [shadow-auth/SKILL.md](../shadow-auth/SKILL.md)

**Penerimaan positif.** Pada fixture server lokal, tiap identitas yang disiapkan memperoleh respons serta header sesuai kontrak, dan fungsi mutasi hanya dipanggil pada izin yang cocok.

**Penerimaan negatif dan handoff.** Klaim role dari input tidak memberi akses; log uji tidak menyimpan kredensial atau token. Handoff ke tim API menyertakan tabel policy, status/error yang diharapkan, serta bukti terhadap fixture.

## shadow-bootstrap

**Kasus tim.** Bandingkan CLI konversi file offline, situs statis, dan layanan HTTP dengan penyimpanan. Semuanya greenfield tetapi kebutuhan operasional dan biaya tooling berbeda.

**Keputusan desain.** Pisahkan kebutuhan lintas proyek (cara build, test, konfigurasi dasar) dari kapabilitas bersyarat seperti persistensi, queue, HTTP/API docs, telemetry, container dan CI. Gunakan stack yang dipilih. Ketidakjelasan format atau biaya layanan memerlukan pilihan pengguna.

**Increment dan pemilik.** Ganti delapan pilar seragam dengan tabel kebutuhan → bukti → kapabilitas → generator resmi → berkas yang diharapkan. Gunakan verifier resmi untuk provenance generator. Buat preview manifest dan jalankan generator hanya di target yang disetujui. Uji pengulangan pada target nonkosong dan kegagalan parsial. [shadow-bootstrap/SKILL.md](../shadow-bootstrap/SKILL.md) · [shadow-monarch/scripts/official_first_verifier.py](../shadow-monarch/scripts/official_first_verifier.py)

**Penerimaan positif.** CLI offline mendapat entrypoint, build/test dan konfigurasi minimum. Layanan ber-DB mendapat migrasi dan readiness sesuai stack. Verifikasi kedua hasil dengan menjalankan entrypoint normal di direktori sementara.

**Penerimaan negatif dan handoff.** Situs statis tidak memperoleh OpenAPI, ORM, Redis atau Compose tanpa kebutuhan. Target yang berisi file pengguna tidak boleh tertimpa saat retry. Serahkan manifest, versi generator, perintah reproduce dan laporan file yang disentuh.

## shadow-browser

**Kasus tim.** QA memeriksa login invalid di lokal. Respons 401 adalah hasil yang diharapkan, tetapi bundle JS 404 akan menggagalkan UI.

**Keputusan desain.** Nyatakan oracle untuk tiap aksi melalui status, konten, fokus dan state UI. Saat server tidak dapat dijangkau, bedakan kegagalan lingkungan dari regresi. Batasi pemeriksaan ke rute dan role yang relevan.

**Increment dan pemilik.** Ubah checklist browser menjadi alur siap-fixture → aksi → ekspektasi → observasi → cleanup. Pilih viewport berdasarkan layout dan target tugas. Periksa request terkait dan log dengan redaksi data sensitif. [shadow-browser/SKILL.md](../shadow-browser/SKILL.md)

**Penerimaan positif.** Pada fixture login invalid, 401 dan pesan pemulihan tepat dinilai lulus. Jalankan satu alur sukses terpisah.

**Penerimaan negatif dan handoff.** 404 pada JS, klik yang tidak berfungsi atau request ke luar host yang disetujui harus terlihat dalam hasil. QA menyerahkan langkah, viewport, URL teredaksi, status aktual dan batas pengujian ke engineer.

## shadow-cache

**Kasus tim.** Aplikasi menampilkan stok dari client cache dan server cache. Operasi mutasi dapat diulang akibat timeout. Konsistensi stok dan idempotensi transaksi membutuhkan pemilik berbeda.

**Keputusan desain.** Turunkan scope cache dari tenant, identitas, representasi dan perubahan otorisasi. Untuk idempotensi, sepakati arti kunci, fingerprint, response replay, retensi serta keterkaitan dengan commit durable. Pilih mekanisme yang sesuai jaminan bisnis.

**Increment dan pemilik.** Pisahkan bab freshness dan idempotency. Dokumentasikan snapshot waktu yang dapat diterima, pemicu invalidasi dan sumber otoritatif. Arahkan atomicity domain ke shadow-concurrency. Jangan mewajibkan Redis bila uniqueness DB sudah mencukupi. [shadow-cache/SKILL.md](../shadow-cache/SKILL.md)

**Penerimaan positif.** Model lokal mencakup timeout setelah commit dan replay payload sama, menghasilkan satu perubahan stok. Perubahan akses menghapus keterlihatan data lama dari cache yang relevan.

**Penerimaan negatif dan handoff.** Kunci sama dengan payload berbeda harus mengikuti kebijakan konflik. Tenant berbeda tidak mendapat entri cache tenant pertama. Serahkan skema kunci dan tabel transisi ke owner backend/frontend dengan batas kesegaran yang dipilih.

## shadow-compat

**Kasus tim.** Tim menurunkan default page size. OpenAPI masih valid namun aplikasi mitra dapat gagal memuat daftar lengkap.

**Keputusan desain.** Klasifikasikan kompatibilitas bentuk, makna, perilaku, data dan platform. Bedakan konsumen yang diketahui, dapat diuji, dan belum teramati. Pilih replay fixture, contract test, canary yang disetujui atau eskalasi berdasar risiko.

**Increment dan pemilik.** Tambahkan inventaris konsumen dan matriks versi ke kontrak. Gunakan contract/golden replay yang sudah ada. Kaitkan rollout dan rollback ke owner serta versi konsumen, tanpa mewajibkan framework test baru. [shadow-compat/SKILL.md](../shadow-compat/SKILL.md)

**Penerimaan positif.** Jalankan replay payload lama dan bandingkan jumlah item, cursor serta pemrosesan klien. Temuan menyebut dampak terhadap versi tertentu walau schema diff kosong.

**Penerimaan negatif dan handoff.** Jika aplikasi mitra offline, catat bukti yang belum diperoleh. Status semua klien kompatibel harus ditolak. Handoff memuat owner kontak, keputusan release yang tertunda dan batas observabilitas.

## shadow-data

**Kasus tim.** Migrasi mengganti kolom lama dengan bentuk baru saat dua versi aplikasi masih berjalan. Backfill dapat berhenti di tengah atau berbenturan dengan penulisan aktif.

**Keputusan desain.** Buat keputusan per fase berdasarkan ukuran tabel, pola baca/tulis, indeks, locking, replika dan opsi rollback. Batas batch dan ambang lag diambil dari lingkungan nyata setelah disetujui. Hapus janji universal “zero impact”.

**Increment dan pemilik.** Di tabel expand/backfill/switch/contract, tambahkan owner pembaca, penulis, checkpoint, penanganan konflik dan kondisi abort. Uji SQL target pada DB lokal yang seversi bila tersedia. Serahkan kontrak payload lama/baru ke shadow-compat. [shadow-data/SKILL.md](../shadow-data/SKILL.md)

**Penerimaan positif.** Fixture backfill dihentikan setelah satu batch, dilanjutkan dengan checkpoint sambil ada satu update. Invariant hasil akhir dan jumlah baris terjaga, data lebih baru tetap tersimpan.

**Penerimaan negatif dan handoff.** Jika consumer lama masih membaca kolom atau ada mismatch yang belum dijelaskan, tahan contract. Handoff menyertakan hasil rekonsiliasi, batas verifikasi lock/lag dan prosedur rollback per fase.

## shadow-db

**Kasus tim.** Tim memindahkan snapshot antar-engine dan mengharapkan ERD serta blueprint ETL. Tipe temporal, presisi numerik dan NULL dapat berubah makna walau file dapat diparse.

**Keputusan desain.** Pisahkan discovery read-only, pembangkitan desain, validasi sintaks, eksekusi lokal dan rekonsiliasi. Catat kemampuan driver/engine dan perilaku konversi yang hilang. Runtime yang tak tersedia membatasi klaim.

**Increment dan pemilik.** Perinci kapabilitas dan bukti per target di kontrak. Pada MCP telusuri detectEngine, mapTypeToTargetEngine dan handler generator. Tambahkan manifest hasil per artefak serta peringatan pemetaan lossy tanpa memecahkan caller lama. [shadow-db/SKILL.md](../shadow-db/SKILL.md) · [mcp-servers/shadow-db-mcp/index.mjs](../mcp-servers/shadow-db-mcp/index.mjs)

**Penerimaan positif.** Gunakan sumber lokal berisi desimal, dua NULL, timestamp, dan kunci gabungan. Cocokkan jumlah, nilai, key dan hasil replay dua batch di target lokal yang benar-benar tersedia.

**Penerimaan negatif dan handoff.** Saat hanya XML dapat diparse, hasil belum membuktikan job Pentaho berjalan. Unknown host tetap tertahan. Serahkan mapping yang perlu keputusan dan selisih rekonsiliasi ke DBA.

## shadow-design

**Kasus tim.** Designer, engineer dan QA berbagi alur pengajuan yang memiliki draft, pending, rejected dan retry. Mereka bekerja dari tiga host dengan root instalasi berbeda.

**Keputusan desain.** Gunakan bukti alur dan state yang dapat dicapai, lalu pilih referensi relevan secara relatif terhadap paket terpasang. Bedakan state domain dari status jaringan atau kondisi tampilan; beberapa state hanya berlaku untuk satu komponen.

**Increment dan pemilik.** Ganti alamat drive absolut di tabel Foreign-Key Reference Routing dengan referensi portabel. Uji resolusi setelah paket dipindah. Tambahkan kolom owner, event, guard, feedback, recovery dan alasan N/A pada model state. [shadow-design/SKILL.md](../shadow-design/SKILL.md)

**Penerimaan positif.** Pada instalasi sementara di root lain, semua tautan lokal yang dipakai dapat dibuka. Untuk fixture alur pengajuan, trace satu user story sampai recovery setelah timeout.

**Penerimaan negatif dan handoff.** Tolak tautan absolut yang hanya ada di mesin penulis serta state buatan tanpa transisi. Handoff ke frontend/QA menyertakan alur, state yang dicapai dan acceptance yang bisa diuji.

## shadow-discovery

**Kasus tim.** Satu kebijakan tanggal jatuh tempo ambigu dapat diselesaikan satu domain owner. Discovery produk baru memerlukan banyak stakeholder dan penelusuran data.

**Keputusan desain.** Pilih kedalaman berdasarkan besarnya keputusan, biaya kesalahan dan nilai bukti. Pisahkan fakta dari asumsi dan pihak yang berwenang menyelesaikan konflik. Gunakan interaksi langsung ketika satu jawaban dapat membuka pekerjaan.

**Increment dan pemilik.** Tambahkan tiga jalur pada kontrak: klarifikasi satu keputusan, discovery fitur dan discovery proyek. Untuk masing-masing nyatakan minimum input, keluaran, kondisi berhenti dan kriteria eskalasi. Hubungkan PRD penuh hanya dengan kebutuhan yang sesuai. [shadow-discovery/SKILL.md](../shadow-discovery/SKILL.md)

**Penerimaan positif.** Ambiguitas apakah “7 hari” kalender atau kerja memicu satu pertanyaan berpilihan kepada pemilik kebijakan. Setelah jawab, tambahkan contoh sebelum/sesudah tanggal batas ke acceptance.

**Penerimaan negatif dan handoff.** Jangan mengarang jawaban saat owner belum merespons atau membuat PRD untuk satu pilihan. Handoff mencatat keputusan, siapa yang memutuskan, tanggal dan bagian requirement yang berubah.

## shadow-doc

**Kasus tim.** Repo sudah membangun panduan dari Markdown melalui generator internal. Pengguna meminta koreksi konten. Pipeline global diperlukan hanya pada proyek yang memang memilihnya.

**Keputusan desain.** Turunkan graf sumber → transformasi → output → validasi dari konfigurasi dan perintah yang didukung. Bila ada dua generator aktif, pisahkan target dan ownership. Dukungan sebagian dapat diselesaikan melalui adapter kecil jika proyek mengizinkan.

**Increment dan pemilik.** Selaraskan Golden Laws dan urutan pada bagian 3A. Kaitkan resolve, assess_generator_compatibility dan pengujian suite dokumen ke keputusan yang sama. Verifikasi referensi, gambar, font atau diagram sesuai permintaan artefak. [shadow-doc/SKILL.md](../shadow-doc/SKILL.md) · [shadow-doc/scripts/doc_orchestrator.py](../shadow-doc/scripts/doc_orchestrator.py) · [shadow-doc/scripts/doc_engine_test_suite.py](../shadow-doc/scripts/doc_engine_test_suite.py)

**Penerimaan positif.** Fixture repo memiliki generator internal, satu sumber editable dan satu output. Perubahan satu paragraf menghasilkan diff di jalur yang diharapkan, tidak menambah pipeline dan dapat dibangun ulang.

**Penerimaan negatif dan handoff.** Output yang tidak punya sumber terverifikasi atau dua pipeline tanpa owner menahan penulisan. Handoff berisi lokasi sumber, entrypoint, tipe output, manifest perubahan dan mana yang sudah divalidasi secara visual.
