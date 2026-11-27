
"""Local BM25 candidate retrieval over installed skill descriptions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path
import re

from skill_lexicon_id import english_term, expand_phrases, loanword_stem


WORD_RE = re.compile(r"[a-z][a-z0-9]*")
STOPWORDS = frozenset("""
    a an and are as at be by can could do does for from has have how i in is it its me my
    need of on only or our should that the their this to use using vs was we when where
    which while with without would you your fix help check review design build create
    ada agar akan apa apakah atau bantu biar bisa buat buatkan dalam dan dari dengan
    di gimana ini itu jadi juga kami karena ke kena kita kok lagi mau minta oleh pada
    pakai perlu sudah supaya sedang sama saja saya setelah sebelum terus tidak tolong
    untuk yang cek bikin perbaiki rancang audit
""".split())
NORMALIZED_TERMS = {
    "aksesibilitas": "accessibility",
    "antrean": "queue",
    "berkas": "file",
    "biaya": "cost",
    "cabang": "branch",
    "cadangan": "backup",
    "duplikasi": "duplicate",
    "galat": "error",
    "indeks": "index",
    "kejadian": "event",
    "ketergantungan": "dependency",
    "kredensial": "credential",
    "kueri": "query",
    "migrasi": "migration",
    "pencadangan": "backup",
    "penerimaan": "acceptance",
    "peramban": "browser",
    "rancangan": "design",
    "riwayat": "history",
    "takarir": "subtitle",
    "tagihan": "bill",
    "tangkapan": "capture",
    "tata": "layout",
    "unggah": "upload",
    "verifikasi": "verification",
}
SHORT_TERMS = frozenset({"ab", "ai", "ci", "db", "dr", "go", "id", "it", "qa", "ui", "ux"})
USAGE_BOUNDARY = re.compile(r"(?:^|\s)(?:do not use|not for|skip for)\b", re.IGNORECASE)
DESCRIPTION_FIELD = re.compile(r"^description:[ \t]*(.*)$", re.MULTILINE)

CLAUSE_BREAK = re.compile(r"(?:[.!?;](?=\s|$)|\n+|\s+(?:but|namun|tetapi)\s+(?=(?:the only|tugas|yang))|\s+(?:and separately|dan secara terpisah)\s+)", re.IGNORECASE)
REQUEST_CLAUSE = re.compile(
    r"^\s*(?:(?:please|tolong|now|next|sekarang|lalu|bantu(?:\s+saya)?)\s+)*(?:(?:we|i)\s+need\s+to\s+)?"
    r"(?:the\s+only\s+change\b|adapt|audit|build|check|choose|compare|configure|create|define|design|draft|evaluate|fix|implement|"
    r"inspect|isolate|launch|measure|model|navigate|open|plan|produce|review|rotate|run|set\s+up|specify|test|verify|write|"
    r"analisis|bandingkan|buat(?:kan)?|buka|gali|jalankan|jelaskan|kaji|perbaiki|periksa|petakan|pilih|siapkan|"
    r"rancang|rumuskan|selidiki|rotasi|susun|tambah|telaah|tentukan|tinjau|tulis|ubah|uji|ukur|verifikasi)\b",
    re.IGNORECASE,
)

ALIASES = {
    "antislop": "ai slop|generic ai interface|generic ai output|template default|tampilan generik|cek slop frontend",
    "antislop-code": "redundant comments|obvious comments|useless comments|code comments|inline comments|komentar kode|komentar mubazir|hapus komentar",
    "antislop-copywriting": "button copy|empty state wording|confirmation wording|error text|button label|ui text|teks tombol|pesan kesalahan|salinan ui|bahasa antarmuka",
    "antislop-human": "focus indicator|keyboard focus|disabled affordance|pointer cursor|interaction state|kontras tombol|indikator fokus|kursor tombol|statis dan interaktif",
    "antislop-layoutmobile": "mobile overflow|responsive grid|responsive layout|tap target|small screen wrap|layar sempit|geser horizontal|melebihi viewport|tata letak ponsel",
    "antislop-ui": "visual polish|spacing rhythm|typographic scale|motion polish|visual balance|spasi komponen|hierarki tipografi|rapikan tampilan|gradasi generik",
    "context7": "current documentation|official docs|version specific|relation filter syntax|reference docs|api syntax|dokumentasi resmi|contoh versi|sintaks terbaru|referensi resmi",
    "handoff": "save handoff|load handoff|same session context|agent huddle|continue previous session|simpan sesi|lanjut sesi coding|simpan konteks|pindah agen",
    "modern-web-guidance": "baseline feature|largest contentful paint|next js bundle|web platform|container query|native modal|native popover|lcp landing page|fitur browser|performa render",
    "shadow-accessibility": "focus order|accessible names|screen reader|assistive technology|accessibility audit|accessible name|wcag conformance|pembaca layar|akses pengguna buta|audit aksesibilitas|pengumuman pembaca layar",
    "shadow-ai-eng": "tool calling|agent runtime|provider fallback|llm gateway|structured output|mcp transport|tool approval|pemanggilan alat|agen llm|antarmuka tool",
    "shadow-analytics": "event tracking|product metric|conversion funnel|sample ratio mismatch|experiment power|pelacakan kejadian|rasio sampel|retensi pengguna|konversi produk",
    "shadow-api": "api contract|rest endpoint|response envelope|file upload|gateway timeout api|kode status api|kontrak api|unggah multipart|endpoint backend",
    "shadow-architect": "single application|architecture decision|module boundaries|context diagram|system topology|satu aplikasi|batas antarmodul|arsitektur layanan|diagram konteks",
    "shadow-auth": "jwt signing keys|rotate jwt|access token|refresh token|sign in|session cookie|multi tenant login|login sso|sesi pengguna|izin tenant|hak akses peran",
    "shadow-bootstrap": "blank repository|new project|initial project|project scaffold|repo kosong|proyek baru|mulai proyek|generator resmi|kerangka awal",
    "shadow-browser": "playwright|live browser|e2e browser|browser console|viewport screenshot|cek browser|alur klik|uji halaman nyata",
    "shadow-cache": "cache keys|shared cache|cache stampede|cache expired|redis returns|redis cache|cache antar tenant|kunci cache|cache basi|hapus cache",
    "shadow-compat": "backward compatibility|breaking upgrade|version upgrade|consumer replay|upgrade react|bump react|migrasi versi|naik versi|kontrak lama|klien lama",
    "shadow-concurrency": "pengakuan pesan|pencegahan duplikasi|message redelivery|distributed queue|concurrent workers|duplicate jobs|dead letter queue|antrean pesan|pesan ganda|pekerjaan dobel|pekerja paralel|retry antrean",
    "shadow-data": "online migration|not null|expand contract|data lineage|column backfill|live backfill|migrasi kolom|jutaan baris|isi ulang kolom|retensi data|jejak asal data",
    "shadow-db": "rencana eksekusi|execution statistics|query plan|why this query|slow query|execution plan|sql planner|explain query|query lambat|indeks gabungan|rencana eksekusi|koneksi database|database terkunci",
    "shadow-debug": "find root cause|reproduce failure|unexpected error|stack trace|intermittent failure|diagnose bug|cari penyebab|galat acak|macet sesekali|reproduksi bug",
    "shadow-design": "wireframe|design tokens|user journey|design system|user flow|alur pengguna|rancangan antarmuka|sistem desain|struktur halaman|sketsa layar",
    "shadow-discovery": "requirements elicitation|interview stakeholders|requirements workshop|acceptance criteria|gali kebutuhan|wawancara pemangku kepentingan|spesifikasi kebutuhan|kebutuhan belum jelas",
    "shadow-doc": "generate docx|regenerate srs|document generator|source document|canonical json|citation check|buat dokumen|regenerasi dokumen|format laporan word|perbarui dokumen",
    "shadow-domain": "domain invariant|business invariant|order state|state machine|aggregate root|business rules|aturan bisnis|transisi status|status batal|konsistensi agregat",
    "shadow-ea": "application portfolio|enterprise architecture|technology roadmap|several systems|capability map|portofolio aplikasi|peta kapabilitas|arsitektur lintas sistem|konsolidasi aplikasi",
    "shadow-email": "otp mail|email spam|spam folder|mail bounced|email deliverability|smtp|email masuk spam|email otp|surat elektronik|pantulan email",
    "shadow-eval": "rag evaluation|grounded answers|hallucination rate|llm judge|evaluate citations|tool trace grading|akurasi jawaban|penilai llm|uji halusinasi|ketepatan kutipan",
    "shadow-finops": "cloud spend|cost allocation|token costs|egress cost|budget alert|biaya cloud|tagihan awan|biaya token|belanja cloud|alokasi biaya",
    "shadow-git": "git worktree|branch drift|merge conflicts|branch divergence|git merge tree|cabang tertinggal|gabung branch|konflik git|sinkron cabang|pemeriksaan cabang",
    "shadow-grc": "governance control|capability assessment|statement of applicability|control evidence|audit maturity|tingkat kapabilitas|bukti kontrol|tata kelola ti|audit kepatuhan",
    "shadow-handover": "client handover|handover package|operator handbook|credential transfer|serah terima|buku operator|pemindahan kredensial|pelatihan pengguna",
    "shadow-illustration": "hero artwork|svg artwork|product mascot|art direction|draw icon|gambar maskot|ilustrasi produk|grafis teknis|ikon aplikasi|ubah png",
    "shadow-integrate": "incoming webhook|payment gateway|payment reconciliation|provider retries|webhook signature|pembayaran ganda|rekonsiliasi transaksi|tanda tangan webhook|status pembayaran|integrasi mitra",
    "shadow-maintain": "production outage|production incident|live outage|incident response|blameless postmortem|layanan produksi down|insiden produksi|gangguan layanan|pemulihan insiden",
    "shadow-mobile": "app signing|privacy manifest|store rejection|itms 91053|mobile release|target sdk|play console|rilis aplikasi android|tanda tangan aplikasi|ditolak app store",
    "shadow-modernize": "legacy modernization|legacy estate|rewrite strategy|technical due diligence|strangler fig|sistem warisan|kode warisan|tulis ulang sistem|modernisasi sistem|pelajari aturan lama",
    "shadow-monarch": "multiple specialists|cross skill|specialist orchestration|one accountable owner|execution approval boundaries|koordinasi spesialis|lintas skill|pemilik utama|batas persetujuan",
    "shadow-observe": "error budget|service level objective|distributed tracing|structured logs|latency alert|anggaran error|latensi layanan|metrik observabilitas|jejak permintaan|log terstruktur",
    "shadow-ops": "container deployment|reverse proxy|docker compose|ci pipeline|nginx config|sertifikat tls|konfigurasi server|konfigurasi kontainer|pipa ci|rute proxy",
    "shadow-perf": "pre uat|stress test|soak test|load testing|performance benchmark|uji beban|tolok ukur latensi|profil kinerja",
    "shadow-plan": "sprint backlog|delivery backlog|split requirements|backlog items|story points|pecah kebutuhan|turunkan kebutuhan|susun backlog|rencana sprint|cerita pengguna",
    "shadow-pmo": "change request|contract scope|earned value|paid change|schedule risk|permintaan perubahan|lingkup kontrak|defek kontrak|proyeksi jadwal|jadwal proyek",
    "shadow-presales": "bid no bid|tender estimate|bill of quantities|pre sales|estimasi tender|harga penawaran|rincian biaya penawaran|kebutuhan tender",
    "shadow-privacy": "personal data|data minimization|subject access|right to erasure|data breach|hapus data pribadi|hak subjek data|pelindungan data|kebocoran data|persetujuan pengguna",
    "shadow-quality": "lint gate|quality gate|convention drift|static analysis|code review|quality check|kompleksitas kode|konvensi repo|gerbang mutu|cek lint",
    "shadow-realtime": "live presence|client resumption|slow consumer|event stream|server sent events|sinkron langsung|koneksi putus|pesan langsung|status online|aliran kejadian",
    "shadow-refactor": "preserve behavior|characterization tests|behavior preserving|extract seam|incremental refactor|rapikan kode|tanpa ubah perilaku|perilaku tetap|ekstrak helper|rapikan modul",
    "shadow-release": "release checklist|canary rollout|release version|rollback plan|rollout strategy|rencana rilis|rilis produksi|skenario rollback|strategi peluncuran|versi mayor",
    "shadow-resilience": "restore drill|recovery point|recovery time|backup restore|fault injection drill|uji pemulihan|simulasi bencana|pulihkan cadangan|waktu pemulihan|latihan dr",
    "shadow-search": "search relevance|search ranking|query recall|hybrid retrieval|index shards|peringkat pencarian|relevansi pencarian|hasil pencarian|pencarian bahasa indonesia|indeks pencarian",
    "shadow-sec": "application security|threat model|appsec audit|third party skill|pre install review|model ancaman|audit keamanan|tinjau sebelum instalasi|pemeriksaan rahasia",
    "shadow-seo": "search engine indexing|structured data|search console|crawl budget|technical seo|kemampuan indeks|indeks mesin pencari|pengindeksan google|perayapan situs",
    "shadow-supplychain": "software supply chain|lockfile audit|build provenance|dependency pinning|rantai pasok perangkat lunak|bukti asal build|asal artefak|ketergantungan transitif",
    "shadow-test": "unit test|integration test|regression tests|assertions|test fixtures|tes unit|uji unit|tes integrasi|uji regresi|uji kontrak|pengujian otomatis",
    "shadow-uat": "user acceptance testing|uat signoff|staging sign off|requirement traceability|uji penerimaan|penerimaan pengguna|tanda tangan uat|skenario uat|matriks ketertelusuran",
    "shadow-video": "video walkthrough|tutorial video|screen capture|narrated tutorial|video panduan|rekam layar|narasi video|rekaman demo|teks subtitle",
}


def read_description(skill_md: Path) -> str | None:
    """Read this catalog's single-line frontmatter description."""
    try:
        text = skill_md.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None
    if not text.startswith("---\n"):
        return None
    frontmatter, end, _ = text[4:].partition("\n---\n")
    match = DESCRIPTION_FIELD.search(frontmatter) if end else None
    if not match:
        return None
    value = match[1].strip()
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, str) else None
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def _normalized_words(text: str, translate: bool = False) -> list[str]:
    """Tokenize and normalize text; ``translate`` maps Indonesian terms onto English ones."""
    words: list[str] = []
    folded = expand_phrases(text.casefold()) if translate else text.casefold()
    for word in WORD_RE.findall(folded):
        if word in NORMALIZED_TERMS:
            words.append(NORMALIZED_TERMS[word])
            continue
        translated = english_term(word) if translate else None
        if translated is not None:
            words.extend(translated.split())
            continue
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "ps", "us")):
            word = word[:-1]
        words.append(NORMALIZED_TERMS.get(word, word))
        stem = loanword_stem(word) if translate else None
        if stem is not None:
            words.append(stem)
    return words


