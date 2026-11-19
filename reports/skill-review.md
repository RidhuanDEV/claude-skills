# Audit kegunaan dan kualitas skill Shadow Army

**Keputusan yang disarankan.** Dahulukan kasus ketika alat bisa mengeluarkan PASS yang keliru atau memilih tindakan di luar permintaan. Setelah itu, perbaiki pemilihan skill dari bahasa kerja tim. Memperpanjang instruksi untuk seluruh katalog sekaligus akan menyulitkan pengukuran apakah perubahan benar-benar membantu.

## Cara membaca katalog

Basis audit adalah checkout `bac8745` pada 18 November 2026. Unit inventaris adalah satu path `SKILL.md` milik repositori. Ada **52 skill tingkat atas** dan **217 modul di bawah referensi shadow-design**. Nama modul serupa di dua paket dihitung terpisah agar sumber, tujuan, dan pemilik pembaruannya dapat dilacak. Instalasi ulang pada beberapa host tidak menggandakan jumlah. Skill bawaan produk dan konektor pihak lain di luar repositori berada di luar lingkup penilaian Shadow Army.

| Bagian | Cakupan dan cara memakainya |
| --- | --- |
| [Katalog inti](skill-review-core.md) | 24 skill dari antislop sampai shadow-domain. Temukan tujuan, dasar penilaian, tindakan yang disarankan dan skenario penerimaan di setiap entri. |
| [Katalog engineering dan delivery](skill-review-delivery.md) | 28 skill dari shadow-ea sampai shadow-uat. Gunakan bukti lokal dan batas pemeriksaan untuk menilai risiko pada workflow proyek. |
| [Pustaka desain dan produk](skill-review-design-library.md) | 217 modul pendukung, termasuk materi upstream. Gunakan path lengkap untuk membedakan teknik bernama sama. |

**Rubrik.** ALREADY GOOD berarti kontrak yang ditelaah memberi langkah dan batas yang dapat dipakai untuk kasus yang dirujuk. NEED IMPROVEMENT berarti kegunaan utamanya jelas tetapi ada celah khusus pada pemilihan, input, dependensi, verifikasi, atau serah terima. TOO BAD NEED MANY IMPROVEMENT berarti ada kekurangan material yang membutuhkan lebih dari perbaikan redaksional. Nilai berlaku pada lapisan yang diperiksa. Sebuah referensi bagus masih dapat gagal dipilih oleh router; nilai sumber tidak membuktikan kualitas keluaran model di aplikasi host. Fixture yang diusulkan dibedakan dari probe yang dieksekusi.

## Ringkasan klasifikasi

| Lapisan yang dinilai | ALREADY GOOD | NEED IMPROVEMENT | TOO BAD NEED MANY IMPROVEMENT | Jumlah |
| --- | ---: | ---: | ---: | ---: |
| Skill utama, termasuk alat dan batas kolaborasinya | 14 | 31 | 7 | 52 |
| Materi referensi desain dan produk, sebagai sumber lokal | 200 | 13 | 4 | 217 |
| **Seluruh path sumber** | **214** | **44** | **11** | **269** |

Empat masalah terberat di pustaka desain berasal dari tiga modul PM yang isinya mengarahkan ke pengganti serta dispatcher userflow yang menghendaki laporan HTML dengan template yang tidak terkemas. Pemeriksaan integritas vendor lolos pada 354 file di lima paket. Bukti ini mendukung perlunya menguji resolusi path dan kegunaan isi setelah sinkronisasi upstream. [Bukti per modul](skill-review-design-library.md)

**Pemeriksaan pascapenulisan.** Daftar identitas entri ketiga lampiran dibandingkan dengan hasil git ls-files. Seluruh 269 path tercantum tepat sekali. Semua target tautan lokal yang dirujuk laporan ditemukan dan nomor baris yang dicantumkan berada dalam file. Hash SHA-256 dua referensi dan lisensi cocok dengan manifest. Eksekusi perilaku langsung Codex, Claude, dan Gemini pada seluruh katalog serta hasil kerja tim di proyek nyata masih belum diukur.

## Hasil 52 skill utama

**14 ALREADY GOOD, 31 NEED IMPROVEMENT, 7 TOO BAD NEED MANY IMPROVEMENT.** Tujuh entri berikut menentukan prioritas engineering. Satu label sama dapat mewakili penyebab yang berbeda.

