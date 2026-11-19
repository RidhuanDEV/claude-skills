# Audit skill inti dari antislop sampai shadow-domain

Lingkup mencakup 24 direktori skill tingkat atas dalam urutan alfabet. Setiap tautan menunjuk kontrak milik skill. Nilai menggambarkan kecocokan kontrak untuk kerja lintas agen dan proyek. “ALREADY GOOD” menunjukkan bahwa kontrak memberi batas yang berguna dan cara membedakan hasil benar dari salah. “NEED IMPROVEMENT” menandai celah spesifik yang dapat diperbaiki tanpa mendesain ulang fungsi utama. “TOO BAD NEED MANY IMPROVEMENT” dipakai bila instruksi wajib dapat menghasilkan beberapa subsistem di luar kebutuhan pada tugas yang sah.

## Reproduksi dan batas bukti

Perintah berikut dijalankan dari akar checkout. Keempat suite lulus. Checker Python memeriksa model atau laporan contoh. Suite Node memeriksa keputusan melalui MCP dengan repositori fixture. Skenario penerimaan di setiap entri adalah usulan pengujian berikutnya kecuali bila disebut telah dijalankan. Audit ini tidak mengukur hasil percakapan langsung pada tiga host.

```powershell
python shadow-debug/scripts/debug_hypothesis_gate.py --self-test
python shadow-concurrency/scripts/concurrency_invariant_checker.py --self-test
python shadow-domain/scripts/domain_invariant_verifier.py --self-test
node --test mcp-servers/shadow-api-mcp/discovery.test.mjs
```

## antislop — NEED IMPROVEMENT

Memilih mode audit atau pendampingan UI, lalu mengaktifkan filter visual, bahasa, dan interaksi sesuai kebutuhan. [Kontrak antislop](../antislop/SKILL.md)

**Dasar penilaian.** Bagian Two Usage Modes memeriksa sesi dan preferensi lintas proyek. Saat berkas preferensi hilang, proses berhenti untuk menanyakan mode bahkan pada review baca-saja. Instruksi Monarch telah menetapkan `during`.

**Perbaikan.** Masukkan keputusan tingkat proyek/host yang eksplisit ke urutan resolusi.

**Skenario penerimaan.** Dengan preferensi proyek `during`, tanpa settings, review satu label harus menghasilkan temuan langsung tanpa menulis laporan atau bertanya ulang.

## antislop-code — ALREADY GOOD

Menyeleksi komentar yang perlu menjelaskan alasan, kontrak publik, atau batas non-obvious ketika kode berubah. [Kontrak antislop-code](../antislop-code/SKILL.md)

**Dasar penilaian.** Bagian Not a Ban memberi pengecualian atas heuristik membersihkan komentar. Reviewer dapat membedakan dokumentasi publik dari narasi mekanis.

**Perbaikan.** Tambahkan pasangan contoh pragmas dan pengecualian lisensi ke corpus pengujian.

**Skenario penerimaan.** Pada diff dengan komentar pengulang assignment dan direktif linter, hanya komentar pengulang layak diusulkan untuk dihapus.

## antislop-copywriting — ALREADY GOOD

Mengedit CTA, pesan kesalahan, dan microcopy Inggris/Indonesia agar pengguna tahu tindakan berikut. [Kontrak antislop-copywriting](../antislop-copywriting/SKILL.md)

**Dasar penilaian.** What NOT to flag dan Voice calibration membatasi false positive terhadap suara penulis dan istilah yang disengaja.

**Perbaikan.** Tambahkan fixture lintas bahasa dengan label produk yang sudah disetujui tim.

**Skenario penerimaan.** Pada dialog pembayaran, pertahankan label merek dan angka invoice, ganti tombol ambigu dengan tindakan yang benar-benar akan dijalankan.

## antislop-human — ALREADY GOOD

Mengidentifikasi hambatan praktis penggunaan seperti status yang hanya dibedakan oleh warna, fokus hilang, dan kontrol yang sulit dicapai. [Kontrak antislop-human](../antislop-human/SKILL.md)

**Dasar penilaian.** Bagian Focus & States memberi kondisi yang dapat diamati pada tema terang, gelap, dan forced-colors.

**Perbaikan.** Tambahkan bentuk bukti untuk menyerahkan masalah semantik yang lebih dalam kepada shadow-accessibility.

