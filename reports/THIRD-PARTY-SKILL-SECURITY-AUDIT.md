# Laporan Audit Keamanan Pra-Instalasi Skill Pihak Ketiga (`G0–G7`)

**25 November 2026 · Shadow Army · VPS Lab Terisolasi (`L4_HIGH_IMPACT` disetujui Monarch; PC lokal tidak disentuh)**

Audit penuh dilakukan terhadap 3 repositori GitHub pada commit 40-karakter terpatok di VPS lab (`<disposable-vps-lab>`, Ubuntu 26.04.1 LTS) menggunakan:
- Checkout `git` non-eksekusi (`core.hooksPath=/dev/null`, `core.symlinks=false`).
- Pemindaian statis, secret, prompt-injection, dan inventaris pada **100% file (594/594 file)** di ketiga repositori.
- Uji runtime terisolasi **`G6`** di dalam container Docker sekali pakai (`--rm --label shadow.ephemeral=true --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 65534:65534`), **tanpa `npm install`** dan **tanpa egress jaringan**.
- Nol byte kode kandidat diunduh, dijalankan, atau dipasang di PC Monarch.

---

## 1. Ringkasan Kandidat, Digest & Verdict

| Kandidat | Commit SHA & `git archive` TAR SHA-256 | Cakupan Inventaris | Lisensi | Verdict Instalasi Asli | Verdict Adopsi Lokal Mandiri |
| --- | --- | --- | --- | --- | --- |
| **Unslop** (`heydamir/unslop`) | `620163eedb3529d9cd23a3994ed8d287d06f760d`<br>`tar_sha256: 93a3f53f388a703870d6b011aa27c2bd921b97bb1abca045336604aa809d19c2` | `29/29` file (`23` teks dipindai 100%, `6` `.webp`, `0` symlink) | `CC BY 4.0` | `REJECTED` (untuk pilot `.md/.txt`-only; membawa skrip Chromium/FFmpeg) | **`CONDITIONALLY APPROVED`** (ambil metodologi teks + atribusi `CC BY 4.0`, pakai browser internal Shadow Army) |
| **Stack Diagram** (`caru-ini/stack-diagram`) | `1b375941783ff0b1503b91afa079cdf59a966523`<br>`tar_sha256: 03c3f567a0f8d7517c599a7af495f33428013f0c60bd64f0d135addc98952d63` | `252/252` file (`232` teks dipindai 100%, `20` biner, `0` symlink) | `MIT` (kode) + `SIL OFL 1.1` (font) | **`REJECTED`** (`share.py` upload publik + `render_png.py --no-sandbox` + fetch ikon live) | **`CONDITIONALLY APPROVED`** (adopsi `build.py` + `template.html` + `geometry.md` + font offline; **buang** `share.py`, `fetch_icons.py`, dan `--no-sandbox`) |
| **PixelFX** (`patch-gg/pixelfx`) | `5294518ce7c72e48b6100a744596e0acf57f2826`<br>`tar_sha256: ca4ed4715d7befef3fe9fc3f4f443732cd52ee498403515ec881e543f1bd1c63` | `313/313` file (`310` teks dipindai 100%, `3` biner, `0` symlink) | `MIT` | **`REJECTED`** (`SKILL.md` memuat `curl \| sh` & `irm \| iex` + `serve.mjs` wildcard bind + `esbuild` dev install script) | **`CONDITIONALLY APPROVED`** (`src/core/*`, `src/fx/*`, `tools/render.mjs`, `tools/check.mjs` terbukti **100% offline & zero runtime deps**; buang Section 5 `patch.gg`, kunci `serve.mjs` ke `127.0.0.1` atau hapus, buang `esbuild`) |

**Kesimpulan utama keamanan:** **Tidak ditemukan malware, backdoor, obfuscated payload, hidden Unicode, atau credential exfiltration tersembunyi** pada 594/594 file di ketiga repositori. Seluruh temuan berisiko di bawah berasal dari fitur desain (upload galeri, pipe-to-shell CLI installer, Chromium `--no-sandbox`, wildcard bind HTTP server, dan ketergantungan jaringan ikon) yang dapat dihilangkan seluruhnya saat diadopsi menjadi skill lokal mandiri.

---

## 2. Temuan Terverifikasi (Ranked by Severity)