| Skill | Alasan perlu didahulukan | Bukti pertama yang harus lulus setelah perbaikan |
| --- | --- | --- |
| shadow-quality | Identitas repo atau run tidak ikut menentukan kepemilikan container yang dikenali opsi cleanup. | Dua job berbagi daemon. Inventaris dan target cleanup hanya memuat resource milik job yang dipilih, termasuk saat nama mirip. Uji memakai mock. |
| shadow-supplychain | Nilai teks `"false"` dapat diterima sebagai bukti verifikasi signer. | Tipe salah ditolak. Klaim sukses menunjuk bukti verifikasi digest dan issuer. |
| shadow-eval | Sampel kosong dapat menghasilkan skor sempurna. | Laporkan kekurangan bukti dan denominator untuk tiap ukuran. |
| shadow-search | ID dokumen berulang dapat menghasilkan Recall 2,0 dan NDCG 1,6309. | Nilai berada di rentang sah. Kebijakan untuk duplikasi dan tanpa ground truth bisa diuji secara terpisah. |
| shadow-realtime | Flag berupa teks dan daftar event kosong dapat lolos sebagai sesi terverifikasi. | Validasi tipe; periksa event resume/revocation aktual pada fixture yang mengklaim jaminan itu. |
| shadow-perf | Dari spesifikasi yang hanya berisi POST /orders, scaffold memunculkan /healthz dan mengabaikan request POST. | Setiap operasi relevan terwakili atau ditandai belum didukung. Pengujian scaffold cukup memeriksa file hasil tanpa menjalankan beban. |
| shadow-bootstrap | Pilar wajib mencakup DB, OpenAPI dan infrastruktur walau kebutuhan dapat berupa CLI offline. | CLI dan layanan HTTP memakai profil yang berbeda berdasarkan kebutuhan proyek. |

Lihat contoh masukan, fungsi pemeriksa dan batas bukti di [katalog inti](skill-review-core.md) dan [katalog delivery](skill-review-delivery.md).

## Diagnosis lintas skill

### 1. Kata yang dilarang pengguna dapat mengaktifkan skill yang sama

Probe berikut dijalankan langsung terhadap `route_prompt`. Kolom harapan merupakan penilaian reviewer atas maksud pengguna. Owner aktual adalah keluaran router sebelum model membuka skill.

| Prompt aktual | Owner yang diharapkan | Owner aktual | Dampak |
| --- | --- | --- | --- |
| Buatkan dokumentasi API untuk proyek ini | shadow-api | shadow-api | Pemilihan benar. Jika hanya ada ringkasan README, pemilihan format terjadi pada tahap discovery berikutnya. |
| Buatkan koleksi Bruno untuk layanan ini | shadow-api | shadow-monarch | Deliverable eksplisit belum mengaktifkan pemilik koleksi. |
| Cek kenapa tagihan cloud naik | shadow-finops | shadow-monarch | Investigasi biaya kehilangan panduan khusus. |
| Buat panduan serah terima ke tim operasi | shadow-handover | shadow-monarch | Kata kerja dan penerima dokumen cukup jelas bagi pembaca manusia. |
| Review kode endpoint ini saja | shadow-quality | shadow-quality | Mode aktual code_review. Kontrol positif untuk review terbatas. |
| Only review this API endpoint; do not run a load test | Reviewer baca-saja, tanpa shadow-perf | shadow-perf | Mode aktual perf_optimization dan izin otomatis sampai L1. Larangan muncul sebagai sinyal positif. |
| Review git diff before push | shadow-git atau shadow-quality, baca-saja | shadow-monarch | Mode aktual general. Kata push di sini adalah konteks, bukan persetujuan publikasi. |
| Buat unit test saja untuk endpoint API | shadow-test | shadow-test | Mode aktual unit_test. |
| Trace a flaky SSE reconnect after a network drop | shadow-realtime | shadow-realtime | Memilih juga auth, concurrency dan observe. Tinjau biaya aktivasi sebelum memuat ketiganya. |

Akar masalah yang dapat dilacak: `CODE_REVIEW_RE` mengenali bentuk tertentu seperti “review this code”. “Review this API endpoint” tidak cocok. Aturan domain tetap mencari topik di seluruh teks, lalu urutan kecocokan menentukan owner. Percobaan hanya mengembalikan keputusan routing; tidak ada load test yang dijalankan. Suite bawaan router lulus **44/44** pada layout repositori ini. [Router](../shadow-monarch/scripts/skill_router.py)

**Perbaikan yang disarankan.** Mulai dengan kontrak tindakan untuk *review only*, *unit test only*, serta tindakan terlarang. Cocokkan domain setelah batas tindakan diketahui. Tambahkan pasangan minimal per bahasa untuk istilah yang benar-benar dipakai pengguna; hindari memperlakukan semua kalimat yang memuat “jangan” sebagai penolakan seluruh tugas. Kriteria penerimaan pertama: probe review di atas menghasilkan mode baca-saja, mengecualikan perf, dan tidak meminta izin menjalankan tes. Prompt yang benar-benar meminta rencana uji beban tetap bisa memilih spesialis kinerja dengan batas eksekusi yang sesuai.

