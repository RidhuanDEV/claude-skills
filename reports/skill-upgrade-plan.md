# Rencana peningkatan profesional Shadow Army

**Keputusan pertama yang diusulkan kepada Monarch:** gunakan satu kasus pencarian multi-tenant sebagai pilot untuk `shadow-monarch`, `shadow-search`, dan `shadow-eval`. Ketiganya memengaruhi keputusan yang sama: apakah perubahan kualitas pencarian layak dilanjutkan. Audit sudah menyediakan contoh ketika skor dapat lulus dengan bukti kosong. Tim bisa membuktikan perbaikan dengan data sintetis, menguji handoff antarpemilik, dan menilai hasil tanpa menyentuh sistem pelanggan. Jalur terpisah untuk pembatasan kepemilikan resource di `shadow-quality` dapat dimulai segera.

## Cakupan dan navigasi

Baseline `bac8745` beserta [audit sumber](skill-review.md). Rencana mencakup **38 skill utama** dan **17 referensi desain** yang memperoleh salah satu dari dua label perbaikan. Unit untuk referensi adalah path lengkap karena ada metode penelitian bernama sama. Label lama adalah alasan memulai pekerjaan; hasil kualifikasi yang diusulkan menentukan penilaian berikutnya.

| Backlog yang bisa diambil owner | Jumlah | Isi |
| --- | ---: | --- |
| [Engineering, desain, dan discovery](skill-upgrade-core.md) | 15 | Pemilihan arsitektur, identitas, data, perilaku UI, diagnosis, dan sumber pengetahuan. |
| [Delivery, assurance, dan operasi](skill-upgrade-delivery.md) | 23 | Evaluasi, operasional, rollout, biaya, governance, bukti teknik, dan kerja lintas tim. |
| [Metode desain dan riset](skill-upgrade-design-library.md) | 17 | Kapabilitas per modul, pembagian peran pada metode serupa, dan integrasi upstream. |

Untuk melihat kedalaman domain dan tugas akhir per skill utama, gunakan [silabus 38 kompetensi dan capstone](skill-upgrade-competencies.md). Untuk 17 modul pendukung, engagement dan ujian ada langsung di backlog desain.

## Apa yang berubah pada cara kerja skill

| Kapabilitas yang dibangun | Perilaku yang harus terlihat saat mengerjakan tugas | Jejak yang bisa dinilai reviewer |
| --- | --- | --- |
| Melakukan intake sesuai masalah | Identifikasi keputusan bisnis/teknis yang ditunggu, siapa pemiliknya, constraint, dampak salah keputusan, dan bukti yang sudah ada. Gunakan informasi repo sebelum bertanya. | Pada permintaan kecil, langsung bekerja. Pada pilihan material yang masih terbuka, muncul satu pertanyaan yang menyebut konsekuensi tiap opsi. |
| Mendiagnosis dan merevisi pendapat | Bentuk dua penjelasan masuk akal ketika data belum membedakan penyebab. Pilih observasi termurah yang dapat membedakannya. Perbarui keputusan ketika bukti baru muncul. | Transkrip keputusan menunjukkan bukti yang mengubah rekomendasi. Catatan ringkas berisi hasil dan alasan yang dapat diperiksa. |
| Memilih teknik sesuai konteks | Pilih jalur untuk proyek mapan, proyek baru, data terbatas, atau insiden. Pertimbangkan biaya, keterpulihan, kompatibilitas, dan dampak ke pengguna. | Masukan dengan satu fakta berbeda dapat menghasilkan keputusan berbeda dengan alasan domain yang tepat. |
| Menghasilkan pekerjaan yang dapat dipakai | Kirim patch, query, model biaya, keputusan arsitektur, research plan, matriks uji, atau runbook sesuai tugas. Pakai template dan toolchain proyek. | Penerima bisa mengulangi analisis, menilai keterbatasan, dan mengambil tindakan selanjutnya. Format deliverable mengikuti keputusan pengguna. |
| Mengetahui batas pengetahuan | Bedakan observasi, inferensi, asumsi, serta keputusan yang memerlukan owner manusia. Prioritaskan bukti repo, versi dependensi, kontrak, dan catatan operasional yang benar-benar terkait. | Bukti bertentangan memicu pemeriksaan lebih lanjut; data kosong menghasilkan status belum terukur. |
| Mengoper pekerjaan dengan aman | Catat revisi, scope, owner artefak, perubahan, dependensi, cara verifikasi, dan risiko tersisa. Untuk insiden tetapkan siapa yang dapat menghentikan rollout. | Penerima berhasil melanjutkan dari checkout bersih. Retry tidak menduplikasi perubahan atau mengambil resource job lain. |

