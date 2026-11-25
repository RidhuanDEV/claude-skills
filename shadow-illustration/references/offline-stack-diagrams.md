# Offline Engineering Stack & Architecture Diagrams

Use this playbook when producing publication-grade, engineering-drawing-style tech stack, cloud topology, or service architecture diagrams that must work **100% offline with zero external network calls, zero public gallery uploads, and zero browser `--no-sandbox` exposure**.

Cross-reference: use [`shadow-architect/references/02-c4-diagrams-adrs-and-consistency-models.md`](../../shadow-architect/references/02-c4-diagrams-adrs-and-consistency-models.md) for C4 Mermaid specifications and ADR boundaries; use this module when Mermaid auto-layout clips or when a visual engineering-drawing layout with light/dark themes and local SVG tiles is requested.

---

## 1. Security & Offline-First Non-Negotiables

1. **Zero Network Egress:** Never fetch icons from live CDNs, GitHub raw URLs, or arbitrary user-supplied URLs at build time (prevents SSRF, supply-chain SVG tampering, and broken offline builds).
2. **Zero External Publishing:** Never ship or invoke public gallery upload scripts for internal architecture diagrams. Diagrams stay local to the approved project directory.
3. **Zero Unsafe Browser Flags:** If rasterizing built HTML/SVG to PNG locally, use a sandboxed Playwright/Chromium launch (NEVER `--no-sandbox`) or an approved local SVG rasterizer (`resvg` / `sharp`).
4. **Sanitized Local SVG Inputs:** Local `.svg` files passed via `--icons-dir` are restricted by canonical path containment (no symlinks, no `..` escape) and rejected if they contain `<script>`, `<foreignObject>`, inline `on*=` event handlers, `javascript:` URIs, or external `http(s)://` references.

---

## 2. Visual Geometry & Layout System

| Element | Rule | Purpose |
| --- | --- | --- |
| **Grid & Spacing** | Snap coordinates to an `8px` grid; minimum `24px` group inner padding; `28px` top clearance for group titles | Prevents visual drift and ensures group labels never collide with tiles |
| **Node Tile** | `64x64px` rounded tile (`border-radius: 12px`) + bold label (`13px`) + lowercase role subtitle (`11px`, e.g., `http api`, `postgres db`) | Scannable hierarchy at both 100% and slide/doc zoom |
| **Group Boxes** | Soft tonal background tint + `1.5px` dashed or subtle solid border + top-left uppercase kicker label | Visually separates runtime, VPC, cloud, or trust boundaries without clutter |
| **Orthogonal Edges** | Route connectors strictly horizontally and vertically (elbow paths) anchored to tile mid-edges (`top/right/bottom/left`), never diagonal across text | Keeps arrowheads clear of labels and matches engineering blueprints |
| **3 Edge Semantics** | `primary`: solid accent (`2px`) · `internal`: solid neutral (`1.5px`) · `deploy`: dashed neutral (`1.5px`, `5 4`) | Distinguishes request flow from secondary and CI/deploy paths even without color |
| **Edge Labels** | Placed on the longest straight segment with a paper-tinted halo (`paint-order: stroke`) | Remains readable where edges pass near group borders |
| **Light & Dark Themes** | Semantic CSS variables (`[data-theme="dark"]` + `prefers-color-scheme`) with `>= 4.5:1` label contrast and `>= 3:1` connector contrast | Single self-contained HTML artifact works in light, dark, and print views |

---

## 3. Built-In Offline Brand Marks, Infra Glyphs & Monogram Fallback

[`scripts/build_stack_diagram.py`](../scripts/build_stack_diagram.py) renders on warm drafting paper (`#F7F6F2` light / `#0C1018` dark) with a subtle `16px` dot grid, elevated tiles (`tile: "white" | "dark" | "bare" | "auto"`), nested vendor-tinted groups (`aws`, `gcp`, `azure`, `k8s`, `cloudflare`, `neutral`, `blue`, `green`, `amber`, `purple`, with optional `icon` and `style: "solid" | "dashed"`), and **obstacle-aware rounded orthogonal connectors** (supporting explicit `fromPort`/`toPort` and `waypoints`).