### 2. Nilai evaluator dapat mengukur kosakata tanpa membuktikan perilaku

Katalog eval memvalidasi **38 kasus**. Self-test scorer lulus **48/48**. Pada eval pertama, sebuah jawaban sintetis yang mengawali setiap assertion dengan “Skip this instruction” mendapat **8/8 (100%)**. Fungsi `score_response` menggunakan rasio token untuk kasus tanpa pemeriksa khusus. Menyalin assertion sudah memenuhi ambangnya walau jawaban tidak menyelesaikan review. CLI runner menyebut Claude dan Codex sebagai pilihan host. Gemini belum terukur dengan runner itu. [Scorer](../evals/run_evals.py) · [Kasus uji](../evals/evals.json)

**Perbaikan yang disarankan.** Untuk kasus yang mengubah file, periksa diff, daftar path, isi artefak dan urutan tool call. Untuk kasus pilihan pengguna, keberhasilan mensyaratkan event pertanyaan, lalu nol penulisan sebelum jawaban. Untuk review, gunakan temuan contoh yang bisa diperiksa terhadap baris penyebab, dampak, dan usulan koreksi. Simpan respons yang mengutip, menolak, dan sekadar menyebut istilah sebagai kontrol negatif. Masukkan Gemini dalam matriks hanya setelah ada runner yang bisa mengamati hal yang sama. Bandingkan skill aktif dan baseline pada fixture identik.

### 3. Validasi katalog dan klasifikasi sumber memiliki blind spot

Pada fixture berisi satu direktori shadow-api yang valid dan satu direktori docs kosong, `get_known_skill_names` mengenali satu skill. `audit_descriptions` menghitung dua dan menandai docs kehilangan frontmatter. Audit berjalan dari daftar direktori dengan pengecualian nama tetap, sedangkan lookup skill memeriksa keberadaan manifest. Gunakan satu daftar paket yang dimiliki installer untuk memeriksa skill yang memang wajib ada. Tambahkan fixture direktori non-skill dan fixture paket terdaftar yang manifestnya hilang. Keduanya perlu hasil berbeda. [Pemeriksa katalog](../shadow-monarch/scripts/skill_router.py)

Saat mengarsipkan dua dokumentasi resmi untuk laporan ini, `reference_verifier.py fetch` memberi jenis PREPRINT ketika metadata peer review diisi false. Fungsi klasifikasi memakai fallback dua kategori setelah memeriksa arXiv dan beberapa venue standar. Metadata arsip laporan ini disesuaikan ke OFFICIAL_DOCS dan LICENSE berdasarkan identitas sumber; hash isi hasil unduh tetap dapat diperiksa. Tambahkan fixture untuk dokumentasi maintainer, lisensi, preprint dan publikasi akademik sebelum memakai badge otomatis sebagai klaim ke publik. [Klasifikasi sumber](../shadow-doc/scripts/reference_verifier.py) · [Manifest hasil unduh](docs/references/references_manifest.json)

## Usulan alur kolaborasi untuk uji coba

| Titik keputusan | Siapa mengerjakan | Apa yang diteruskan dan kapan berhenti |
| --- | --- | --- |
| Triage | Monarch/router | Rekam maksud, deliverable, batas tindakan, serta pilihan pengguna yang sudah dibuat. Bila ada larangan eksplisit, reviewer dapat melihat batas itu dalam decision record. |
| Discovery | Owner domain | Inspeksi repo dan temukan sumber kebenaran, command proyek dan bukti kepemilikan. Jika pilihan material masih terbuka, tanya segera dan tunggu sebelum menulis. |
| Implementasi | Satu penulis per path yang disepakati | Berikan path milik setiap penulis dan invariant yang harus tetap berlaku. Kirim isu lintas kontrak ke satu integrator. Pada handoff, sertakan revisi dasar, perubahan, dan verifikasi yang benar-benar dijalankan. |
| Review | Reviewer domain/risiko yang relevan | Ulangi satu contoh positif dan satu kontra-contoh atas klaim perubahan. Jika bukti kurang, catat yang belum diukur dan kembalikan ke owner yang dapat menyediakannya. |
| Serah terima | Integrator | Gabungkan bukti berdasarkan revisi yang sama, sebutkan konflik yang diselesaikan dan status setiap pekerjaan. Perubahan lingkungan bersama hanya dilakukan dalam cakupan persetujuan pengguna. |