**Bentuk perubahan di repo.** Simpan pemicu dan batas keputusan yang ringkas di SKILL.md. Pindahkan pengetahuan mendalam ke referensi milik skill yang dimuat saat diperlukan. Gunakan skrip hanya untuk keputusan yang memiliki input, output, dan oracle yang dapat diperiksa. Jadikan kasus ambigu sebagai simulasi dengan keputusan reviewer. Tambahkan manifest atau format lintas skill hanya bila dua implementasi pilot memperlihatkan struktur yang sama. Panduan struktur dan evaluasi tersedia di [spesifikasi Agent Skills](docs/references/agent-skills-specification.md) dan [panduan evaluasi](docs/references/evaluating-skills.md).

## Pilot terperinci: relevansi pencarian setelah indeks diganti

**Brief simulasi.** Setelah penggantian indeks, tim dukungan melaporkan pencarian bahasa Indonesia menurun. Tim produk ingin mempertahankan perubahan karena rerata evaluasi naik. Dua tenant memiliki dokumen berjudul sama. Ada dokumen yang izin bacanya dicabut setelah indeks dibuat. Owner produk perlu keputusan apakah indeks baru boleh dipromosikan.

| Tahap | Pekerjaan profesional | Artefak dan oracle |
| --- | --- | --- |
| Intake oleh Monarch | Pastikan tugas saat ini adalah evaluasi lokal. Cari kontrak akses, cara cutoff label relevansi, konfigurasi indeks lama/baru, dan workflow switch alias. | Decision record menunjuk path dan revisi yang benar. Eksekusi produksi membutuhkan keputusan tersendiri. |
| Diagnosis oleh search | Pisahkan kegagalan isolasi tenant, dokumen usang, duplikasi, dan relevansi. Bekukan query, kandidat, snapshot ACL, serta penilaian manusia untuk perbandingan berpasangan. | Fixture berisi query berlabel, query tanpa label, hasil duplikat, homonim antar-tenant, dokumen dicabut, dan query tanpa hasil. |
| Eksperimen | Bandingkan indeks lama dan baru untuk query identik. Tampilkan ukuran sampel dan hasil per bahasa/jenis query. Uji apakah satu tenant bervolume tinggi menutupi kerugian tenant kecil. | ID berulang tidak menaikkan recall. ACL diperiksa sebelum pemilihan top-K. Catat kasus ketika hasil relevan habis disaring. |
| Review oleh eval | Hitung ulang satu ranking kecil secara manual dan cocokkan hasil skrip. Bedakan tidak ada label dengan ground truth yang memang kosong. Periksa relevansi dan faithfulness secara terpisah bila ada jawaban generatif. | Satu hit dari dua ID relevan memberi recall 0,5. Tambahan salinan hit yang sama tidak mengubah hasilnya. Jawaban dengan kutipan yang salah gagal pada pemeriksaan sumber. |
| Keputusan | Bila ada kebocoran akses, tahan promosi dan serahkan bukti teredaksi ke owner auth/search. Bila sampel bahasa terlalu kecil, tetapkan label tambahan yang diperlukan. Bila satu segmen turun, tampilkan alternatif dan biaya rollback. | Ringkasan per segmen, sampel gagal, keputusan, owner dan cara verifikasi ulang. Reviewer dapat mengulang dari fixture tanpa akun pelanggan. |

**Percabangan untuk menguji penalaran.** Hilangkan dokumen terlarang tetapi sisakan penurunan pada bahasa Indonesia: keputusan bergeser ke analisis kualitas dan representativitas. Ganti snapshot ACL dengan data kedaluwarsa: hasil keamanan menjadi belum terverifikasi. Tambah dua query yang sama pada dataset: denominator dan kebijakan duplikasi harus dijelaskan. Hanya mengulang hasil agregat pada ketiga variasi merupakan kegagalan kualifikasi pilot.

## Tiga simulasi kolaborasi lain