**Skenario penerimaan.** Untuk badge gagal yang hanya berwarna merah, minta teks status dan verifikasi bahwa keyboard dapat mengakses tindakan pemulihan pada fixture lokal.

## antislop-layoutmobile — ALREADY GOOD

Menguji reflow berdasarkan ukuran konten dan memastikan grid, teks, serta tindakan tetap dapat digunakan di lebar antara dua viewport populer. [Kontrak antislop-layoutmobile](../antislop-layoutmobile/SKILL.md)

**Dasar penilaian.** Bagian Breakpoints meminta peninjau menyempitkan viewport hingga konten pecah. Penyebab masalah ditautkan ke ukuran konten aktual.

**Perbaikan.** Sertakan fixture tabel lebar dengan scroll lokal yang disengaja.

**Skenario penerimaan.** Minta layout daftar dan tabel pada lebar transisi. Daftar harus reflow, tabel dapat scroll di dalam wadah tanpa overflow halaman.

## antislop-ui — ALREADY GOOD

Memeriksa hierarki visual, gerak, warna dan tipografi agar mengikuti identitas produk dan fungsi kontrol. [Kontrak antislop-ui](../antislop-ui/SKILL.md)

**Dasar penilaian.** Visual & Color membedakan default tanpa alasan dari pilihan warna yang didukung identitas merek.

**Perbaikan.** Rekam referensi desain yang dipakai untuk menerima pengecualian agar reviewer berikutnya memahami pilihan tim.

**Skenario penerimaan.** Bandingkan dua hero dengan gradasi sama. Pertahankan yang didukung brand guide, minta alasan atau revisi pada yang sekadar dekorasi.

## context7 — NEED IMPROVEMENT

Mengambil dokumentasi pustaka melalui resolver dan query dokumentasi untuk mendukung keputusan implementasi. [Kontrak context7](../context7/SKILL.md)

**Dasar penilaian.** Empat langkah Workflow berakhir dengan penerapan sintaks terkini. Tidak ada langkah eksplisit untuk mengekstrak versi lockfile atau menangani hasil untuk major berbeda.

**Perbaikan.** Catat versi terpasang, identitas sumber resmi dan versi sumber. Jika cakupan versi belum jelas, gunakan sumber yang cocok sebelum menerapkan.

**Skenario penerimaan.** Pada proyek yang mengunci major lama, berikan hasil dokumentasi major baru. Agent harus meminta atau mencari rujukan yang cocok sebelum mengganti API.

## handoff — NEED IMPROVEMENT

Mentransfer tujuan, keputusan, status bukti, dan permukaan yang belum diuji antaragen, termasuk sesi paralel. [Kontrak handoff](../handoff/SKILL.md)

**Dasar penilaian.** Kontrak merge memelihara readiness terendah dan memberi peringatan konflik, tetapi fallback save menyebut path drive D pada mesin penulis.

**Perbaikan.** Temukan MCP dari konfigurasi host atau akar instalasi. Validasi HEAD saat melanjutkan langkah yang bergantung pada snapshot.

**Skenario penerimaan.** Di checkout Unix atau drive lain, simulasi MCP belum dimuat. Laporan harus menyebut lokasi yang ditemukan atau blocker nyata dan menjaga label sesi lama.

## shadow-accessibility — NEED IMPROVEMENT

Menelaah semantik, navigasi keyboard, pembaca layar dan reflow serta menjembatani temuan UI ke perbaikan terukur. [Kontrak shadow-accessibility](../shadow-accessibility/SKILL.md)

**Dasar penilaian.** Pilar formulir mewajibkan `<label htmlFor>` untuk setiap input. Aturan React yang spesifik terlalu sempit untuk kontrol native dengan label pembungkus dan proyek HTML non-React.

**Perbaikan.** Nilai hubungan label dan accessible name dari DOM serta pohon aksesibilitas sebelum menyarankan mekanisme framework tertentu.

**Skenario penerimaan.** Fixture berisi label pembungkus dan input tanpa accessible name. Tuntut temuan untuk kasus kedua saja jika perilaku label pertama terkonfirmasi.

## shadow-api — ALREADY GOOD