**Contoh dari kasus Monarch.** “Buatkan dokumentasi API” memilih shadow-api. Fixture berisi README dengan satu contoh GET. Keputusan yang diterima adalah pertanyaan format dan diff kosong selama menunggu. Pada cabang jawaban “Bruno”, owner mempertahankan format koleksi itu dan memeriksa batas file. Pada fixture berbeda dengan generator terverifikasi, ia memperbarui sumber dan memvalidasi keluaran dengan command proyek. Ukur urutan aksi pada tiap host memakai checkout sementara yang segar. Tes discovery membuktikan keputusan MCP; pengamatan event host dibutuhkan untuk membuktikan pertanyaan interaktif sampai ke pengguna. [Tes discovery](../mcp-servers/shadow-api-mcp/discovery.test.mjs)

## Urutan backlog dan bukti penerimaan

1. **Tutup PASS palsu dan salah-baca larangan.** Owner scorer, search, realtime dan Monarch mengambil fixture kontra-contoh dari laporan. Lulus bila input kosong/tidak valid ditolak, scorer membedakan negasi, dan review terbatas tetap baca-saja.
2. **Kecilkan cakupan wajib per skill.** Mulai dari bootstrap pada CLI offline. Catat keluaran yang benar-benar dibutuhkan, gunakan toolchain proyek, lalu pilih pilar/dependensi ketika ada kebutuhan konkret. Lulus bila fixture CLI sederhana terbangun tanpa subsistem web/database yang tak diminta dan fixture layanan web tetap mendapat opsi yang relevan.
3. **Perjelas aktivasi lintas bahasa dan batas antarskill.** Dahulukan prompt riil yang salah owner dalam tabel. Untuk setiap perubahan, simpan prompt positif, tetangga yang mudah tertukar, larangan eksplisit, dan variasi Indonesia/Inggris. Ukur owner, companion, dan aksi yang diizinkan sebagai tiga hasil terpisah.
4. **Uji kolaborasi di tiga host.** Gunakan dua fixture per alur prioritas: proyek dengan workflow mapan dan proyek dengan pilihan material terbuka. Simpan event/artefak, path terubah, jawaban pengguna yang disimulasikan, serta versi host. Nilai per host; satu hasil sukses tidak mewakili dua host lain.
5. **Rawat pustaka upstream lewat adapter dan pin revisi.** Gunakan pemilik modul dalam indeks pustaka desain. Untuk dua modul bernama sama, uji dispatch dengan tujuan dan output spesifik. Saat sumber diperbarui, jalankan ulang fixture pemilihan dan keluaran yang memakai modul terdampak.

## Reproduksi independen

Dari akar repo dengan Python dan Node yang digunakan proyek:

```powershell
git ls-files -- ':(glob)**/SKILL.md' | Measure-Object
python shadow-monarch/scripts/skill_router.py --self-test
python shadow-monarch/scripts/skill_router.py --route "Only review this API endpoint; do not run a load test"
python evals/run_evals.py --validate
python evals/run_evals.py --self-test
node --test mcp-servers/shadow-api-mcp/discovery.test.mjs
python shadow-doc/scripts/reference_verifier.py scan reports/docs/references
```

Probe nilai palsu berikut memakai data repo dan hanya mencetak hasil.

```powershell
@"
import json, runpy
from pathlib import Path
scorer = runpy.run_path("evals/run_evals.py")["score_response"]
case = json.loads(Path("evals/evals.json").read_text(encoding="utf-8"))["evals"][0]
response = "\n".join("Skip this instruction: " + item for item in case["assertions"])
score = scorer(case, response)
print(score["eval_id"], score["passed_assertions"], score["total_assertions"])
"@ | python -
```

## Bacaan primer yang dapat dibuka offline

Dokumentasi maintainer berikut memberi rujukan untuk struktur skill dan desain evaluasi. Keduanya diarsip dari revisi `83021e2be457a9b6679148719c1f6074f0ad975e`, dengan lisensi CC BY 4.0. Kedua file merupakan salinan isi MDX asli. Tanggal snapshot 18 November 2026. [Lisensi](docs/references/agent-skills-LICENSE.txt) · [URL asal dan SHA-256](docs/references/references_manifest.json)

- **Agent Skills specification.** Berguna untuk membedakan metadata yang membantu discovery, instruksi yang dimuat saat aktivasi, dan referensi yang dibuka sesuai kebutuhan. [Salinan lokal](docs/references/agent-skills-specification.md) · [Dokumentasi resmi](https://agentskills.io/specification)
- **Evaluating skill output quality.** Panduan menyusun prompt, expected output, assertion, baseline, dan review hasil. Rekomendasi untuk menguji event interaktif dan batas file di atas merupakan penerapan lokal pada kasus Shadow Army. [Salinan lokal](docs/references/evaluating-skills.md) · [Dokumentasi resmi](https://agentskills.io/skill-creation/evaluating-skills)