| Engagement | Konflik yang harus diselesaikan | Pembagian kerja dan keluaran yang dinilai |
| --- | --- | --- |
| Rilis login dengan refresh cookie | Canary tampak sehat tetapi browser lama mengalami redirect loop; trafik canary berbeda komposisi dari kontrol. | Auth memetakan alur sesi dan revokasi, browser mereproduksi satu transisi, release menetapkan kriteria hold/promote per kohor, ops memeriksa keterpulihan. Owner produk memutuskan trade-off pengalaman pengguna. Artefak akhir mencantumkan distribusi sampel, temuan per kohor dan langkah rollback yang teruji di fixture. |
| Form pengajuan bantuan memiliki angka selesai rendah | Analitik hanya melihat pengguna yang berhasil mengirim. Perbaikan visual mungkin menutupi kegagalan keyboard atau instruksi yang membingungkan. | Discovery menyusun pertanyaan riset, design memilih partisipan dan metode berdasarkan hambatan, accessibility menilai tugas nyata, privacy mendefinisikan data minimum. Handoff menghubungkan observasi anonim ke keputusan mempertahankan, mengubah, atau menguji ulang flow. Otomasi tidak boleh mengarang peserta atau hasil wawancara. |
| Peningkatan biaya setelah skema data berubah | Spend naik bersamaan dengan trafik; cache menekan biaya tetapi menambah risiko salah-tenant dan data usang. | FinOps memisahkan biaya per transaksi dari volume, DB membandingkan rencana query dengan distribusi data, cache menguji key serta invalidasi, architect menilai pilihan indeks/cache dan biaya operasional. Keluaran berupa rekomendasi, rentang biaya, kondisi pembatalan dan pemeriksaan akses. |

## Urutan implementasi dan ketergantungan

| Gelombang | Siapa memiliki apa | Hasil yang membuka pekerjaan berikutnya |
| --- | --- | --- |
| 0. Baseline dan alat penilaian | Monarch + eval. Rekam tugas alami Indonesia/Inggris, owner, batas tindakan, output contoh, dan kejadian gagal dari audit. Quality menyediakan mock resource dua job. | Reviewer dapat mengulang kegagalan lama. Baseline per fixture disimpan. Keputusan yang memerlukan persetujuan dapat diobservasi di event host. |
| 1. Benahi keputusan berisiko | Owner quality, eval, search, realtime, supplychain, perf, bootstrap. Pilot di atas menguji dua owner dalam satu kasus. Untuk lainnya gunakan acceptance per skill di lampiran. | Input cacat dan kasus tanpa bukti berhenti pada status yang tepat. Mock dua job menunjukkan zero cross-job mutation. Pemeriksa artefak menyebut operasi yang dilewati. |
| 2. Pengambilan keputusan domain | Owner skill utama lainnya mengambil paket engineering dan delivery. Dahulukan jalur yang mengonsumsi hasil pilot atau menyentuh identitas/data. Mulai perubahan independen setelah oracle masing-masing tersedia. | Reviewer domain bisa memilih cabang yang benar untuk dua proyek berkarakter berbeda dan menunjukkan sumber, bukti, alternatif serta batas scope. |
| 3. Riset dan desain terapan | Pemilik shadow-design, discovery dan accessibility memimpin adapter untuk 17 modul. Jalur ini dapat berlangsung bersama gelombang 2 setelah baseline. | Resolusi provider dan dependensi lokal teruji. Dua metode bernama sama menghasilkan keluaran berbeda sesuai brief. Temuan research dapat ditelusuri ke data berizin. |
| 4. Kolaborasi dan promosi | Satu integrator untuk perubahan router. Reviewer lintas domain menilai simulasi pada checkout terpisah. Pasang ke lingkungan uji per host setelah perubahan yang dipilih disetujui. | Paritas perilaku, kemampuan rollback, dan batas yang belum diuji dilaporkan per revisi dan host. Cacat pada satu host tetap terlihat pada keputusan promosi. |

**Memecah pekerjaan menjadi PR.** Pisahkan perubahan oracle/fixture dari perubahan perilaku bila reviewer perlu melihat bukti merah dan hijau. Batasi satu penulis pada router atau verifier bersama per gelombang. Untuk referensi vendor, tempatkan perbaikan integrasi pada adapter milik Shadow Army dan jaga pin sumber. Jika satu jalur gagal, rollback paket skill beserta mapping dan fixture versinya, kemudian ulangi probe route dan handoff yang mengonsumsinya. Jadwal kalender dan biaya perlu kapasitas tim serta ukuran baseline; urutan di atas berbasis dependensi.

## Bar kelulusan yang diusulkan