### `HIGH` · PixelFX `SKILL.md` menginstruksikan instalasi remote via pipe-to-shell (`curl | sh` & `irm | iex`)
- **Lokasi:** `pixelfx/skills/pixelfx/SKILL.md:146-158`, `pixelfx/README.md:191`
- **Bukti:** Section *"5. Publish it on Patch"* meminta agent menawarkan publikasi ke `https://patch.gg` dan menjalankan `curl -fsSL https://patch.gg/install.sh | sh` atau `irm https://patch.gg/install.ps1 | iex` / `npm i -g @patchgg/cli`.
- **Impact:** Eksekusi skrip jarak jauh tanpa verifikasi digest (supply-chain RCE pada host jika domain/CDN terkompromi) serta publikasi artefak proyek ke layanan eksternal.
- **Remediation:** Hapus total Section 5 (`Publish it on Patch`) dan seluruh rujukan `pch` / `patch.gg` saat membangun skill lokal.

### `HIGH` · Stack Diagram `share.py` mengirim diagram & metadata arsitektur ke galeri publik
- **Lokasi:** `stack-diagram/skills/stack-diagram/scripts/share.py:27,42,178`, `stack-diagram/skills/stack-diagram/SKILL.md:127-151`
- **Bukti:** Default target `https://stacks.caru.moe` via `POST /api/stacks` (dua PNG + judul + tech stack + display name + optional GitHub login) dan menyimpan `deleteKey` ke disk lokal. Diuji di `G6` (`--network none`): `share.py submit` langsung mencoba koneksi keluar (`cannot reach https://stacks.caru.moe: [Errno -3] Try again`). Pagar "konfirmasi 2x" hanya hidup sebagai teks di `SKILL.md`, bukan kontrol teknis.
- **Impact:** Kebocoran topologi infrastruktur internal ke galeri publik jika agent keliru atau terkena indirect prompt injection.
- **Remediation:** Hapus `share.py` dan Section 7 (`Share to the gallery`) sepenuhnya pada versi lokal.

### `MEDIUM` · PixelFX `tools/serve.mjs` bind ke wildcard `::` / `0.0.0.0` (semua interface jaringan)
- **Lokasi:** `pixelfx/tools/serve.mjs:17-29`
- **Bukti:** Baris 29 memanggil `.listen(PORT, ...)` tanpa argumen host `"127.0.0.1"`. Terverifikasi di `G6` (`node:22-alpine`): `DEFAULT_LISTEN_ADDR: {"address":"::","family":"IPv6"}`. Path traversal memang sudah dicegah (`!file.startsWith(ROOT + sep)`), namun seluruh isi direktori repo tetap terbuka ke jaringan LAN/Wi-Fi.
- **Impact:** Eksposur file lokal pada jaringan bersama saat preview gallery dijalankan.
- **Remediation:** Ubah menjadi `.listen(PORT, "127.0.0.1", ...)` atau hilangkan `serve.mjs` (cukup gunakan output PNG/sprite-sheet offline).

### `MEDIUM` · Stack Diagram `render_png.py` menonaktifkan OS sandbox Chromium (`--no-sandbox`)
- **Lokasi:** `stack-diagram/skills/stack-diagram/scripts/render_png.py:77`
- **Bukti:** `p.chromium.launch(args=["--no-sandbox", "--font-render-hinting=none"])`.
- **Impact:** Menonaktifkan isolasi proses renderer Chromium pada host Windows; berbahaya jika dikombinasikan dengan SVG/ikon yang diambil dari jaringan eksternal.
- **Remediation:** Hapus `--no-sandbox` pada renderer lokal atau gunakan renderer Playwright/browser Shadow Army dengan sandbox aktif.

### `MEDIUM` · Stack Diagram `fetch_icons.py` bergantung penuh pada 7+ sumber jaringan eksternal tanpa anti-SSRF guard
- **Lokasi:** `stack-diagram/skills/stack-diagram/scripts/fetch_icons.py:58-228,257-582`
- **Bukti:** Mengunduh ZIP/SVG live dari `api.svgl.app`, `awsstatic.com`, `services.google.com`, `azureedge.net`, `raw.githubusercontent.com`, `cdn.jsdelivr.net`, plus opsi `name=URL` bebas ke `urllib.request.urlopen` tanpa validasi IP/SSRF. Diuji di `G6` (`--network none`): `fetch_icons.py` gagal total (`FAIL react`).
- **Impact:** Gagal bekerja offline, membuka risiko SSRF via `name=URL`, dan menarik SVG pihak ketiga yang tidak terpatok digest-nya.
- **Remediation:** Ganti dengan bundel katalog ikon SVG lokal terkurasi + generator badge SVG deterministik offline untuk teknologi kustom.

