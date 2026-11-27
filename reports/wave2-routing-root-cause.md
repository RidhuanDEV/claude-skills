# Wave 2 — Diagnosis kegagalan routing skill

27 November 2026

**Gate penerimaan `FAIL`** · **Diagnosis `VERIFIED-LOCAL`** · **Perbaikan reranker `NOT_RUN`**

Router salah menentukan pemilik utama pada 113 dari 354 kasus positif. Pada 85 dari 113 kegagalan (75,2%), skill yang benar sudah tersedia di lima kandidat leksikal yang lolos filter. Masalah terbesar ada pada penentuan owner berdasarkan tindakan yang diminta. Cakupan retrieval dan pengenalan intent untuk pekerjaan yang dibatasi scope juga perlu diperbaiki agar setiap skill bisa memenuhi gate. [Hasil penerimaan](wave2-routing-evaluation.md)

## Trace pada kandidat yang dibekukan

Kandidat `000be25a10f3e9a4dd6f257948e5b6aec2acd4aa6389a647720870f069ad9aa3` diperiksa secara read-only pada 472 fixture adjudikasi. Trace Python `sys.settrace` merekam variabel `ranked`, `eligible`, `lexical_winner`, dan `directed_owner` pada saat `route_prompt` selesai. Analisis menyamakan fallback dengan tidak adanya prediksi, sesuai dengan evaluator. Hanya agregat yang digunakan untuk rancangan eksperimen. [Router](../shadow-monarch/scripts/skill_router.py) · [Evaluator](../evals/compare_skill_trigger_routing.py)

| Hasil 354 kasus positif | Jumlah | Mekanisme yang teramati |
| --- | ---: | --- |
| Primary benar | 241 | 126/177 EN dan 115/177 ID |
| Primary salah, skill benar di peringkat 1 yang eligible | 36 | 25 gagal syarat bukti atau margin skor (8 bukti minimum, 17 margin), 10 kuat secara leksikal tanpa memenuhi syarat promosi, 3 didahului owner dari aturan permintaan |
| Primary salah, skill benar di peringkat 2–5 yang eligible | 49 | Skill tersedia, tetapi router hanya mempertimbangkan kandidat leksikal pertama untuk promosi |
| Primary salah, skill benar di bawah peringkat 5 yang eligible | 4 | Keempatnya masuk ketika K dinaikkan ke 10 |
| Primary salah, skill benar tidak muncul di hasil leksikal mentah | 17 | Indeks dari deskripsi, alias, dan topik referensi melewatkan owner |
| Primary salah, skill benar muncul di hasil mentah tetapi gugur pada eligibility | 7 | 3 `shadow-browser` dan 4 `shadow-perf` tanpa rule intent yang cocok. Kandidat jenis ini memerlukan rule yang cocok sebelum boleh dipromosikan |

Pada 11 dari 241 keputusan yang benar, kandidat leksikal pertama justru skill lain. Memaksa peringkat 1 menjadi owner akan merusak keputusan tersebut. Di sisi lain, bahkan pemilih sempurna atas gabungan pilihan sekarang dan top 5 eligible hanya menjangkau **326/354 (92,1%)**, dengan **16 skill** masih kehilangan sedikitnya satu positif. K = 10 memberi **330/354 (93,2%)** dan **13 skill** masih kehilangan positif. K = 20 hingga seluruh daftar memberi hasil yang sama. Angka tersebut adalah batas atas dengan candidate pool ini, tanpa menghitung kesalahan primary pada near-miss maupun presisi. [Logika promosi dan eligibility](../shadow-monarch/scripts/skill_router.py) · [Indeks leksikal](../shadow-monarch/scripts/skill_retrieval.py)

Gate aktif menuntut recall ≥90%, precision ≥95%, dan near-miss specificity ≥95% **per skill**. Dengan enam positif dan dua near-miss, setiap skill harus merutekan keenam positifnya dengan benar dan menahan kedua near-miss sesuai exclusion. Owner benar juga dapat muncul pada near-miss skill lain, sehingga denominator presisi berbeda. Jumlah maksimum penugasan primary yang benar per skill pada 472 kasus ini adalah 11. Satu penugasan primary keliru saja memberi presisi paling tinggi 11/12 (91,7%). Saat ini **5/59 skill** lulus ketiganya. Specificity adjudikasi 117/118 (99,2%), dengan 116/118 (98,3%) pada fixture asli. [Definisi dan hasil gate](wave2-routing-evaluation.md)

