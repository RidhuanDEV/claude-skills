"""Indonesian-to-English technical vocabulary for the local skill index.

The skill documents are written in English, so Indonesian requests share few
tokens with them. This glossary maps common Indonesian software, delivery and
governance terms onto the English words used in the catalog. A light affix
stripper resolves inflected forms such as ``dipulihkan`` or ``menggabungkan``
before the glossary lookup. Queries and documents use the same normalization.
"""

from __future__ import annotations

import re

PHRASES: dict[str, str] = {
    "akar masalah": "root cause",
    "anggaran biaya": "cost budget",
    "basis data": "database",
    "buku panduan": "manual",
    "cerita pengguna": "user story",
    "data pribadi": "personal data",
    "gerbang mutu": "quality gate",
    "hak akses": "access permission",
    "kata sandi": "password",
    "kotak masuk": "inbox",
    "mesin pencari": "search engine",
    "pemangku kepentingan": "stakeholder",
    "peta situs": "sitemap",
    "rantai pasok": "supply chain",
    "serah terima": "handover",
    "surat elektronik": "email",
    "tanda tangan": "signature",
    "tata kelola": "governance",
    "tata letak": "layout",
    "tulis ulang": "rewrite",
    "uji beban": "load test",
}

WORDS: dict[str, str] = {
    "agen": "agent", "akses": "access", "alat": "tool", "alur": "flow", "analitik": "analytics",
    "anggaran": "budget", "animasi": "animation", "antarmuka": "interface", "antrean": "queue",
    "aplikasi": "app", "arsitektur": "architecture", "asal": "provenance", "bayar": "payment",
    "beban": "load", "berkas": "file", "biaya": "cost", "cabang": "branch", "cadang": "backup",
    "cadangan": "backup", "degradasi": "degradation", "histori": "history", "kalimat": "wording", "konfirmasi": "confirmation", "celah": "vulnerability", "cerita": "story", "corong": "funnel",
    "dasbor": "dashboard", "delegasi": "delegate", "desain": "design", "dokumen": "document",
    "dokumentasi": "documentation", "duplikasi": "duplicate", "enkripsi": "encryption", "evaluasi": "evaluation",
    "fungsi": "function", "galat": "error", "gambar": "image", "gabung": "merge", "gangguan": "outage",
    "halaman": "page", "halusinasi": "hallucination", "hapus": "delete", "huruf": "font", "ikon": "icon",
    "ilustrasi": "illustration", "indeks": "index", "insiden": "incident", "integrasi": "integration",
    "izin": "permission", "jadwal": "schedule", "jaringan": "network", "jawab": "answer", "jawaban": "answer",
    "jejak": "trace", "kebocoran": "breach", "kebutuhan": "requirement", "kecepatan": "speed",
    "kejadian": "event", "keamanan": "security", "kepatuhan": "compliance", "kerentanan": "vulnerability",
    "kesalahan": "error", "ketergantungan": "dependency", "kinerja": "performance", "klien": "client",
    "kode": "code", "kolom": "column", "komentar": "comment", "kompatibilitas": "compatibility",
    "konflik": "conflict", "konteks": "context", "kontainer": "container", "kontrak": "contract",
    "kontrol": "control", "konversi": "conversion", "kredensial": "credential", "kueri": "query",
    "kunci": "key", "kutipan": "citation", "lambat": "slow", "laporan": "report", "latensi": "latency",
    "layanan": "service", "layar": "screen", "lemot": "slow", "lingkungan": "environment", "lingkup": "scope",
    "luring": "offline", "masalah": "issue", "metrik": "metric", "migrasi": "migration", "mitra": "partner",
    "modul": "module", "pantau": "monitor", "panduan": "guide", "pecah": "split", "pelacakan": "tracking",
    "pelatihan": "training", "peluncuran": "rollout", "pemantauan": "monitoring", "penawaran": "bid",
    "penerimaan": "acceptance", "pengguna": "user", "penyebab": "cause", "peramban": "browser",
    "peran": "role", "perayapan": "crawl", "performa": "performance", "peringatan": "alert",
    "peringkat": "ranking", "perilaku": "behavior", "persetujuan": "consent", "persyaratan": "requirement",
    "pesan": "message", "pindai": "scan", "pisah": "split", "ponsel": "mobile", "privasi": "privacy",
    "profil": "profile", "proyek": "project", "pulih": "restore", "pustaka": "library", "rahasia": "secret",
    "rapi": "cleanup", "rekaman": "recording", "relevansi": "relevance", "reproduksi": "reproduce",
    "retensi": "retention", "riwayat": "history", "rilis": "release", "risiko": "risk", "rotasi": "rotate",
    "sandi": "password", "sertifikat": "certificate", "sesi": "session", "sinkron": "sync",
    "sinkronisasi": "sync", "sintaks": "syntax", "sistem": "system", "skema": "schema", "sumber": "source",
    "surel": "email", "tabel": "table", "tagihan": "bill", "tampilan": "view", "tautan": "link",
    "teks": "text", "tes": "test", "toko": "store", "tombol": "button", "transaksi": "transaction",
    "tumpukan": "stack", "uji": "test", "unduh": "download", "unggah": "upload", "versi": "version",
    "video": "video", "wajah": "face", "warisan": "legacy", "warna": "color", "wawancara": "interview",
}

PREFIXES = ("meng", "meny", "mem", "men", "me", "peng", "peny", "pem", "pen", "pe", "ber", "ter", "di", "ke", "se")
SUFFIXES = ("nya", "kan", "an", "i", "lah")
NASAL_RESTORE = {"mem": "p", "pem": "p", "men": "t", "pen": "t", "meny": "s", "peny": "s", "meng": "k", "peng": "k"}
PHRASE_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, PHRASES), key=len, reverse=True)) + r")\b", re.IGNORECASE)


def expand_phrases(text: str) -> str:
    """Replace multi-word Indonesian terms with their English equivalent."""
    return PHRASE_RE.sub(lambda match: PHRASES[match[1].casefold()], text)


def _lookup(word: str) -> str | None:
    return WORDS.get(word)


def english_term(word: str) -> str | None:
    """Return the English term for an Indonesian word or one of its inflected forms."""
    direct = _lookup(word)
    if direct is not None:
        return direct
    if len(word) < 5:
        return None
    stems = {word}
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            stems.add(word[: -len(suffix)])
    for stem in list(stems):
        for prefix in PREFIXES:
            if stem.startswith(prefix) and len(stem) - len(prefix) >= 3:
                rest = stem[len(prefix):]
                stems.add(rest)
                if prefix in NASAL_RESTORE:
                    stems.add(NASAL_RESTORE[prefix] + rest)
    for stem in sorted(stems, key=len, reverse=True):
        for candidate in (stem, *(stem[: -len(suffix)] for suffix in SUFFIXES if stem.endswith(suffix) and len(stem) - len(suffix) >= 4)):
            found = _lookup(candidate)
            if found is not None:
                return found
    return None


LOANWORD_PREFIXES = ("di", "ter", "ke")


def loanword_stem(word: str) -> str | None:
    """Return the English stem of a prefixed loanword such as ``direstore`` or ``dideploy``."""
    for prefix in LOANWORD_PREFIXES:
        rest = word[len(prefix):]
        if word.startswith(prefix) and len(rest) >= 4 and rest.isascii():
            return rest
    return None