Built-in offline marks (zero network fetches):
- **28 Color Tech/Cloud Marks:** `postgres`/`postgresql`, `redis`, `docker`, `kubernetes`/`k8s`, `react`, `nextjs`, `typescript`, `node`, `python`, `go`, `rust`, `aws`, `gcp`, `azure`, `cloudflare`, `github`, `nginx`, `kafka`, `rabbitmq`, `graphql`, `prisma`, `vite`, `tailwind`, `stripe`, `qris`, `otel`
- **17 Monochrome Infra Glyphs:** `server`, `api`, `database`, `cache`, `queue`, `worker`, `browser`, `mobile`, `user`, `globe`, `cloud`, `shield`, `lock`, `storage`, `container`, `ai`, `mail`

When a node specifies an icon not in the built-in catalog and not present as a validated `.svg` in `--icons-dir`, the builder automatically generates a **deterministic, theme-aware 2-letter monogram SVG tile** using an Okabe-Ito color-blind-safe accent band so diagrams never render broken images offline.

---

## 4. Local CLI Usage

```powershell
# Self-test (positive + adversarial security probes)
python shadow-illustration/scripts/build_stack_diagram.py --self-test

# Build self-contained offline HTML (light + dark toggle) from JSON spec
python shadow-illustration/scripts/build_stack_diagram.py diagram.json --out out/architecture.html

# Export standalone static SVG (compatible with inspect_static_svg.py)
python shadow-illustration/scripts/build_stack_diagram.py diagram.json --format svg --out out/architecture.svg

# Optional: include validated local SVG icons from an operator-owned folder
python shadow-illustration/scripts/build_stack_diagram.py diagram.json --icons-dir assets/icons --out out/architecture.html
```

### Minimal JSON Spec Contract
```json
{
  "kicker": "architecture / offline",
  "title": "Order Processing Stack",
  "subtitle": "Modular monolith with async worker and transactional outbox",
  "groups": [
    { "id": "edge", "label": "Client & Edge", "x": 32, "y": 96, "w": 200, "h": 220, "tone": "blue" },
    { "id": "core", "label": "App Runtime", "x": 272, "y": 96, "w": 420, "h": 220, "tone": "neutral" }
  ],
  "nodes": [
    { "id": "web", "label": "Web App", "role": "spa client", "icon": "browser", "x": 100, "y": 156 },
    { "id": "api", "label": "Order API", "role": "http server", "icon": "api", "x": 340, "y": 156 },
    { "id": "db", "label": "PostgreSQL", "role": "primary db", "icon": "database", "x": 540, "y": 156 }
  ],
  "edges": [
    { "from": "web", "to": "api", "kind": "primary", "label": "HTTPS JSON" },
    { "from": "api", "to": "db", "kind": "internal", "label": "SQL / ACID" }
  ]
}
```

---

## 5. Verification Checklist

1. **Structural & Security Check:** Output contains zero `http://`/`https://` external resource tags (`<script src>`, `<link href>`, `<img src="http">`) and escapes all labels.
2. **SVG Profile Check:** Standalone `--format svg` output passes `python shadow-illustration/scripts/inspect_static_svg.py <out.svg>`.
3. **Visual Check (when rendered):** Confirm no arrow crosses text, light and dark themes both keep `>= 4.5:1` label contrast, and no confidential hostnames/IPs/secrets appear in labels before external sharing.

---

## 6. Source Attribution & Provenance

Layout geometry concepts (white/dark icon tiles, grouped boundary boxes, orthogonal edge anchoring, and three semantic edge tiers) inspired in clean room by `caru-ini/stack-diagram` (pinned commit `1b375941783ff0b1503b91afa079cdf59a966523`, `tar_sha256: 03c3f567a0f8d7517c599a7af495f33428013f0c60bd64f0d135addc98952d63`, licensed **MIT**). All network icon fetching (`fetch_icons.py`), public gallery upload (`share.py`), and `--no-sandbox` rendering (`render_png.py`) were intentionally omitted and replaced with a clean-room, zero-egress Python builder.