Menentukan sumber dokumentasi, generator, viewer, koleksi dan cara memperbaruinya. Membantu memilih format saat README hanya merangkum endpoint. [Kontrak shadow-api](../shadow-api/SKILL.md)

**Dasar penilaian.** Implementasi memisahkan bukti pendukung dari sumber otoritatif. Suite discovery lokal lulus 38/38 termasuk README, pilihan eksplisit, generator, serta kepemilikan yang belum pasti.

**Perbaikan.** Tambahkan evaluasi percakapan host dengan penulisan file dicegat sampai jawaban pilihan format masuk.

**Skenario penerimaan.** Menjalankan suite pada bagian Reproduksi menguji keputusan MCP. Ulangi prompt generik pada repo README saja dan rekam urutan event pertanyaan, jawaban, lalu penulisan di tiap host.

## shadow-architect — NEED IMPROVEMENT

Memilih batas modul dan ADR yang dapat dipelihara di dalam satu sistem, dengan preseden brownfield dan pertimbangan biaya perubahan. [Kontrak shadow-architect](../shadow-architect/SKILL.md)

**Dasar penilaian.** Persyaratan Mandatory Architecture Deliverables dan gate menuju plan/bootstrap tidak membedakan pertanyaan desain satu modul dari desain aplikasi penuh secara operasional.

**Perbaikan.** Tetapkan pemicu ADR berdasarkan dampak keputusan, serta keluaran minimum untuk konsultasi baca-saja.

**Skenario penerimaan.** Untuk memilih letak validasi satu kasus penggunaan, hasil cukup memuat preseden, invariant dan trade-off. Desain multi-modul yang mengubah deployment layak memperoleh ADR lebih lengkap.

## shadow-auth — NEED IMPROVEMENT

Memeriksa otorisasi di server, batas tenant, revocation dan penjagaan integrasi SSO internal. [Kontrak shadow-auth](../shadow-auth/SKILL.md)

**Dasar penilaian.** Bagian Policy Test Matrix menyebut 403/404 juga untuk pemanggil tanpa autentikasi. Aturan literal bisa mengubah respons 401 yang sudah menjadi kontrak endpoint.

**Perbaikan.** Pisahkan principal anonim, login sah tanpa izin, dan penyembunyian keberadaan resource. Ambil status yang disepakati dari kontrak proyek.

**Skenario penerimaan.** Fixture endpoint yang mendefinisikan 401 anonim dan 403 untuk role salah harus mempertahankan keduanya, termasuk header autentikasi yang telah ditetapkan.

## shadow-bootstrap — TOO BAD NEED MANY IMPROVEMENT

Memulai repo baru dengan stack pilihan tim, generator resmi dan langkah awal yang dapat dijalankan ulang. [Kontrak shadow-bootstrap](../shadow-bootstrap/SKILL.md)

**Dasar penilaian.** Delapan pilar wajib menggabungkan OpenAPI, DB/ORM, health probe DB+Redis, Compose dan struktur direktori tertentu. Proyek CLI offline dan situs statis juga masuk cakupan deskripsi greenfield.

**Perbaikan.** Pisahkan baseline dari kapabilitas opsional. Petakan tiap artefak ke kebutuhan proyek dan keputusan pengguna sebelum generator dijalankan.

**Skenario penerimaan.** Bandingkan CLI lokal tanpa HTTP/DB dengan layanan HTTP ber-DB. Fixture pertama harus menghasilkan nol spesifikasi API, migrasi dan layanan data. Fixture kedua hanya mengaktifkan tooling yang dipilih.

## shadow-browser — NEED IMPROVEMENT

Memverifikasi interaksi web nyata, overflow, konsol dan jaringan pada rute lokal yang diizinkan. [Kontrak shadow-browser](../shadow-browser/SKILL.md)

**Dasar penilaian.** Bagian Console & Network meminta pelaporan semua 4xx/5xx. Tanpa oracle per skenario, respons valid pada alur login gagal dapat dibaca sebagai regresi.

**Perbaikan.** Catat hasil yang diharapkan, rute dan fixture sebelum klik. Bedakan respons yang sengaja dipicu dari kegagalan aset tak terduga.

**Skenario penerimaan.** Pada fixture login invalid, 401 yang ditampilkan dengan benar memenuhi skenario, sedangkan 404 pada bundle JavaScript menghasilkan temuan.