### `MEDIUM` · Unslop membawa skrip eksekusi host (`snapshot.mjs` & `story.mjs`) dengan `fetch()` inlining & FFmpeg
- **Lokasi:** `unslop/skills/unslop/scripts/snapshot.mjs:47-194`, `unslop/skills/unslop/scripts/story.mjs:4-505`
- **Bukti:** `snapshot.mjs` membuka URL/file lokal via Chromium dan memanggil `fetch()` untuk inline CSS/font; `story.mjs` membuka HTTP server lokal di `127.0.0.1` (sudah memakai `resolveStoryFile` dengan proteksi path traversal/symlink) dan memanggil `execFileSync("ffmpeg", ...)`. Tidak memakai `--no-sandbox`. Diuji di `G6`: `test/story-path.test.mjs` **9/9 PASS**.
- **Impact:** Melampaui batas skill dokumentasi murni; membuka halaman eksternal di browser lokal memerlukan isolasi dan izin eksplisit.
- **Remediation:** Adopsi prinsip desain & pass review sebagai referensi teks lokal (`shadow-design`, dengan atribusi `CC BY 4.0`); ganti capture/preview dengan alur Playwright/`shadow-browser` terkontrol jika diperlukan.

### `LOW` · Dev dependency `esbuild` dengan `hasInstallScript: true` (PixelFX) & mutable CI tags (Stack Diagram)
- **Lokasi:** `pixelfx/package-lock.json` (`node_modules/esbuild`), `stack-diagram/.github/workflows/*.yml` (`@v7`/`@v5`/`@v4`)
- **Bukti:** `pixelfx/package.json` memiliki **`dependencies: []`** (nol runtime dependency). `esbuild` hanya `devDependencies` yang tidak dipakai oleh `tools/render.mjs` atau `tools/check.mjs`.
- **Remediation:** Jangan jalankan `npm install` dan buang `package-lock.json` / `esbuild` saat mengadopsi PixelFX secara lokal.

---

## 3. Matriks Hasil Gate (`G0–G7`)

| Gate | Status | Bukti Terukur |
| --- | --- | --- |
| **G0 · Origin** | `PASS` | 3 repo kanonis GitHub, 3 commit 40-char SHA, 3 digest `git archive` TAR SHA-256, lisensi (`CC BY 4.0`, `MIT + SIL OFL 1.1`, `MIT`), 0 symlink pada 594/594 file. |
| **G1 · Static** | `PASS` (dengan temuan) | 100% file teks dipindai (`23/23` Unslop, `232/232` Stack Diagram, `310/310` PixelFX). `0` sink berbahaya pada 260+ modul efek `pixelfx/src/fx/*` & `src/core/*`. Seluruh sink di `tools/*` dan `scripts/*` ditinjau baris per baris. |
| **G2 · Dependencies** | `PASS` (dengan temuan) | `Unslop`: tanpa `package.json` (runtime membutuhkan Playwright/FFmpeg eksternal). `Stack Diagram`: skill Python stdlib murni (`render_png.py` butuh Playwright; `site/` adalah web app terpisah). `PixelFX`: **`dependencies: []`**, 1 `devDependency` (`esbuild` dengan `hasInstallScript: true`). CVE DB live: `NOT_RUN` (tidak relevan untuk runtime zero-dependency). |
| **G3 · Secrets** | `PASS` | Pemindaian regex secret & private key pada 100% file teks (565 file teks): **0 secret nyata ditemukan** (hanya string dummy `"test-secret"`/`"other-secret"` pada unit test `stack-diagram/site/`). |
| **G4 · Instructions** | `FAIL` (PixelFX/Stack Diagram), `PASS` (Unslop) | 100% file `.md`/`.json`/`.yaml` dipindai (termasuk deteksi hidden Unicode: `0` temuan). `PixelFX` `SKILL.md:152` memuat `curl \| sh` / `irm \| iex`. `Stack Diagram` `SKILL.md:127-151` menawarkan upload publik hanya dengan pagar teks. `Unslop` `SKILL.md` bersih dari instruksi berbahaya. |
| **G5 · Permissions** | `FAIL` (instalasi utuh) | `PixelFX` `serve.mjs` bind ke `::` (wildcard). `Stack Diagram` `share.py` egress ke `stacks.caru.moe` + tulis key lokal; `fetch_icons.py` egress multi-domain; `render_png.py` `--no-sandbox`. Tidak ada MCP server atau lifecycle hook repo aktif. |
| **G6 · Runtime** | `PASS` (parsial terisolasi) | Dijalankan di VPS lab via Docker `--rm --network none --read-only --cap-drop ALL --user 65534:65534`:<br>- **Unslop:** `test/story-path.test.mjs` **9/9 PASS**; `snapshot.mjs --help` bersih.<br>- **Stack Diagram:** `build.py` **PASS offline**; `fetch_icons.py` & `share.py` terbukti mencoba egress dan gagal bersih (`FETCH_BLOCKED_OK`, `SHARE_BLOCKED_OK`).<br>- **PixelFX:** `render.mjs fire/torch --sheet` **PASS 100% offline** (60 frame PNG+JSON, 0 deps); `check.mjs fire/torch ice/frost-nova ui/level-up` **3/3 PASS**; bind address wildcard `::` terverifikasi.<br>- *Not measured:* Render Chromium/FFmpeg penuh pada Unslop & Stack Diagram, serta full sweep 241 efek sisa pada `pixelfx/tools/check.mjs` (dibatalkan atas permintaan Monarch karena durasi CPU). |
| **G7 · Decision** | `BLOCKED` (instalasi asli) | Ketiga repo **TIDAK BOLEH diinstal mentah** ke PC. Ketiganya **layak diadopsi & di-enhance menjadi skill lokal mandiri Shadow Army** dengan membuang seluruh komponen berisiko di atas. |

