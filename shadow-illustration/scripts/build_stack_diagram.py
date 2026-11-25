#!/usr/bin/env python3
"""Offline engineering-drawing stack & architecture diagram builder (HTML + standalone SVG).

Zero external dependencies (Python stdlib only), zero network access, zero subprocesses.
Features:
- Architectural drafting-paper canvas with subtle dot-grid, light/dark themes, legend, and footer.
- 26+ built-in color tech/cloud marks + 18 monochrome infra glyphs + deterministic monogram fallback.
- Crisp white/dark/bare icon tiles with soft elevation and nested vendor-tinted group boxes.
- Obstacle-aware rounded orthogonal edge routing with explicit port anchors and haloed edge labels.
- Strict HTML/XSS escaping, canonical local SVG containment, and active SVG content rejection.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any


TILE_SIZE = 56
NODE_W = 128
NODE_H = 104
SAFE_ICON_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
UNSAFE_SVG_RE = re.compile(
    r"(?i)(<\s*script\b|<\s*foreignObject\b|<\s*iframe\b|<\s*object\b|<\s*embed\b|"
    r"\bon[a-z]+\s*=|javascript\s*:|vbscript\s*:|<!ENTITY|<!DOCTYPE|"
    r"(?:xlink:)?href\s*=\s*['\"]?\s*https?://|src\s*=\s*['\"]?\s*https?://|"
    r"url\s*\(\s*['\"]?\s*https?://|@import\b)"
)

OKABE_ITO = ("#0072B2", "#009E73", "#D55E00", "#CC79A7", "#E69F00", "#56B4E9")

# Clean 24x24 currentColor offline infra glyphs
BUILTIN_ICONS: dict[str, str] = {
    "server": '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><circle cx="7" cy="7" r="1"/><circle cx="7" cy="17" r="1"/>',
    "api": '<path d="M4 8h16M4 16h16M8 4v16M16 4v16"/><circle cx="12" cy="12" r="2.5"/>',
    "database": '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v13c0 1.38 3.36 2.5 7.5 2.5s7.5-1.12 7.5-2.5v-13"/><path d="M4.5 12c0 1.38 3.36 2.5 7.5 2.5s7.5-1.12 7.5-2.5"/>',
    "cache": '<path d="M13 2 4.5 13h6.5l-1 9L19.5 11H13l0-9z"/>',
    "queue": '<rect x="3" y="6" width="4" height="12" rx="1"/><rect x="10" y="6" width="4" height="12" rx="1"/><rect x="17" y="6" width="4" height="12" rx="1"/>',
    "worker": '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
    "browser": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><circle cx="6.5" cy="6.5" r="0.7"/><circle cx="9.5" cy="6.5" r="0.7"/>',
    "mobile": '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18h2"/>',
    "user": '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a13 13 0 0 1 0 18M12 3a13 13 0 0 0 0 18"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .8-7.9A5.5 5.5 0 0 0 7.2 8.5 3.8 3.8 0 0 0 7 18z"/>',
    "shield": '<path d="M12 3 5 6v5.5c0 4.6 3 8 7 9.5 4-1.5 7-4.9 7-9.5V6l-7-3z"/><path d="m9 12 2 2 4-4"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "storage": '<path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
    "container": '<rect x="3" y="6" width="18" height="12" rx="1.5"/><path d="M7.5 6v12M12 6v12M16.5 6v12"/>',
    "ai": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
}

# Built-in offline color tech & cloud marks (32x32 viewBox, zero network fetches)
BRAND_MARKS: dict[str, str] = {
    "postgres": '<rect x="3" y="4" width="26" height="24" rx="6" fill="#336791"/><ellipse cx="16" cy="11" rx="7" ry="2.6" fill="none" stroke="#FFFFFF" stroke-width="2"/><path d="M9 11v10c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V11" fill="none" stroke="#FFFFFF" stroke-width="2"/><path d="M9 16c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6" fill="none" stroke="#93C5FD" stroke-width="1.6"/>',
    "postgresql": '<rect x="3" y="4" width="26" height="24" rx="6" fill="#336791"/><ellipse cx="16" cy="11" rx="7" ry="2.6" fill="none" stroke="#FFFFFF" stroke-width="2"/><path d="M9 11v10c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V11" fill="none" stroke="#FFFFFF" stroke-width="2"/><path d="M9 16c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6" fill="none" stroke="#93C5FD" stroke-width="1.6"/>',
    "redis": '<polygon points="16,4 28,10 16,16 4,10" fill="#DC382D"/><polygon points="16,12 28,18 16,24 4,18" fill="#B91C1C" opacity="0.9"/><polygon points="16,18 28,24 16,29 4,24" fill="#991B1B" opacity="0.85"/><circle cx="16" cy="10" r="2.2" fill="#FFFFFF"/>',
    "docker": '<rect x="5" y="15" width="22" height="9" rx="3" fill="#0DB7ED"/><rect x="8" y="10" width="4" height="4" rx="0.6" fill="#2496ED"/><rect x="13" y="10" width="4" height="4" rx="0.6" fill="#2496ED"/><rect x="18" y="10" width="4" height="4" rx="0.6" fill="#2496ED"/><rect x="13" y="5" width="4" height="4" rx="0.6" fill="#38BDF8"/><circle cx="22.5" cy="19.5" r="1.3" fill="#FFFFFF"/>',
    "kubernetes": '<polygon points="16,3 27,9.5 27,22.5 16,29 5,22.5 5,9.5" fill="#326CE5"/><circle cx="16" cy="16" r="4" fill="none" stroke="#FFFFFF" stroke-width="2"/><path d="M16 7v5M16 20v5M8.5 11.5l4.2 2.4M19.3 18.1l4.2 2.4M23.5 11.5l-4.2 2.4M12.7 18.1l-4.2 2.4" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round"/>',
    "k8s": '<polygon points="16,3 27,9.5 27,22.5 16,29 5,22.5 5,9.5" fill="#326CE5"/><circle cx="16" cy="16" r="4" fill="none" stroke="#FFFFFF" stroke-width="2"/><path d="M16 7v5M16 20v5M8.5 11.5l4.2 2.4M19.3 18.1l4.2 2.4M23.5 11.5l-4.2 2.4M12.7 18.1l-4.2 2.4" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round"/>',
    "react": '<circle cx="16" cy="16" r="2.7" fill="#0EA5E9"/><ellipse cx="16" cy="16" rx="12" ry="4.6" fill="none" stroke="#0EA5E9" stroke-width="1.8"/><ellipse cx="16" cy="16" rx="12" ry="4.6" fill="none" stroke="#0EA5E9" stroke-width="1.8" transform="rotate(60 16 16)"/><ellipse cx="16" cy="16" rx="12" ry="4.6" fill="none" stroke="#0EA5E9" stroke-width="1.8" transform="rotate(120 16 16)"/>',
    "nextjs": '<circle cx="16" cy="16" r="13" fill="#0F172A"/><path d="M11 22V10l11 13" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="M21 10v7" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round"/>',
    "typescript": '<rect x="3" y="3" width="26" height="26" rx="5" fill="#3178C6"/><text x="16" y="22" text-anchor="middle" font-family="system-ui,Segoe UI,sans-serif" font-size="13" font-weight="800" fill="#FFFFFF">TS</text>',
    "node": '<polygon points="16,3 27,9.5 27,22.5 16,29 5,22.5 5,9.5" fill="#339933"/><text x="16" y="20" text-anchor="middle" font-family="ui-monospace,Consolas,monospace" font-size="10.5" font-weight="800" fill="#FFFFFF">JS</text>',
    "python": '<rect x="5" y="5" width="14" height="14" rx="4" fill="#3776AB"/><rect x="13" y="13" width="14" height="14" rx="4" fill="#FFD43B"/><circle cx="10" cy="10" r="1.4" fill="#FFFFFF"/><circle cx="22" cy="22" r="1.4" fill="#1E293B"/>',
    "go": '<rect x="3" y="7" width="26" height="18" rx="9" fill="#00ADD8"/><text x="16" y="20" text-anchor="middle" font-family="system-ui,Segoe UI,sans-serif" font-size="12" font-weight="800" fill="#FFFFFF">GO</text>',
    "rust": '<circle cx="16" cy="16" r="12" fill="#1E293B" stroke="#EA580C" stroke-width="2.2" stroke-dasharray="3 2"/><text x="16" y="20.5" text-anchor="middle" font-family="ui-monospace,Consolas,monospace" font-size="12" font-weight="800" fill="#FFFFFF">RS</text>',
    "aws": '<rect x="3" y="4" width="26" height="24" rx="6" fill="#232F3E"/><text x="16" y="16.5" text-anchor="middle" font-family="system-ui,Segoe UI,sans-serif" font-size="9.5" font-weight="800" fill="#FFFFFF">AWS</text><path d="M8 21.5c4.5 3 11.5 3 16 0" fill="none" stroke="#FF9900" stroke-width="2.2" stroke-linecap="round"/>',
    "gcp": '<polygon points="16,4 27,10.5 27,21.5 16,28 5,21.5 5,10.5" fill="#FFFFFF" stroke="#4285F4" stroke-width="2.4"/><circle cx="16" cy="16" r="5" fill="none" stroke="#EA4335" stroke-width="2.4" stroke-dasharray="8 8"/><circle cx="16" cy="16" r="2.2" fill="#34A853"/>',
    "azure": '<polygon points="14,5 25,25 18,25 13,15 8,25 5,25" fill="#0078D4"/><polygon points="16,13 27,25 13,25" fill="#38BDF8" opacity="0.85"/>',
    "cloudflare": '<path d="M8 22h16.5a4.2 4.2 0 0 0 .6-8.3A6.5 6.5 0 0 0 12.5 11a4.8 4.8 0 0 0-4.5 11z" fill="#F38020"/><path d="M21 22h5.5a3 3 0 0 0 .2-6 4 4 0 0 0-5.7 6z" fill="#FBAE40"/>',
    "github": '<circle cx="16" cy="16" r="13" fill="#181717"/><path d="M12 23v-3c-2.5.6-3-1.2-3-1.2-.5-1-1-1.3-1-1.3-.8-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .8 1.5 2.2 1 2.7.8.1-.6.3-1 .6-1.3-2-.2-4.2-1-4.2-4.6 0-1 .4-1.8 1-2.5-.1-.2-.4-1.2.1-2.5 0 0 .8-.3 2.6 1a9 9 0 0 1 4.8 0c1.8-1.3 2.6-1 2.6-1 .5 1.3.2 2.3.1 2.5.6.7 1 1.5 1 2.5 0 3.6-2.2 4.4-4.2 4.6.4.3.7 1 .7 2v3" fill="#FFFFFF"/>',
    "nginx": '<polygon points="16,3 27,9.5 27,22.5 16,29 5,22.5 5,9.5" fill="#009639"/><path d="M11 21V11l10 10V11" fill="none" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    "kafka": '<circle cx="11" cy="16" r="3" fill="none" stroke="#0F172A" stroke-width="2.2"/><circle cx="21" cy="9" r="2.6" fill="#0F172A"/><circle cx="21" cy="16" r="2.6" fill="#0F172A"/><circle cx="21" cy="23" r="2.6" fill="#0F172A"/><path d="M13.5 14.3 18.8 10.5M14 16h4.4M13.5 17.7 18.8 21.5" stroke="#0F172A" stroke-width="1.8"/>',
    "rabbitmq": '<rect x="5" y="13" width="22" height="14" rx="3" fill="#FF6600"/><rect x="7" y="5" width="4.5" height="9" rx="1.5" fill="#FF6600"/><rect x="14" y="5" width="4.5" height="9" rx="1.5" fill="#FF6600"/><rect x="18" y="18" width="4.5" height="4.5" rx="1" fill="#FFFFFF"/>',
    "graphql": '<polygon points="16,4 26,10 26,22 16,28 6,22 6,10" fill="none" stroke="#E10098" stroke-width="2"/><polygon points="16,6 24.5,21 7.5,21" fill="none" stroke="#E10098" stroke-width="1.8"/><circle cx="16" cy="4" r="2" fill="#E10098"/><circle cx="26" cy="10" r="2" fill="#E10098"/><circle cx="26" cy="22" r="2" fill="#E10098"/><circle cx="16" cy="28" r="2" fill="#E10098"/><circle cx="6" cy="22" r="2" fill="#E10098"/><circle cx="6" cy="10" r="2" fill="#E10098"/>',
    "prisma": '<polygon points="16,4 26,24 12,28 6,21" fill="#0C344B"/><path d="M16 8l6.5 13.5L13 24.5z" fill="#38BDF8" opacity="0.35"/>',
    "vite": '<polygon points="6,7 26,7 16,28" fill="#646CFF"/><polygon points="17,5 12,17 17,16 14,25 22,13 17,14" fill="#FFD62E"/>',
    "tailwind": '<path d="M9 14c1.2-3 3.4-4.5 6.5-4.5 3.6 0 4.4 2.7 6.3 3.2 1.3.3 2.5-.2 3.7-1.4-1.2 3-3.4 4.5-6.5 4.5-3.6 0-4.4-2.7-6.3-3.2-1.3-.3-2.5.2-3.7 1.4zm-3 6.5c1.2-3 3.4-4.5 6.5-4.5 3.6 0 4.4 2.7 6.3 3.2 1.3.3 2.5-.2 3.7-1.4-1.2 3-3.4 4.5-6.5 4.5-3.6 0-4.4-2.7-6.3-3.2-1.3-.3-2.5.2-3.7 1.4z" fill="#06B6D4"/>',
    "stripe": '<rect x="3" y="4" width="26" height="24" rx="6" fill="#635BFF"/><text x="16" y="21.5" text-anchor="middle" font-family="system-ui,Segoe UI,sans-serif" font-size="14" font-weight="800" fill="#FFFFFF">S</text>',
    "qris": '<rect x="3" y="4" width="26" height="24" rx="6" fill="#DC2626"/><text x="16" y="19.5" text-anchor="middle" font-family="ui-monospace,Consolas,monospace" font-size="9.5" font-weight="800" fill="#FFFFFF">QRIS</text>',
    "otel": '<circle cx="16" cy="16" r="10" fill="none" stroke="#425CC7" stroke-width="2.4"/><circle cx="16" cy="16" r="4" fill="#F5A800"/><path d="M16 6v4M26 16h-4M16 26v-4M6 16h4" stroke="#425CC7" stroke-width="2.2" stroke-linecap="round"/>',
}

# Vendor & semantic group tints: (light_bg, light_border, light_label, dark_bg, dark_border, dark_label)
GROUP_TONES: dict[str, tuple[str, str, str, str, str, str]] = {
    "neutral": ("#F1F0EC", "#CFCBC2", "#57534E", "#131926", "#2B364E", "#94A3B8"),
    "blue": ("#EEF5FF", "#9EC5FE", "#1D4ED8", "#0F1D33", "#1E40AF", "#93C5FD"),
    "green": ("#ECFDF5", "#6EE7B7", "#047857", "#0B241C", "#059669", "#6EE7B7"),
    "amber": ("#FFFBEB", "#FCD34D", "#B45309", "#24190A", "#B45309", "#FCD34D"),
    "purple": ("#F5F3FF", "#C4B5FD", "#6D28D9", "#1B1330", "#6D28D9", "#C4B5FD"),
    "aws": ("#FFF7ED", "#FDBA74", "#C2410C", "#24160B", "#C2410C", "#FDBA74"),
    "gcp": ("#EFF6FF", "#93C5FD", "#1D4ED8", "#0E1C36", "#2563EB", "#93C5FD"),
    "azure": ("#F0F9FF", "#7DD3FC", "#0369A1", "#0C1E2E", "#0284C7", "#7DD3FC"),
    "k8s": ("#EEF2FF", "#A5B4FC", "#3730A3", "#131836", "#4338CA", "#A5B4FC"),
    "cloudflare": ("#FFF7ED", "#FDBA74", "#C2410C", "#25170B", "#EA580C", "#FDBA74"),
}


def _is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _load_safe_local_svg(icons_dir: Path, icon_name: str) -> str | None:
    if not SAFE_ICON_NAME_RE.fullmatch(icon_name):
        raise ValueError(f"Unsafe icon name rejected: {icon_name!r}")
    root = icons_dir.resolve()
    candidate = root / f"{icon_name}.svg"
    if not candidate.exists():
        return None
    info = candidate.lstat()
    if not stat.S_ISREG(info.st_mode) or _is_link(info):
        raise ValueError(f"Symlink or non-regular SVG rejected: {candidate.name}")
    resolved = candidate.resolve()
    if root not in resolved.parents:
        raise ValueError(f"Icon path escapes icons_dir: {icon_name!r}")
    raw = resolved.read_bytes()
    if len(raw) > 128 * 1024:
        raise ValueError(f"SVG icon exceeds 128 KB limit: {candidate.name}")
    text = raw.decode("utf-8")
    if "<svg" not in text.lower() or UNSAFE_SVG_RE.search(text):
        raise ValueError(f"Unsafe active or external content detected in SVG: {candidate.name}")
    return text


def _monogram_svg(label: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", label) if w]
    if not words:
        letters = "??"
    elif len(words) == 1:
        letters = words[0][:2].upper()
    else:
        letters = (words[0][0] + words[1][0]).upper()
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    accent = OKABE_ITO[digest[0] % len(OKABE_ITO)]
    safe_letters = html.escape(letters)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
        f'<rect x="2" y="2" width="28" height="28" rx="7" fill="{accent}"/>'
        f'<rect x="2" y="2" width="28" height="10" rx="7" fill="#FFFFFF" opacity="0.14"/>'
        f'<text x="16" y="20.8" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        f'font-size="12" font-weight="800" fill="#FFFFFF">{safe_letters}</text>'
        f"</svg>"
    )


def _builtin_svg(icon_name: str, stroke_color: str = "#0F172A") -> str:
    body = BUILTIN_ICONS[icon_name]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28" '
        f'fill="none" stroke="{stroke_color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )


def _brand_svg(icon_name: str) -> str:
    body = BRAND_MARKS[icon_name]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">{body}</svg>'


def _resolve_icon_svg(icon_name: str, label: str, icons_dir: Path | None, stroke_color: str = "#0F172A") -> tuple[str, str]:
    low = icon_name.lower() if icon_name else ""
    if icon_name and icons_dir is not None:
        local = _load_safe_local_svg(icons_dir, icon_name)
        if local is not None:
            return local, "local-svg"
    if low in BRAND_MARKS:
        return _brand_svg(low), "brand"
    if low in BUILTIN_ICONS:
        return _builtin_svg(low, stroke_color), "builtin"
    if icon_name and not SAFE_ICON_NAME_RE.fullmatch(icon_name):
        raise ValueError(f"Unsafe icon identifier rejected: {icon_name!r}")
    return _monogram_svg(label), "monogram"


def _port_coords(node: dict[str, Any], port: str) -> tuple[float, float]:
    nx, ny = float(node["x"]), float(node["y"])
    if port == "right":
        return nx + TILE_SIZE + 3, ny + TILE_SIZE / 2
    if port == "left":
        return nx - 3, ny + TILE_SIZE / 2
    if port == "top":
        return nx + TILE_SIZE / 2, ny - 3
    if port == "bottom":
        return nx + TILE_SIZE / 2, ny + NODE_H - 12
    return nx + TILE_SIZE / 2, ny + TILE_SIZE / 2


def _segment_hits_box(x1: float, y1: float, x2: float, y2: float, box: tuple[float, float, float, float]) -> bool:
    bx0, by0, bx1, by1 = box
    if abs(y1 - y2) < 1e-6:
        lo, hi = min(x1, x2), max(x1, x2)
        return by0 <= y1 <= by1 and hi >= bx0 and lo <= bx1
    if abs(x1 - x2) < 1e-6:
        lo, hi = min(y1, y2), max(y1, y2)
        return bx0 <= x1 <= bx1 and hi >= by0 and lo <= by1
    return False


def _rounded_polyline_path(points: list[tuple[float, float]], radius: float = 8.0) -> str:
    # Deduplicate consecutive identical points
    clean: list[tuple[float, float]] = []
    for pt in points:
        if not clean or abs(clean[-1][0] - pt[0]) > 0.5 or abs(clean[-1][1] - pt[1]) > 0.5:
            clean.append(pt)
    if len(clean) < 2:
        return ""
    if len(clean) == 2:
        return f"M {clean[0][0]:.1f} {clean[0][1]:.1f} L {clean[1][0]:.1f} {clean[1][1]:.1f}"
    cmds = [f"M {clean[0][0]:.1f} {clean[0][1]:.1f}"]
    for i in range(1, len(clean) - 1):
        p0, p1, p2 = clean[i - 1], clean[i], clean[i + 1]
        v1x, v1y = p1[0] - p0[0], p1[1] - p0[1]
        v2x, v2y = p2[0] - p1[0], p2[1] - p1[1]
        l1 = (v1x * v1x + v1y * v1y) ** 0.5
        l2 = (v2x * v2x + v2y * v2y) ** 0.5
        if l1 < 1 or l2 < 1:
            cmds.append(f"L {p1[0]:.1f} {p1[1]:.1f}")
            continue
        r = min(radius, l1 / 2.2, l2 / 2.2)
        ax, ay = p1[0] - (v1x / l1) * r, p1[1] - (v1y / l1) * r
        bx, by = p1[0] + (v2x / l2) * r, p1[1] + (v2y / l2) * r
        cmds.append(f"L {ax:.1f} {ay:.1f} Q {p1[0]:.1f} {p1[1]:.1f} {bx:.1f} {by:.1f}")
    cmds.append(f"L {clean[-1][0]:.1f} {clean[-1][1]:.1f}")
    return " ".join(cmds)


def _orthogonal_route(edge: dict[str, Any], node_map: dict[str, dict[str, Any]]) -> tuple[str, float, float]:
    """Compute obstacle-aware rounded orthogonal SVG path between two nodes."""
    src = node_map[edge["from"]]
    dst = node_map[edge["to"]]
    sx, sy = float(src["x"]) + TILE_SIZE / 2, float(src["y"]) + TILE_SIZE / 2
    dx, dy = float(dst["x"]) + TILE_SIZE / 2, float(dst["y"]) + TILE_SIZE / 2
    adx, ady = abs(dx - sx), abs(dy - sy)

    from_port = str(edge.get("fromPort") or ("right" if adx >= ady and dx >= sx else "left" if adx >= ady else "bottom" if dy >= sy else "top"))
    to_port = str(edge.get("toPort") or ("left" if adx >= ady and dx >= sx else "right" if adx >= ady else "top" if dy >= sy else "bottom"))
    p_start = _port_coords(src, from_port)
    p_end = _port_coords(dst, to_port)

    # Custom waypoints take full precedence
    if edge.get("waypoints"):
        pts = [p_start] + [(float(w[0]), float(w[1])) for w in edge["waypoints"]] + [p_end]
    else:
        obstacles = [
            (float(n["x"]) - 10, float(n["y"]) - 10, float(n["x"]) + TILE_SIZE + 10, float(n["y"]) + NODE_H - 4)
            for nid, n in node_map.items()
            if nid not in {edge["from"], edge["to"]}
        ]
        if from_port in {"left", "right"} and to_port in {"left", "right"}:
            mid_x = round((p_start[0] + p_end[0]) / 2, 1)
            pts = [p_start, (mid_x, p_start[1]), (mid_x, p_end[1]), p_end]
            # Check if any segment crosses an obstacle node; if so, route cleanly above or below
            hits = [
                b
                for b in obstacles
                if any(_segment_hits_box(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], b) for i in range(len(pts) - 1))
            ]
            if hits:
                top_clear = min(b[1] for b in hits) - 18
                bot_clear = max(b[3] for b in hits) + 16
                detour_y = top_clear if abs(top_clear - p_start[1]) <= abs(bot_clear - p_start[1]) and top_clear > 92 else bot_clear
                stub_s = p_start[0] + (18 if from_port == "right" else -18)
                stub_e = p_end[0] + (-18 if to_port == "left" else 18)
                pts = [p_start, (stub_s, p_start[1]), (stub_s, detour_y), (stub_e, detour_y), (stub_e, p_end[1]), p_end]
        elif from_port in {"top", "bottom"} and to_port in {"top", "bottom"}:
            mid_y = round((p_start[1] + p_end[1]) / 2, 1)
            pts = [p_start, (p_start[0], mid_y), (p_end[0], mid_y), p_end]
        elif from_port in {"left", "right"}:
            pts = [p_start, (p_end[0], p_start[1]), p_end]
        else:
            pts = [p_start, (p_start[0], p_end[1]), p_end]

    # Pick longest segment for edge label placement
    best_len = -1.0
    lx, ly = (p_start[0] + p_end[0]) / 2, (p_start[1] + p_end[1]) / 2 - 8
    for i in range(len(pts) - 1):
        seg_len = ((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
        if seg_len > best_len:
            best_len = seg_len
            lx = (pts[i][0] + pts[i + 1][0]) / 2
            ly = (pts[i][1] + pts[i + 1][1]) / 2 - 7
    return _rounded_polyline_path(pts, radius=8.0), lx, ly


def _validate_spec(spec: dict[str, Any]) -> tuple[int, int]:
    if not isinstance(spec, dict):
        raise ValueError("Spec root must be a JSON object.")
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("Spec must define a non-empty 'nodes' list.")
    seen_ids: set[str] = set()
    max_x, max_y = 680, 360
    for node in nodes:
        nid = node.get("id")
        if not isinstance(nid, str) or not SAFE_ICON_NAME_RE.fullmatch(nid):
            raise ValueError(f"Invalid node id: {nid!r}")
        if nid in seen_ids:
            raise ValueError(f"Duplicate node id: {nid!r}")
        seen_ids.add(nid)
        x, y = float(node["x"]), float(node["y"])
        max_x = max(max_x, int(x + NODE_W + 48))
        max_y = max(max_y, int(y + NODE_H + 84))
    for grp in spec.get("groups", []):
        max_x = max(max_x, int(float(grp["x"]) + float(grp["w"]) + 40))
        max_y = max(max_y, int(float(grp["y"]) + float(grp["h"]) + 76))
    for edge in spec.get("edges", []):
        if edge.get("from") not in seen_ids or edge.get("to") not in seen_ids:
            raise ValueError(f"Edge references unknown node: {edge!r}")
        if edge.get("kind", "internal") not in {"primary", "internal", "deploy"}:
            raise ValueError(f"Unsupported edge kind: {edge.get('kind')!r}")
    return max_x, max_y


def _embed_svg_inner(svg_icon: str, target_px: float) -> tuple[str, float]:
    inner = re.sub(r"^<\?xml[^>]*\?>\s*", "", svg_icon.strip())
    vb_match = re.search(r'viewBox="([^"]+)"', inner)
    vb = vb_match.group(1) if vb_match else "0 0 24 24"
    vb_nums = [float(x) for x in re.split(r"[,\s]+", vb.strip())[:4]]
    scale = target_px / max(vb_nums[2], vb_nums[3], 1.0)
    body = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", inner, flags=re.S)
    return body, scale


def build_svg(spec: dict[str, Any], icons_dir: Path | None = None, theme: str = "light") -> str:
    """Render a standalone, drafting-paper-styled static SVG architecture diagram."""
    width, height = _validate_spec(spec)
    dark = theme == "dark"
    bg = "#0C1018" if dark else "#F7F6F2"
    dot_color = "#1E293B" if dark else "#E2DFD7"
    ink = "#F8FAFC" if dark else "#111827"
    muted = "#94A3B8" if dark else "#57534E"
    accent = "#38BDF8" if dark else "#0072B2"
    edge_neutral = "#94A3B8" if dark else "#64748B"
    footer_rule = "#1E293B" if dark else "#E5E2DA"

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        "<defs>",
        f'<pattern id="dot-grid" width="16" height="16" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="0.9" fill="{dot_color}"/></pattern>',
        '<filter id="tile-shadow" x="-15%" y="-15%" width="130%" height="140%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#0F172A" flood-opacity="0.12"/></filter>',
        f'<marker id="arrow-primary" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">'
        f'<path d="M 0 1 L 10 5 L 0 9 z" fill="{accent}"/></marker>',
        f'<marker id="arrow-neutral" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
        f'<path d="M 0 1 L 10 5 L 0 9 z" fill="{edge_neutral}"/></marker>',
        "</defs>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{bg}"/>',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#dot-grid)"/>',
    ]

    # Engineering sheet header
    kicker = html.escape(str(spec.get("kicker", "stack-diagram / offline")))
    title = html.escape(str(spec.get("title", "System Architecture")))
    subtitle = html.escape(str(spec.get("subtitle", "")))
    parts.append('<g id="header">')
    parts.append(f'<text x="32" y="28" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11" letter-spacing="0.06em" fill="{muted}">{kicker.upper()}</text>')
    parts.append(f'<text x="32" y="54" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="22" font-weight="700" letter-spacing="-0.02em" fill="{ink}">{title}</text>')
    if subtitle:
        parts.append(f'<text x="32" y="75" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="13" fill="{muted}">{subtitle}</text>')
    parts.append("</g>")

    # Groups (supports nested boxes & optional 14px header icon)
    parts.append('<g id="groups">')
    for grp in spec.get("groups", []):
        tone = GROUP_TONES.get(str(grp.get("tone", "neutral")), GROUP_TONES["neutral"])
        g_bg, g_border, g_label_col = (tone[3], tone[4], tone[5]) if dark else (tone[0], tone[1], tone[2])
        gx, gy, gw, gh = float(grp["x"]), float(grp["y"]), float(grp["w"]), float(grp["h"])
        glabel = html.escape(str(grp.get("label", "")))
        gstyle = str(grp.get("style", "dashed"))
        dash = ' stroke-dasharray="6 4"' if gstyle == "dashed" else ""
        parts.append(
            f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" height="{gh:.1f}" rx="14" '
            f'fill="{g_bg}" stroke="{g_border}" stroke-width="1.35"{dash}/>'
        )
        label_x = gx + 14
        g_icon = str(grp.get("icon", ""))
        if g_icon:
            g_svg, g_kind = _resolve_icon_svg(g_icon, glabel, icons_dir, stroke_color=g_label_col)
            body, scale = _embed_svg_inner(g_svg, 14.0)
            stroke_attr = f' stroke="{g_label_col}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"' if g_kind == "builtin" else ""
            parts.append(f'<g transform="translate({gx + 12:.1f},{gy + 10:.1f}) scale({scale:.4f})"{stroke_attr}>{body}</g>')
            label_x = gx + 31
        parts.append(
            f'<text x="{label_x:.1f}" y="{gy + 21:.1f}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="10.5" font-weight="700" letter-spacing="0.05em" fill="{g_label_col}">{glabel}</text>'
        )
    parts.append("</g>")

    # Edges (obstacle-aware rounded orthogonal connectors)
    node_map = {n["id"]: n for n in spec["nodes"]}
    parts.append('<g id="edges">')
    for edge in spec.get("edges", []):
        kind = str(edge.get("kind", "internal"))
        d, lx, ly = _orthogonal_route(edge, node_map)
        stroke = accent if kind == "primary" else edge_neutral
        swidth = "2.1" if kind == "primary" else "1.5"
        dash = ' stroke-dasharray="5 4"' if kind == "deploy" else ""
        marker = "url(#arrow-primary)" if kind == "primary" else "url(#arrow-neutral)"
        parts.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{swidth}" stroke-linecap="round"{dash} marker-end="{marker}"/>')
        elabel = html.escape(str(edge.get("label", "")))
        if elabel:
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
                f'font-size="10.5" font-weight="600" fill="{ink}" stroke="{bg}" stroke-width="5" stroke-linejoin="round" paint-order="stroke">{elabel}</text>'
            )
    parts.append("</g>")

    # Nodes (crisp white/dark/bare icon tiles with elevation + clear role hierarchy)
    parts.append('<g id="nodes">')
    used_sources: set[str] = set()
    for node in spec["nodes"]:
        nx, ny = float(node["x"]), float(node["y"])
        nlabel = html.escape(str(node.get("label", node["id"])))
        nrole = html.escape(str(node.get("role", "")))
        icon_name = str(node.get("icon", ""))
        tile_mode = str(node.get("tile", "auto"))

        # Determine tile fill & border
        is_brand_or_custom = (icon_name.lower() in BRAND_MARKS) or (icon_name and icon_name.lower() not in BUILTIN_ICONS)
        if tile_mode == "dark":
            t_bg, t_border, icon_ink = "#182235", "#334155", "#F8FAFC"
        elif tile_mode == "white" or (tile_mode == "auto" and is_brand_or_custom):
            t_bg, t_border, icon_ink = "#FFFFFF", ("#334155" if dark else "#D6D3CB"), "#0F172A"
        else:
            t_bg = "#182235" if dark else "#FFFFFF"
            t_border = "#334155" if dark else "#D6D3CB"
            icon_ink = "#F8FAFC" if dark else "#0F172A"

        svg_icon, source_kind = _resolve_icon_svg(icon_name, str(node.get("label", node["id"])), icons_dir, stroke_color=icon_ink)
        used_sources.add(source_kind)
        target_px = 38.0 if tile_mode == "bare" else 32.0
        body, scale = _embed_svg_inner(svg_icon, target_px)
        stroke_attr = f' stroke="{icon_ink}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"' if source_kind == "builtin" else ""

        parts.append(f'<g id="node-{html.escape(node["id"])}">')
        if tile_mode != "bare":
            parts.append(
                f'<rect x="{nx:.1f}" y="{ny:.1f}" width="{TILE_SIZE}" height="{TILE_SIZE}" rx="13" '
                f'fill="{t_bg}" stroke="{t_border}" stroke-width="1.25" filter="url(#tile-shadow)"/>'
            )
        ix = nx + (TILE_SIZE - target_px) / 2
        iy = ny + (TILE_SIZE - target_px) / 2
        parts.append(f'<g transform="translate({ix:.1f},{iy:.1f}) scale({scale:.4f})"{stroke_attr}>{body}</g>')
        cx = nx + TILE_SIZE / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{ny + TILE_SIZE + 17:.1f}" text-anchor="middle" '
            f'font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="12.5" font-weight="650" fill="{ink}">{nlabel}</text>'
        )
        if nrole:
            parts.append(
                f'<text x="{cx:.1f}" y="{ny + TILE_SIZE + 32:.1f}" text-anchor="middle" '
                f'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10.5" fill="{muted}">{nrole}</text>'
            )
        parts.append("</g>")
    parts.append("</g>")

    # Engineering Legend & Offline Provenance Footer
    fy = height - 24
    parts.append('<g id="footer">')
    parts.append(f'<line x1="32" y1="{fy - 18}" x2="{width - 32}" y2="{fy - 18}" stroke="{footer_rule}" stroke-width="1"/>')
    parts.append(f'<line x1="32" y1="{fy}" x2="54" y2="{fy}" stroke="{accent}" stroke-width="2.1"/>')
    parts.append(f'<text x="60" y="{fy + 3.5}" font-family="ui-monospace,Consolas,monospace" font-size="10" fill="{muted}">primary flow</text>')
    parts.append(f'<line x1="154" y1="{fy}" x2="176" y2="{fy}" stroke="{edge_neutral}" stroke-width="1.5"/>')
    parts.append(f'<text x="182" y="{fy + 3.5}" font-family="ui-monospace,Consolas,monospace" font-size="10" fill="{muted}">internal</text>')
    parts.append(f'<line x1="250" y1="{fy}" x2="272" y2="{fy}" stroke="{edge_neutral}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    parts.append(f'<text x="278" y="{fy + 3.5}" font-family="ui-monospace,Consolas,monospace" font-size="10" fill="{muted}">async / deploy</text>')
    src_credit = html.escape(" / ".join(sorted(used_sources)))
    parts.append(
        f'<text x="{width - 32}" y="{fy + 3.5}" text-anchor="end" font-family="ui-monospace,Consolas,monospace" '
        f'font-size="10" fill="{muted}">icons: {src_credit} · offline</text>'
    )
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def build_html(spec: dict[str, Any], icons_dir: Path | None = None) -> str:
    """Build a self-contained, 100% offline HTML viewer embedding light/dark SVG diagrams + export."""
    light_svg = build_svg(spec, icons_dir=icons_dir, theme="light")
    dark_svg = build_svg(spec, icons_dir=icons_dir, theme="dark")
    title = html.escape(str(spec.get("title", "System Architecture")))
    light_b64 = base64.b64encode(light_svg.encode("utf-8")).decode("ascii")
    dark_b64 = base64.b64encode(dark_svg.encode("utf-8")).decode("ascii")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ --bg: #EEEDE8; --fg: #111827; --border: #D6D3CB; --btn-bg: #FFFFFF; --accent: #0072B2; }}
    [data-theme="dark"] {{ --bg: #070A10; --fg: #F8FAFC; --border: #1E293B; --btn-bg: #111827; --accent: #38BDF8; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 24px; background: var(--bg); color: var(--fg); font-family: system-ui, -apple-system, Segoe UI, sans-serif; }}
    .toolbar {{ display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; margin: 0 auto 12px; max-width: 1240px; }}
    button {{ cursor: pointer; padding: 7px 13px; border-radius: 8px; border: 1px solid var(--border); background: var(--btn-bg); color: var(--fg); font: 600 12.5px/1 system-ui, sans-serif; }}
    button:hover {{ border-color: var(--accent); }}
    button:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 2px; }}
    .canvas {{ max-width: 1240px; margin: 0 auto; border: 1px solid var(--border); border-radius: 16px; overflow: auto; box-shadow: 0 8px 28px rgba(15,23,42,0.08); }}
    .canvas img {{ display: block; width: 100%; height: auto; }}
    .canvas.zoom-125 img {{ width: 125%; max-width: none; }}
    .img-dark {{ display: none; }}
    [data-theme="dark"] .img-light {{ display: none; }}
    [data-theme="dark"] .img-dark {{ display: block; }}
  </style>
</head>
<body>
  <div class="toolbar">
    <button id="zoom-btn" type="button">Zoom: Fit</button>
    <button id="theme-toggle" type="button" aria-label="Toggle light and dark theme">Theme: Light</button>
    <button id="download-svg" type="button">Download SVG</button>
  </div>
  <main class="canvas" id="canvas">
    <img class="img-light" alt="{title} (light theme)" src="data:image/svg+xml;base64,{light_b64}">
    <img class="img-dark" alt="{title} (dark theme)" src="data:image/svg+xml;base64,{dark_b64}">
  </main>
  <script>
    const root = document.documentElement;
    const themeBtn = document.getElementById("theme-toggle");
    const zoomBtn = document.getElementById("zoom-btn");
    const canvas = document.getElementById("canvas");
    const LIGHT_B64 = "{light_b64}";
    const DARK_B64 = "{dark_b64}";
    function syncLabel() {{ themeBtn.textContent = "Theme: " + (root.getAttribute("data-theme") === "dark" ? "Dark" : "Light"); }}
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) root.setAttribute("data-theme", "dark");
    syncLabel();
    themeBtn.addEventListener("click", () => {{
      root.setAttribute("data-theme", root.getAttribute("data-theme") === "dark" ? "light" : "dark");
      syncLabel();
    }});
    zoomBtn.addEventListener("click", () => {{
      const zoomed = canvas.classList.toggle("zoom-125");
      zoomBtn.textContent = zoomed ? "Zoom: 125%" : "Zoom: Fit";
    }});
    document.getElementById("download-svg").addEventListener("click", () => {{
      const isDark = root.getAttribute("data-theme") === "dark";
      const bytes = Uint8Array.from(atob(isDark ? DARK_B64 : LIGHT_B64), (c) => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], {{ type: "image/svg+xml" }}));
      const a = document.createElement("a");
      a.href = url;
      a.download = isDark ? "stack-diagram-dark.svg" : "stack-diagram-light.svg";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }});
  </script>
</body>
</html>
"""


