# Roadmap transformasi dan gerbang keputusan

**Keputusan Stage A untuk Monarch.** Rekomendasi pertama adalah mengesahkan pilot pencarian multi-tenant dan pengujian isolasi cleanup dengan mock. Pilot ini menguji seluruh rantai keputusan dari routing sampai verifikasi data dan handoff. Ia memiliki baseline gagal yang bisa diulang, sementara risiko resource tetangga dapat diuji tanpa Docker nyata. Persetujuan implementasi mengacu ke ID backlog dan batas lingkungan yang dipilih. Dokumen ini belum mengubah versi skill yang dipasang di host.

## Paket keputusan Stage A

| Yang perlu ditinjau | Artefak otoritatif |
| --- | --- |
| Sistem yang ada, gap nyata dan kemampuan tools | [Audit ekosistem](SKILL-ECOSYSTEM-AUDIT.md) |
| Level awal, evidence, target dan area tanpa pengukuran | [Matriks kompetensi profesional](PROFESSIONAL-COMPETENCY-MATRIX.md) |
| Kebutuhan pengetahuan, sumber, pemilik dan siklus pembaruan | [Rencana riset](KNOWLEDGE-RESEARCH-PLAN.md) |
| Unit implementasi, prioritas, dependensi, effort dan DoD | [Master backlog](MASTER-ENHANCEMENT-BACKLOG.md) |
| Pemilik komponen, workflow, kerangka keputusan dan 30 kapabilitas frontend | [Arsitektur target](TARGET-SKILL-ARCHITECTURE.md) |
| Baseline, holdout, observasi, skor, biaya dan pembanding | [Evaluasi dan benchmark](EVALUATION-AND-BENCHMARK-PLAN.md) |
| Risiko, compatibility fixture, tindakan kegagalan dan rollback | [Register risiko](RISK-AND-COMPATIBILITY-REGISTER.md) |

## Stage B setelah rencana disetujui

| Urutan dan dependensi | Unit kerja dan owner | Bukti untuk membuka tahap berikutnya |
| --- | --- | --- |
| 0. Bekukan baseline pada revisi yang disepakati | Eval + quality. Pin revisi skill, fixture, versi host/tool, izin, data sintetis, oracle dan budget. Buat daftar diff awal serta temuan audit yang harus direproduksi. | Red case lama dan positive control tereproduksi. Perbedaan source, oracle dan host trace dapat dibedakan. |
| 1. Kontrak shared minimum | Monarch + eval + quality. Tangani intent/negasi, status bukti, holdout, identitas pemilik resource, dan satu format handoff minimum yang kompatibel. | Reproduksi gagal lama berubah ke hasil benar pada kasus yang diperbaiki. Mock dua job serta payload lama/baru lulus. Jika oracle belum valid, tunda penilaian maturity. |
| 2. Pilot vertikal | Search memeriksa ACL, ranking dan duplikasi; eval mengukur bukti, segmen, abstention; Monarch merutekan dan meneruskan constraint. Quality memverifikasi resource ownership di jalur paralel. | Dua indeks dengan query identik menghasilkan perbandingan per segmen. Satu leak memblokir promosi, data kurang menahan klaim, dan fixture sehat dapat dilanjutkan. Reviewer independen merekonstruksi keputusan. |
| 3. Gate yang berdampak pada rilis | Owner realtime, supplychain, perf, bootstrap. Tuntaskan jalur aman untuk input invalid, contract generation dan workload nyata. | Negatif dan holdout menangkap kesalahan spesifik. Verifikasi ulang integrasi lama pada kontrak yang sah. Pertahankan versi lama bila consumer belum bisa membaca hasil baru. |
| 4. Paket profesi engineering dan delivery | Kerjakan unit C/T di backlog menurut dependensi, dimulai dengan identitas/data, lalu operasi, release, governance dan handover. Bagi ownership menurut path. | Untuk tiap owner ada knowledge relevan, workflow, keputusan kontra-faktual, output profesional, bukti positif/negatif dan batas kemampuan. |
| 5. Pustaka desain dan frontend | Design mengendalikan adapter untuk 17 path; aksesibilitas, riset, API dan browser bekerja sesuai brief. Dapat dimulai setelah baseline serta resolver yang dibutuhkannya tersedia. | Dua metode dengan nama sama dipilih tepat. Jalur review tidak menulis file. Tabel berfilter lulus perubahan state dan satu uji keyboard; fallback repo lama tetap kompatibel. |
| 6. Paritas, rilis bertahap, dan pemeliharaan | Integrator mengevaluasi tiap kandidat pada host yang diizinkan, kemudian canary kelompok kecil. Owner pengetahuan menindaklanjuti perubahan versi/insiden. | Laporan per host dan per dimensi, cost delta, rollback rehearsal dan daftar untested. Target L4/L5 hanya untuk dimensi inti yang terbukti pada kasus baru. |