---

## 4. Residual Risk, Cleanup VPS & Rencana Adopsi Lokal Mandiri

- **Residual risk jika diadopsi dengan sanitasi di atas:** Sangat rendah — seluruh komponen lokal berjalan offline tanpa kredensial, tanpa `curl | sh`, tanpa upload galeri, tanpa `--no-sandbox`, dan tanpa `npm install` pihak ketiga. Khusus Unslop wajib mempertahankan atribusi `CC BY 4.0`.
- **Verifikasi Cleanup VPS (`<disposable-vps-lab>`):**
  - `/tmp/shadow-audit-lab` dihapus total (`CLEAN_LAB_DIR`).
  - Container & image ephemeral (`node:22-alpine`, `python:3.12-alpine`) dihapus total; container `traefik` milik Monarch tetap utuh (`Up 4 days`).
  - Kunci SSH privat sementara & `known_hosts` scratch di PC Monarch sudah dihapus (`LOCAL_SCRATCH_KEYS_CLEANED`).
  - Baris public key sementara `shadow-audit-lab-ephemeral` di `/root/.ssh/authorized_keys` VPS sudah terhapus (`EPHEMERAL_COUNT:0`).
- **Metode Instalasi / Adopsi yang Direkomendasikan (Zero External Dependency):**
  1. **Unslop → Enhanced `shadow-design` (sudah mulai di `visual-refinement-review.md`):** Lengkapi menjadi alur audit 9-pass + checklist + token lokal, pakai Playwright/`shadow-browser` internal, dan rapikan penempatan skill lokal agar sesuai struktur installer root repo `SKILL`.
  2. **Stack Diagram → Skill lokal baru (mis. `shadow-diagram` / modul di `shadow-architect`):** Adopsi `build.py` + `template.html` + `geometry.md` + font offline (`MIT` + `SIL OFL 1.1`), **buang** `share.py` & `fetch_icons.py`, tambahkan **pustaka ikon SVG lokal + fallback badge SVG deterministik offline**, dan renderer Playwright lokal **dengan sandbox aktif** (tanpa `--no-sandbox`).
  3. **PixelFX → Skill lokal baru (mis. `shadow-pixelfx` atau modul di `shadow-illustration`):** Adopsi `src/core/*`, `src/fx/*`, `tools/render.mjs`, `tools/check.mjs`, `tools/list.mjs`, `tools/new.mjs`, `tools/act.mjs`, `docs/AUTHORING.md` (`MIT`, 100% Node stdlib, **0 npm dependency**), **buang** Section 5 (`patch.gg` / `curl | sh`), buang `esbuild`/lockfile, dan jika butuh preview server, kunci `serve.mjs` ke `127.0.0.1`.