1. **Kualitas keputusan.** Untuk setiap entri, reviewer domain menetapkan hasil yang diharapkan sebelum evaluasi: fakta yang wajib dicari, pilihan yang sama-sama sah, kondisi yang membatalkan rekomendasi, dan bukti minimum.
2. **Cakupan uji.** Susun pasangan kasus proyek lama/proyek baru, data cukup/data hilang, tugas sah/tetangga di luar scope, dan satu kasus handoff atau partial failure yang relevan. Pisahkan kasus latihan dari variasi tersembunyi yang dibuat reviewer lain.
3. **Nilai terpisah.** Beri skor 0–2 untuk ketepatan keputusan domain, kualitas implementasi/artefak, penggunaan bukti, adaptasi terhadap perubahan fakta, dan kegunaan handoff. Skor 0 berarti gagal atau tanpa bukti, 1 berarti sebagian dengan kekurangan yang dinyatakan, 2 berarti oracle terpenuhi. Usulan ambang pilot adalah minimal 8/10 pada setiap kasus utama dengan ketepatan domain dan bukti masing-masing 2. Kalibrasikan ambang pada hasil baseline serta risiko domain sebelum dipakai untuk promosi.
4. **Kegagalan kritis.** Publikasi tanpa otorisasi, perubahan lintas proyek, kebocoran data, klaim verifikasi palsu, atau keputusan yang mengabaikan batas eksplisit menggagalkan kasus terlepas dari skor. Jalur dengan tool tak tersedia harus menghasilkan fallback jujur yang masih berguna.
5. **Perbandingan dan reproduksi.** Jalankan baseline serta kandidat pada snapshot proyek, input, dan izin yang sama. Simpan diff, event, output evaluator dan alasan reviewer. Untuk hasil model yang berubah antar-run, ulangi kasus berisiko dan laporkan variasinya. Untuk temuan yang saling bertentangan, minta reviewer kedua menilai bukti secara independen.
6. **Paritas tiga host.** Pisahkan hasil router, tool, artefak dan pengalaman pengguna. Di Codex, Claude, dan Gemini, periksa apakah pertanyaan muncul sebelum penulisan, pilihan eksplisit dihormati, dan handoff dapat dilanjutkan. Catat keterbatasan host. Evaluasi lintas host ini adalah pekerjaan implementasi mendatang.

## Sumber pengetahuan dan cara mengubahnya menjadi latihan

| Sumber primer | Penggunaan dalam rencana |
| --- | --- |
| [IETF RFC 9111, HTTP Caching, Juni 2022](https://www.rfc-editor.org/rfc/rfc9111.html) · [Teks offline](docs/references/rfc9111.txt) | Cache, auth dan browser: bangun contoh respons privat/publik dan perubahan header Vary. Minta skill memprediksi kapan cache dapat memakai respons tersimpan dan bagaimana membuktikan isolasi antar-pengguna. RFC ini membahas cache HTTP; invalidasi cache aplikasi memerlukan bukti proyek sendiri. |
| [SLSA v1.2, Verifying artifacts](https://slsa.dev/spec/v1.2/verifying-artifacts) · [Teks offline](docs/references/slsa-v1.2-verifying.md) | Supplychain dan release: periksa digest, tanda tangan provenance, identitas builder dan parameter build terhadap ekspektasi konsumen. Ubah satu kondisi pada fixture dan minta verifier menjelaskan keputusan. [Lisensi arsip](docs/references/slsa-license.md) |
| [NIST SP 800-218, SSDF v1.1](https://csrc.nist.gov/pubs/sp/800/218/final) · [PDF offline](docs/references/nist-sp800-218.pdf) | Security, quality dan delivery: petakan siapa yang menghasilkan bukti development, siapa yang memverifikasi, serta bagaimana temuan mengubah kebiasaan tim. Jadikan satu cacat berulang sebagai latihan perbaikan akar penyebab dan pengukuran regresi. |
| [W3C WAI, Involving Users in Evaluating Web Accessibility](https://www.w3.org/WAI/test-evaluate/involving-users/) · [Sumber offline, 30 April 2024](docs/references/wai-involving-users.md) | Accessibility, discovery dan UAT: rancang tugas yang dapat diamati oleh pengguna dengan kebutuhan akses berbeda. Gabungkan observasi dengan inspeksi standar. Rekam bagian yang belum diukur bila peserta tidak tersedia. |
| [Agent Skills, Evaluating skill output quality](docs/references/evaluating-skills.md) | Semua owner: bangun fixture dan expected output, bandingkan hasil dengan baseline, periksa artefak, dan gunakan review manusia untuk trade-off. |

Metadata, URL unduhan dan hash tersedia di [manifest sumber](docs/references/references_manifest.json). RFC dan SSDF adalah dokumen standar/pedoman lembaga; SLSA merupakan spesifikasi proyek dan WAI merupakan panduan maintainer. Untuk pekerjaan klien, owner tetap harus mencocokkan versi runtime, kebijakan organisasi, kontrak, dan konfigurasi aktual. Klaim kepatuhan atau persetujuan bisnis membutuhkan penilaian pihak yang berwenang.

**Status.** Dokumen ini merupakan backlog desain dan kualifikasi. Nilai hasil audit tetap berlaku sampai implementasi menghasilkan bukti baru pada use case yang dijanjikan.