def _keywords(words: list[str], digit_terms: bool = False) -> list[str]:
    """Drop stopwords and short tokens; ``digit_terms`` keeps specific ones such as c4, k6 or s3."""
    return [
        word for word in words
        if word not in STOPWORDS and (
            len(word) >= 3 or word in SHORT_TERMS or (digit_terms and len(word) == 2 and word[1].isdigit())
        )
    ]


def _reference_topics(skill_md: Path) -> str:
    try:
        text = skill_md.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return ""
    guide = text.partition("\n## Reference Guide")[2]
    table = guide.partition("\n## ")[0]
    topics = []
    for line in table.splitlines():
        columns = line.strip().strip("|").split("|")
        if len(columns) < 2 or not line.startswith("|") or "references/" not in line:
            continue
        for cell in columns:
            if cell and "](" not in cell:
                topics.append(USAGE_BOUNDARY.split(cell, maxsplit=1)[0])
    return " ".join(topics)


@dataclass(frozen=True)
class Candidate:
    skill: str
    score: float
    terms: int
    rare_terms: int
    phrases: int
    requested_terms: int = 0
    requested_phrases: int = 0


@dataclass(frozen=True)
class SkillIndex:
    documents: dict[str, Counter[str]]
    topics: dict[str, set[str]]
    topic_frequencies: Counter[str]
    phrase_patterns: dict[str, tuple[str, ...]]
    frequencies: Counter[str]
    average_size: float
    translate: bool = False


