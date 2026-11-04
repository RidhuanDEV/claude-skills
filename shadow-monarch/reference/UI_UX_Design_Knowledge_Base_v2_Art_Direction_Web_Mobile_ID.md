# UI/UX, Visual Art Direction & Product Interface Knowledge Base

**Versi:** 2.0 — Extended Art Direction, Web & Mobile  
**Bahasa:** Indonesia  
**Cakupan:** UI/UX + graphic art + editorial composition + visual choreography + web/mobile engineering.  
**Basis:** Seluruh knowledge base v1.0 dipertahankan; bab 26–43 ditambahkan sebagai pendalaman.  
**Status:** Dokumen referensi dan panduan kerja, bukan pengganti pengujian pengguna, dokumentasi platform, atau creative direction manusia.

**Cara pakai untuk AI agent:** Baca bagian 26 (aturan keputusan), 27–34 (art direction), 35–39 (web/mobile), 40 (prompt), 41 (audit), lalu gunakan bab 1–25 sebagai fondasi UX. Jangan menerapkan semua efek desain sekaligus.

## Navigasi materi tambahan

- [26. Decision framework dan anti-generic AI](#26-decision-framework-dan-anti-generic-ai)
- [27. Kosakata seni desain digital](#27-kosakata-seni-desain-digital)
- [28. Komposisi dan visual choreography](#28-komposisi-dan-visual-choreography)
- [29. Art direction editorial dan modernisme](#29-art-direction-editorial-dan-modernisme)
- [30. Ornamentasi, edge art, dan section continuity](#30-ornamentasi-edge-art-dan-section-continuity)
- [31. Ilustrasi, visual metaphors dan icon family](#31-ilustrasi-visual-metaphors-dan-icon-family)
- [32. Advanced typography dan layout expression](#32-advanced-typography-dan-layout-expression)
- [33. Color dramaturgy, material, dan texture](#33-color-dramaturgy-material-dan-texture)
- [34. Motion choreography dan prototyping](#34-motion-choreography-dan-prototyping)
- [35. Website composition and implementation patterns](#35-website-composition-and-implementation-patterns)
- [36. Mobile app art direction and native UX](#36-mobile-app-art-direction-and-native-ux)
- [37. Accessibility and inclusive creative UI](#37-accessibility-and-inclusive-creative-ui)
- [38. Performance, assets, and delivery](#38-performance-assets-and-delivery)
- [39. Practical design recipes](#39-practical-design-recipes)
- [40. AI prompt and agent playbook](#40-ai-prompt-and-agent-playbook)
- [41. Design critique and validation rubrics](#41-design-critique-and-validation-rubrics)
- [42. Case study: Program Riset Nasional](#42-case-study-program-riset-nasional)
- [43. External source hierarchy and update policy](#43-external-source-hierarchy-and-update-policy)

---

# Bagian A — Fondasi UI/UX Design Knowledge Base v1.0

**Versi:** 1.0  
**Bahasa:** Indonesia  
**Tujuan:** Referensi belajar dan praktik desain antarmuka web serta aplikasi mobile, dari fondasi UX sampai handoff ke developer.  
**Prinsip editorial:** *Human-led design.* AI boleh membantu eksplorasi, membuat variasi, atau mempercepat dokumentasi, tetapi keputusan desain harus tetap diuji terhadap kebutuhan manusia, konteks penggunaan, aksesibilitas, bukti riset, dan batasan produk.

> **Cara menggunakan dokumen ini**
> 1. Mulai dari prinsip 1–30 untuk memahami dasar desain.
> 2. Gunakan bagian pola UI dan aset untuk memilih bentuk visual yang sesuai dengan tujuan, bukan sekadar mengikuti tren.
> 3. Pakai checklist sebelum mengirim desain atau implementasi ke production.
> 4. Gunakan prompt di bagian akhir sebagai brief awal, lalu iterasikan berdasarkan hasil nyata.
> 5. Referensi eksternal adalah titik awal. Periksa tanggal, dokumentasi, dan lisensi pada sumber aslinya sebelum mengandalkannya.

## Daftar isi

1. [Fondasi UI/UX dan filosofi desain](#1-fondasi-uiux-dan-filosofi-desain)
2. [Riset pengguna dan problem framing](#2-riset-pengguna-dan-problem-framing)
3. [Hierarki visual dan Gestalt](#3-hierarki-visual-dan-gestalt)
4. [Layout, grid, spacing, dan komposisi](#4-layout-grid-spacing-dan-komposisi)
5. [Warna dan sistem warna](#5-warna-dan-sistem-warna)
6. [Tipografi dan konten antarmuka](#6-tipografi-dan-konten-antarmuka)
7. [Gambar, ilustrasi, ikon, dan dekorasi](#7-gambar-ilustrasi-ikon-dan-dekorasi)
8. [Bahasa visual dan gaya desain](#8-bahasa-visual-dan-gaya-desain)
9. [Informasi, navigasi, dan arsitektur konten](#9-informasi-navigasi-dan-arsitektur-konten)
10. [Komponen dan design system](#10-komponen-dan-design-system)
11. [Responsive, adaptive, dan layout lintas perangkat](#11-responsive-adaptive-dan-layout-lintas-perangkat)
12. [Pola desain aplikasi mobile](#12-pola-desain-aplikasi-mobile)
13. [Interaksi, feedback, dan motion](#13-interaksi-feedback-dan-motion)
14. [Form, validasi, dan penanganan error](#14-form-validasi-dan-penanganan-error)
15. [Dashboard, tabel, dan visualisasi data](#15-dashboard-tabel-dan-visualisasi-data)
16. [Aksesibilitas dan desain inklusif](#16-aksesibilitas-dan-desain-inklusif)
17. [Wireframe, prototipe, dan proses kerja](#17-wireframe-prototipe-dan-proses-kerja)
18. [Usability testing dan evaluasi](#18-usability-testing-dan-evaluasi)
19. [Handoff, implementasi, dan quality assurance](#19-handoff-implementasi-dan-quality-assurance)
20. [Etika, orisinalitas, dan desain yang bertanggung jawab](#20-etika-orisinalitas-dan-desain-yang-bertanggung-jawab)
21. [Glosarium istilah visual dan pola UI](#21-glosarium-istilah-visual-dan-pola-ui)
22. [Prompt library untuk AI desain dan AI coding](#22-prompt-library-untuk-ai-desain-dan-ai-coding)
23. [Checklist praktik](#23-checklist-praktik)
24. [Referensi belajar, dokumentasi, galeri, dan aset](#24-referensi-belajar-dokumentasi-galeri-dan-aset)
25. [Rencana belajar 8 minggu](#25-rencana-belajar-8-minggu)

---

# 1. Fondasi UI/UX dan filosofi desain

UI (*user interface*) adalah bagian yang dilihat dan digunakan seseorang: teks, tombol, layout, ikon, field, gambar, dan status. UX (*user experience*) adalah pengalaman menyeluruh ketika seseorang mencoba mencapai tujuan, termasuk persepsi, hambatan, kepercayaan, waktu, dan hasil akhir. UI yang menarik tidak otomatis menghasilkan UX yang baik.

### 1.1 Prinsip dasar

1. **Mulai dari tujuan pengguna.** Tentukan pekerjaan yang ingin diselesaikan pengguna sebelum memilih warna, font, atau animasi.
2. **Desain untuk konteks, bukan layar kosong.** Pertimbangkan perangkat, koneksi, lingkungan, tingkat keahlian, bahasa, urgensi, dan gangguan saat produk digunakan.
3. **Utamakan kejelasan daripada dekorasi.** Elemen visual harus membantu memahami prioritas, struktur, atau tindakan. Dekorasi tanpa fungsi tetap boleh, tetapi jangan mengganggu tugas utama.
4. **Konsistensi mengurangi beban berpikir.** Pola tombol, label, navigasi, dan feedback yang serupa sebaiknya berperilaku serupa.
5. **Buat tindakan penting mudah ditemukan.** Pengguna tidak seharusnya menebak bagaimana memulai atau menyelesaikan tugas utamanya.
6. **Tampilkan status sistem.** Beri tahu apakah aplikasi sedang memuat, menyimpan, berhasil, gagal, offline, atau menunggu tindakan pengguna.
7. **Cegah kesalahan sebelum terjadi.** Pilihan yang aman, batas yang jelas, konfirmasi yang tepat, dan nilai default yang baik biasanya lebih efektif daripada hanya menampilkan pesan error.
8. **Sediakan jalan keluar.** Undo, cancel, back, edit, dan pemulihan dari error membuat orang lebih berani mencoba.
9. **Minimalkan beban ingatan.** Pilihan yang perlu dibandingkan sebaiknya terlihat bersama; jangan memaksa pengguna mengingat informasi dari layar sebelumnya.
10. **Desain harus bisa diuji.** Ubah opini menjadi hipotesis yang dapat dinilai melalui pengamatan, pengujian, data, atau umpan balik nyata.

### 1.2 Model mental, affordance, dan signifier

11. **Model mental harus selaras dengan produk.** Orang datang dengan ekspektasi dari aplikasi lain; gunakan pola familier kecuali ada alasan kuat untuk berbeda.
12. **Affordance adalah kemungkinan tindakan.** Tombol tampak dapat ditekan, slider tampak dapat digeser, dan field tampak bisa diisi karena bentuk serta konteksnya mengisyaratkan tindakan tersebut.
13. **Signifier menunjukkan cara bertindak.** Label, ikon, garis tepi, handle, hover, dan hint membantu seseorang mengenali affordance.
14. **Jangan membuat elemen statis tampak interaktif.** Jika sesuatu terlihat seperti tombol atau link, pastikan benar-benar melakukan sesuatu.
15. **Jangan menyembunyikan aksi inti di hover saja.** Hover tidak tersedia pada layar sentuh dan sulit diandalkan untuk keyboard atau pembaca layar.
16. **Gunakan bahasa pengguna.** Hindari istilah internal, singkatan tim, atau jargon kecuali audiens memang memahaminya.
17. **Pertahankan kendali pengguna.** Otomatisasi boleh membantu, tetapi tindakan yang berdampak besar harus dapat dipahami dan, bila perlu, dibatalkan.
18. **Hormati pola platform.** Web, iOS, dan Android memiliki kebiasaan interaksi berbeda. Konsistensi produk penting, tetapi jangan mengabaikan ekspektasi platform tanpa alasan.
19. **Buat trade-off secara sadar.** Keindahan, kepadatan informasi, kecepatan, fleksibilitas, dan aksesibilitas kadang bertentangan. Jelaskan prioritas produk dan uji dampaknya.
20. **Nilai hasil, bukan selera semata.** Pertanyaan evaluasi yang baik adalah apakah desain membantu orang menyelesaikan tugas secara lebih mudah, aman, dan percaya diri.

# 2. Riset pengguna dan problem framing

21. **Bedakan pengguna, pembeli, dan pemangku kepentingan.** Orang yang membayar, mengelola, dan memakai produk bisa memiliki kebutuhan berbeda.
22. **Definisikan masalah sebelum solusi.** Jangan langsung memutuskan “perlu dashboard” sebelum mengetahui keputusan apa yang harus dibuat pengguna.
23. **Pisahkan bukti dari asumsi.** Tandai hal yang berasal dari wawancara, analitik, kebijakan, observasi, atau dugaan tim.
24. **Riset pertanyaan perilaku.** “Ceritakan terakhir kali Anda melakukan X” biasanya menghasilkan cerita nyata lebih baik daripada “Apakah Anda akan memakai fitur X?”.
25. **Amati perilaku, bukan hanya opini.** Orang bisa menjelaskan preferensi tertentu tetapi bertindak berbeda ketika mengerjakan tugas nyata.
26. **Sampel harus relevan dengan tujuan.** Uji dengan pengguna yang mewakili kemampuan, perangkat, bahasa, dan konteks penggunaan yang penting.
27. **Jangan menganggap satu persona mewakili semua orang.** Segmentasikan berdasarkan tujuan dan kebutuhan yang berdampak pada desain, bukan atribut dekoratif.
28. **Petakan perjalanan pengguna.** Catat tahap, tujuan, pertanyaan, emosi, hambatan, kanal, dan kesempatan perbaikan dari awal sampai selesai.
29. **Tulis problem statement yang spesifik.** Sebutkan siapa yang mengalami masalah, dalam situasi apa, masalahnya apa, dan dampaknya terhadap tugas.
30. **Susun prioritas dengan dampak dan bukti.** Dahulukan masalah yang sering terjadi, berdampak besar, atau berisiko tinggi, bukan sekadar masalah yang paling mudah diperbaiki.

# 3. Hierarki visual dan Gestalt

Hierarki visual membantu mata memahami mana yang utama, mana yang pendukung, dan ke mana harus bergerak. Prinsip Gestalt menjelaskan kecenderungan manusia mengelompokkan bentuk menjadi pola yang bermakna.

31. **Gunakan satu fokus utama per area.** Halaman boleh memiliki beberapa bagian, tetapi setiap viewport perlu menunjukkan prioritas yang mudah dipahami.
32. **Ukuran memberi sinyal kepentingan.** Judul biasanya lebih besar daripada deskripsi, tetapi skala harus konsisten dan tidak digunakan untuk semua elemen sekaligus.
33. **Kontras menunjukkan prioritas.** Kontras dapat berasal dari ukuran, warna, ketebalan, posisi, bentuk, atau ruang kosong, bukan hanya warna mencolok.
34. **Kedekatan mengisyaratkan hubungan.** Label sebaiknya dekat dengan field yang dijelaskannya; metadata sebaiknya dekat dengan konten terkait.
35. **Kesamaan membentuk kelompok.** Elemen dengan bentuk, warna, atau gaya serupa sering dianggap memiliki fungsi serupa. Jangan menyamakan tampilan untuk tindakan yang berbeda tanpa konteks.
36. **Kontinuitas mengarahkan pandangan.** Alignment dan garis visual yang konsisten membantu mata mengikuti urutan konten.
37. **Closure membuat otak melengkapi bentuk.** Bentuk yang terpotong masih bisa dikenali, tetapi jangan mengandalkan ilusi bila dapat membuat status atau batas komponen ambigu.
38. **Figure-ground membedakan objek dari latar.** Pastikan panel, dialog, teks, dan kontrol tidak tenggelam dalam dekorasi background.
39. **Gunakan ruang kosong secara sengaja.** White space adalah alat struktur dan penekanan, bukan ruang yang otomatis harus diisi.
40. **Hindari kompetisi visual.** Banyak badge, warna aksen, tombol primer, bayangan, dan animasi sekaligus membuat prioritas kehilangan makna.

# 4. Layout, grid, spacing, dan komposisi

41. **Mulai dari struktur konten.** Tentukan urutan informasi dan tugas sebelum menyusun dekorasi.
42. **Gunakan grid untuk konsistensi.** Grid membantu alignment lintas kolom dan halaman, tetapi tidak harus membatasi setiap elemen secara kaku.
43. **Terapkan sistem spacing.** Pilih skala yang konsisten, misalnya kelipatan 4 atau 8, lalu gunakan token spacing daripada angka acak di seluruh aplikasi.
44. **Kelompokkan elemen terkait.** Jarak di dalam kelompok biasanya lebih kecil daripada jarak antarkelompok.
45. **Gunakan container width yang nyaman.** Teks panjang yang terlalu lebar membuat mata kesulitan kembali ke awal baris; atur `max-width` sesuai jenis konten.
46. **Alignment perlu punya alasan.** Teks, field, judul, dan tombol yang terkait sebaiknya mengikuti garis alignment yang jelas.
47. **Jangan memusatkan semua hal.** Center alignment cocok untuk headline pendek, empty state, atau halaman fokus; paragraf panjang biasanya lebih nyaman rata kiri.
48. **Atur kepadatan sesuai tugas.** Dashboard ahli dapat membutuhkan kepadatan lebih tinggi daripada aplikasi konsumen, tetapi kepadatan harus tetap terstruktur.
49. **Buat ritme antarbagiannya.** Variasi ukuran, jarak, dan pengelompokan membuat halaman panjang terasa memiliki bab yang jelas.
50. **Atur keseimbangan visual.** Bobot visual bukan hanya ukuran. Gambar besar, warna pekat, dan elemen kompleks juga menarik perhatian.
51. **Jangan mengandalkan posisi yang sama di semua ukuran layar.** Grid 12 kolom desktop tidak harus menjadi 12 kolom mungil pada ponsel; susun ulang struktur.
52. **Gunakan batas layout yang masuk akal.** Hindari konten melebar tanpa batas pada monitor besar atau terlalu sempit pada perangkat kecil.
53. **Sisakan ruang untuk konten nyata.** Nama pengguna, judul panjang, angka besar, bahasa berbeda, dan gambar yang tidak sempurna harus tetap muat.
54. **Gunakan negative space untuk memberi jeda.** Bagian yang sengaja lebih lapang dapat membantu pengguna memahami perubahan konteks atau prioritas.
55. **Desain di beberapa viewport sejak awal.** Jangan menganggap tampilan mobile sebagai hasil mengecilkan desain desktop setelah semuanya selesai.

# 5. Warna dan sistem warna

56. **Warna harus punya peran.** Definisikan warna untuk teks, background, border, primary action, success, warning, danger, info, dan disabled state.
57. **Bangun palet dengan skala.** Sediakan tingkat warna terang hingga gelap agar komponen dapat memiliki hover, border, surface, dan teks yang konsisten.
58. **Pisahkan warna brand dari warna status.** Warna brand tidak otomatis cocok untuk error atau sukses.
59. **Jangan mengandalkan warna saja.** Status error harus disertai teks atau ikon; grafik perlu label atau pola jika pembeda warna tidak cukup.
60. **Periksa kontras teks.** Ukur pasangan teks dan background menggunakan alat contrast checker, bukan hanya berdasarkan mata.
61. **Perhatikan kontras kontrol nonteks.** Border field, fokus, ikon bermakna, dan indikator status juga perlu terlihat dengan jelas.
62. **Warna memiliki asosiasi budaya.** Makna merah, putih, hijau, dan warna lain dapat berbeda menurut budaya serta konteks; validasi dengan audiens produk.
63. **Gunakan aksen dengan hemat.** Jika setiap elemen diberi warna kuat, tidak ada elemen yang benar-benar menjadi fokus.
64. **Dark mode bukan sekadar membalik warna.** Atur ulang surface, elevation, kontras, gambar, dan status agar hierarki tetap terbaca.
65. **Hati-hati dengan saturasi tinggi.** Area besar dengan warna sangat jenuh bisa melelahkan dan mengalahkan konten penting.
66. **Gunakan gradient untuk tujuan yang jelas.** Gradient dapat memberi kedalaman atau suasana, tetapi jangan sampai menurunkan keterbacaan teks.
67. **Uji warna dalam konteks.** Warna yang terlihat bagus di swatch bisa berubah persepsinya ketika berdampingan dengan warna lain atau pada layar berbeda.
68. **Siapkan token semantik.** Gunakan `--color-text-primary` dan `--color-danger` alih-alih menyebar hex literal di seluruh kode.
69. **Perhatikan kondisi hover, focus, active, selected, dan disabled.** Setiap status harus dapat dibedakan, tetapi tetap menjadi bagian dari sistem visual yang sama.
70. **Dokumentasikan aturan penggunaan warna.** Token tanpa aturan penggunaan sering berkembang menjadi palet yang tidak konsisten.

# 6. Tipografi dan konten antarmuka

71. **Font adalah bagian dari fungsi.** Pilih typeface yang cocok dengan bahasa, kepadatan, kepribadian produk, dan kebutuhan baca.
72. **Batasi jumlah keluarga font.** Satu keluarga dengan beberapa weight sering cukup; terlalu banyak keluarga membuat sistem terasa tidak padu.
73. **Bangun type scale.** Tetapkan level untuk display, heading, body, label, caption, dan metadata, termasuk line-height serta weight.
74. **Jangan memakai ukuran kecil hanya agar muat.** Potong atau susun ulang konten sebelum mengecilkan tulisan penting.
75. **Atur line-height sesuai ukuran.** Teks body memerlukan ruang vertikal yang nyaman; heading besar biasanya memakai line-height lebih rapat.
76. **Perhatikan panjang baris.** Baris yang terlalu panjang menyulitkan pelacakan mata; sesuaikan lebar kontainer dengan jenis konten.
77. **Gunakan weight untuk hierarki dengan konsisten.** Bold tidak perlu digunakan untuk semua label dan informasi.
78. **Hindari paragraf kapital semua untuk konten panjang.** All caps lebih cocok sebagai aksen pendek, bukan bacaan utama.
79. **Gunakan kalimat yang langsung.** Label seperti “Simpan perubahan” lebih jelas daripada kata kerja abstrak seperti “Proses”.
80. **Tuliskan CTA yang menjelaskan hasil.** “Unduh laporan” lebih informatif daripada “Klik di sini”.
81. **Jangan menyalahkan pengguna dalam pesan error.** Jelaskan masalah dan langkah pemulihan dengan netral.
82. **Microcopy dapat mengurangi kecemasan.** Jelaskan mengapa data dibutuhkan, apa yang akan terjadi selanjutnya, atau apakah tindakan dapat dibatalkan.
83. **Pertahankan konsistensi istilah.** Jika objek disebut “dokumen” di satu layar, hindari berganti menjadi “berkas” tanpa alasan.
84. **Rancang untuk lokalisasi.** Teks bahasa Indonesia, Inggris, dan bahasa lain bisa memiliki panjang berbeda; hindari mengunci ukuran komponen ke teks contoh.
85. **Uji font untuk karakter nyata.** Pastikan tanda baca, aksara, angka, mata uang, diakritik, dan fallback font tampil baik.

# 7. Gambar, ilustrasi, ikon, dan dekorasi

86. **Aset harus punya tugas.** Gambar dapat menjelaskan produk, membantu orientasi, membangun emosi, atau memberi konteks. Jika tidak melakukan apa pun, pertimbangkan untuk menghapusnya.
87. **Pilih visual yang relevan dengan pengguna.** Gambar yang indah tetapi tidak mewakili produk atau audiens dapat mengurangi kepercayaan.
88. **Gunakan gambar dengan hak pakai jelas.** Periksa lisensi, atribusi, batas komersial, izin model, merek dagang, dan syarat redistribusi sesuai sumber.
89. **Perhatikan focal point dan cropping.** Tentukan bagian gambar yang penting dan gunakan `object-position` atau art direction pada ukuran layar berbeda.
90. **Gunakan rasio aspek dengan konsisten.** Thumbnail, avatar, hero image, dan kartu konten biasanya membutuhkan rasio berbeda.
91. **Sediakan placeholder dan fallback.** Gambar gagal dimuat, avatar kosong, dan rasio yang belum diketahui tidak boleh merusak layout.
92. **Optimalkan format dan ukuran.** Gunakan format modern yang sesuai, dimensi cukup, kompresi wajar, dan lazy loading untuk gambar nonkritis.
93. **Tulis alt text untuk gambar informatif.** Deskripsikan fungsi atau informasi gambar; gambar dekoratif umumnya menggunakan alt kosong agar tidak mengganggu pembaca layar.
94. **Jangan menaruh teks penting langsung di dalam gambar.** Teks yang dirender sebagai teks asli lebih mudah diakses, responsif, diterjemahkan, dan diperbesar.
95. **Ikon harus dikenali dan konsisten.** Campuran ikon outline, filled, dan gaya berbeda tanpa aturan membuat antarmuka terlihat acak.
96. **Tambahkan label ketika ikon ambigu.** Ikon tidak selalu memiliki arti universal; label yang jelas meningkatkan pemahaman.
97. **Ukuran ikon mengikuti fungsi dan target.** Ukuran visual ikon tidak sama dengan ukuran area sentuhnya.
98. **Gunakan ilustrasi untuk memperjelas, bukan mengisi kekosongan.** Empty state, onboarding, atau penjelasan konsep dapat terbantu oleh ilustrasi yang relevan.
99. **Hindari gambar stok yang terasa tidak autentik.** Pilih aset yang relevan dengan konteks nyata dan tidak menyesatkan tentang pengguna atau layanan.
100. **Dekorasi harus tunduk pada konten.** Bentuk wave, blob, gradient, tekstur, dan lipatan kain dapat memperindah halaman, tetapi jangan menutupi teks atau kontrol.
101. **Gunakan SVG untuk bentuk dekoratif yang skalabel.** Gelombang, mask, garis, dan shape sederhana cocok dijadikan SVG bila tidak memerlukan raster detail.
102. **Jaga kontras dekorasi terhadap konten.** Background dekoratif sebaiknya cukup lembut ketika berada di belakang teks atau field.
103. **Jangan memakai aset berat tanpa alasan.** Video background dan animasi besar menambah beban jaringan, baterai, serta perhatian.
104. **Gunakan placeholder yang jujur.** Jangan memakai foto stok untuk menyiratkan bahwa itu foto fasilitas, anggota tim, pelanggan, atau hasil nyata jika bukan.
105. **Lakukan audit lisensi per aset.** Lisensi sebuah situs tidak selalu sama dengan lisensi setiap koleksi, ikon, font, template, atau kontributor.

# 8. Bahasa visual dan gaya desain

106. **Pilih gaya setelah memahami produk.** Gaya bukan tujuan terpisah; ia harus mendukung kepercayaan, tugas, identitas, dan konteks audiens.
107. **Minimalism berarti mengurangi yang tidak perlu.** Minimalis bukan sekadar memakai warna putih dan sedikit komponen; struktur dan hierarki tetap harus kuat.
108. **Editorial cocok untuk konten dengan narasi.** Tipografi dominan, kolom teks, dan komposisi asimetris dapat cocok untuk artikel, portofolio, atau storytelling.
109. **Bento grid membantu mengelompokkan highlight.** Gunakan ukuran kartu bervariasi untuk menunjukkan prioritas, bukan membuat semua kartu berbeda tanpa makna.
110. **Glassmorphism butuh kontras dan konteks.** Blur dan transparansi dapat memberi kesan berlapis, tetapi teks di atas latar bergerak atau beragam perlu diuji serius.
111. **Neumorphism memiliki risiko affordance.** Bayangan lembut yang menyatu dengan background dapat membuat tombol dan kontrol sulit dikenali, sehingga jangan menjadikannya satu-satunya penanda interaksi.
112. **Brutalism mengutamakan ekspresi visual yang berani.** Kontras, garis, dan tipografi kuat dapat cocok untuk brand tertentu, tetapi keterbacaan tetap perlu dijaga.
113. **3D bukan solusi universal.** Objek 3D dapat menambah kedalaman dan karakter, tetapi ukuran file, rendering, dan distraksi perlu diperhitungkan.
114. **Gradient mesh memberi atmosfer.** Pakai sebagai latar pendukung dan pastikan elemen utama tetap memiliki kontras yang cukup.
115. **Texture atau grain dapat mengurangi kesan steril.** Gunakan tipis dan periksa kompresi, noise visual, aksesibilitas, serta dampak terhadap performa.
116. **Draped fabric atau silk folds memberi kesan lembut dan premium.** Bentuk seperti kain/hordeng cocok sebagai aksen visual, tetapi harus tetap mendukung komposisi, bukan mendominasi form utama.
117. **Abstract waves dan organic shapes memberi kesan cair.** Bentuk gelombang cocok untuk latar section atau pemisah konten, terutama bila mengikuti alur halaman.
118. **Scalloped edge adalah tepi berlekuk berulang.** Cocok sebagai batas dekoratif pada kartu atau section, tetapi pola terlalu rapat dapat terasa ramai.
119. **Split-screen adalah pola layout, bukan gaya visual.** Pembagian area untuk visual dan form dapat membantu orientasi, tetapi perlu responsif pada layar kecil.
120. **Visual trend harus memiliki masa pakai yang masuk akal.** Gunakan tren pada area yang mudah diperbarui dan hindari mengorbankan usability demi tampilan sesaat.

# 9. Informasi, navigasi, dan arsitektur konten

121. **Susun informasi sesuai tugas.** Urutan konten sebaiknya mengikuti pertanyaan pengguna, bukan struktur organisasi internal.
122. **Label navigasi harus mudah diprediksi.** Gunakan istilah yang dimengerti audiens dan jangan membuat nama menu terlalu kreatif hingga menutupi makna.
123. **Navigasi utama harus menunjukkan lokasi dan pilihan.** Berikan penanda halaman aktif dan hindari banyak menu yang tampak aktif bersamaan tanpa alasan.
124. **Gunakan breadcrumb untuk struktur bertingkat.** Breadcrumb membantu pada situs dengan hierarki kategori yang dalam, bukan selalu dibutuhkan di aplikasi sederhana.
125. **Search cocok untuk kumpulan besar.** Pastikan hasil pencarian informatif, mendukung kondisi kosong, dan memberi cara memperbaiki query yang tidak menghasilkan hasil.
126. **Filter dan sort harus jelas berbeda.** Filter mengurangi kumpulan hasil; sort mengubah urutan. Tampilkan filter aktif dan sediakan cara reset.
127. **Tab harus mewakili kategori sejajar.** Jangan gunakan tab untuk urutan langkah atau navigasi menuju halaman yang tidak berkaitan.
128. **Menu tidak boleh menyembunyikan hal yang kritis.** Pastikan tindakan penting dapat ditemukan dan bisa dioperasikan dengan keyboard serta sentuhan.
129. **Gunakan progressive disclosure dengan bijak.** Tampilkan hal inti lebih awal, lalu detail lanjutan saat dibutuhkan; jangan menyembunyikan informasi esensial.
130. **Beri informasi orientasi.** Judul halaman, breadcrumb, section title, atau state terpilih membantu pengguna tahu posisi mereka.
131. **Hindari menu terlalu dalam.** Jika pengguna harus melewati banyak tingkatan untuk tugas umum, pertimbangkan pencarian, shortcut, atau pengelompokan ulang.
132. **Rancang halaman kosong.** Empty state perlu menjelaskan mengapa belum ada data, apa yang bisa dilakukan, dan apakah pengguna perlu menunggu atau membuat item baru.
133. **Bedakan tidak ada data dengan gagal memuat.** Keduanya memerlukan pesan dan tindakan lanjutan yang berbeda.
134. **Sediakan cara kembali yang dapat diprediksi.** Jangan membuang state filter atau isian pengguna tanpa alasan saat mereka kembali dari detail.
135. **Gunakan metadata seperlunya.** Waktu, status, pemilik, dan kategori membantu keputusan; terlalu banyak metadata meningkatkan kebisingan.

# 10. Komponen dan design system

136. **Komponen mengkodekan keputusan berulang.** Gunakan komponen ketika struktur, perilaku, dan tampilan dipakai berulang atau perlu konsistensi.
137. **Bedakan komponen dasar dan pola halaman.** Button dan input adalah komponen dasar; login form atau data table dapat menjadi pola yang menggabungkan beberapa komponen.
138. **Gunakan token desain.** Warna, spacing, radius, elevation, typography, dan motion sebaiknya menjadi nilai yang dikelola secara terpusat.
139. **Buat variasi komponen secara eksplisit.** Contoh: button `primary`, `secondary`, `tertiary`, `danger`; jangan menambahkan style ad hoc untuk setiap kasus.
140. **Status merupakan bagian dari komponen.** Rancang default, hover, focus-visible, pressed, selected, loading, disabled, dan error sesuai relevansinya.
141. **API komponen harus sederhana.** Prop yang banyak, saling bertentangan, dan sulit diprediksi sering menandakan komponen terlalu generik.
142. **Hindari abstraksi terlalu dini.** Jangan membuat komponen universal sebelum pola kebutuhan berulang terlihat jelas.
143. **Dokumentasikan kapan komponen digunakan.** Contoh dan larangan penggunaan sama pentingnya dengan nama prop.
144. **Design system bukan cuma kumpulan komponen.** Ia mencakup prinsip, token, panduan penggunaan, aksesibilitas, kontribusi, dan tata kelola perubahan.
145. **Jaga satu sumber kebenaran.** Bila token diubah, komponen terkait seharusnya bisa mengikuti perubahan tanpa memperbaiki banyak file secara manual.
146. **Uji komponen dalam konteks nyata.** Komponen yang bagus di Storybook bisa gagal ketika label panjang, localization, error message, atau data besar digunakan.
147. **Tetapkan kebijakan deprecation.** Komponen lama memerlukan migrasi yang jelas agar desain dan implementasi tidak terpecah terlalu lama.
148. **Gunakan dokumentasi interaktif.** Storybook dan contoh kode dapat menunjukkan keadaan komponen secara konsisten untuk designer dan developer.
149. **Bedakan design token dan data produk.** Nama organisasi, teks, atau nilai spesifik bukan token visual dan tidak semestinya ditanam di komponen generik.
150. **Perubahan sistem harus membawa alasan.** Catat masalah yang hendak diselesaikan dan dampak komponen yang berubah.

# 11. Responsive, adaptive, dan layout lintas perangkat

151. **Responsive layout menyesuaikan ruang yang tersedia.** Gunakan ukuran relatif, grid fleksibel, wrapping, dan breakpoint berdasarkan kebutuhan konten.
152. **Breakpoint bukan angka sakral.** Pilih breakpoint saat layout mulai rusak atau terlalu renggang, lalu uji perangkat nyata dan ukuran viewport representatif.
153. **Mobile-first adalah strategi, bukan hukum.** Mulai dari kebutuhan inti dan keterbatasan ruang jika itu membantu, tetapi pilih urutan kerja berdasarkan produk dan kompleksitasnya.
154. **Konten harus reflow.** Hindari horizontal scrolling untuk teks dan form biasa; gunakan horizontal scroll hanya untuk pola yang memang cocok seperti carousel atau tabel tertentu.
155. **Tombol harus nyaman disentuh.** Ukuran target sentuh dan jarak antaraksi perlu cukup untuk mencegah salah tekan.
156. **Jangan bergantung pada hover.** Tindakan utama harus tersedia melalui tap, keyboard, dan aksesibilitas.
157. **Pertimbangkan safe area perangkat.** Notch, home indicator, status bar, dan navigation bar memengaruhi posisi konten mobile.
158. **Perhatikan orientasi dan ukuran teks.** Layout harus bertahan ketika perangkat diputar atau pengguna memperbesar ukuran teks.
159. **Jangan hanya menguji viewport populer.** Uji ukuran sempit, lebar, zoom, tablet, serta desktop dengan tinggi layar berbeda.
160. **Gunakan art direction bila perlu.** Gambar atau komposisi tertentu bisa memerlukan versi berbeda, bukan hanya dipotong secara otomatis.

# 12. Pola desain aplikasi mobile

161. **Hormati navigasi platform.** Perhatikan pola back, tab bar, navigation bar, modal, sheet, dan gesture pada iOS atau Android.
162. **Bottom navigation untuk tujuan utama yang sejajar.** Biasanya berisi beberapa destinasi yang sering digunakan, bukan daftar panjang semua fitur.
163. **Tab bukan pengganti navigasi universal.** Tab sebaiknya membagi konten dalam konteks yang sama, bukan membentuk hierarki halaman tanpa hubungan.
164. **Bottom sheet cocok untuk tindakan kontekstual.** Pastikan pengguna memahami apakah sheet dapat ditutup, digeser, atau memiliki tindakan primer.
165. **Dialog dipakai untuk keputusan fokus.** Jangan memunculkan dialog untuk setiap pesan kecil; gangguan terlalu sering menurunkan kepercayaan.
166. **Onboarding fokus pada nilai dan tugas.** Hindari slideshow panjang yang hanya menjelaskan fitur tanpa memberi pengguna kesempatan mencoba.
167. **Minta izin saat konteksnya relevan.** Jelaskan manfaat izin kamera, lokasi, notifikasi, atau kontak ketika pengguna memahami mengapa dibutuhkan.
168. **Rancang jaringan lambat dan offline.** Tampilkan cache, retry, status sinkronisasi, serta penjelasan jika tindakan belum terkirim.
169. **Gunakan gesture sebagai tambahan.** Sediakan affordance alternatif bagi aksi swipe yang penting karena gesture sering tidak ditemukan secara spontan.
170. **Jangan membuat pengguna kehilangan input.** Simpan draft yang masuk akal dan beri peringatan sebelum keluar dari form panjang.

# 13. Interaksi, feedback, dan motion

171. **Setiap tindakan perlu feedback.** Tombol yang ditekan harus menunjukkan state yang sesuai, dan hasil tindakan perlu dikonfirmasi.
172. **Respons harus terasa tepat waktu.** Jika proses panjang, tampilkan progress atau status. Jangan membuat spinner terus-menerus tanpa penjelasan bila ada informasi yang lebih berguna.
173. **Microinteraction memperjelas sebab-akibat.** Animasi kecil saat menyimpan, memilih, atau menyelesaikan tugas dapat menghubungkan aksi dengan hasil.
174. **Motion harus memiliki fungsi.** Animasi idealnya memberi orientasi, memperlihatkan perubahan state, atau mengurangi kebingungan, bukan sekadar hiasan.
175. **Durasi animasi harus sesuai perubahan.** Perubahan mikro umumnya cepat; perpindahan besar mungkin memerlukan lebih banyak waktu, namun jangan membuat pengguna menunggu dekorasi.
176. **Hormati reduced motion.** Beri alternatif atau kurangi animasi nonesensial bagi pengguna yang mengatur preferensi pengurangan gerakan.
177. **Hindari animasi yang menghalangi tugas.** Jangan membuat input, navigasi, atau aksi penting tertunda oleh efek yang tidak diperlukan.
178. **Pastikan state terlihat tanpa animasi.** Informasi yang bermakna tidak boleh hanya dapat dipahami ketika pengguna melihat gerakan.
179. **Hover, focus, pressed, dan selected bukan hal yang sama.** Gunakan visual state yang membedakan pointer, keyboard, penekanan, dan seleksi yang bertahan.
180. **Konfirmasi harus sebanding dengan risiko.** Tindakan biasa tidak perlu dialog konfirmasi; tindakan destruktif atau sulit dipulihkan perlu proteksi yang proporsional.
181. **Optimistic UI memerlukan pemulihan.** Jika UI langsung menunjukkan hasil sebelum server merespons, tangani kegagalan dengan jelas dan kembalikan state secara aman.
182. **Jangan mengubah UI tanpa alasan yang terbaca.** Perubahan konteks, urutan, atau posisi kontrol yang mendadak dapat membuat pengguna kehilangan orientasi.

# 14. Form, validasi, dan penanganan error

183. **Label harus tetap terlihat.** Placeholder bukan pengganti label karena menghilang ketika pengguna mulai mengetik dan bisa memiliki kontras rendah.
184. **Kelompokkan field berdasarkan makna.** Form panjang lebih mudah dipahami bila dibagi menjadi bagian yang logis dan diberi heading.
185. **Tanyakan data seperlunya.** Setiap field menambah biaya pengisian, risiko privasi, dan peluang pengguna berhenti.
186. **Pilih input berdasarkan data.** Email, nomor, tanggal, pencarian, password, dan jumlah membutuhkan tipe serta affordance yang sesuai.
187. **Tampilkan aturan sebelum kesalahan terjadi.** Jelaskan format password atau batas ukuran file pada waktu yang tepat, bukan hanya setelah gagal.
188. **Validasi dekat dengan penyebab.** Pesan error sebaiknya dekat dengan field yang bermasalah dan dapat dibaca oleh teknologi bantu.
189. **Jangan hanya mengandalkan validasi saat submit.** Validasi langsung dapat membantu, tetapi hindari terlalu cepat menandai isian yang belum selesai sebagai salah.
190. **Pertahankan data setelah error.** Jangan menghapus semua input ketika satu field tidak valid kecuali ada alasan keamanan yang jelas.
191. **Gunakan contoh format yang konkret.** Misalnya format tanggal atau kode pos; jangan berharap pengguna menebak bentuk yang diterima.
192. **Tombol submit harus memiliki state.** Bedakan idle, loading, sukses, dan gagal; cegah pengiriman ganda bila relevan.
193. **Pesan error menjelaskan tindakan berikutnya.** “Gagal menyimpan” kurang membantu dibanding menjelaskan masalah yang diketahui dan pilihan retry atau koreksi.
194. **Autofill dan password manager perlu didukung.** Gunakan atribut form yang semantik agar browser atau sistem dapat membantu pengguna.
195. **Berikan konfirmasi sukses yang spesifik.** Jelaskan apa yang tersimpan atau tindakan yang selesai, terutama pada operasi penting.

# 15. Dashboard, tabel, dan visualisasi data

196. **Mulai dari keputusan yang harus dibuat.** Setiap kartu metrik atau grafik perlu menjawab pertanyaan tertentu.
197. **Bedakan angka utama dan konteks.** Angka besar saja tidak cukup; sertakan unit, periode waktu, baseline, dan perbandingan yang relevan.
198. **Jangan memotong sumbu secara menyesatkan.** Gunakan skala yang sesuai dan beritahu pengguna bila visualisasi memakai transformasi atau rentang yang tidak lazim.
199. **Pilih bentuk grafik yang sesuai.** Bar chart cocok untuk perbandingan kategori; line chart untuk tren waktu; scatter untuk hubungan; pie/donut hanya untuk komposisi kecil yang mudah dibandingkan.
200. **Gunakan warna seri secara konsisten.** Kategori yang sama harus tetap memakai warna yang sama lintas grafik bila konteksnya sama.
201. **Tabel harus mendukung pemindaian.** Alignment angka, label kolom jelas, zebra striping yang tidak berlebihan, dan jarak yang sesuai meningkatkan keterbacaan.
202. **Jangan jadikan setiap metrik sebagai kartu.** Kartu cocok untuk ringkasan; terlalu banyak kartu membuat dashboard kehilangan hierarki.
203. **Sediakan filter dengan konteks.** Periode, unit organisasi, kategori, dan pilihan lain perlu terlihat sehingga pengguna tahu cakupan data yang sedang dilihat.
204. **Tampilkan waktu pembaruan data.** Informasi yang terlambat diperbarui dapat mengubah keputusan; nyatakan kapan data terakhir diperbarui bila relevan.
205. **Rancang keadaan tanpa data.** Grafik harus menjelaskan apakah data belum tersedia, filter terlalu ketat, proses gagal, atau akses tidak diizinkan.
206. **Jaga keterbacaan angka.** Atur format ribuan, desimal, mata uang, persentase, dan satuan menurut kebiasaan audiens.
207. **Jangan mengandalkan tooltip untuk semua data.** Informasi penting harus tersedia tanpa hover, terutama di mobile dan untuk teknologi bantu.
208. **Tampilkan ketidakpastian dengan jujur.** Estimasi, interval, data parsial, atau nilai yang belum final perlu dibedakan dari angka pasti.

# 16. Aksesibilitas dan desain inklusif

209. **Aksesibilitas bagian dari kualitas, bukan add-on.** Rancang sejak awal agar orang dengan keterbatasan visual, motorik, pendengaran, kognitif, atau situasional tetap bisa menggunakan produk.
210. **Gunakan struktur semantik.** Heading berurutan, tombol sebagai button, link sebagai link, label field yang terhubung, dan landmark membuat UI lebih mudah dioperasikan teknologi bantu.
211. **Pastikan keyboard bisa mencapai semua fungsi.** Urutan fokus harus logis dan tidak ada keyboard trap.
212. **Fokus harus terlihat jelas.** Jangan menghapus outline tanpa pengganti yang memadai.
213. **Kontras sesuai standar yang relevan.** Gunakan WCAG sebagai acuan dan uji kombinasi nyata, termasuk state hover dan disabled sesuai konteks.
214. **Jangan menyampaikan status hanya melalui warna.** Sertakan teks, ikon dengan nama, pola, atau bentuk tambahan.
215. **Label kontrol harus bisa dipahami.** Nama aksesibel tidak boleh generik seperti “button” untuk semua tombol.
216. **Konten tetap dapat digunakan pada zoom.** Uji pembesaran dan ukuran teks besar, terutama untuk dialog, navigasi, serta layout yang padat.
217. **Target interaksi perlu ruang yang cukup.** Kontrol kecil yang berdempetan meningkatkan kesalahan, khususnya pada layar sentuh.
218. **Sediakan caption atau transkrip untuk media yang relevan.** Pastikan informasi penting tidak hanya disampaikan melalui suara.
219. **Hormati preferensi pengguna.** Reduced motion, tema sistem, kontras, dan pengaturan teks perlu dipertimbangkan bila didukung platform.
220. **Gunakan bahasa yang inklusif dan konkret.** Hindari asumsi tentang gender, keluarga, kemampuan, lokasi, atau kondisi ekonomi pengguna.
221. **Uji dengan pengguna yang beragam.** Pemeriksaan otomatis membantu tetapi tidak menggantikan keyboard testing, screen reader testing, dan pengujian oleh manusia.
222. **Accessibility statement bukan pengganti perbaikan.** Catat kekurangan, prioritas, dan jalur pelaporan, sambil terus memperbaiki pengalaman.

# 17. Wireframe, prototipe, dan proses kerja

223. **Mulai dengan alur tugas.** Gambarkan langkah yang dibutuhkan sebelum memoles tampilan visual.
224. **Wireframe menguji struktur.** Pada tahap awal, fokus pada konten, hierarki, dan navigasi agar biaya perubahan tetap rendah.
225. **Jangan menganggap low fidelity berarti asal-asalan.** Wireframe harus cukup akurat untuk menguji urutan dan pemahaman, meskipun warna belum final.
226. **Prototype menjawab pertanyaan spesifik.** Tentukan apa yang ingin diuji, misalnya apakah orang menemukan CTA atau memahami alur pembayaran.
227. **Pilih fidelity sesuai tujuan.** Prototype interaktif penuh tidak selalu dibutuhkan untuk memvalidasi konsep awal.
228. **Uji alur utama dan alur gagal.** Prototipe yang hanya menunjukkan happy path menyembunyikan banyak masalah nyata.
229. **Dokumentasikan keputusan.** Catat alasan perubahan dan bukti yang mendukungnya, bukan hanya hasil akhirnya.
230. **Iterasi berdasarkan temuan.** Bedakan masalah kosmetik dari hambatan yang menghalangi tugas.
231. **Gunakan data konten yang realistis.** Lorem ipsum tidak menunjukkan masalah panjang judul, nama, status, atau nilai angka.
232. **Sertakan keadaan komponen dalam prototype.** Loading, empty, error, success, disabled, dan permission state sering menentukan keberhasilan UX.
233. **Batasi variasi yang diuji sekaligus.** Bila terlalu banyak hal berubah, akan sulit memahami faktor yang membuat hasil lebih baik atau buruk.
234. **Bawa developer ke proses sejak awal.** Diskusi awal tentang data, API, batasan platform, dan aksesibilitas mengurangi kejutan pada tahap implementasi.

# 18. Usability testing dan evaluasi

235. **Tentukan metrik sebelum tes.** Contoh: tingkat keberhasilan tugas, waktu penyelesaian, jumlah kesalahan, kebutuhan bantuan, dan penilaian kepercayaan.
236. **Berikan tugas, bukan arahan klik.** Minta peserta mencapai hasil, bukan memberitahu tombol mana yang harus ditekan.
237. **Amati tanpa terlalu cepat membantu.** Diam sejenak memberi kesempatan melihat apakah desain bisa dipahami sendiri.
238. **Catat perilaku dan kutipan terpisah.** Observasi seperti “peserta kembali tiga kali” lebih konkret daripada kesimpulan “navigasi buruk”.
239. **Jangan menganggap tes kecil sebagai bukti statistik.** Uji kualitatif dapat menemukan hambatan, tetapi tidak otomatis membuktikan proporsi masalah di seluruh populasi.
240. **Prioritaskan keparahan masalah.** Pertimbangkan dampak pada tugas, frekuensi, dan kemampuan pulih.
241. **Perhatikan false confidence.** Pengguna yang mengatakan “mudah” belum tentu berhasil menyelesaikan tugas tanpa bantuan.
242. **Lakukan evaluasi heuristik.** Periksa visibility of system status, match with real world, user control, consistency, error prevention, recognition, flexibility, minimalism, recovery, dan help/documentation.
243. **Gunakan analytics secara hati-hati.** Data klik dapat menunjukkan pola, tetapi jarang menjelaskan alasan tanpa riset tambahan.
244. **A/B testing perlu hipotesis.** Perubahan harus mengukur tujuan yang relevan dan memerhatikan efek samping serta segmen pengguna.
245. **Uji sebelum dan sesudah rilis.** Kondisi produksi dapat berbeda karena data nyata, perangkat, jaringan, atau izin yang tidak ada dalam prototype.
246. **Buat daftar temuan yang dapat ditindaklanjuti.** Sertakan bukti, tingkat keparahan, rekomendasi, dan cara menguji perbaikannya.

# 19. Handoff, implementasi, dan quality assurance

247. **Spesifikasi desain perlu menyertakan perilaku.** Catat bukan hanya ukuran dan warna, tetapi state, validasi, loading, empty, error, dan respons saat aksi berhasil.
248. **Gunakan nama token dan komponen yang konsisten.** Nama yang mudah dipahami mengurangi interpretasi berbeda antara designer dan developer.
249. **Berikan redline atau nilai terukur bila diperlukan.** Untuk layout kritis, jelaskan ukuran, jarak, constraints, dan breakpoint alih-alih berharap developer menebak.
250. **Dokumentasikan aset dan lisensinya.** Cantumkan sumber, format, dimensi, alt text, serta hak penggunaan bila relevan.
251. **Jangan hanya menyerahkan screenshot.** Berikan file sumber, alur interaksi, state, dan catatan implementasi yang dibutuhkan untuk membangun perilaku sebenarnya.
252. **Jaga fidelity tanpa mengorbankan usability.** Pixel-perfect bukan alasan untuk membuat kontrol terlalu kecil, teks tidak fleksibel, atau aksesibilitas buruk.
253. **Bandingkan pada viewport yang sama.** Screenshot design dan implementasi harus memakai ukuran layar, zoom, data, dan state yang setara.
254. **Uji konten ekstrem.** Teks panjang, angka besar, daftar kosong, nama panjang, error berulang, dan koneksi lambat perlu diuji.
255. **Uji browser dan perangkat yang relevan.** Jangan menganggap hasil Chrome desktop mewakili Safari iOS atau perangkat Android low-end.
256. **Periksa performa visual.** CLS, gambar yang terlambat muncul, font swap, dan animasi berat dapat merusak pengalaman walau screenshot final terlihat bagus.
257. **Gunakan automated checks sebagai lapisan awal.** Linting, test komponen, screenshot test, dan accessibility scan membantu menemukan regresi, tetapi tidak membuktikan UX sudah baik.
258. **Sisakan waktu untuk visual QA.** Implementasi selesai secara fungsional belum tentu selesai secara visual dan aksesibilitas.

# 20. Etika, orisinalitas, dan desain yang bertanggung jawab

259. **Jangan menggunakan dark pattern.** Hindari menyamarkan biaya, mempersulit berhenti berlangganan, memaksa consent, atau mengarahkan orang ke pilihan yang tidak mereka inginkan.
260. **Permintaan izin harus bermakna.** Minta data yang diperlukan, jelaskan penggunaannya, dan sediakan pilihan yang proporsional.
261. **Jangan mengecoh lewat visual.** Hirarki, warna, atau tombol tidak boleh sengaja menyamarkan konsekuensi tindakan.
262. **Buat konsekuensi dapat dipahami.** Pengguna perlu mengetahui apa yang terjadi ketika menghapus data, mengirim formulir, menyetujui akses, atau mempublikasikan konten.
263. **Jaga privasi dalam desain.** Hindari menampilkan data pribadi di notifikasi, placeholder, URL, atau layar yang mudah terlihat pihak lain tanpa kebutuhan.
264. **Gunakan gambar manusia dengan hormat.** Pertimbangkan izin, representasi, konteks, dan risiko stereotip.
265. **Jangan mengklaim desain telah tervalidasi tanpa bukti.** Bedakan prinsip yang diasumsikan, temuan riset, hasil pengujian, dan keputusan artistik.
266. **Jangan menyalin karya secara mentah.** Referensi membantu mempelajari struktur dan pola, tetapi hasil akhir sebaiknya menyesuaikan kebutuhan, identitas, dan constraints produk.
267. **Gunakan AI secara transparan dalam proses internal.** Verifikasi output, cek sumber, cek lisensi, dan jangan memperlakukan konten AI sebagai fakta teruji.
268. **Human-led berarti manusia bertanggung jawab.** Desainer atau tim produk tetap bertanggung jawab atas dampak, kualitas, aksesibilitas, orisinalitas, dan konsekuensi desain.

---

# 21. Glosarium istilah visual dan pola UI

Bagian ini membantu menerjemahkan referensi visual menjadi istilah yang bisa dicari atau digunakan dalam brief desain.

| Istilah | Arti praktis | Kapan berguna | Kata kunci pencarian |
|---|---|---|---|
| Split-screen layout | Layar dibagi menjadi dua area utama | Login, onboarding, landing page | `split screen login UI` |
| Image carousel | Deretan gambar/slide yang dapat berganti | Testimoni visual, galeri, konten editorial | `image carousel UI` |
| Slideshow panel | Panel menampilkan visual secara bergantian | Panel promosi di sisi form login | `login page slideshow panel` |
| Draggable slider | Handle yang bisa digeser untuk membandingkan atau memilih nilai | Before-after, rentang nilai | `draggable comparison slider` |
| Draped fabric background | Bentuk seperti kain atau hordeng berlipat | Dekorasi lembut atau premium | `draped fabric abstract background` |
| Silk/satin folds | Kain berkilau dengan gelombang dan lipatan | Hero visual, poster, background | `3D silk folds background` |
| Abstract wavy background | Kurva dan gelombang dekoratif | Pemisah section, landing page | `abstract wavy SVG background` |
| Scalloped edge | Tepi dengan lengkungan berulang | Card, banner, section boundary | `scalloped border SVG` |
| Blob / organic shape | Bentuk organik tidak beraturan | Dekorasi background | `organic blob SVG` |
| Gradient mesh | Gradasi dengan beberapa titik warna | Background hero yang atmosferik | `gradient mesh background` |
| Grain / noise texture | Tekstur titik halus | Mengurangi kesan digital terlalu licin | `subtle grain texture UI` |
| Bento grid | Grid dengan kartu berbagai ukuran | Menampilkan fitur atau ringkasan | `bento grid website UI` |
| Glassmorphism | Surface transparan dengan blur | Overlay atau panel berlapis | `glassmorphism UI` |
| Neumorphism | Komponen tampak timbul/cekung melalui bayangan lembut | Eksperimen visual, bukan default untuk kontrol kritis | `neumorphism interface` |
| Neobrutalism | Warna kontras, garis kuat, bentuk berani | Brand ekspresif | `neobrutalist web design` |
| Editorial layout | Tipografi dan struktur mirip majalah | Portofolio, artikel, storytelling | `editorial website design` |
| Minimalist UI | Mengurangi elemen yang tidak dibutuhkan | Produk dengan tugas fokus | `minimalist dashboard UI` |
| Card-based layout | Informasi dikelompokkan ke kartu | Ringkasan, katalog, dashboard | `card based interface design` |
| Sticky header | Header tetap terlihat saat scroll | Halaman panjang, navigasi penting | `sticky navigation UX` |
| Floating action button | Aksi utama berbentuk tombol melayang | Alur mobile tertentu | `FAB mobile UI` |
| Bottom sheet | Panel muncul dari bagian bawah layar | Aksi kontekstual, filter, detail ringkas | `mobile bottom sheet UI` |
| Skeleton loading | Placeholder bentuk konten saat memuat | Loading data dengan struktur yang diketahui | `skeleton screen UI` |
| Empty state | Tampilan ketika belum ada konten | Daftar kosong, pencarian tanpa hasil | `empty state design` |
| Glass / layered panels | Panel bertumpuk dengan perbedaan kedalaman | Dashboard atau visual premium | `layered panel UI` |
| Split hero | Hero dibagi antara copy dan visual | Website produk | `split hero landing page` |
| Asymmetric grid | Kolom atau kartu tidak simetris | Editorial, portofolio | `asymmetric grid web design` |
| Marquee | Konten bergerak terus secara horizontal | Pengumuman atau visual brand secara terbatas | `marquee web design` |
| Parallax | Elemen bergerak dengan laju berbeda saat scroll | Storytelling visual | `parallax scrolling website` |
| Microinteraction | Respon kecil terhadap aksi pengguna | Feedback, transisi state | `UI microinteractions` |
| Motion design | Sistem gerakan yang mengomunikasikan perubahan | Transisi, navigasi, feedback | `motion design interface` |
| Design token | Variabel keputusan visual dan sistem | Konsistensi lintas komponen | `design tokens system` |

**Catatan untuk contoh hordeng:** bila ingin lekukan dekoratif seperti kain sungguhan, cari `draped fabric`, `silk folds`, atau `curtain folds`. Bila hanya ingin garis melengkung yang sederhana dan mudah diimplementasikan, cari `abstract wave SVG` atau `flowing organic shapes`. Istilah-istilah ini berdekatan, tetapi hasil visualnya berbeda.

# 22. Prompt library untuk AI desain dan AI coding

Prompt yang baik menjelaskan **konteks, pengguna, tujuan, struktur, gaya visual, kendala, state, aksesibilitas, dan kriteria penerimaan**. Hindari prompt yang hanya berkata “buat modern dan keren”; kata-kata tersebut terlalu subjektif dan mudah menghasilkan UI generik.

## 22.1 Template prompt universal

```text
Bertindak sebagai senior product designer dan UI/UX engineer.

KONTEKS PRODUK
- Produk: [nama dan jenis aplikasi]
- Pengguna utama: [siapa yang menggunakan]
- Tugas utama: [apa yang ingin mereka selesaikan]
- Platform: [web desktop / responsive web / iOS / Android]
- Bahasa dan konteks lokal: [bahasa, format angka/tanggal, kebiasaan yang relevan]

TUJUAN DESAIN
- Masalah yang perlu diselesaikan: [masalah nyata]
- Prioritas utama: [misalnya kejelasan, kecepatan, kepercayaan, eksplorasi]
- Tindakan utama pengguna: [CTA atau tugas utama]

LAYOUT DAN HIERARKI
- Susun konten sesuai prioritas tugas.
- Jelaskan struktur dari atas ke bawah.
- Gunakan grid dan spacing yang konsisten.
- Nyatakan apa yang berubah pada mobile, tablet, dan desktop.

BAHASA VISUAL
- Arah visual: [contoh: clean minimal, editorial, soft premium]
- Warna: [brand palette atau minta palet yang punya peran semantik]
- Tipografi: [kebutuhan dan tingkat formalitas]
- Aset/dekorasi: [jenis gambar, ilustrasi, shape, atau tanpa dekorasi]
- Hindari: [gaya atau pola yang tidak diinginkan]

INTERAKSI DAN STATE
- Sertakan default, hover, focus-visible, pressed, loading, empty, error,
  success, disabled, dan selected state sesuai kebutuhan.
- Jelaskan perilaku setiap aksi dan feedback yang diberikan.
- Pastikan seluruh tugas bisa dijalankan dengan keyboard dan layar sentuh.

AKSESIBILITAS DAN TEKNIS
- Gunakan struktur semantik, label yang jelas, fokus terlihat, dan kontras memadai.
- Hormati preferensi reduced motion.
- Jangan menaruh teks penting hanya di gambar.
- Jangan menambahkan library baru tanpa alasan dan pemeriksaan codebase.
- Gunakan aset dengan sumber dan lisensi yang dapat diperiksa.

KRITERIA PENERIMAAN
1. [hasil yang dapat diuji]
2. [perilaku yang dapat diuji]
3. [batasan responsif atau aksesibilitas]

Sebelum membuat hasil akhir, tuliskan asumsi penting dan daftar keputusan desain.
Jika ada hal yang tidak dapat dipastikan, nyatakan sebagai asumsi, bukan fakta.
```

## 22.2 Prompt: halaman login dengan dekorasi lipatan kain

```text
Rancang dan implementasikan halaman login untuk [nama produk] dengan layout
split-screen. Panel kiri berisi visual dekoratif abstrak seperti draped fabric /
silk folds yang mengalir lembut, sedangkan panel kanan berisi form login yang
jelas dan mudah digunakan.

Arah visual: modern, refined, calm, dan professional. Gunakan lipatan abstrak
berlapis dengan gradient lembut, depth tipis, dan negative space. Dekorasi harus
berada di belakang konten visual, bukan menutupi form. Jangan membuat background
terlihat seperti foto hordeng literal kecuali memang dibutuhkan oleh brand.

Panel form mencakup logo, heading, deskripsi singkat, email, password, toggle
show/hide password, remember me jika relevan, forgot password, tombol sign in,
serta opsi lain hanya jika benar-benar didukung produk. Tambahkan validasi,
loading, error, dan success states. Jangan mengarang metode autentikasi yang
belum ada di sistem.

Desktop: dua panel seimbang dengan form memiliki lebar baca yang nyaman.
Tablet dan mobile: susun ulang menjadi satu kolom, kurangi atau hilangkan dekorasi
berat, dan pastikan form menjadi fokus utama. Jangan bergantung pada hover.
Pastikan label terlihat, focus ring jelas, kontras memadai, ukuran target sentuh
nyaman, dan animasi menghormati prefers-reduced-motion.

Implementasi dengan [React + Tailwind / stack yang digunakan]. Ikuti struktur
project yang sudah ada. Reuse komponen dan design token yang tersedia. Jangan
menambahkan dependency baru tanpa memeriksa apakah kebutuhan dapat dipenuhi
oleh stack saat ini. Jika menggunakan SVG atau CSS untuk dekorasi, pisahkan dari
konten form agar mudah dipelihara.

Kriteria penerimaan: layout tetap baik pada viewport sempit dan lebar, form bisa
dipakai dengan keyboard, tidak ada teks terpotong, seluruh state utama tersedia,
dan dekorasi tidak mengganggu performa atau keterbacaan.
```

## 22.3 Prompt: desain mobile app

```text
Bertindak sebagai product designer untuk aplikasi mobile [kategori produk].
Pengguna utama adalah [audiens] yang ingin [tugas utama]. Buat user flow untuk
skenario utama terlebih dahulu, lalu rancangkan screen yang dibutuhkan.

Untuk setiap screen, jelaskan: tujuan, informasi utama, hierarki visual, aksi
primer, aksi sekunder, navigasi, empty/loading/error/success state, dan perilaku
saat offline atau jaringan lambat jika relevan. Ikuti pola platform [iOS / Android]
dan jangan sekadar mengecilkan layout desktop.

Gunakan bahasa visual [gaya], type scale dan spacing yang konsisten. Periksa
safe area, ukuran teks besar, target sentuh, keyboard, permission timing, dan
reduced motion. Hindari onboarding panjang tanpa kebutuhan. Jangan meminta izin
perangkat sebelum konteks manfaatnya jelas.

Berikan output berupa: (1) asumsi dan problem statement, (2) flow, (3) daftar
screen, (4) spesifikasi tiap screen, (5) design tokens, (6) komponen yang dapat
dipakai ulang, (7) edge cases, dan (8) checklist pengujian.
```

## 22.4 Prompt: dashboard data-heavy

```text
Desain dashboard untuk [peran pengguna] yang perlu mengambil keputusan tentang
[data/proses]. Jangan mulai dari jumlah kartu; mulai dari keputusan yang harus
dibuat dan pertanyaan yang perlu dijawab.

Kelompokkan ringkasan, tren, perbandingan, daftar rinci, dan filter sesuai tugas.
Untuk setiap metrik, sertakan nama, nilai, satuan, periode, pembanding jika ada,
dan waktu pembaruan data jika relevan. Pilih jenis grafik berdasarkan pertanyaan,
bukan karena variasi visual. Hindari penggunaan warna yang hanya bersifat dekoratif.

Sediakan state loading, no data, filter tanpa hasil, error, akses ditolak, dan data
stale bila relevan. Tabel harus dapat dipindai, responsive, dan memiliki aturan
untuk sorting, filtering, pagination, serta kolom pada layar kecil.

Jangan mengarang data atau menyamarkan ketidakpastian. Gunakan data contoh yang
jelas ditandai sebagai contoh. Sertakan keyboard behavior, kontras, label, dan
alternatif informasi bagi grafik.
```

## 22.5 Prompt: review/critique screenshot UI

```text
Evaluasi screenshot UI ini sebagai senior UI/UX designer. Jangan hanya menilai
apakah tampilannya menarik. Nilai berdasarkan tujuan pengguna, hierarki visual,
layout, konsistensi, tipografi, warna/kontras, affordance, navigasi, aksesibilitas,
responsivitas, konten, dan state yang belum tampak.

Untuk setiap temuan, berikan:
- Tingkat prioritas: P0 blocker, P1 tinggi, P2 sedang, P3 polish.
- Bukti yang terlihat pada screenshot.
- Dampak potensial terhadap pengguna.
- Rekomendasi perubahan yang spesifik.
- Contoh sebelum/sesudah dalam bentuk deskripsi atau potongan kode bila relevan.
- Cara memverifikasi bahwa perbaikan berhasil.

Pisahkan observasi yang pasti dari hipotesis yang butuh diuji. Jangan mengasumsikan
perilaku yang tidak bisa diketahui hanya dari gambar. Akhiri dengan tiga perbaikan
paling berdampak yang sebaiknya dikerjakan terlebih dahulu.
```

## 22.6 Prompt: membuat design system

```text
Audit UI dan codebase yang sudah ada sebelum membuat design system baru. Temukan
pola yang berulang, komponen yang sudah tersedia, konflik antar-token, dan variasi
yang memang dibutuhkan produk.

Buat fondasi untuk color roles, typography, spacing, radius, border, elevation,
focus ring, motion, dan breakpoints. Definisikan komponen Button, Input, Select,
Checkbox, Radio, Switch, Dialog, Toast, Tabs, Tooltip, Card, Table, Badge, dan
Navigation sesuai kebutuhan nyata, bukan sekadar memenuhi daftar.

Untuk setiap komponen, dokumentasikan kegunaan, kapan tidak digunakan, variants,
props/API, states, keyboard behavior, accessibility notes, contoh, dan edge cases.
Gunakan token semantik. Hindari duplikasi dan abstraksi terlalu generik. Jangan
mengubah gaya seluruh produk tanpa menjelaskan migrasi dan risiko regresinya.

Output: token table, component inventory, aturan penggunaan, contoh implementasi,
strategi migrasi, dan checklist QA.
```

## 22.7 Prompt: menghasilkan background dekoratif SVG/CSS

```text
Buat dekorasi background berupa [abstract waves / draped fabric folds / scalloped
edge / organic blobs] untuk [bagian halaman]. Dekorasi harus berupa lapisan visual
non-interaktif, ringan, skalabel, dan tidak mengganggu teks atau kontrol.

Jelaskan pendekatan yang dipilih: SVG inline, file SVG, CSS gradients, atau kombinasi.
Utamakan bentuk yang mudah dipelihara, hindari efek filter berlebihan, dan sediakan
fallback untuk kondisi rendering terbatas. Pastikan dekorasi tidak menambah overflow
horizontal, tidak menutupi fokus keyboard, tidak menghalangi pointer, dan beradaptasi
pada mobile. Gunakan aria-hidden untuk ornamen yang tidak membawa informasi.

Berikan implementasi, cara menyesuaikan warna/ukuran, dan contoh responsive. Jangan
menggunakan gambar berhak cipta atau menyalin karya referensi secara persis.
```

## 22.8 Prompt untuk AI coding agent yang sudah diberi codebase

```text
Sebelum mengubah kode, periksa struktur proyek, framework, komponen yang tersedia,
style/token yang dipakai, aturan linting, test, dan konvensi penamaan. Laporkan ringkas
apa yang akan digunakan kembali dan file yang mungkin perlu diubah.

Implementasikan desain [brief] dengan mengikuti arsitektur yang ada. Jangan mengganti
stack, menambahkan library, atau menulis ulang bagian yang tidak relevan tanpa alasan.
Jaga business logic, route, API contract, authentication flow, dan state management
yang sudah berjalan.

Setelah implementasi:
1. Jalankan pemeriksaan yang relevan (lint/typecheck/test/build yang tersedia).
2. Uji breakpoint utama dan state loading/empty/error/success.
3. Pastikan akses keyboard, fokus terlihat, label input, dan kontras.
4. Periksa layout overflow, teks panjang, dan console error.
5. Laporkan file yang berubah, keputusan desain, hasil verifikasi, dan sisa risiko.
Jangan menyatakan test berhasil jika tidak benar-benar dijalankan.
```

## 22.9 Prompt untuk membuat variasi visual tanpa kehilangan tujuan

```text
Buat tiga arah visual yang berbeda untuk masalah dan alur yang sama:
A. Clean minimal dan utilitarian.
B. Editorial dengan tipografi dan komposisi kuat.
C. Warm, organic, dan human-centered.

Jangan mengubah kebutuhan pengguna atau perilaku utama antarvariasi. Untuk tiap arah,
jelaskan hierarki, palet, tipografi, aset, trade-off, risiko aksesibilitas, serta produk
apa yang paling cocok. Hindari hanya mengganti warna dari layout yang sama. Setelah
membandingkan, rekomendasikan satu arah berdasarkan konteks produk dan bukti yang ada.
```

## 22.10 Prompt untuk memperbaiki UI yang terasa generik

```text
UI ini terasa generik. Jangan sekadar menambahkan gradient, shadow, glass effect,
atau lebih banyak warna. Cari penyebabnya melalui hierarchy, layout, typography,
content density, brand expression, image direction, component rhythm, dan detail
interaksi.

Pertahankan tugas utama dan aksesibilitas. Usulkan tiga perubahan dengan dampak besar,
jelaskan alasan tiap perubahan, dan tandai mana yang merupakan hipotesis. Jangan
menyalin desain referensi secara langsung. Bangun visual identity yang sesuai dengan
produk, pengguna, dan konten nyata.
```

## 22.11 Prompt untuk audit aset dan lisensi

```text
Buat inventaris seluruh aset visual yang digunakan UI: gambar, ikon, ilustrasi, font,
background, video, dan animasi. Untuk tiap aset, catat nama/file, sumber URL, pembuat
jika diketahui, lisensi atau syarat penggunaan yang telah diverifikasi, kebutuhan
atribusi, ukuran/format, tujuan, alt text, dan fallback.

Jangan menebak lisensi dari nama situs atau tampilan file. Jika bukti lisensi tidak
tersedia, tandai 'perlu verifikasi' dan rekomendasikan aset alternatif dengan sumber
serta lisensi yang dapat diperiksa. Jangan menyimpulkan bahwa aset aman untuk komersial
sebelum memeriksa syarat yang berlaku.
```

## 22.12 Cara memperbaiki prompt secara iteratif

1. Minta AI menyatakan asumsi dan pertanyaan yang belum terjawab sebelum menghasilkan UI, terutama bila brief memuat risiko besar.
2. Beri feedback berdasarkan elemen spesifik: “form terlalu lebar pada 1440 px” lebih berguna daripada “kurang bagus”.
3. Tunjukkan prioritas: “jangan ubah alur; perbaiki hierarki dan kontras saja”.
4. Minta beberapa alternatif untuk masalah yang memang memiliki trade-off, bukan variasi acak.
5. Setelah implementasi, minta audit terhadap hasil yang benar-benar ada, bukan meminta AI menyatakan bahwa desainnya bagus.
6. Pastikan hasil diuji di browser/perangkat. Prompt tidak menggantikan uji usability, visual QA, atau pengecekan lisensi.

---

# 23. Checklist praktik

## 23.1 Sebelum mendesain

- [ ] Apakah pengguna dan tugas utama sudah jelas?
- [ ] Masalah apa yang ingin diselesaikan dan bukti apa yang mendukungnya?
- [ ] Apa yang paling penting dipahami atau dilakukan pengguna pada halaman ini?
- [ ] Apakah konten dan data yang akan tampil sudah diketahui?
- [ ] Platform, kondisi jaringan, bahasa, dan perangkat apa yang perlu didukung?
- [ ] Apakah ada persyaratan keamanan, privasi, atau aksesibilitas?

## 23.2 Saat menyusun layout

- [ ] Hierarki visual menunjukkan prioritas yang jelas.
- [ ] Elemen yang berhubungan terlihat berdekatan.
- [ ] Alignment dan spacing konsisten.
- [ ] Lebar konten nyaman untuk dibaca.
- [ ] CTA utama mudah ditemukan tetapi tidak memanipulasi pengguna.
- [ ] Layout memiliki versi untuk mobile, tablet, dan desktop bila diperlukan.
- [ ] Data/teks panjang tidak merusak komposisi.

## 23.3 Saat memilih visual dan aset

- [ ] Gambar, ikon, atau dekorasi membantu tujuan produk.
- [ ] Aset tidak membuat konten penting kurang terbaca.
- [ ] Rasio dan crop gambar sudah ditetapkan.
- [ ] Ada fallback untuk gambar gagal dimuat.
- [ ] Alt text atau penanganan dekoratif sudah sesuai.
- [ ] Sumber, atribusi, dan lisensi sudah diperiksa.
- [ ] Ukuran file serta performa dipertimbangkan.

## 23.4 Sebelum release

- [ ] Semua kontrol dapat dioperasikan dengan keyboard.
- [ ] Fokus terlihat dan urutannya logis.
- [ ] Kontras dan ukuran teks sudah diperiksa.
- [ ] Label dan pesan error dapat dipahami.
- [ ] Loading, empty, error, success, dan disabled states tersedia.
- [ ] Tidak ada teks terpotong, overflow tidak disengaja, atau elemen yang saling menimpa.
- [ ] Form tidak kehilangan input tanpa alasan.
- [ ] Reduced motion dan layar sentuh diperhatikan.
- [ ] Visual QA dilakukan pada viewport/perangkat yang relevan.
- [ ] Automated tests, lint, build, atau accessibility checks dijalankan bila tersedia.
- [ ] Kekurangan yang diketahui dicatat, bukan disembunyikan.

## 23.5 Evaluasi pascarilis

- [ ] Tugas utama berhasil diselesaikan pengguna?
- [ ] Di tahap mana pengguna berhenti, mengulang, atau mengalami error?
- [ ] Apakah masalah yang ditemukan memiliki bukti yang cukup?
- [ ] Apakah perubahan baru menghasilkan dampak samping?
- [ ] Apakah konten, perangkat, atau kebutuhan pengguna berubah?
- [ ] Apakah sistem desain perlu diperbarui dari temuan berulang?

---

# 24. Referensi belajar, dokumentasi, galeri, dan aset

Sumber berikut dipilih sebagai titik awal belajar. Kategori berbeda memiliki tujuan berbeda: dokumentasi resmi membantu memahami konvensi platform; standar aksesibilitas menjadi dasar pengujian; galeri inspirasi membantu eksplorasi visual; library dan repositori membantu implementasi. **Galeri inspirasi tidak otomatis memberi hak untuk menyalin desain atau aset.**

## 24.1 Prinsip, UX, dan evaluasi

| Sumber | Fokus | Tautan |
|---|---|---|
| Nielsen Norman Group | Usability, riset, heuristik, information architecture | https://www.nngroup.com/articles/ten-usability-heuristics/ |
| Laws of UX | Ringkasan prinsip psikologi dan perilaku dalam desain | https://lawsofux.com/ |
| Interaction Design Foundation | Materi UX, riset, prototyping, design thinking | https://www.interaction-design.org/ |
| GOV.UK Design System | Komponen dan pola untuk layanan publik | https://design-system.service.gov.uk/ |
| US Web Design System | Panduan sistem desain layanan digital | https://designsystem.digital.gov/ |
| W3C Web Accessibility Initiative | Panduan aksesibilitas web | https://www.w3.org/WAI/ |
| WCAG 2.2 Understanding | Penjelasan kriteria WCAG | https://www.w3.org/WAI/WCAG22/Understanding/ |
| WAI Tutorials | Panduan implementasi aksesibilitas | https://www.w3.org/WAI/tutorials/ |
| WebAIM | Edukasi dan pemeriksaan aksesibilitas | https://webaim.org/ |
| Baymard Institute | Riset e-commerce UX; sebagian konten berbayar | https://baymard.com/ |

## 24.2 Panduan platform dan layout web/mobile

| Sumber | Fokus | Tautan |
|---|---|---|
| Apple Human Interface Guidelines | Pola desain untuk platform Apple | https://developer.apple.com/design/human-interface-guidelines/ |
| Android UI Design | Panduan UI Android | https://developer.android.com/design/ui/mobile |
| Material Design 3 | Komponen, tokens, dan prinsip desain | https://m3.material.io/ |
| Figma Learn | Materi belajar Figma dan workflow desain | https://help.figma.com/hc/en-us/categories/360002042553-Learn-design |
| MDN Responsive Design | Konsep layout responsive CSS | https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/CSS_layout/Responsive_Design |
| web.dev Learn Design | Dasar desain web dan responsive | https://web.dev/learn/design/ |
| web.dev Accessibility | Aksesibilitas web praktis | https://web.dev/learn/accessibility/ |
| Material Symbols | Ikon dari Google | https://fonts.google.com/icons |

## 24.3 Design systems dan komponen untuk developer

| Sumber | Fokus | Tautan |
|---|---|---|
| shadcn/ui | Komponen React yang dapat diadopsi dan disesuaikan | https://ui.shadcn.com/ |
| Radix Primitives | Komponen aksesibel tanpa gaya visual yang mengikat | https://www.radix-ui.com/primitives |
| Material UI | Implementasi React dari Material Design | https://mui.com/ |
| Chakra UI | Sistem komponen React | https://chakra-ui.com/ |
| DaisyUI | Komponen berbasis Tailwind CSS | https://daisyui.com/ |
| Storybook | Dokumentasi dan pengujian komponen UI terisolasi | https://storybook.js.org/ |
| Carbon Design System | Design system IBM | https://carbondesignsystem.com/ |
| Atlassian Design System | Komponen dan pola produk Atlassian | https://atlassian.design/ |
| Primer | Design system GitHub | https://primer.style/ |
| Fluent 2 | Design system Microsoft | https://fluent2.microsoft.design/ |
| Spectrum | Design system Adobe | https://spectrum.adobe.com/ |

## 24.4 Repository dan koleksi untuk belajar dari implementasi

| Sumber/repository | Kegunaan | Tautan |
|---|---|---|
| Awesome Design Systems | Kumpulan referensi design system | https://github.com/alexpate/awesome-design-systems |
| Awesome Design | Kurasi sumber dan alat desain | https://github.com/gztchan/awesome-design |
| Awesome Accessibility | Sumber aksesibilitas untuk developer | https://github.com/brunopulis/awesome-a11y |
| Awesome Figma | Resource dan plugin Figma yang dikurasi komunitas | https://github.com/torikay/awesome-figma |
| Storybook examples | Belajar pola pengembangan komponen | https://storybook.js.org/showcase |
| shadcn/ui examples | Referensi komponen dan halaman dengan source code | https://ui.shadcn.com/examples |
| Tailwind UI | Contoh implementasi Tailwind; periksa lisensi/paket | https://tailwindui.com/ |
| HyperUI | Komponen UI berbasis Tailwind; periksa lisensi saat memakai | https://www.hyperui.dev/ |
| Flowbite | Komponen dan template Tailwind; cek lisensi masing-masing | https://flowbite.com/ |
| Preline UI | Komponen UI; cek lisensi dan ketentuan | https://preline.co/ |

## 24.5 Galeri inspirasi desain

| Sumber | Bagus untuk | Tautan |
|---|---|---|
| Dribbble | Eksplorasi arah visual dan konsep UI | https://dribbble.com/ |
| Behance | Studi kasus, proses, dan portofolio | https://www.behance.net/ |
| Mobbin | Referensi pola aplikasi mobile dan web | https://mobbin.com/ |
| Pageflows | Alur produk dan screen flow | https://pageflows.com/ |
| Land-book | Inspirasi landing page | https://land-book.com/ |
| Awwwards | Website eksperimental dan kualitas visual | https://www.awwwards.com/ |
| SiteInspire | Referensi website berdasarkan kategori/gaya | https://www.siteinspire.com/ |
| Httpster | Inspirasi website dan layout | https://httpster.net/ |
| Godly | Kurasi website dengan visual berkarakter | https://godly.website/ |
| One Page Love | Landing page dan website satu halaman | https://onepagelove.com/ |

**Cara belajar dari galeri:** jangan hanya mengambil screenshot. Catat tujuan halaman, struktur, grid, urutan konten, tipografi, penggunaan aset, state, dan perilaku responsive. Kemudian buat versi sendiri dengan kebutuhan dan konten yang berbeda.

## 24.6 Ikon, font, foto, ilustrasi, dan background

| Sumber | Jenis | Catatan |
|---|---|---|
| Lucide | Ikon outline | https://lucide.dev/ |
| Phosphor Icons | Koleksi ikon dengan beberapa gaya | https://phosphoricons.com/ |
| Heroicons | Ikon SVG untuk interface | https://heroicons.com/ |
| Tabler Icons | Ikon SVG | https://tabler.io/icons |
| Google Fonts | Font web | https://fonts.google.com/ |
| Unsplash | Fotografi | https://unsplash.com/license |
| Pexels | Foto dan video | https://www.pexels.com/license/ |
| unDraw | Ilustrasi SVG | https://undraw.co/license |
| Storyset | Ilustrasi yang dapat dikustomisasi | https://storyset.com/ |
| Haikei | Generator bentuk dan background SVG | https://haikei.app/ |
| Get Waves | Generator wave SVG | https://getwaves.io/ |
| Blobmaker | Generator blob SVG | https://www.blobmaker.app/ |
| SVG Backgrounds | Background dan pola SVG | https://www.svgbackgrounds.com/ |
| Hero Patterns | Pola background SVG | https://heropatterns.com/ |
| BGJar | Generator background SVG | https://bgjar.com/ |
| Meshy | Tool generatif 3D, cek syarat penggunaan | https://www.meshy.ai/ |
| Adobe Color | Eksplorasi palet warna | https://color.adobe.com/ |
| Coolors | Generator palet warna | https://coolors.co/ |
| WebAIM Contrast Checker | Pemeriksaan kontras | https://webaim.org/resources/contrastchecker/ |
| Contrast Ratio | Kalkulator kontras | https://contrast-ratio.com/ |

**Catatan lisensi:** tautan di atas bukan jaminan bahwa semua file, template, font, atau paket di dalam suatu platform bebas untuk tujuan komersial. Periksa terms/lisensi resmi untuk aset spesifik, termasuk kebutuhan atribusi dan pembatasan redistribusi.

## 24.7 Tool untuk workflow desain

| Kebutuhan | Tool yang bisa dipertimbangkan | Tautan |
|---|---|---|
| UI design dan prototype | Figma | https://www.figma.com/ |
| Whiteboarding | FigJam | https://www.figma.com/figjam/ |
| UI design alternatif | Penpot, open source | https://penpot.app/ |
| Diagram alur | Excalidraw | https://excalidraw.com/ |
| Diagram dan dokumentasi | Mermaid | https://mermaid.js.org/ |
| Handoff komponen | Storybook | https://storybook.js.org/ |
| Pemeriksaan aksesibilitas | axe DevTools | https://www.deque.com/axe/devtools/ |
| Pengujian lintas browser | Playwright | https://playwright.dev/ |
| Visual regression | Percy | https://percy.io/ |
| Optimasi gambar | Squoosh | https://squoosh.app/ |

---

# 25. Rencana belajar 8 minggu

Rencana ini dapat disesuaikan dengan waktu luang. Fokusnya bukan menyelesaikan sebanyak mungkin tutorial, melainkan membangun kemampuan mengamati, membuat keputusan, menguji, dan menjelaskan alasan desain.

## Minggu 1: Observasi dan fondasi

- Pelajari prinsip UI/UX, affordance, hierarki, dan Gestalt.
- Pilih tiga aplikasi yang sering digunakan. Catat tugas utama, pola navigasi, dan titik kebingungan.
- Latihan: redesign satu layar dengan mempertahankan fungsi yang sama.
- Output: satu halaman analisis berisi masalah, bukti visual, hipotesis, dan perbaikan.

## Minggu 2: Grid, spacing, dan typography

- Pelajari grid, alignment, type scale, line-height, dan panjang baris.
- Buat satu layout dalam versi mobile dan desktop.
- Latihan: gunakan konten asli, termasuk judul panjang, error, dan metadata.
- Output: satu set token spacing dan typography sederhana.

## Minggu 3: Warna, ikon, dan aset

- Buat palet semantik dan periksa kontras.
- Bandingkan ikon outline, filled, dan duotone pada konteks yang sama.
- Cari aset dengan lisensi yang jelas.
- Output: halaman dokumentasi palet, ikon, gambar, alt text, dan sumber/lisensi.

## Minggu 4: Komponen dan design system

- Buat Button, Input, Checkbox, Select, Dialog, Toast, dan Card yang relevan.
- Dokumentasikan variants dan states.
- Output: mini design system dengan contoh penggunaan.

## Minggu 5: Mobile dan responsive

- Pelajari pola platform, safe area, bottom navigation, sheet, dan form mobile.
- Uji layout pada ukuran layar sempit hingga lebar.
- Output: flow tiga hingga lima screen untuk satu tugas utama.

## Minggu 6: UX flow dan prototype

- Buat problem statement dan user flow.
- Buat prototype untuk happy path dan setidaknya dua edge cases.
- Minta satu atau dua orang mencoba tanpa diberi petunjuk klik.
- Output: daftar temuan dan perubahan berdasarkan observasi.

## Minggu 7: Dashboard dan kompleksitas data

- Pilih pertanyaan bisnis atau operasional.
- Rancang ringkasan, filter, tabel, dan visualisasi yang benar-benar membantu keputusan.
- Output: dashboard dengan data contoh yang diberi label serta keadaan tanpa data/error.

## Minggu 8: Portofolio dan evaluasi akhir

- Pilih satu pekerjaan terbaik dan dokumentasikan prosesnya.
- Jelaskan masalah, constraints, alternatif, keputusan, hasil pengujian, serta hal yang masih perlu diperbaiki.
- Output: satu studi kasus portofolio, bukan hanya galeri screenshot.

## Rubrik penilaian mandiri

Nilai tiap dimensi dari 1 sampai 5 dan sertakan bukti. Skor tinggi harus berasal dari keputusan yang beralasan, bukan dari subjektivitas visual saja.

| Dimensi | Pertanyaan evaluasi |
|---|---|
| Problem clarity | Apakah masalah dan pengguna utama terdefinisi? |
| Hierarki | Apakah prioritas terlihat dalam beberapa detik? |
| Layout | Apakah alignment, spacing, dan responsivitas konsisten? |
| Typography | Apakah teks mudah dibaca dan istilah konsisten? |
| Visual system | Apakah warna, ikon, gambar, dan dekorasi memiliki peran yang jelas? |
| Interaction | Apakah aksi dan feedback dapat dipahami? |
| States | Apakah loading, empty, error, success, dan disabled sudah dirancang? |
| Accessibility | Apakah keyboard, fokus, kontras, label, dan ukuran kontrol diperiksa? |
| Validation | Apakah desain diuji dengan tugas nyata dan temuan dicatat? |
| Handoff | Apakah orang lain dapat mengimplementasikan desain tanpa menebak? |

---

# Penutup: standar kerja human-led

Desain yang berkualitas lahir dari kombinasi empati, pemahaman konteks, prinsip visual, pengetahuan platform, keterampilan teknis, dan evaluasi berulang. Referensi visual membantu memperluas kemungkinan, tetapi tidak menggantikan pertimbangan tentang kebutuhan pengguna. AI dapat membantu menghasilkan alternatif dan kode awal; keputusan final tetap perlu ditinjau manusia, diverifikasi, dan diuji.

**Aturan praktis:** jangan bertanya hanya “Apakah ini terlihat bagus?”. Tanyakan juga: “Apakah orang memahami apa yang terjadi? Bisakah mereka menyelesaikan tugasnya? Apa yang terjadi ketika gagal? Siapa yang tertinggal? Bukti apa yang menunjukkan bahwa desain ini bekerja?”


---

# Bagian B — Advanced Art Direction, Web & Mobile

# 26. Decision framework dan anti-generic AI

## 26.1 Empat lapisan keputusan

1. **Functional truth:** tugas pengguna, urutan informasi, CTA, status, navigasi, kepercayaan, dan aksesibilitas. Tidak boleh berubah demi estetika.
2. **Visual grammar:** grid, type scale, warna semantik, spacing, bentuk dan iconography. Konsisten pada seluruh produk.
3. **Art direction:** visual motif, metaphor, treatment gambar, crop, kesan, visual tension, karakter unik. Boleh bervariasi antar halaman asal satu sistem.
4. **Micro-polish:** shadows, easing, detail geometris, noise, highlights, feedback interaksi. Diterapkan setelah struktur benar.

**Prioritas:** Jika art direction mengganggu konten, adaptasi art direction; bukan mengorbankan fungsi. Jangan menyamakan *high-polish* dengan *high-complexity*.

## 26.2 Generic AI design failure modes

| Gejala | Penyebab tipikal | Koreksi desain |
|---|---|---|
| Tiga kartu identik, seragam dan datar | Mengulang template tanpa tujuan | Gunakan hierarki dan komposisi yang punya narasi; variasikan artwork, pertahankan konsistensi kontrol |
| Semua objek memiliki shadow + gradient | Efek tanpa sistem | Tetapkan satu material/lighting language; hilangkan efek yang tidak memberi peran |
| Hero seperti slide presentasi | Background diperlakukan sebagai satu poster terisolasi | Gunakan section continuity: dekorasi di tepi, transisi atas/bawah netral |
| Ikon selalu bohlam, roket, gear | Metafora generik | Audit konteks, temukan objek-domain nyata, lalu sederhanakan atau abstraksikan |
| Terlalu banyak hal bergerak | Animasi menjadi tujuan | Petakan motion ke focus/feedback/navigation; hanya satu pola ambient motion per area |
| Terlalu steril | Semua konten diletakkan di dalam kartu | Pertimbangkan unboxed layout, rhythm, material difference, negative space |
| Terlalu “AI” | Objek literal bertumpuk, perspektif tidak stabil, visual tropes | Batasi elemen per ilustrasi, gunakan seni grafis editorial dan detail yang disengaja |
| Terlalu banyak dekorasi | Tidak ada visual budget | Batasi 1 hero motif + 1 supporting motif + 1 micro accent per section |

**Aturan orisinalitas:** Bedakan belajar dari komposisi referensi vs menduplikasi karya. Ambil prinsip (mis. negative space), bukan susunan elemen identik. Jangan menyebut AI-generated visual sebagai foto riset atau dokumentasi kegiatan nyata.

## 26.3 Brief kreatif sebelum mendesain

Jawab: (1) siapa pengguna; (2) apa tugas primer; (3) konteks halaman dan section sebelahnya; (4) karakter brand; (5) satu metafora visual; (6) apa yang sengaja tidak ditampilkan; (7) apa yang berubah di mobile; (8) apa yang mengukur keberhasilan. Lalu buat moodboard berisi tiga arah berbeda dan tulis kriteria pemilihan. Tidak perlu menghasilkan moodboard jika tugas hanya perbaikan minor.

## 26.4 Visual budget

Terapkan batas kualitatif: satu pusat perhatian per viewport; satu warna aksen primer, satu motif dominan, satu transisi utama; gunakan detail dekoratif hanya ketika menguatkan alur pandang. Angka seperti 20px radius, 120px artwork, 24px stagger merupakan **contoh**, bukan standar universal.

# 27. Kosakata seni desain digital

## 27.1 Genre visual dan kapan dipakai

| Arah | Ciri visual | Cocok | Risiko |
|---|---|---|---|
| Swiss International Style | alignment presisi, type besar, grid rasional, kontras | universitas, editorial data | terlihat dingin jika tanpa karakter |
| Bauhaus / modernist | bentuk dasar, warna terukur, fungsi sebagai komposisi | ikon modular, hero kreatif | dekorasi abstrak terlalu dominan |
| Editorial / magazine | asymmetric spread, crop, whitespace, type as object | artikel, landing kreatif | editorial bisa menghambat scanning form |
| Contemporary collage | cutout, layering, gestural shapes, cut-paper | program, budaya, pendidikan | tumpukan detail menyebabkan noise |
| Organic modernism | blob, kurva, garis kontinuitas, imbangan geometri | portal riset modern | template blob generik |
| Neo-brutalism | strokes tegas, warna berani, offset shadow | brand muda | kontras dan density terlalu agresif |
| Art deco inspired | ritme simetris, garis ornamental, geometri elegan | kampanye tertentu | tampilan terlalu formal atau dekoratif |
| Minimalist utility | navigasi tajam, density tepat, warna hemat | aplikasi bisnis dan dashboard | kehilangan identitas brand jika terlalu netral |
| Data-driven generative art | bentuk dari data/proses nyata | storytelling ilmiah | berisiko menyesatkan tanpa label data |
| Illustration-led identity | ilustrasi unik, style guide ketat | modul, onboarding | gaya menjadi childish/stock |

Gunakan genre sebagai **referensi prinsip**, bukan paket efek yang harus disalin. Campuran dua gaya memerlukan aturan: misalnya grid Swiss + organic side ornament; bukan semua gaya digabung.

## 27.2 Terminologi penting

- **Visual grammar:** bahasa bentuk yang berulang: stroke, sudut, proporsi, tone, kesan ruang.
- **Art direction:** keputusan konseptual tentang bagaimana isi ditampilkan, bukan sekadar pilihan warna.
- **Choreography:** urutan, arah, tempo, serta relasi antar elemen saat mata menjelajah halaman atau pengguna berinteraksi.
- **Compositional anchor:** elemen yang menstabilkan komposisi (judul, ilustrasi, garis tepi).
- **Visual tension:** ketidakseimbangan terukur yang menghasilkan ketertarikan.
- **Counterweight:** elemen untuk menyeimbangkan focal point pada sisi lawan, tanpa harus berukuran sama.
- **Bleed:** bentuk keluar melewati tepi canvas/section secara sengaja.
- **Negative space:** ruang tanpa elemen bermakna untuk alur baca dan fokus.
- **Editorial cropping:** memotong visual secara terencana untuk menonjolkan konteks.
- **Art direction responsive:** mengubah komposisi, bukan hanya menskalakan aset.
- **Staggered rhythm:** pola posisi tidak persis satu garis lurus yang tetap mempertahankan keteraturan.
- **Section continuity:** transisi yang terasa menyatu antara section atas, sekarang, dan bawah.
- **Visual metaphor:** objek atau bentuk yang menjelaskan gagasan abstrak tanpa teks panjang.
- **Morphology:** aturan bentuk suatu keluarga objek, mis. lingkaran iris dan stroke sama.

# 28. Komposisi dan visual choreography

## 28.1 Hirarki komposisi tingkat lanjut

Urutan baca dibentuk oleh kontras ukuran, posisi, jarak, bobot warna, ilustrasi, tipografi, dan arah vektor. Mulai dari wireframe grayscale; tunjukkan satu item utama, kelompok sekunder, detail tersier. Pastikan pengguna bisa menjelaskan tujuan section sebelum memperhatikan ornamen.

Teknik: **rule of thirds**, golden-ratio exploration (bukan kewajiban), diagonal composition, asymmetry, axial symmetry, modular grid, baseline grid, clustering, repetition with variation, figure-ground reversals. Uji ketajaman dengan screenshot blur dan zoom out; fokus seharusnya masih jelas.

## 28.2 Ritme antarelement

Definisikan rhythm dengan pola ukuran dan posisi: `small → medium → large`, `high → low → high`, `quiet → emphasis → quiet`. Hindari tiga item tengah-tengah identik jika kontennya perlu narasi; tetapi pada daftar pilihan setara, pertahankan kesetaraan fungsional, alignment CTA, dan akses yang adil.

**Stagger implementation:** Geser hanya artwork atau wrapper visual di desktop (mis. `translateY(24px)`), *bukan* CTA atau konten esensial bila menciptakan perbedaan akses. Pertahankan document order dan DOM order. Pada mobile, hilangkan stagger jika mengganggu scan linear. Jangan mengandalkan visual reorder untuk urutan fokus.

## 28.3 Visual flow antar konten

- Gunakan implied lines dari alignment title → artwork → program name → CTA.
- Garis lengkung di latar boleh menghubungkan seri, namun tidak boleh melintasi label, form, atau tombol.
- Satu kurva yang melintas antar item memberi rasa relasi; terlalu banyak kurva menjadi ilustrasi poster.
- Jangan menjadikan dekorasi sebagai konektor jika item sebenarnya berdiri sendiri dan tidak memiliki urutan.
- Untuk tiga link portal yang setara: ritme bisa berasal dari komposisi artwork, bukan ranking atau perbedaan prominence CTA.

## 28.4 Asymmetry with control

Asimetri butuh sistem penyeimbang: bentuk organik besar di kiri bisa ditimbang oleh titik-titik kecil yang lebih jenuh di kanan. Perhatikan **perceived mass**: warna navy jenuh terasa lebih berat dari blob biru pucat. Jangan sekadar membuat semua sisi identik.

## 28.5 Typography choreography

Sebuah headline mengawali narasi; subhead mengurangi skala; artwork memberi jeda visual; body memberikan konteks; CTA menyelesaikan alur. Gunakan ritme vertikal yang konsisten. Hindari semua subjudul, gambar, badge, dan tombol berlomba menarik perhatian.

# 29. Art direction editorial dan modernisme

## 29.1 Sistem editorial untuk produk

Tetapkan (a) 1–2 font families dengan lisensi; (b) skala type display, heading, body; (c) modular columns; (d) image treatment; (e) color roles; (f) illustration stroke and palette; (g) signature motif; (h) mobile equivalent. Identitas lahir dari **pengulangan keputusan**, bukan banyak dekorasi.

## 29.2 Typography as image

Bentuk seni boleh berasal dari angka besar, huruf inisial, label vertikal pendek, split heading, atau running text; tetap simpan teks penting sebagai HTML/SwiftUI/Compose text. Batasi teks dekoratif, hindari teks utama tertanam dalam JPG/WebP. Jika letterform dijadikan SVG dekoratif, pastikan konten aslinya ada dalam struktur aksesibel.

## 29.3 Modernist abstract illustration

Mulai dengan makna: “proposal” dapat diwakili dokumen + diagram; “perubahan” oleh transformasi bentuk; “riset” oleh hubungan data; “inovasi” oleh pola modul yang berkembang. Kurangi realisme: bentuk datar 2–4 lapis, geometri bermakna, detail terpilih, palet terkendali. Jangan otomatis menambahkan gear atau bohlam untuk setiap fitur.

## 29.4 Art direction artefact

Untuk setiap section, tulis specification sheet:

```
Intent: memberi akses ke tiga portal pendanaan riset nasional
Visual thesis: tiga disiplin berbeda, satu ekosistem riset
Visual language: Swiss modular grid + flat editorial collage
Palette roles: navy typography, blue identity, orange accents, pale-blue decorative field
Primary shape: research motif (books, plantation crop, orbital geometry)
Ornament: cropped edge-only organic blobs; no central frame
Motion: optional 3–5px transform on hover, 160–240ms, reduced-motion fallback
Constraints: no misleading official logos; button external link; mobile stack; no full-section poster
```

Angka-angka di atas hanyalah titik awal untuk dievaluasi sesuai perangkat dan brand.

# 30. Ornamentasi, edge art, dan section continuity

## 30.1 Edge-only art

Dekorasi di kiri dan kanan section memberi karakter tanpa mengorbankan ruang baca. Letakkan dekorasi pada layer *non-interactive*, sementara konten pada layer yang lebih tinggi. **Jangan** memaksakan ornamen mengisi seluruh bidang atau menyentuh setiap elemen. Organic shapes yang terpotong oleh edge sering lebih natural dari blob sempurna di tengah.

**Anti-PPT rule:** section bukan slide mandiri. Jangan membuat full-bleed backdrop bergambar ramai, frame dekoratif mengelilingi seluruh konten, atau shadow panggung. Saat pengguna scroll, batas section harus terasa menyambung dengan artikel/berita di atas dan konten di bawah. Dekorasi tidak boleh bocor keluar section atau memaksa scroll horizontal.

## 30.2 Katalog ornamentasi

| Motif | Fungsi | Penempatan | Hindari |
|---|---|---|---|
| Cropped circles | counterweight dan brand accent | tepi dengan bleed 20–70% | lingkaran di semua sudut |
| Organic blob | organic framing | kiri/kanan di belakang whitespace | blob menabrak teks |
| Dotted matrix | memberi tekstur ilmiah | potongan kecil dekat edge | penuh seperti noise |
| Thin arcs / orbit | implied direction, connective rhythm | dari edge, tidak melewati aksi | garis banyak dan saling silang |
| Paper-cut layer | material contrast | dekat artwork non-kritis | bayangan berat di semua lapisan |
| Scallop / folded geometry | batas editorial | hanya satu transisi section khusus | memecah konten di halaman panjang |
| Soft gradient field | depth lembut | edge backgrounds | menurunkan kontras |
| Repeated glyph motif | identitas brand | 1 sudut atau separator | menggantikan icon bermakna |

## 30.3 Arsitektur DOM untuk ornament

```html
<section class="research-programs" aria-labelledby="research-title">
  <div class="ornament ornament--left" aria-hidden="true"></div>
  <div class="ornament ornament--right" aria-hidden="true"></div>
  <div class="research-programs__content">
    <h2 id="research-title">Program Riset Nasional</h2>
    <!-- program links -->
  </div>
</section>
```

```css
.research-programs { position: relative; isolation: isolate; overflow: clip; background: #fff; }
.research-programs__content { position: relative; z-index: 1; max-width: 1200px; margin-inline: auto; padding: clamp(40px, 6vw, 88px) 24px; }
.ornament { position: absolute; z-index: 0; pointer-events: none; width: clamp(100px, 14vw, 200px); aspect-ratio: 1; opacity: .65; }
.ornament--left { top: 20%; left: -90px; border-radius: 42% 58% 68% 32%; background: #dceaf9; }
.ornament--right { right: -95px; bottom: 8%; border-radius: 58% 42% 35% 65%; background: #dceaf9; }
@media (max-width: 680px) { .ornament { width: 110px; opacity: .3; } .ornament--left { left: -75px; } .ornament--right { right: -78px; } }
```

Use SVG for sophisticated paths; CSS for simple geometry. Do not use thousands of DOM nodes for dots. Verify clipped focus indicators are not hidden by `overflow: clip`; place important focusable content away from clipped edge or adjust architecture.

## 30.4 Section continuity checklist

[ ] screenshot tiga section sekaligus, bukan satu section saja.  
[ ] Dekorasi tidak membuat abrupt full-screen background band.  
[ ] Header dan footer section memiliki breathing room.  
[ ] Ornament tidak menabrak next/previous section.  
[ ] Kontras terpenuhi pada seluruh posisi.  
[ ] Saat mobile, konten terbaca tanpa harus memahami dekorasi.  
[ ] Tidak muncul horizontal scroll.  
[ ] Ketika text scaling 200%, dekorasi tetap tidak menghalangi tugas.

# 31. Ilustrasi, visual metaphors dan icon family

## 31.1 Semantic icon design pipeline

1. Tentukan action/object: “arsip hibah” berarti dokumen lama yang disimpan, bukan sekadar laci cantik.
2. Kumpulkan 3 metafora, uji pada orang yang memahami domain.
3. Pilih yang paling jelas pada ukuran kecil dan tanpa caption.
4. Definisikan grammar: canvas square, safe inset, stroke, corner radius, flat fill, accent proportion, light-blue blob consistency.
5. Bentuk icon sebagai SVG bila perlu ketajaman dan editability; WebP transparan jika kompleksitas ilustrasi membutuhkannya.
6. Uji alpha transparency, ukuran file, pixel artifact, konsistensi visual mass, cropping, dan theme background.

## 31.2 Icon families vs illustration families

Icon utilitas 16–24px perlu detail minimum; ilustrasi modul 128–512px boleh punya 2–4 elemen konsep. Jangan memakai ilustrasi modul untuk tombol mungil. Tetapkan skala yang konsisten dan kepadatan visual setara. Jadikan ornament/blue blob satu language; hindari memakai blob identik jika terasa tempelan mesin.

## 31.3 Anti-symbol clichés

- Gear: gunakan untuk benar-benar *settings*; bukan untuk semua `kelola`.
- Shield/lock: hak akses dan keamanan; jangan untuk semua halaman admin.
- Bulb: boleh untuk ide/inovasi, tetapi orbit/data modules sering lebih distinctive.
- Trophy: capaian/penghargaan; tidak selalu tepat untuk luaran akademik.
- Folder: arsip/dokumen; kombinasikan dengan ciri semantik jika beberapa fitur dokumen berdekatan.

## 31.4 Visual asset specification

```
Name: icon_pengabdian.webp
Role: module-launcher illustration (informative when paired with title)
Canvas: 512×512 pixels, transparent outside artwork
Palette: navy + PRPM-blue + orange + pale-blue blob
Style: flat editorial, no 3D or gear, no embedded text
Visual: hands/community; recognizability at 112px CSS
Optimization: WebP with alpha; compare quality at target display size
Accessibility: if title adjacent, icon can have empty alt to avoid duplicate reading
Fallback: semantic labeled link remains functional if image fails
```

**Check:** Make transparent export truly alpha, not checkerboard pixels; never remove white areas within the illustration that are deliberate design. Prefer local assets with versioning to avoid external hotlink issues.

# 32. Advanced typography dan layout expression

## 32.1 Type hierarchy as art

Differentiate editorial display from utilitarian body copy. Use typographic contrast through weight, width, spacing and line breaks; avoid relying only on font size. Align headline baseline with visual anchor. For long Indonesian words, test wrapping (e.g. Kemdiktisaintek, Pengabdian kepada Masyarakat), abbreviation policy, and text scaling.

## 32.2 Baseline and modular layout

Adopt an 8px spatial rhythm as starting heuristic, not rigid law. Use coherent column widths and vertical anchors: image-top, badge, title, description, action. On three equal portal links, content columns may use `display:flex` and CTA `margin-top:auto`. Card outlines can be absent while the internal grid remains strict.

## 32.3 Unboxed layout

A grid does not require filled cards. Use image + heading + description + CTA with whitespace separating groups. Provide focus/hover treatment for actual links. If entire tile is clickable, avoid nested interactive elements; a single `<a>` element can include content and an explicit visible CTA style. For external links, distinguish external navigation and open-new-tab behavior consistently; do not force new tabs without a product reason.

## 32.4 Responsive editorial typesetting

Use `clamp()` for display, but test minimum size on narrow screens. Avoid fixed-height headings. Line length for body depends on script, font, and device; optimize readability rather than one universal character count. Localize all date and number formats.

# 33. Color dramaturgy, material, dan texture

## 33.1 Color roles

Primary brand blue does not need to fill every card. Preserve navy for titles/actions and reserve orange for a small number of high-information accents. Background can be pure white/off-white with edge-only pale blue. Semantically dangerous states must not borrow brand orange without a distinct meaning.

## 33.2 Color distribution

The familiar 60/30/10 color ratio is a **heuristic**, not a standard. A research portal might use 80% neutral, 15% blue, 5% orange if that makes content clearest. Test color-blind differentiability and contrast with actual typography.

## 33.3 Material language

Choose either flat print-like, cut paper, soft clay, or photorealism for a surface. Avoid mixing glossy gradient 3D icons with hard flat graphics unless deliberate and justified. Consistent edge treatment, stroke and grain matter more than adding texture everywhere.

## 33.4 Texture and grain

Use subtle grain to reduce artificial sterility in editorial artwork; not over body text and interactive controls. JPEG/WebP noise can increase asset weight; measure before deployment. For small UI components, clean vector often wins. Ensure gradients do not band noticeably on target screens.

# 34. Motion choreography dan prototyping

## 34.1 Motion hierarchy

1. **State motion**: hover, pressed, loading, expand/collapse.
2. **Navigation motion**: page/stack transitions; show spatial relationships.
3. **Spatial feedback**: parallax/float tied to cursor or scroll when useful.
4. **Ambient art motion**: extremely limited; optional, never blocking.

## 34.2 Choreography principles

Use coordinated motion rather than random movement: if the image elevates, shadow softens and accent moves a little, but text remains readable. Animate `transform` and `opacity` when feasible instead of layout properties. Motion should have a beginning and settling point; avoid continuous bouncing on reading-heavy pages.

Suggested microinteraction ranges such as 120–240ms are design starting points, not mandatory platform specs. Test with keyboard and touch. Never communicate state only through motion.

```css
.portal-art { transition: transform 200ms ease; will-change: auto; }
.portal-link:hover .portal-art, .portal-link:focus-visible .portal-art { transform: translateY(-4px); }
@media (prefers-reduced-motion: reduce) { .portal-art { transition: none; transform: none !important; } }
```

Avoid persistent `will-change` for dozens of elements because it may increase memory use. Use only when profiling demonstrates a benefit.

## 34.3 Mobile motion

Touch screens have no stable hover: provide pressed state, spring/scale only when relevant, and preserve screen-reader focus. Avoid motion sickness from scroll-linked parallax. App transitions should match platform navigational model. Respect system reduce motion preferences on iOS and Android.

## 34.4 Motion spec handoff

Specify trigger, duration, easing, property, delay, interrupt behavior, reverse behavior, reduced-motion fallback, and end state. Example: `portal illustration: hover/keyboard focus -> transform translateY(-4px), 200ms ease-out; touch -> pressed opacity transition; reduced motion -> no transform`.

# 35. Website composition and implementation patterns

## 35.1 Section taxonomy

- **Informational hero:** mission, proposition, primary CTA.
- **Editorial feature strip:** insight, program summaries, visual narrative.
- **Portal launcher:** choices with equal action importance.
- **Content feed:** news/cards/list; density and scan order first.
- **Data dashboard:** insight/action with filters; fewer decorative distractions.
- **Conversion panel:** decision and action; keep distractions minimal.

Do not use the same bento, gradient and blob treatment for all section types. A long page needs cadence: dense news → breathable program links → denser detail → footer.

## 35.2 Responsive and container strategy

Use fluid layout with content-based breakpoints and CSS grid. Example:

```css
.portal-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:clamp(20px,3vw,36px); }
.portal-item { min-width:0; display:flex; flex-direction:column; }
.portal-item__art { width:min(100%, 180px); aspect-ratio:1; object-fit:contain; }
.portal-item__action { margin-top:auto; width:100%; min-height:44px; }
@media (max-width:900px) { .portal-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:620px) { .portal-grid { grid-template-columns:1fr; } }
```

Breakpoints are examples; test narrow devices, long titles and zoom. Avoid fixed card heights that clip localized text. Make sure art is not the only indication of what clicking does.

## 35.3 External link UX

Use `<a href>` for navigation, not click handlers on `div`; ensure destination URLs are configured and verified. Label CTA “Kunjungi situs” or site-specific destination. For `target="_blank"`, apply `rel="noopener noreferrer"` as appropriate and signal new-tab behavior if UX expects it; opening in same tab can be preferable for predictability. Track clicks only with privacy-aware analytics.

## 35.4 State and data handling

Skeletons should preserve dimensions and reduce layout shift. Fetch only when needed based on data semantics; caching/revalidation is separate from styling. Use progressive enhancement: content and links should remain usable without motion or complex JavaScript. No unnecessary service/Redis dependency for purely decorative UI.

## 35.5 Web visual QA matrix

Test at 320, 375, 390, 768, 1024, 1280, 1440, and ultrawide as *sample viewports*, not target-device absolutes. Test 200% zoom, reduced-motion, dark mode if supported, slow network, image failure, and keyboard. Verify Firefox, Chromium, and Safari where supported. Inspect appearance beside adjacent sections, not only isolated component screenshots.

# 36. Mobile app art direction and native UX

## 36.1 Platform-native foundation

Choose whether the app is native iOS (SwiftUI/UIKit), Android (Compose/Views), or cross-platform (Flutter/React Native). Respect back gestures, system bars, keyboard, safe area, navigation architecture, dynamic type, accessibility, and platform interactions. Never blindly copy desktop sidebar cards onto narrow mobile screens.

## 36.2 Navigation and information architecture

- App home should prioritize top user tasks, not mirror org chart.
- Bottom navigation for few peer destinations; drill-down for detail; search for large catalogs.
- Use modal/sheet for contextual decisions, not primary navigation sprawl.
- Mobile launcher may use 2-column illustrated modules with labels, but only when feature count and scanability justify it.
- Keep navigation state when returning; don't reset forms/filters unexpectedly.

## 36.3 Native design systems

Material Design 3 and Apple Human Interface Guidelines provide current platform-specific patterns; consult latest vendor docs for sizes, component behavior, and system APIs. Typical guidance often uses comfortable touch areas around **48dp on Android** and **44pt on iOS**, but these are platform-specific design rules of thumb, not interchangeable CSS pixels or exact WCAG requirements.

## 36.4 Responsive vs adaptive mobile

Phone portrait, landscape, tablet and foldable may require *different composition*. Example: phone uses single column, tablet combines navigation rail plus content, large screen offers split detail. For illustration, use safe crop and alternate framing rather than merely reducing entire artwork.

## 36.5 Mobile art-direction patterns

| Pattern | Art treatment | Interaction |
|---|---|---|
| Onboarding value | bold editorial composition, one focus, restrained caption | swipe plus explicit next/skip |
| Empty state | one meaningful illustration, unobtrusive color | primary recovery/action |
| Home launcher | unified icon family, negative space, predictable grid | full accessible tap targets |
| Detail screen | hero crop, progressive disclosure | back navigation predictable |
| Profile/admin | utility-first, sparse art | stable forms, validation, permission cues |
| Progress/task flow | visual steps, accurate states | progress + save/draft recovery |

## 36.6 Gestures and haptics

Use gestures only when discoverable or backed by visible controls. Haptic feedback should communicate meaningful results and honor system settings. Don't attach vibration to every hover/tap. Avoid animations that obscure permission/privacy consequences.

## 36.7 System integrations and edge cases

Design offline/error/timeout, push permission timing, deep links, biometric auth fallback, keyboard overlap, soft navigation bar, screen rotation, dark mode, large text, OS-level screen readers (VoiceOver/TalkBack), multi-window, foldables when relevant. Never fake a permission screen that looks identical to an OS dialog.

# 37. Accessibility and inclusive creative UI

## 37.1 Accessibility tiers

Treat WCAG 2.2 as a web conformance reference where relevant; mobile accessibility also requires platform testing. For WCAG 2.2 AA, success criterion 2.5.8 has a **24×24 CSS px target-size minimum with exceptions**, not a blanket 44px rule. Design for more comfortable targets beyond the bare minimum where possible. WCAG AAA has additional criteria; do not misstate AAA as AA.

## 37.2 Creative art accessibility

Decorative side ornaments: `aria-hidden="true"` and non-interactive; decorative images `alt=""`. Informative charts need text equivalents. Embedded illustrations cannot contain the only copy of title or CTA. Verify contrast against dynamic backgrounds and focus indicators when using clipping. `prefers-reduced-motion` must be honored for nonessential motion.

## 37.3 Test protocol

Keyboard-only traverse; screen reader spot-check; zoom to 200%; 320px reflow; high text scale on native; high contrast where supported; simulate reduced motion; test RTL/localization if product supports it. Automated audits supplement human tests; they cannot prove semantic clarity or good choreography.

# 38. Performance, assets, and delivery

## 38.1 Performance targets (web)

As of verified Google guidance: good Core Web Vitals thresholds **LCP ≤2.5s**, **INP ≤200ms**, **CLS ≤0.1**, evaluated with real-user data at p75. These are quality targets, not guaranteed by asset dimensions alone. Verify any changed threshold against current official documentation.

## 38.2 Asset format matrix

| Media | Default candidate | Why | Caution |
|---|---|---|---|
| Simple icons and geometry | SVG | scalable and editable | sanitize embedded SVG and avoid huge paths |
| Small illustration with alpha | WebP / AVIF | efficient raster | alpha artifacts, browser/platform support |
| Photo | AVIF/WebP + fallback if needed | high compression | verify quality and decoding |
| Small UI animation | CSS / SVG / native animation | interactive, lightweight | reduced-motion / CPU |
| Rich animation | Lottie/Rive after evaluation | controlled playback | bundle size, accessibility, licenses |
| Large photographic background | optimized responsive image | art direction variants | avoid costly LCP |

Do not insist everything must be 512×512; 512 is appropriate for downloadable module illustrations, while displayed CSS dimension and DPR determine served variants. Provide `width` and `height` to prevent layout shifts, `srcset` where useful, lazy-load below-the-fold assets, and consider preload for critical hero only when measured.

## 38.3 Asset QA

Inspect image at actual displayed size, not just zoomed 1000px. Test dark/light surrounding backgrounds, high DPR, alpha boundaries, compressed halos, semantic consistency, and image absence. Provide deterministic file names, versioning, and source metadata. Confirm WebP alpha channel with actual pixel inspection.

## 38.4 Performance monitoring

Use browser performance tools, Lighthouse for diagnosis, real user monitoring when available, and mobile profiler for actual-device jank/energy. Avoid adding heavy shader, filter, backdrop blur or continuous JS animation solely for ornamentation. Audit memory, battery and scroll performance on mid/low-end devices.

# 39. Practical design recipes

## 39.1 News → Programs → Next content

**Problem:** Program section between news and other content feels too clean or isolated.  
**Recipe:** Neutral background, edge-only shapes, content 3-column unboxed grid, artwork as focus, small colored badge, heading, one-line contextual description, full-width per-column CTA.  
**Don't:** huge decorative banner, dark full-background card, ornaments crossing texts, fake wave as information when not meaningful.

## 39.2 Module dashboard with many submodules

Use role grouping, search/filter when large, consistent 512px-derived WebP illustrations shown at ~96–140 CSS px as needed, full semantic labels, tile radius 20px as one design token if brand uses it. Distinguish primary module from submodules; icon only for level requested, never duplicate icon language unnecessarily. Validate semantics without relying only on icon.

## 39.3 Admin dashboard

Use restrained brand accent; prioritize data, filter and action status. Reserve large artwork for empty states/onboarding. Art-heavy cards can undermine dense operational workflows.

## 39.4 Academic mobile home

Use top task shortcuts, contextual updates, badges for meaningful statuses only, easy bottom navigation if appropriate, two-column icon modules at mobile sizes with text that wraps. Avoid fixed button widths and unsafe bottom overlaps.

## 39.5 Long-form editorial article

Combine measured reading width, varied headings, pull quotes or images with captions, stable contents navigation, and restrained side art. Side decorations should vanish or simplify on narrow viewports.

# 40. AI prompt and agent playbook

## 40.1 The non-generic master prompt

```text
ROLE: Senior product designer + editorial art director + front-end/mobile engineer.
SOURCE OF TRUTH: existing UI/UX knowledge base; existing codebase, brand assets and user content.

TASK: Redesign [specific section or screen], not an unrelated rebrand.
FIRST AUDIT: inspect existing DOM/route/components/design tokens/adjacent sections/platform.
GOAL: solve user task with distinctive, human-led art direction, not stock UI or AI clichés.
ART DIRECTION: [Swiss editorial + modernist abstract, or other justified direction].
COMPOSITION: define one focal point, visual rhythm, alignment, whitespace and visual counterweights.
SECTION CONTINUITY: inspect above and below; artwork edge-only if section is part of a long page.
AVOID: gear-on-every-feature, glossy 3D, random gradients, all-blue card blocks, full-slide hero,
      unnecessary shadow, glow, parallax, fake brand logo, invented content, image-embedded CTA.
ASSETS: reuse or create semantically meaningful coherent icon family; WebP/SVG lightweight.
WEB: semantic links, responsive grid, keyboard focus, reduced motion, real URLs, performance.
MOBILE: use native interaction, safe area, large text, appropriate touch target, system behavior.
PROCESS: propose 2–3 clearly different directions if major redesign; choose one with reasons.
IMPLEMENTATION: preserve business logic/API/routing/auth; no new dependency without need.
VALIDATION: screenshot in context at desktop/mobile; test content overflow, keyboard, motion,
            image failure, contrast, external navigation, and actual route behavior.
REPORT: before/after, files changed, evidence from testing, known limitations, rollback.
```

## 40.2 Art director critique prompt

```text
Act as a senior editorial art director, not an illustration generator.
Critique this UI in layers: functional hierarchy → compositional rhythm → semantic artwork →
brand identity → implementation quality. Mark precisely where it feels templated/AI-generated.
Identify the visual center, counterweights, negative space, and visual flow.
Give 3 targeted high-impact changes and 3 elements to deliberately remove.
For each change specify intended user effect, responsive behavior, and verification method.
Do not add decorative artifacts just to fill blank space.
```

## 40.3 Edge-only ornament prompt

```text
Enhance only the side edges of the existing [section].
Use cropped organic pale-blue shapes, a restrained navy/orange ring, and tiny dotted grids.
Keep central content background neutral, no central image, no full-section frame.
Observe the content directly above and below; make transition seamless.
Use aria-hidden decorative SVG/CSS with pointer-events:none, no overflow and no extra packages.
Retain existing headline, texts, links and assets; make CTA width 100% per column.
Desktop edge ornaments can be ~80-160px as starting point; mobile simplify and fade.
Validate at 320px, 390px, 768px, 1440px, 200% zoom, focus and reduced-motion.
```

## 40.4 Mobile screen prompt

```text
Analyze native platform first: [iOS/Android/Flutter/React Native].
Specify user task, navigation/back expectations, safe area, keyboard and dynamic text.
Use [art direction] without sacrificing tap targets or readability.
Deliver flow, screens, states, token system, icon family, responsive/adaptive design,
permissions, offline/errors and QA on real device. Avoid desktop-port aesthetics.
```

## 40.5 Code-agent guardrails

- Read project files and available dependencies before editing.
- Preserve route, state management, tracking, authorization and accessible naming.
- Do not implement UI screenshot as a single image; use real semantic structure.
- Do not modify external URLs without verification.
- Do not install animation libraries for one CSS hover.
- Do not report “production ready” without test evidence.
- Don't claim improved performance without measurement.
- Use feature-scoped changes, screenshot/regression tests, and list changed files.

# 41. Design critique and validation rubrics

## 41.1 100-point rubric (evaluation aid, not universal objective truth)

| Criterion | Weight | Evidence |
|---|---:|---|
| Functional clarity and task success | 20 | task test, CTA visibility, information architecture |
| Visual hierarchy and typography | 15 | first glance, legibility, real content |
| Art direction identity and originality | 15 | coherent visual grammar, differentiates from generic templates |
| Composition and choreography | 15 | spatial rhythm, counterweight, section continuity |
| Responsiveness and platform respect | 10 | multiple viewport/device screenshots |
| Accessibility and inclusive UX | 10 | focus, labels, contrast, motion, touch |
| Performance and asset engineering | 10 | CWV/device profile, optimized media |
| Maintainability and handoff | 5 | tokens, components, tests, documentation |

Score only with evidence. Don't declare “less AI-generated” as fact; treat it as subjective perception to test with design reviewers or users.

## 41.2 Severity mapping

- **P0 blocker:** can't complete primary task, inaccessible critical path, broken navigation.
- **P1 high:** misleading controls, unreadable UI, broken mobile layout, severe performance.
- **P2 medium:** inconsistent icon language, weak hierarchy, excessive ornaments.
- **P3 polish:** micro-spacing, tonal nuance, minor animation feel.

## 41.3 Visual audit in context

Capture complete scroll progression: previous section tail → target section → next section head. Review at real browser zoom, no cropped demo-only previews. Ask: Is this a page section or a detached poster? Is the brand identifiable without header? Is one CTA consistently apparent? Are all three portal options equal in importance? Is the experience still coherent with imagery disabled?

# 42. Case study: Program Riset Nasional

## 42.1 Problem context

Three external links: Hibah BIMA, Hibah Riset BPDP, Program RIIM. The section sits below news and before other homepage content. Old presentation used dark solid blue boxes; initial redesign felt generic and AI-generated; user preferred unboxed white/pale-blue composition with restrained edge art.

## 42.2 Approved direction

- Section surface: white/light ice blue, visually connected to surrounding sections.
- Unboxed 3-column layout (not three giant colored cards).
- Illustration family: flat educational editorial, distinct semantic icon per program, blue+orange.
- Desktop: equal column widths; optional stagger limited to artwork, not essential CTA alignment.
- Accent: cropped organic art shapes **only at left/right edges**; tiny dotted motif, orbit ring; no central full-screen poster.
- Text: program badge, readable title, short factual description; no text embedded in raster artwork.
- CTA: full width of **each** column container, not full section; semantic external link.
- Mobile: stack, simplify ornaments, consistent actions, no horizontal scroll.
- Motion: optional subtle hover illustration lift and reduced-motion fallback.

## 42.3 Rejected patterns

- Large blue solid rectangles enclosing every element.
- Generative photorealistic labs/tropical scenery for simple navigation.
- Too many gradients, floating particles, glow, or dramatic 3D shadows.
- Using ornamental art as slide background covering whole section.
- Irregular CTA width, cards with inconsistent bottoms, text misalignment.

## 42.4 Acceptance tests

1. Three links open intended official destinations, without inventing URLs.
2. Button widths match corresponding columns and align visually.
3. Decor remains behind content, no pointer interception.
4. At mobile width, art does not collide with text and layout stacks.
5. At full-page scroll, transition to/from news is natural.
6. When image blocked, text/links still usable.
7. Keyboard focus visible and reduced-motion honored.
8. Assets load efficiently and do not induce CLS.

# 43. External source hierarchy and update policy

## 43.1 Source priority

1. **Accessibility standards:** https://www.w3.org/TR/WCAG22/ (normative, check amendments/version).
2. **Web performance:** https://web.dev/articles/vitals and https://developers.google.com/search/docs/appearance/core-web-vitals (current thresholds and measurement).
3. **Apple platform:** https://developer.apple.com/design/human-interface-guidelines/ (native iOS patterns and controls).
4. **Android/Material:** https://m3.material.io/ and https://developer.android.com/design (Android patterns, Compose, accessibility).
5. **MDN:** https://developer.mozilla.org/ (CSS, HTML, responsive image, semantic API).
6. **WAI patterns:** https://www.w3.org/WAI/ARIA/apg/ (when complex custom widgets need ARIA guidance; prefer native controls).
7. **Research/human factors:** https://www.nngroup.com/ (heuristics and UX methods; cite specific article when relying on a claim).
8. **Design resources:** https://www.figma.com/ ; https://storybook.js.org/ (workflow tooling, not authority over UX).
9. **Art and design history:** museum archives or primary institutional collections for Bauhaus, Swiss typography and modernist poster research. Distinguish descriptive historical facts from contemporary stylistic recommendations.

## 43.2 Freshness rule

Verify version-specific guidance and active links when used. UI trends and platform components change; do not invent "latest" features. For normative standards, quote exact criterion or reference link rather than simplifying requirements into universal numbers. Use real device or browser testing for performance. Keep dated notes on which documents were verified.

## 43.3 Documentation versus taste

- **Standard:** explicit normative accessibility criterion, browser/API contract.
- **Platform guideline:** recommended component/gesture and native convention.
- **Heuristic:** 8px spacing, 60/30/10 color, ~200ms hover, 24px stagger.
- **Creative preference:** Swiss editorial, edge-only blob, no gear, unboxed layout.
- **Empirical evidence:** usability observation, analytics, performance field data.

Never present a creative taste as a technical requirement, and never claim a visual was user-tested if it was not.

---

# Penutup v2.0 — Design identity without losing utility

Desain yang unik bukan hasil dari menambah objek atau efek sebanyak mungkin. Keunikan yang tahan lama berasal dari keputusan yang selaras: konten, tipografi, komposisi, metafora domain, palet, posisi ruang kosong, gerak dan perilaku platform. Untuk website panjang, periksa hubungan antar-section; untuk mobile, mulailah dari interaksi dan keterbatasan perangkat; untuk AI agent, gunakan referensi sebagai *direction*, bukan template visual yang disalin. 
