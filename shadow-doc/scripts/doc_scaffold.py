#!/usr/bin/env python3
"""Shadow Doc Pipeline Utility (Hybrid .md <-> .json AST + Readiness Validator + DOCX/XLSX Builder).

Inspired by D:\\Pekerjaan-Sistem-Analis\\Laporan\\Laporan-Generator.
All file operations enforce explicit UTF-8 encoding on Windows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

POLA_DAFTAR = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
POLA_ANGKA_BERSATUAN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:%|persen|ms|detik|menit|jam|hari|bulan|tahun|KB|MB|GB|TB|req/s|RPS|baris|halaman|rupiah|Rp)\b",
    re.IGNORECASE,
)
AKHIR_KALIMAT_VALID = (".", "!", "?", ":", ";", ")", '"', "'", "”")


def _sebaris(teks: str) -> str:
    teks = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", teks)
    return re.sub(r"\s+", " ", teks).strip()


def md_to_json_ast(md_path: Path, jenis: str, judul: str) -> dict[str, Any]:
    """Convert a Markdown document (.md) into the canonical Shadow-Doc JSON AST."""
    sumber_default = f"Dokumen sumber '{md_path.name}'"
    baris = md_path.read_text(encoding="utf-8").splitlines()

    bagian: list[dict[str, Any]] = []
    judul_aktif = judul
    target: list[dict[str, Any]] | None = None
    paragraf: list[str] = []

    def bersumber(blok: dict[str, Any], teks_uji: str) -> dict[str, Any]:
        polos_uji = re.sub(r"[*`]", "", teks_uji)
        if POLA_ANGKA_BERSATUAN.search(polos_uji) and "sumber" not in blok:
            blok["sumber"] = sumber_default
        return blok

    def tutup_paragraf() -> None:
        nonlocal paragraf, target
        if paragraf and target is not None:
            teks = _sebaris(" ".join(paragraf))
            if teks:
                target.append(bersumber({"paragraf": teks}, teks))
        paragraf = []

    i = 0
    while i < len(baris):
        b = baris[i]
        polos = b.strip()

        if re.match(r"^#\s+", b) and not bagian:
            judul_h1 = re.sub(r"^#\s+", "", b).strip()
            if judul == "Dokumen Teknis":
                judul = judul_h1
            i += 1
            continue

        if re.match(r"^##\s+", b):
            tutup_paragraf()
            judul_aktif = re.sub(r"^##\s+[\d.]*\s*", "", b).strip()
            bagian.append({"judul": judul_aktif, "blok": [], "subbagian": []})
            target = bagian[-1]["blok"]
        elif re.match(r"^###\s+", b):
            tutup_paragraf()
            if not bagian:
                bagian.append({"judul": "Pendahuluan", "blok": [], "subbagian": []})
            judul_aktif = re.sub(r"^###\s+[\d.]*\s*", "", b).strip()
            bagian[-1]["subbagian"].append({"judul": judul_aktif, "blok": []})
            target = bagian[-1]["subbagian"][-1]["blok"]
        elif re.match(r"^####\s+", b):
            tutup_paragraf()
            if not bagian:
                bagian.append({"judul": "Pendahuluan", "blok": [], "subbagian": []})
            judul_aktif = re.sub(r"^####\s+[\d.]*\s*", "", b).strip()
            induk = (
                bagian[-1]["subbagian"][-1]["blok"]
                if bagian[-1]["subbagian"]
                else bagian[-1]["blok"]
            )
            induk.append({"subbab": {"judul": judul_aktif, "blok": []}})
            target = induk[-1]["subbab"]["blok"]
        elif polos.startswith("```"):
            tutup_paragraf()
            if target is None:
                bagian.append({"judul": "Pendahuluan", "blok": [], "subbagian": []})
                target = bagian[-1]["blok"]
            bahasa = polos[3:].strip()
            isi_kode: list[str] = []
            i += 1
            while i < len(baris) and not baris[i].strip().startswith("```"):
                isi_kode.append(baris[i])
                i += 1
            lekuk = min((len(x) - len(x.lstrip()) for x in isi_kode if x.strip()), default=0)
            isi_kode = [x[lekuk:] for x in isi_kode]
            if bahasa.lower() == "mermaid":
                target.append(
                    {
                        "diagram": {
                            "mermaid": "\n".join(isi_kode),
                            "keterangan": f"Diagram {judul_aktif}",
                        }
                    }
                )
            else:
                target.append({"kode": {"bahasa": bahasa or "text", "isi": "\n".join(isi_kode)}})
        elif polos.startswith("|"):
            tutup_paragraf()
            if target is None:
                bagian.append({"judul": "Pendahuluan", "blok": [], "subbagian": []})
                target = bagian[-1]["blok"]
            tabel: list[list[str]] = []
            while i < len(baris) and baris[i].strip().startswith("|"):
                tabel.append([_sebaris(c) for c in baris[i].strip().strip("|").split("|")])
                i += 1
            i -= 1
            if len(tabel) >= 2:
                kepala = tabel[0]
                isi_baris = [
                    r
                    for idx, r in enumerate(tabel[1:], start=1)
                    if idx != 1 or not all(re.match(r"^:?-{2,}:?$", c) for c in r)
                ]
                isi_baris = [r for r in isi_baris if len(r) == len(kepala)]
                kolom = []
                for k, j in enumerate(kepala):
                    panjang = max([len(j)] + [len(r[k]) for r in isi_baris]) if isi_baris else len(j)
                    pendek = bool(isi_baris) and all(len(r[k]) <= 10 for r in isi_baris)
                    kolom.append(
                        {
                            "judul": j.replace("**", "").strip() or "-",
                            "lebar": min(max(panjang, 4), 40),
                            "rata": "tengah" if pendek else "kiri",
                        }
                    )
                baris_bersih = [[c if c else "-" for c in r] for r in isi_baris]
                blok_tabel: dict[str, Any] = {
                    "tabel": {
                        "keterangan": f"Tabel {judul_aktif}",
                        "kolom": kolom,
                        "baris": baris_bersih,
                    }
                }
                target.append(
                    bersumber(blok_tabel, json.dumps(baris_bersih, ensure_ascii=False))
                )
        elif POLA_DAFTAR.match(b):
            tutup_paragraf()
            if target is None:
                bagian.append({"judul": "Pendahuluan", "blok": [], "subbagian": []})
                target = bagian[-1]["blok"]
            m = POLA_DAFTAR.match(b)
            assert m is not None
            tingkat = 1 if len(m.group(1)) < 4 else 2
            teks = _sebaris(m.group(3))
            mj = re.match(r"^\*\*(.+?)\*\*:?\s*(.*)$", teks)
            item: Any = (
                {"judul": mj.group(1).rstrip(":"), "uraian": mj.group(2)}
                if mj and mj.group(2)
                else teks
            )
            if target and "daftar" in target[-1] and target[-1].get("tingkat", 1) == tingkat:
                target[-1]["daftar"].append(item)
            else:
                blok_daftar: dict[str, Any] = {"daftar": [item]}
                if tingkat > 1:
                    blok_daftar["tingkat"] = tingkat
                target.append(blok_daftar)
        elif polos in ("---", "") or polos.startswith("<"):
            tutup_paragraf()
        else:
            if target is None:
                bagian.append({"judul": "Pendahuluan", "blok": [], "subbagian": []})
                target = bagian[-1]["blok"]
            paragraf.append(polos)
        i += 1

    tutup_paragraf()
    for bg in bagian:
        if not bg.get("subbagian"):
            bg.pop("subbagian", None)
        if not bg.get("blok"):
            bg.pop("blok", None)

    return {
        "jenis": jenis,
        "judul": judul,
        "metadata": {
            "sumber_berkas": md_path.name,
            "istilah_terlarang": [],
        },
        "bagian": bagian,
    }


def check_readiness(doc: dict[str, Any], base_dir: Path) -> tuple[list[str], list[str]]:
    """Validate canonical JSON AST for errors (galat) and warnings (peringatan)."""
    galat: list[str] = []
    peringatan: list[str] = []

    if not doc.get("judul"):
        galat.append("Ruas 'judul' dokumen kosong.")
    bagian = doc.get("bagian", [])
    kasus_uji = doc.get("kasus_uji", [])
    if not bagian and not kasus_uji:
        galat.append("Dokumen tidak memiliki 'bagian' maupun 'kasus_uji'.")

    terlarang = [
        t.lower()
        for t in doc.get("metadata", {}).get("istilah_terlarang", [])
        if isinstance(t, str) and t.strip()
    ]

    def periksa_teks(teks: str, lokasi: str, punya_sumber: bool) -> None:
        if not teks.strip():
            galat.append(f"{lokasi}: teks kosong.")
            return
        rendah = teks.lower()
        for istilah in terlarang:
            if istilah in rendah:
                galat.append(
                    f"{lokasi}: ditemukan istilah terlarang lintas-klien/internal '{istilah}'."
                )
        if POLA_ANGKA_BERSATUAN.search(teks) and not punya_sumber:
            peringatan.append(
                f"{lokasi}: memuat angka bersatuan tanpa atribusi 'sumber' eksplisit."
            )

    def periksa_blok_list(blok_list: list[dict[str, Any]], konteks: str) -> None:
        for idx, b in enumerate(blok_list, start=1):
            lok = f"{konteks} > blok[{idx}]"
            punya_sumber = bool(b.get("sumber"))
            if "paragraf" in b:
                p = str(b["paragraf"]).strip()
                periksa_teks(p, lok, punya_sumber)
                if p and not p.endswith(AKHIR_KALIMAT_VALID):
                    galat.append(
                        f"{lok}: kalimat paragraf diduga terpotong (tidak diakhiri tanda baca titik/valid): '...{p[-25:]}'"
                    )
            elif "tabel" in b:
                tbl = b["tabel"]
                kolom = tbl.get("kolom", [])
                baris = tbl.get("baris", [])
                if not kolom:
                    galat.append(f"{lok}: tabel tidak memiliki definisi kolom.")
                for r_idx, r in enumerate(baris, start=1):
                    if len(r) != len(kolom):
                        galat.append(
                            f"{lok}: baris tabel ke-{r_idx} memiliki {len(r)} sel, seharusnya {len(kolom)}."
                        )
            elif "bukti" in b:
                for b_item in b["bukti"]:
                    berkas = b_item.get("berkas", "")
                    if berkas and not (base_dir / berkas).exists():
                        peringatan.append(
                            f"{lok}: berkas gambar bukti '{berkas}' belum ditemukan di '{base_dir}'."
                        )
            elif "subbab" in b:
                sub = b["subbab"]
                periksa_blok_list(sub.get("blok", []), f"{lok} ({sub.get('judul', 'Subbab')})")

    for bg in bagian:
        j_bg = bg.get("judul", "Tanpa Judul")
        periksa_blok_list(bg.get("blok", []), f"Bagian '{j_bg}'")
        for sub in bg.get("subbagian", []):
            j_sub = sub.get("judul", "Tanpa Judul")
            periksa_blok_list(sub.get("blok", []), f"Bagian '{j_bg}' > '{j_sub}'")

    return galat, peringatan


def run_selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        sample_md = tmp_dir / "sample_spec.md"
        sample_md.write_text(
            "# Spesifikasi Teknis Layanan\n\n"
            "## 1. Pendahuluan\n\n"
            "Sistem dirancang untuk melayani 500 req/s dengan ketersediaan 99,9%.\n\n"
            "### 1.1 Komponen Utama\n\n"
            "- **API Gateway**: Mengelola autentikasi dan pembatasan laju.\n"
            "- **Worker Antrean**: Memproses pengiriman laporan asinkron.\n\n"
            "| Kode | Komponen | Target |\n"
            "| --- | --- | --- |\n"
            "| C-01 | Gateway | 99,9% |\n"
            "| C-02 | Worker | 99,5% |\n\n"
            "```mermaid\n"
            "flowchart LR\n"
            "  A[\"Client\"] --> B[\"API Gateway\"]\n"
            "```\n",
            encoding="utf-8",
        )
        ast_data = md_to_json_ast(sample_md, "dokteknis", "Dokumen Teknis")
        galat, peringatan = check_readiness(ast_data, tmp_dir)
        assert len(galat) == 0, f"Expected 0 galat, got: {galat}"
        assert len(ast_data["bagian"]) == 1, "Expected 1 bagian"
        out_json = tmp_dir / "naskah.json"
        out_json.write_text(json.dumps(ast_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "SELFTEST_OK",
                    "sections": len(ast_data["bagian"]),
                    "galat": len(galat),
                    "peringatan": len(peringatan),
                }
            )
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Doc Hybrid JSON/MD Pipeline")
    parser.add_argument("--selftest", action="store_true", help="Run self-test")
    sub = parser.add_subparsers(dest="cmd")

    p_m2j = sub.add_parser("md-to-json", help="Convert .md file to canonical .json AST")
    p_m2j.add_argument("--input", required=True, help="Input .md file path")
    p_m2j.add_argument("--output", required=True, help="Output .json file path")
    p_m2j.add_argument("--jenis", default="dokteknis", help="Document type")
    p_m2j.add_argument("--judul", default="Dokumen Teknis", help="Document title")

    p_chk = sub.add_parser("check-readiness", help="Validate canonical .json before rendering")
    p_chk.add_argument("--input", required=True, help="Input .json file path")

    args = parser.parse_args()
    if args.selftest:
        return run_selftest()

    if args.cmd == "md-to-json":
        in_path = Path(args.input).resolve()
        out_path = Path(args.output).resolve()
        ast_data = md_to_json_ast(in_path, args.jenis, args.judul)
        galat, peringatan = check_readiness(ast_data, in_path.parent)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(ast_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "CONVERTED",
                    "output": str(out_path),
                    "galat": galat,
                    "peringatan": peringatan,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if galat else 0

    if args.cmd == "check-readiness":
        in_path = Path(args.input).resolve()
        doc = json.loads(in_path.read_text(encoding="utf-8"))
        galat, peringatan = check_readiness(doc, in_path.parent)
        print(
            json.dumps(
                {
                    "status": "READY" if not galat else "BLOCKED_BY_GALAT",
                    "galatCount": len(galat),
                    "peringatanCount": len(peringatan),
                    "galat": galat,
                    "peringatan": peringatan,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if galat else 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