@lru_cache(maxsize=8)
def skill_index(root: Path, skills: tuple[str, ...], translate: bool = False) -> SkillIndex:
    documents: dict[str, Counter[str]] = {}
    topics: dict[str, set[str]] = {}
    phrase_patterns: dict[str, tuple[str, ...]] = {}
    for skill in skills:
        skill_file = root / skill / "SKILL.md"
        description = read_description(skill_file)
        if not description:
            continue
        positive_text = USAGE_BOUNDARY.split(description, maxsplit=1)[0]
        aliases = ALIASES.get(skill, "")
        phrases = tuple(
            " " + " ".join(_normalized_words(alias, translate)) + " " for alias in aliases.split("|") if alias
        )
        phrase_patterns[skill] = phrases
        documents[skill] = Counter(_keywords(_normalized_words(positive_text + " " + aliases, translate), translate))
        topics[skill] = set(_keywords(_normalized_words(_reference_topics(skill_file), translate), translate))
    frequencies: Counter[str] = Counter(word for document in documents.values() for word in document)
    average_size = sum(sum(doc.values()) for doc in documents.values()) / max(1, len(documents))
    topic_frequencies: Counter[str] = Counter(word for topic in topics.values() for word in topic)
    return SkillIndex(documents, topics, topic_frequencies, phrase_patterns, frequencies, average_size, translate)