### Kegagalan near-miss yang tersisa

Pada `shadow-auth-08`, sinyal produksi dan dampak autentikasi sama-sama cocok. Sinyal status outage serta sinyal tindakan pemulihan tidak cocok, sehingga `active_outage` bernilai `false`. Router juga mendeteksi bahwa pengguna tidak meminta perubahan kontrol autentikasi, tetapi hanya mencocokkan rule `shadow-auth` sebagai owner. Permintaan pemulihan operasional adalah bagian dari triage dan containment milik `shadow-maintain`. [Syarat active outage](../shadow-monarch/scripts/skill_router.py) · [Playbook pemeliharaan](../shadow-maintain/SKILL.md)

Tiga probe terkait autentikasi dan satu kontrol redaksi yang ditulis di luar fixture mengisolasi batas itu.

| Probe sintetis | Hasil saat ini | `active_outage` |
| --- | --- | --- |
| Desain login SSO dan implementasi validasi token OIDC | `shadow-auth` | `false` |
| Koordinasi respons insiden produksi dan pemulihan akses dinyatakan eksplisit | `shadow-maintain` | `true` |
| Pengguna terkunci setelah rollout SSO. Diminta urutan containment, kapan membatalkan rollout, dan kriteria akses pulih | `shadow-auth` | `false` |
| Revisi judul pada layar yang menampilkan pesan gangguan produksi | Fallback | `false` |

## Riset dan uji hipotesis

