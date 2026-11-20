# Video Pipeline (shadow-video)

Video tutorial dan E2E GUI aplikasi web: **Playwright** memperagakan langkah di frontend lokal atau staging
dengan kursor yang bergerak seperti manusia, **Azure AI Speech** membacakan narasi Bahasa Indonesia, dan
**ffmpeg** menggabungkannya menjadi MP4 + SRT. Berkas scene yang sama dipakai untuk uji E2E GUI.

Dibuat dari skill `shadow-video`. Engine (`src/`) sama untuk semua proyek; hal khusus proyek ada di
`video.config.json`, `.env`, `scenes/`, `tutorial/`, dan `tools/build-*.py`.

```
tools/build-NN.py ─► tutorial/NN-*.md + scenes/NN-*.json   (satu sumber narasi)
scenes ─► validate ─► e2e ─► tts ─► record ─► merge ─► verify ─► final
```

## Prasyarat

| Alat | Versi | Catatan |
|---|---|---|
| Node.js | >= 20.12 | |
| Python | >= 3.10 | hanya untuk `tools/build-*.py` |
| ffmpeg dan ffprobe | 7 atau lebih baru | Windows: `winget install --id Gyan.FFmpeg -e` |
| Playwright | 1.63.0 (dikunci) | `npx playwright install chromium`; Google Chrome bila login memakai Turnstile |
| Azure AI Speech | tier F0 | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` di `.env` |

```
npm ci
cp .env.example .env            # PowerShell: Copy-Item .env.example .env
npm run doctor
npm run typecheck
npm run selftest -- --e2e       # uji engine offline tanpa TTS dan ffmpeg
npm run selftest                # uji offline penuh -> output/selftest.mp4 (butuh TTS)
```

## Konfigurasi proyek: `video.config.json`

| Kunci | Isi |
|---|---|
| `appName`, `outputPrefix`, `cardFooter` | nama aplikasi, awalan nama berkas video lengkap, teks kaki kartu judul (pertahankan pengungkapan suara AI) |
| `brand` | logo PNG (relatif terhadap folder ini), warna aksen dan latar kartu judul |
| `login` | path dan selector halaman login, ditelusuri dari kode aplikasi |
| `rolePrefixes` | prefix akun di `.env` (`LOGIN`, `ADMIN`, ...) untuk placeholder dan `snapshot` |
| `chapters`, `guides` | bab (kartu judul per modul) dan video lengkap per jalur untuk `npm run final` |

## Perintah

```
npm run validate [-- <id>]                          # validasi scenes/*.json
npm run snapshot -- <ROLE> <route> [langkah...]     # riset selector: snapshot ARIA + screenshot
python tools/build-NN.py                            # bangkitkan tutorial/NN-*.md dan scenes/NN-*.json
npm run e2e -- <id> [--headed] [--shots] [--trace]  # E2E GUI tanpa rekaman -> output/e2e/<id>/report.md
npm run login -- --auto                             # sesi akun LOGIN -> auth/storageState.json
npm run build:video -- <id>                         # tts -> record -> merge -> output/<id>.mp4 + .srt
npm run verify [-- <id>]                            # bukti keluaran: codec, kanvas, fps, audio, durasi, SRT, narasi terbaru
npm run final                                       # kartu judul, thumbnail, video per modul dan video lengkap
```

Bantuan debug: `HEADED=1`, `E2E_SLOWMO_MS=300`, `SLOW_FACTOR=2`, `AV_OFFSET_MS=-80`.

## Aturan

- `BASE_URL` hanya lokal atau staging dengan database uji; `BLOCKED_HOSTS` wajib berisi host produksi.
- Data yang dibuat saat rekaman berawalan `Demo – `.
- `.env`, `auth/`, `cache/`, `output/` tidak di-commit (lihat `.gitignore`).
- Narasi diubah hanya lewat `tools/build-NN.py`, tidak langsung di `.md` atau `.json`.
- Perubahan `src/` dikembalikan ke template skill `shadow-video` agar proyek lain ikut mendapatkannya.