def request_clauses(prompt: str) -> list[str]:
    return [clause.strip() for clause in CLAUSE_BREAK.split(prompt) if REQUEST_CLAUSE.match(clause)]


def retrieve(prompt: str, index: SkillIndex) -> list[Candidate]:
    """Rank candidate owners with BM25 and separate exact domain-phrase evidence."""
    words = _normalized_words(prompt, index.translate)
    query = set(_keywords(words, index.translate))
    phrase_query = " " + " ".join(words) + " "
    requests = []
    for clause in request_clauses(prompt):
        clause_words = _normalized_words(clause, index.translate)
        requests.append((set(_keywords(clause_words, index.translate)), " " + " ".join(clause_words) + " "))

    ranked: list[Candidate] = []
    size = len(index.documents)
    if not query or not index.average_size:
        return ranked

    for skill, document in index.documents.items():
        matched = query & document.keys()
        topic_matches = (query & index.topics[skill]) - matched
        specific_topics = {term for term in topic_matches if index.topic_frequencies[term] <= 5}
        if not matched and len(specific_topics) < 2:
            continue
        phrases = sum(phrase in phrase_query for phrase in index.phrase_patterns[skill])
        normalization = 1.2 * (0.25 + 0.75 * sum(document.values()) / index.average_size)
        score = sum(
            math.log1p((size - index.frequencies[word] + 0.5) / (index.frequencies[word] + 0.5))
            * (2.2 * document[word] / (document[word] + normalization))
            for word in sorted(matched)
        )
        topic_score = sum(
            math.log1p((size - index.topic_frequencies[word] + 0.5) / (index.topic_frequencies[word] + 0.5))
            for word in sorted(specific_topics)
        )
        specific_terms = {word for word in matched if index.frequencies[word] <= 4}
        requested_phrases, requested_terms = max(
            (
                (sum(pattern in clause for pattern in index.phrase_patterns[skill]), len(specific_terms & terms))
                for terms, clause in requests
            ),
            default=(0, 0),
        )
        request_bonus = min(requested_terms, 4) * 0.55 + requested_phrases * 1.25
        ranked.append(Candidate(
            skill, score + 2.0 * phrases + 0.4 * topic_score + request_bonus,
            len(matched) + len(specific_topics), len(specific_terms) + len(specific_topics),
            phrases, requested_terms, requested_phrases,
        ))
    return sorted(ranked, key=lambda match: (-match.score, match.skill))


CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)


@dataclass(frozen=True)
class BodyIndex:
    documents: dict[str, Counter[str]]
    frequencies: Counter[str]
    average_size: float


@lru_cache(maxsize=8)
def body_index(root: Path, skills: tuple[str, ...]) -> BodyIndex:
    """Index each skill's full SKILL.md text plus its reference module titles."""
    documents: dict[str, Counter[str]] = {}
    for skill in skills:
        skill_file = root / skill / "SKILL.md"
        try:
            text = CODE_FENCE.sub(" ", skill_file.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError):
            continue
        references = root / skill / "references"
        titles = " ".join(
            re.sub(r"[-_]", " ", path.stem) for path in sorted(references.glob("*.md"))
        ) if references.is_dir() else ""
        documents[skill] = Counter(_keywords(_normalized_words(text + " " + titles, translate=True), digit_terms=True))
    frequencies: Counter[str] = Counter(word for document in documents.values() for word in document)
    average_size = sum(sum(doc.values()) for doc in documents.values()) / max(1, len(documents))
    return BodyIndex(documents, frequencies, average_size)


def retrieve_body(prompt: str, index: BodyIndex) -> list[tuple[str, float]]:
    """Rank skills by BM25 over their full instructions; returns (skill, score) best first."""
    query = set(_keywords(_normalized_words(prompt, translate=True), digit_terms=True))
    size = len(index.documents)
    ranked: list[tuple[str, float]] = []
    if not query or not index.average_size:
        return ranked
    for skill, document in index.documents.items():
        matched = query & document.keys()
        if not matched:
            continue
        normalization = 1.2 * (0.25 + 0.75 * sum(document.values()) / index.average_size)
        score = sum(
            math.log1p((size - index.frequencies[word] + 0.5) / (index.frequencies[word] + 0.5))
            * (2.2 * document[word] / (document[word] + normalization))
            for word in sorted(matched)
        )
        ranked.append((skill, score))
    return sorted(ranked, key=lambda item: (-item[1], item[0]))
