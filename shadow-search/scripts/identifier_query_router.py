"""Split a search query into exact identifiers and free text for hybrid retrieval.

Product codes (``INV-8841-ID``, ``SKU123``) and Indonesian legal citations (``PP 27/2022``,
``Pasal 56``) go to an exact ``term`` clause on a normalized keyword field; the remaining text
goes to the analyzed BM25 + vector branch.

Usage:
    python identifier_query_router.py "cari INV-8841-ID dan PP-27/2022"
    python identifier_query_router.py --self-test
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import sys
import unicodedata

CODE_RE = re.compile(
    r"\b(?=[A-Za-z0-9/-]*\d)(?=[A-Za-z0-9/-]*[A-Za-z])[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+\b"
    r"|\b[A-Z]{2,}\d+[A-Z0-9]*\b"
)
CITATION_RE = re.compile(
    r"(?i)\b(?:uu|pp|perpres|permen\w*|perda|pojk|pasal|ayat)\s*(?:no\.?\s*)?\d+(?:\s*/\s*\d{4})?\b"
)
SEPARATORS_RE = re.compile(r"[^0-9a-z]")
NUMBER_LABEL_RE = re.compile(r"no\.?(?=\d)")


@dataclass(frozen=True)
class RoutedQuery:
    identifiers: tuple[str, ...]
    normalized: tuple[str, ...]
    text: str


def normalize_identifier(raw: str) -> str:
    """Match the index-side ``code_normalizer``: fold accents, lowercase, drop separators."""
    folded = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii").lower()
    return SEPARATORS_RE.sub("", NUMBER_LABEL_RE.sub("", folded.replace(" ", "")))


def route_query(query: str) -> RoutedQuery:
    spans: list[tuple[int, int]] = []
    for pattern in (CITATION_RE, CODE_RE):
        for match in pattern.finditer(query):
            if not any(start < match.end() and match.start() < end for start, end in spans):
                spans.append((match.start(), match.end()))
    spans.sort()
    identifiers = tuple(query[start:end] for start, end in spans)
    remainder = query
    for start, end in reversed(spans):
        remainder = remainder[:start] + " " + remainder[end:]
    normalized = tuple(dict.fromkeys(normalize_identifier(value) for value in identifiers))
    return RoutedQuery(identifiers, normalized, " ".join(remainder.split()))


RECALL_PROBES: dict[str, tuple[str, ...]] = {
    "PP-27/2022": ("pp272022",),
    "pp 27/2022": ("pp272022",),
    "INV-8841-ID": ("inv8841id",),
    "Perpres 46/2025": ("perpres462025",),
    "SKU123": ("sku123",),
    "Pasal 56": ("pasal56",),
    "UU No. 27/2022": ("uu272022",),
    "POJK 11/2022": ("pojk112022",),
    "cari INV-8841-ID warna merah": ("inv8841id",),
}
PRECISION_PROBES = (
    "peraturan pemerintah", "tahun 2022", "pajak penghasilan", "2022",
    "tanggal 12/05", "ukuran 3 kg", "halaman 2", "tidak ada stok",
)


def self_test() -> list[str]:
    failures: list[str] = []
    for query, expected in RECALL_PROBES.items():
        got = route_query(query).normalized
        if got != expected:
            failures.append(f"recall {query!r}: expected {expected}, got {got}")
    for query in PRECISION_PROBES:
        got = route_query(query)
        if got.identifiers or got.text != query:
            failures.append(f"precision {query!r}: unexpected {got.identifiers}")
    mixed = route_query("cari INV-8841-ID warna merah")
    if mixed.text != "cari warna merah":
        failures.append(f"remainder: got {mixed.text!r}")
    return failures


def main(argv: list[str]) -> int:
    if argv[:1] == ["--self-test"]:
        failures = self_test()
        total = len(RECALL_PROBES) + len(PRECISION_PROBES) + 1
        print(json.dumps({"passed": total - len(failures), "failed": len(failures), "failures": failures}, indent=2))
        return 1 if failures else 0
    if len(argv) != 1:
        print(__doc__)
        return 2
    routed = route_query(argv[0])
    print(json.dumps({"identifiers": routed.identifiers, "normalized": routed.normalized, "text": routed.text}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
