"""Satu sumber untuk naskah tutorial dan berkas scene.

Setiap modul (tools/build-NN.py) mendefinisikan daftar scene lalu memanggil `write_module`. Narasi di
tutorial/NN-*.md dan scenes/NN-*.json dibangkitkan dari daftar yang sama sehingga selalu identik, dan
aturan narasi TTS diperiksa sebelum berkas apa pun ditulis.

Scene adalah tuple: (id, tampilan_visual, aksi_di_layar, narasi, aksi_playwright).
"""
import json
import pathlib
import re

PIPELINE = pathlib.Path(__file__).resolve().parents[1]
TUTORIAL_DIR = PIPELINE / "tutorial"
SCENES_DIR = PIPELINE / "scenes"

# Kata per detik narasi Bahasa Indonesia pada TTS_RATE +0% (perkiraan durasi di tabel naskah).
WORDS_PER_SECOND = 2.3
MAX_WORDS_PER_SENTENCE = 20


def button(name: str, exact: bool = False) -> str:
    return f"role=button[name=\"{name}\"{'s' if exact else ''}]"


def button_prefix(name: str) -> str:
    return f"role=button[name^=\"{name}\"]"


def link(name: str) -> str:
    return f"role=link[name=\"{name}\"]"


def option(name: str) -> str:
    return f"role=option[name=\"{name}\"]"


def textbox(name: str) -> str:
    return f"role=textbox[name=\"{name}\"]"


def checkbox(name: str) -> str:
    return f"role=checkbox[name=\"{name}\"]"


def menu_item(name: str, nth: int | None = None) -> dict:
    """Klik item menu. `nth` untuk label yang muncul lebih dari sekali."""
    action = {"type": "click", "selector": f"role=menuitem[name=\"{name}\"]"}
    if nth is not None:
        action["nth"] = nth
    return action


def pick(trigger: str, choice: str) -> list[dict]:
    """Buka dropdown kustom (Radix/shadcn dan sejenisnya) lalu pilih opsinya."""
    return [{"type": "click", "selector": button(trigger)}, {"type": "pause", "ms": 700},
            {"type": "click", "selector": option(choice)}]


def lint(text: str) -> list[str]:
    """Aturan narasi TTS: tanpa digit atau simbol, tanpa emoji, maksimal 20 kata per kalimat."""
    problems = []
    if re.search(r"[0-9/&+()>]", text):
        problems.append("digit atau simbol")
    if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", text):
        problems.append("emoji")
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if len(sentence.split()) > MAX_WORDS_PER_SENTENCE:
            problems.append(f"kalimat lebih dari {MAX_WORDS_PER_SENTENCE} kata: {sentence[:40]}")
    return problems


def write_module(module_id: str, title: str, scenes: list, info: dict, sources: list[str], notes: list[str],
                 extra: dict | None = None) -> None:
    bad = {sid: lint(narr) for sid, _v, _a, narr, _x in scenes if lint(narr)}
    if bad:
        raise SystemExit(f"lint narasi gagal: {bad}")
    ids = [sid for sid, *_ in scenes]
    if len(ids) != len(set(ids)):
        raise SystemExit("id scene ganda")
    if not sources:
        raise SystemExit("SUMBER TEKS UI kosong: kutip file:line untuk setiap label yang dipakai")

    scene_file = {"title": title, **(extra or {}),
                  "scenes": [{"id": sid, "narration": narr, "actions": acts} for sid, _v, _a, narr, acts in scenes]}
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    (SCENES_DIR / f"{module_id}.json").write_text(
        json.dumps(scene_file, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    words = sum(len(narr.split()) for *_x, narr, _acts in scenes)
    rows = "\n".join(
        f"| {i} | {act} | {vis} | {narr} | {max(4, round(len(narr.split()) / WORDS_PER_SECOND))} |"
        for i, (_sid, vis, act, narr, _x) in enumerate(scenes, 1))
    info_lines = "\n".join(f"- **{key}**: {value}" for key, value in info.items())
    md = f"""# {title}

## INFORMASI MODUL
{info_lines}
- **Estimasi Durasi Narasi**: sekitar {max(1, round(words / WORDS_PER_SECOND / 60))} menit ({len(scenes)} scene)

## TABEL NASKAH SCENE & AKSI LAYAR
| No Scene | Aksi di Layar | Tampilan Visual Layar | Naskah Narasi Suara (TTS Bahasa Indonesia) | Durasi (detik) |
| :---: | :--- | :--- | :--- | :---: |
{rows}

## SUMBER TEKS UI (kode adalah sumber kebenaran)
{chr(10).join(f"- {line}" for line in sources)}

## CATATAN PRODUKSI
{chr(10).join(f"- {line}" for line in notes) if notes else "- Tidak ada."}
"""
    TUTORIAL_DIR.mkdir(parents=True, exist_ok=True)
    (TUTORIAL_DIR / f"{module_id}.md").write_text(md, encoding="utf-8")
    print("ok", module_id, len(scenes), "scene")