def run_self_test() -> int:
    sample = {
        "kicker": "self-test / offline",
        "title": "Demo <XSS> & Stack",
        "subtitle": "Offline diagram verification with obstacle detour and color marks",
        "groups": [{"id": "g1", "label": "AWS Cloud", "icon": "aws", "x": 24, "y": 92, "w": 620, "h": 176, "tone": "aws", "style": "solid"}],
        "nodes": [
            {"id": "api", "label": "Order API", "role": "http", "icon": "go", "x": 64, "y": 140},
            {"id": "worker", "label": "Outbox Worker", "role": "async", "icon": "worker", "x": 264, "y": 140},
            {"id": "pg", "label": "PostgreSQL", "role": "primary db", "icon": "postgres", "x": 464, "y": 140},
        ],
        "edges": [
            {"from": "api", "to": "pg", "kind": "primary", "label": "SQL (detours worker)"},
            {"from": "api", "to": "worker", "kind": "internal", "label": "Queue"},
        ],
    }
    svg = build_svg(sample)
    assert "&lt;XSS&gt;" in svg and "<XSS>" not in svg
    assert not re.search(r"https?://(?!www\.w3\.org/2000/svg\b)", svg)
    assert "#336791" in svg  # built-in PostgreSQL brand color mark
    assert " Q " in svg  # rounded orthogonal detour around obstacle worker

    html_doc = build_html(sample)
    assert "data:image/svg+xml;base64," in html_doc
    assert not re.search(r"https?://", html_doc)

    with tempfile.TemporaryDirectory() as tmp:
        icons = Path(tmp) / "icons"
        icons.mkdir()
        (icons / "evil.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', encoding="utf-8")
        try:
            _load_safe_local_svg(icons, "evil")
            raise AssertionError("Failed to block active <script> SVG")
        except ValueError:
            pass
        try:
            _load_safe_local_svg(icons, "../escape")
            raise AssertionError("Failed to block path traversal icon name")
        except ValueError:
            pass

    print(json.dumps({"status": "PASS", "probes": 7, "brand_marks": len(BRAND_MARKS), "builtin_icons": len(BUILTIN_ICONS), "offline_only": True}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", nargs="?", type=Path, help="Path to JSON diagram spec")
    parser.add_argument("--icons-dir", type=Path, help="Optional operator-owned local SVG icons directory")
    parser.add_argument("--format", choices=["html", "svg"], default="html")
    parser.add_argument("--theme", choices=["light", "dark"], default="light", help="Theme for --format svg")
    parser.add_argument("--out", type=Path, help="Output file path")
    parser.add_argument("--self-test", action="store_true", help="Run built-in positive and negative probes")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()
    if not args.spec or not args.out:
        parser.error("Provide <spec.json> and --out <path>, or use --self-test.")

    spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
    output = build_html(spec, icons_dir=args.icons_dir) if args.format == "html" else build_svg(spec, icons_dir=args.icons_dir, theme=args.theme)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(output, encoding="utf-8")
    print(json.dumps({"status": "BUILT", "format": args.format, "out": str(args.out), "bytes": len(output.encode("utf-8"))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
