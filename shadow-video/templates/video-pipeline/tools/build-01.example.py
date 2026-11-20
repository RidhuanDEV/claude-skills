"""Contoh sumber tunggal modul 01. Salin menjadi tools/build-01.py, lalu ganti label dan selector
dengan yang ditelusuri dari kode aplikasi (kutip file:line di `sources`).

Jalankan: python tools/build-01.py  ->  tutorial/01-login-orientasi.md + scenes/01-login-orientasi.json
"""
from naskah import button, write_module

S = [
    ("s01-buka-login", "Halaman login dengan formulir masuk.", "Buka halaman login",
     "Selamat datang di panduan aplikasi. Pada bagian ini, kamu akan belajar masuk dan mengenal menu utama.",
     [{"type": "goto", "url": "/login"}, {"type": "waitFor", "selector": "#username", "state": "visible"},
      {"type": "pause", "ms": 1000}]),
    ("s02-identitas", "Kolom identitas diisi akun demo.", "Klik dan ketik identitas",
     "Klik kolom identitas, lalu ketik alamat surel akun kamu.",
     [{"type": "type", "selector": "#username", "text": "{{LOGIN_EMAIL}}", "clear": True}]),
    ("s03-sandi", "Kolom kata sandi terisi titik.", "Ketik kata sandi",
     "Lalu ketik kata sandi. Kata sandi selalu tampil sebagai titik.",
     [{"type": "type", "selector": "#password", "text": "{{LOGIN_PASSWORD}}", "clear": True}]),
    ("s04-masuk", "Tombol Masuk ditekan dan dasbor tampil.", "Klik Masuk",
     "Tekan tombol Masuk. Bila data benar, kamu langsung diarahkan ke dasbor.",
     # Navigasi SPA tidak memicu event load: tunggu teks halaman tujuan, bukan URL.
     [{"type": "click", "selector": button("Masuk")},
      {"type": "waitFor", "selector": "text=Dashboard", "state": "visible"}]),
    ("s05-penutup", "Dasbor.", "Tidak ada aksi",
     "Selanjutnya, kita akan membuat data pertama dari menu utama.",
     [{"type": "pause", "ms": 600}]),
]

write_module(
    "01-login-orientasi",
    "01 - Login dan Orientasi",
    S,
    info={
        "Tujuan Pembelajaran": "Pengguna dapat masuk ke aplikasi dan mengenal dasbor.",
        "Target Aktor": "Pengguna (akun demo LOGIN_*)",
        "Tampilan Antarmuka": "Desktop 1920x1080",
        "URL Halaman": "`/login`, `/dashboard`",
        "Data Demo yang Digunakan": "akun demo dari .env; kata sandi tidak pernah ditampilkan",
    },
    sources=["GANTI: label dan selector login dari `src/pages/Login.tsx:NN-NN`"],
    notes=[],
    extra={"recordLogin": True},
)