## Langkah operasional untuk satu unit

1. Berikan ID backlog, base SHA, owner, target file, scope user, dependency dan oracle pada penulis serta reviewer. Simpan reproduksi lama pada fixture yang sama sebelum perubahan.
2. Terapkan satu perubahan yang koheren. Simpan jalur yang sudah dipakai konsumen, tambahkan materi keputusan ketika dibutuhkan, dan buat fixture kesalahan bersama contoh benar.
3. Jalankan validasi spesifik lalu regresi konsumen terdekat. Nilai intensitas pengujian terhadap permintaan dan lingkungan. Untuk lokal/fixture, sertakan path yang berubah dan aksi yang sengaja harus terblokir.
4. Reviewer memeriksa satu hasil domain dan satu counterfactual tanpa melihat jawaban penulis. Untuk ketidaksesuaian, tentukan apakah akar masalah ada pada routing, source/knowledge, tool, oracle, data atau runtime host. Perbaiki pada komponen pemiliknya.
5. Publikasikan catatan bukti per unit di artefak review yang sudah dipakai tim: revisi, perintah/input, actual/expected, biaya yang terukur, risiko sisa, rollback dan bagian belum diuji. Klaim kelulusan dibatasi oleh jenis bukti yang dihimpun.

**Ruang persetujuan.** Pilot bisa dibatasi pada checkout fixture, perbaikan skrip dan instruksi yang terdaftar, pengujian lokal serta mock. Live host berbiaya, deployment, publish, akses organisasi dan pengujian beban adalah kelas pekerjaan tersendiri. Estimasi backlog merupakan perkiraan engineering per unit dengan asumsi reviewer dan fixture tersedia; overlap antar-unit dan penyiapan akses host membuat penjumlahan effort tidak setara dengan tanggal delivery. Perbarui estimasi setelah pilot.

## Isi batch pilot yang diusulkan

| Urutan | ID backlog | Hasil yang diperiksa |
| --- | --- | --- |
| Baseline | X01 | Simpan dataset sintetis, query ID, revisi ACL dan label, prompt, versi runner, expected outcome serta contoh yang mengungkap false PASS. |
| Kontrak lintas owner | X02 dan X06 | Intent, larangan serta approval dapat ditelusuri per tindakan; unknown, gagal, dan lolos dibaca konsisten oleh produsen dan konsumen. |
| Kandidat pilot | T09, T19, T01 | Monarch menjaga scope, search menghasilkan metrik berdasar ID unik dan ACL, eval menangani ketiadaan bukti. Reviewer menilai keputusan promosi pada cohort yang mengalami penurunan. |
| Integrasi pilot retrieval dan generation | E01 setelah T01, T19 dan C06 (auth) | Owner auth memvalidasi snapshot izin dan batas tenant. Reviewer memeriksa apakah salah satu dokumen yang tidak diizinkan mencapai konteks jawaban. |
| Kandidat paralel | T14 setelah X01/X02 | Dua job dalam mock daemon memiliki objek berbeda. Periksa daftar target cleanup dan retry dari crash. Resource milik job tetangga tidak boleh menjadi target. |
| Keluar dari pilot | Gunakan kriteria X07/X08 sebelum uji host atau distribusi | Laporkan regresi, variansi, host yang diuji, dan kontrak lama yang terjaga. Jika oracle tidak membedakan pembanding yang sengaja salah, perbaiki oracle dahulu. |

**Pemetaan permintaan Stage A.** Arsitektur saat ini (1) dan gap (3) ada di audit; skor kompetensi dan bukti (2) di matriks. Riset (4) dan modul pengetahuan (7) dijelaskan di rencana riset dan silabus pemilik. Backlog (5) menunjukkan implementasi, target file, dependensi, risiko, prioritas, effort dan DoD per ID. Arsitektur target (6), workflow (8), kerangka keputusan (9), serta integrasi alat (10) dijelaskan di arsitektur dan spesifikasi item. Skenario (11) dan acceptance terukur (15) ada di benchmark serta oracle item. Register menangani risiko keamanan/kompatibilitas (12). Dependensi (13) dan urutan fase (14) ada pada backlog dan roadmap ini.