## shadow-cache — NEED IMPROVEMENT

Menyelaraskan invalidasi UI, cache server dan isolasi cache antar pengguna serta mengurangi pekerjaan ganda. [Kontrak shadow-cache](../shadow-cache/SKILL.md)

**Dasar penilaian.** Bagian Idempotency Keys menetapkan TTL 24 jam dan replay respons tersimpan, tetapi contoh rekaman tidak mengikat kunci ke fingerprint payload.

**Perbaikan.** Serahkan otoritas idempotensi transaksi kepada shadow-concurrency. Tentukan cakupan kunci, fingerprint, retensi dan jendela retry dari kontrak bisnis.

**Skenario penerimaan.** Dalam model lokal, kirim dua operasi dengan identitas kunci sama tetapi isi berbeda. Rekaman respons pertama tidak boleh memenuhi operasi kedua tanpa mendeteksi konflik.

## shadow-compat — NEED IMPROVEMENT

Menganalisis perubahan semantik yang mematahkan konsumen, kompatibilitas runtime, dan variasi browser atau platform. [Kontrak shadow-compat](../shadow-compat/SKILL.md)

**Dasar penilaian.** Aturan akhir meminta pengujian terhadap setiap klien aktif sebelum merge. Skill belum menentukan bukti pengganti bila klien eksternal tidak dapat dijalankan tim.

**Perbaikan.** Daftar owner, versi dan contoh payload yang sah per konsumen. Laporkan cakupan yang tersisa dan pengambil keputusan rollout.

**Skenario penerimaan.** Jika aplikasi internal tersedia dan klien mitra offline, rekam bukti replay untuk internal dan batas verifikasi mitra secara terpisah.

## shadow-concurrency — ALREADY GOOD

Menalar batas transaksi, deduplikasi, urutan pesan, dan pemulihan worker setelah crash. [Kontrak shadow-concurrency](../shadow-concurrency/SKILL.md)

**Dasar penilaian.** Checker lokal lulus 7/7, termasuk penolakan ACK terlalu awal, efek ganda saat replay dan klaim exactly-once eksternal.

**Perbaikan.** Pasangkan hasil checker deskriptif dengan integration fixture untuk storage atau broker yang memang dipakai proyek.

**Skenario penerimaan.** Lakukan redelivery pada model checker. Sebagai penerimaan integrasi mendatang, hentikan worker lokal setelah commit dan sebelum ACK, lalu hitung efek logis sesudah restart.

## shadow-data — NEED IMPROVEMENT

Merencanakan migrasi expand/contract, backfill, seed deterministik dan retensi data sambil menjaga pembaca lama. [Kontrak shadow-data](../shadow-data/SKILL.md)

**Dasar penilaian.** Playbook fase migrasi dan batas izin tersedia. Keputusan melepas skema lama memerlukan bukti konsumsi lintas layanan serta owner operasional yang spesifik proyek.

**Perbaikan.** Jadikan daftar pembaca/penulis, ambang backfill, bukti adopsi dan penanggung jawab pelepasan sebagai keluaran fase contract.

**Skenario penerimaan.** Pada fixture dua consumer, satu masih membaca kolom lama. Expand dapat direncanakan, tetapi contract tertahan sampai konsumen lama dimigrasikan dan diverifikasi.

## shadow-db — NEED IMPROVEMENT

Menginspeksi metadata DB, menggambar ERD, membandingkan skema, dan menyiapkan artefak ETL untuk diperiksa tim data. [Kontrak shadow-db](../shadow-db/SKILL.md)

**Dasar penilaian.** Bagian ETL menyebut enam hasil generator production-ready. Bukti bahwa file terbentuk saja belum mengukur keberhasilan transformasi, checkpoint atau rekonsiliasi target.

**Perbaikan.** Laporkan tingkat bukti per pasangan engine. Bedakan artefak yang dihasilkan, yang lolos validasi format, dan yang berhasil dijalankan pada fixture lokal.

**Skenario penerimaan.** Untuk sumber berisi NULL, kunci gabungan dan dua batch, hitung ulang jumlah serta kunci target setelah replay. Catat kode keluaran runtime ETL yang benar-benar dipakai.

## shadow-debug — ALREADY GOOD