- **Representasi skill yang lebih kaya layak diuji.** SkillRouter v5 melaporkan penurunan 37–44 poin persentase ketika isi skill disembunyikan pada baselines retrieval dan reranking yang mereka uji. Benchmark itu menggunakan 75 query inti dan sekitar 80 ribu kandidat. Ukuran katalog dan label Hit@1 mereka berbeda dari pemilihan satu owner ID/EN pada 59 skill di repo ini. [PREPRINT] [SkillRouter v5](https://arxiv.org/html/2603.22455v5)
- **Retrieval dan pemilihan owner perlu diukur terpisah.** BEIR menemukan BM25 sebagai baseline yang kuat, dengan reranking memberi kinerja zero-shot rata-rata lebih baik pada biaya komputasi yang lebih tinggi. Reciprocal Rank Fusion (RRF) menyediakan pembanding sederhana untuk menggabungkan dua ranking. Keduanya mendukung desain eksperimen, dengan manfaat dan biaya aktual bergantung pada data lokal. [BEIR, NeurIPS](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract-round2.html) · [RRF, ACM SIGIR](https://doi.org/10.1145/1571941.1572114)
- **Embedding multibahasa layak sebagai pembanding retrieval.** Laporan multilingual E5 mengukur pemeringkatan dokumen pada MIRACL. Tabel agregatnya mencakup 16 bahasa dan menyediakan hasil terpisah untuk varian small, base, dan large. Kegunaan pada parafrasa instruksi Indonesia dan pemilihan owner Wave 2 masih perlu diukur. [PREPRINT] [Multilingual E5 Technical Report](https://arxiv.org/html/2402.05672)
- **Eksekusi tugas perlu bukti tersendiri.** SkillsBench v4 mengukur kenaikan pass rate penyelesaian tugas dari 33,9% menjadi 50,5% setelah skill terkurasi diberikan pada 87 tugas dan 18 konfigurasi model–harness. Eksperimen itu mengukur manfaat skill yang sudah dipilih untuk tugas. [PREPRINT] [SkillsBench v4](https://arxiv.org/html/2602.12670v4)

### Eksperimen lokal tanpa model

Corpus dan scorer Python yang sama dipakai untuk tiga varian retrieval di memori. Varian lengkap menambahkan token body setiap `SKILL.md` ke dokumen yang sudah berisi deskripsi dan alias, lalu menghitung ulang frekuensi dokumen serta panjang rata-rata. Frasa dan topik referensi tetap dipakai. Varian gabungan memakai RRF dengan konstanta 60 dan tie-break nama skill. Ukuran di bawah adalah posisi owner dalam **ranking leksikal mentah**, sebelum scope dan keputusan router. Kedua set hanya untuk development. [Kalibrasi 59 kasus](../evals/fixtures/wave2-trigger-development.json) · [Confusion 18 kasus](../evals/fixtures/wave2-trigger-confusion-dev.json)

| Varian | Kalibrasi top 1 | Kalibrasi top 5 | Confusion top 1 | Confusion top 5 | Confusion seluruh daftar |
| --- | ---: | ---: | ---: | ---: | ---: |
| Indeks sekarang | 42/59 | 53/59 | 8/18 | 13/18 | 15/18 |
| Indeks ditambah seluruh body | 41/59 | 54/59 | 7/18 | 13/18 | 18/18 |
| RRF kedua indeks | 48/59 | 54/59 | 9/18 | 16/18 | 18/18 |

Body tambahan mengembalikan tiga owner yang sebelumnya tidak ditemukan pada set confusion, sekaligus menurunkan top 1 dari 8 menjadi 7. RRF membawa tiga tambahan owner ke top 5 dan menggeser top 1 dari 8 menjadi 9. Hasil ini mendukung eksperimen dengan kandidat lebih lengkap dan pemeringkat tersendiri. Sampel development kecil dan set kalibrasi pernah dipakai untuk penyetelan router. Hasil berlaku sebagai petunjuk untuk eksperimen berikutnya.

## Usulan eksperimen perbaikan

1. **Pisahkan tujuan tugas dari topiknya.** Turunkan profil owner dari body skill dan playbook dengan kolom aksi, keluaran yang diminta, fase, batas tanggung jawab, dan skill tetangga. Mulai dari pasangan owner yang sering tertukar. Gunakan skenario baru dengan topik sama tetapi tindakan berbeda, seperti memulihkan akses setelah rollout SSO dan mengubah desain validasi token. Beri label owner dan supporting secara terpisah.
2. **Uji pemilihan owner dan perluasan kandidat secara berpasangan.** Bandingkan router sekarang, shortlist yang sama dengan pemeringkat intent, lalu shortlist yang memakai profil dari body dengan pemeringkat yang sama. Mulai dengan skor yang dapat ditelusuri. Cross-encoder atau pemilih berbasis model menjadi pembanding jika baseline intent masih tertinggal. Uji dense multilingual jika pencarian berbasis profil masih kehilangan owner. Laporkan recall@K mentah dan eligible pada K = 5 dan 10, top-1 final, fallback, precision, specificity, serta waktu p50/p95 per konfigurasi.
3. **Pertahankan syarat scope yang ketat.** Uji browser dan performance dengan pasangan request yang jelas, request analisis tanpa eksekusi, dan larangan eksplisit. Gunakan deteksi kebutuhan kerja untuk menilai relevansi. Keputusan menjalankan alat tetap tunduk pada otorisasi pengguna. Uji kasus pemulihan login dan kontrol redaksi gangguan secara berpasangan. [Aturan execution-sensitive](../shadow-monarch/scripts/skill_router.py)
4. **Bekukan kandidat sebelum uji penerimaan.** Pakai development EN dan ID untuk penyetelan, jalankan kembali gate aktif dengan denominator dan ambang yang sama, lalu lakukan audit buta baru karena agregat holdout sekarang sudah dipakai dalam diagnosis. Verifikasi active roles, disclosure host dan regresi pada keputusan yang sebelumnya benar. [Panduan evaluasi berpasangan dan isolasi tes](../shadow-eval/references/06-regression-baselines-leakage-and-reporting.md)

Konfirmasi gate yang ada dapat diulang dari root repo dengan perintah ini. Exit code `1` menyatakan gate penerimaan gagal.

```powershell
python -B evals/compare_skill_trigger_routing.py --expect-candidate 000be25a10f3e9a4dd6f257948e5b6aec2acd4aa6389a647720870f069ad9aa3
```

**Belum diukur** akurasi pemeringkat intent, recall embedding, latency dan memori konfigurasi usulan, serta aktivasi skill oleh model pada sesi Codex atau Claude Code live. Bukti listing host terdahulu mengukur ketersediaan deskripsi. Pada Claude Code, default dengan konteks 200k masih memiliki 52 dari 59 baris name-only dan profil opt-in mengembalikan 59 deskripsi. Eksperimen indeks lokal berjalan tanpa download model atau perubahan router. [Bukti disclosure host](wave2-routing-evaluation.md#host-listing)