Mengisolasi sebab kegagalan dari gejala melalui hipotesis yang dapat digugurkan dan bukti gagal-sebelum/lulus-sesudah. [Kontrak shadow-debug](../shadow-debug/SKILL.md)

**Dasar penilaian.** Self-test lokal lulus 6/6. Kasus tebakan tunggal, root cause pengulang gejala, dan kebocoran sandi pada laporan ditolak checker.

**Perbaikan.** Tambahkan satu handoff insiden dengan hipotesis yang sudah gugur agar agen penerus tidak mengulang percobaan yang sama.

**Skenario penerimaan.** Jalankan checker bawaan. Fixture lanjutan cukup memuat log yang cocok dengan dua sebab. Agen harus memilih observasi yang membedakan keduanya sebelum mengedit kode.

## shadow-design — NEED IMPROVEMENT

Memetakan cerita pengguna ke alur, layar, state dan kriteria penerimaan serta memilih paket rujukan desain yang sesuai. [Kontrak shadow-design](../shadow-design/SKILL.md)

**Dasar penilaian.** Blok Foreign-Key Reference Routing menggunakan tautan `file:///d:/...` ke checkout penulis. Pemilihan topik bisa benar namun rujukannya gagal dibuka dari instalasi lain.

**Perbaikan.** Gunakan tautan relatif terhadap skill dan verifikasi integritas dari direktori instalasi sementara. Izinkan state yang tidak relevan diberi alasan singkat.

**Skenario penerimaan.** Salin skill dan rujukannya ke root lain, putus akses ke workspace lama, lalu buka referensi empty-state. Pemeriksaan harus menyelesaikan path di dalam salinan.

## shadow-discovery — NEED IMPROVEMENT

Memilah bukti, asumsi, keputusan dan persyaratan sehingga stakeholder serta engineer menyepakati masalah yang sama. [Kontrak shadow-discovery](../shadow-discovery/SKILL.md)

**Dasar penilaian.** Bagian Mandatory Discovery Deliverables dan Stage 1 Exit Gate cocok untuk discovery proyek, namun menambah beban untuk satu ketidakjelasan lokal bila diterapkan sekaligus.

**Perbaikan.** Berikan mode klarifikasi satu keputusan, discovery fitur, dan baseline proyek. Pilih berdasarkan keputusan yang dapat berubah setelah jawaban pengguna.

**Skenario penerimaan.** Untuk dua interpretasi tanggal jatuh tempo, keluarkan satu pertanyaan beropsi kepada owner. PRD lengkap baru masuk akal bila cakupan memang satu produk atau modul.

## shadow-doc — NEED IMPROVEMENT

Menelusuri sumber dokumen, menjaga pipeline proyek, serta membangun dan memvalidasi keluaran berformat dari sumber yang terpelihara. [Kontrak shadow-doc](../shadow-doc/SKILL.md)

**Dasar penilaian.** Golden Laws meminta regenerasi lewat doc_scaffold.py, sedangkan bagian 3A memprioritaskan generator lokal dan membatasi AST pada global engine. Urutan baca dapat mengubah tindakan.

**Perbaikan.** Batasi instruksi scaffold di tempat pertama kali disebut dengan syarat global engine telah dipilih. Gunakan satu tabel presedensi bagi seluruh generator.

**Skenario penerimaan.** Pada proyek yang mendokumentasikan generator sendiri, permintaan koreksi satu paragraf harus mengubah sumber lama dan memakai perintah lokal. Tolak penambahan AST atau generator paralel.

## shadow-domain — ALREADY GOOD

Menerjemahkan aturan bisnis, transisi dan konflik kebijakan ke invariant lintas API, entitas dan penyimpanan. [Kontrak shadow-domain](../shadow-domain/SKILL.md)

**Dasar penilaian.** Self-test lokal lulus 6/6, termasuk eskalasi aturan pembatalan ambigu, deteksi DDD berlebihan pada CRUD dan transisi terminal ilegal.

**Perbaikan.** Tambah skenario handoff perubahan kebijakan dengan nama owner bisnis dan keputusan yang berlaku per tanggal.

**Skenario penerimaan.** Jalankan verifier bawaan. Pada fixture kebijakan void setelah settlement yang belum diputuskan, keluaran harus meminta keputusan dan menahan implementasi transisi.
