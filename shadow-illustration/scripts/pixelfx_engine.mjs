#!/usr/bin/env node
/**
 * Offline Procedural Two-Buffer Pixel-Art VFX Engine & Sprite-Sheet Exporter.
 *
 * Security & Portability Guarantees:
 * - Pure Node.js built-ins only (node:fs, node:path, node:zlib) — ZERO npm dependencies.
 * - ZERO network imports (no http/https/net/fetch), ZERO child_process execution.
 * - Deterministic seeded PRNG (mulberry32) — zero Math.random() calls.
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { deflateSync } from "node:zlib";

const TAU = Math.PI * 2;

export const BAYER4 = [
  0, 8, 2, 10,
  12, 4, 14, 6,
  3, 11, 1, 9,
  15, 7, 13, 5,
];

export const PALETTES = {
  fire: ["#240907", "#7c1d0f", "#d94e14", "#ff9e2c", "#fff4c2"],
  ice: ["#0b1a33", "#1b4978", "#3d93c9", "#9be7ff", "#ffffff"],
  arcane: ["#190a2e", "#4b1d82", "#8e3be0", "#d499ff", "#ffffff"],
  poison: ["#0a1f12", "#1e5928", "#4ca638", "#a8e858", "#efffc4"],
  holy: ["#2b1f08", "#7a5b14", "#d4a62a", "#ffe47a", "#ffffff"],
  cyber: ["#071821", "#0c4f6b", "#00a6c7", "#5cf2ff", "#e8ffff"],
  shadow: ["#090512", "#241242", "#522585", "#9354cf", "#e0c4ff"],
};

export function hexToRgb(hex) {
  const clean = hex.replace(/^#/, "");
  const full = clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean;
  const n = Number.parseInt(full, 16);
  if (!Number.isFinite(n) || full.length !== 6) {
    throw new Error(`Invalid hex color: ${hex}`);
  }
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function createFrame(w, h) {
  return {
    w,
    h,
    color: new Uint8ClampedArray(w * h * 4),
    light: new Float32Array(w * h * 3),
  };
}

export function clearFrame(frame) {
  frame.color.fill(0);
  frame.light.fill(0);
}

export function setPixel(frame, x, y, rgb, alpha = 1) {
  const ix = Math.round(x);
  const iy = Math.round(y);
  if (ix < 0 || iy < 0 || ix >= frame.w || iy >= frame.h || alpha <= 0) return;
  if (alpha < 1) {
    const threshold = (BAYER4[((iy & 3) << 2) | (ix & 3)] + 0.5) / 16;
    if (alpha < threshold) return;
  }
  const idx = (iy * frame.w + ix) * 4;
  frame.color[idx] = rgb[0];
  frame.color[idx + 1] = rgb[1];
  frame.color[idx + 2] = rgb[2];
  frame.color[idx + 3] = 255;
}

export function addGlow(frame, cx, cy, radius, rgb, intensity = 0.45) {
  if (radius <= 0 || intensity <= 0) return;
  const x0 = Math.max(0, Math.floor(cx - radius));
  const x1 = Math.min(frame.w - 1, Math.ceil(cx + radius));
  const y0 = Math.max(0, Math.floor(cy - radius));
  const y1 = Math.min(frame.h - 1, Math.ceil(cy + radius));
  const r2 = radius * radius;
  for (let y = y0; y <= y1; y++) {
    for (let x = x0; x <= x1; x++) {
      const dx = x - cx;
      const dy = y - cy;
      const d2 = dx * dx + dy * dy;
      if (d2 >= r2) continue;
      const falloff = (1 - Math.sqrt(d2) / radius) ** 2 * intensity;
      const idx = (y * frame.w + x) * 3;
      frame.light[idx] += rgb[0] * falloff;
      frame.light[idx + 1] += rgb[1] * falloff;
      frame.light[idx + 2] += rgb[2] * falloff;
    }
  }
}

export function drawDisc(frame, cx, cy, r, rgb, alpha = 1) {
  const x0 = Math.max(0, Math.floor(cx - r));
  const x1 = Math.min(frame.w - 1, Math.ceil(cx + r));
  const y0 = Math.max(0, Math.floor(cy - r));
  const y1 = Math.min(frame.h - 1, Math.ceil(cy + r));
  const r2 = r * r;
  for (let y = y0; y <= y1; y++) {
    for (let x = x0; x <= x1; x++) {
      const dx = x - cx;
      const dy = y - cy;
      if (dx * dx + dy * dy <= r2) setPixel(frame, x, y, rgb, alpha);
    }
  }
}

export function drawRing(frame, cx, cy, r, thickness, rgb, alpha = 1) {
  const outer = r + thickness / 2;
  const inner = Math.max(0, r - thickness / 2);
  const x0 = Math.max(0, Math.floor(cx - outer));
  const x1 = Math.min(frame.w - 1, Math.ceil(cx + outer));
  const y0 = Math.max(0, Math.floor(cy - outer));
  const y1 = Math.min(frame.h - 1, Math.ceil(cy + outer));
  const o2 = outer * outer;
  const i2 = inner * inner;
  for (let y = y0; y <= y1; y++) {
    for (let x = x0; x <= x1; x++) {
      const d2 = (x - cx) ** 2 + (y - cy) ** 2;
      if (d2 <= o2 && d2 >= i2) setPixel(frame, x, y, rgb, alpha);
    }
  }
}

export function composite(frame, bgRgb = null) {
  const out = new Uint8ClampedArray(frame.w * frame.h * 4);
  const pixels = frame.w * frame.h;
  for (let i = 0; i < pixels; i++) {
    const c = i * 4;
    const l = i * 3;
    const a = frame.color[c + 3] / 255;
    const lr = frame.light[l];
    const lg = frame.light[l + 1];
    const lb = frame.light[l + 2];
    if (bgRgb) {
      out[c] = Math.min(255, Math.round(bgRgb[0] * (1 - a) + frame.color[c] * a + lr));
      out[c + 1] = Math.min(255, Math.round(bgRgb[1] * (1 - a) + frame.color[c + 1] * a + lg));
      out[c + 2] = Math.min(255, Math.round(bgRgb[2] * (1 - a) + frame.color[c + 2] * a + lb));
      out[c + 3] = 255;
    } else if (a > 0) {
      out[c] = Math.min(255, Math.round(frame.color[c] + lr));
      out[c + 1] = Math.min(255, Math.round(frame.color[c + 1] + lg));
      out[c + 2] = Math.min(255, Math.round(frame.color[c + 2] + lb));
      out[c + 3] = 255;
    } else {
      const glowMax = Math.max(lr, lg, lb);
      if (glowMax > 4) {
        const ga = Math.min(255, Math.round(glowMax));
        const scale = 255 / glowMax;
        out[c] = Math.min(255, Math.round(lr * scale));
        out[c + 1] = Math.min(255, Math.round(lg * scale));
        out[c + 2] = Math.min(255, Math.round(lb * scale));
        out[c + 3] = ga;
      }
    }
  }
  return out;
}

// Built-in pure-Node PNG encoder (zero external deps)
const CRC_TABLE = (() => {
  const tbl = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    tbl[n] = c >>> 0;
  }
  return tbl;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const t = Buffer.from(type, "ascii");
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([t, data])), 0);
  return Buffer.concat([len, t, data, crc]);
}

export function encodePNG(rgba, width, height) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (stride + 1)] = 0; // filter None
    Buffer.from(rgba.buffer, rgba.byteOffset + y * stride, stride).copy(raw, y * (stride + 1) + 1);
  }
  const idat = deflateSync(raw, { level: 6 });
  return Buffer.concat([sig, pngChunk("IHDR", ihdr), pngChunk("IDAT", idat), pngChunk("IEND", Buffer.alloc(0))]);
}

function scaleNearest(rgba, w, h, scale) {
  if (scale <= 1) return { rgba, w, h };
  const sw = w * scale;
  const sh = h * scale;
  const out = new Uint8ClampedArray(sw * sh * 4);
  for (let y = 0; y < sh; y++) {
    const sy = Math.floor(y / scale);
    for (let x = 0; x < sw; x++) {
      const sx = Math.floor(x / scale);
      const s = (sy * w + sx) * 4;
      const d = (y * sw + x) * 4;
      out[d] = rgba[s];
      out[d + 1] = rgba[s + 1];
      out[d + 2] = rgba[s + 2];
      out[d + 3] = rgba[s + 3];
    }
  }
  return { rgba: out, w: sw, h: sh };
}

function resolvePalette(nameOrArray) {
  const hexes = Array.isArray(nameOrArray) ? nameOrArray : PALETTES[nameOrArray];
  if (!hexes || hexes.length < 4) throw new Error(`Unknown or incomplete palette: ${nameOrArray}`);
  return hexes.map(hexToRgb);
}

// 6 Clean-Room Built-In Procedural Effects (100% deterministic, zero Math.random)
export const EFFECTS = {
  "fire/torch": {
    meta: {
      size: [32, 40],
      origin: [16, 30],
      fps: 16,
      duration: 0.75,
      loop: true,
      palette: "fire",
      tags: ["fire", "loop", "ambient"],
    },
    draw(frame, phase, pal, seed) {
      const ox = 16;
      const oy = 29;
      const sway = Math.sin(phase * TAU) * 1.4;
      addGlow(frame, ox + sway * 0.5, oy - 7, 13, pal[3], 0.42);
      for (let i = 0; i < 6; i++) {
        const u = i / 5;
        const y = oy - u * 13;
        const x = ox + Math.sin(phase * TAU + u * 2.4) * (1.6 * u);
        const r = Math.max(1.2, (1 - u * 0.72) * 5.2);
        const step = u < 0.25 ? 4 : u < 0.5 ? 3 : u < 0.8 ? 2 : 1;
        drawDisc(frame, x, y, r, pal[step], 1);
      }
      // Seamless periodic embers
      const rng = mulberry32(seed + 101);
      for (let e = 0; e < 5; e++) {
        const off = rng();
        const ep = (phase + off) % 1;
        const ex = ox + (rng() - 0.5) * 8 + Math.sin(ep * TAU) * 1.5;
        const ey = oy - 6 - ep * 18;
        setPixel(frame, ex, ey, ep < 0.5 ? pal[4] : pal[2], 1 - ep);
      }
    },
  },

  "ice/frost-nova": {
    meta: {
      size: [64, 48],
      origin: [32, 28],
      fps: 20,
      duration: 0.65,
      loop: false,
      palette: "ice",
      tags: ["ice", "aoe", "burst"],
      act: { windup: 0.12, hits: [{ t: 0.05, freeze: 0.08 }], recovery: 0.2 },
    },
    draw(frame, u, pal, seed) {
      if (u >= 0.999) return;
      const ox = 32;
      const oy = 26;
      const ease = 1 - (1 - u) ** 4;
      const fade = u < 0.55 ? 1 : Math.max(0, 1 - (u - 0.55) / 0.45);
      // Hero white flash on frames 0..1
      if (u < 0.14) {
        drawDisc(frame, ox, oy, 7 * (1 - u * 3), pal[4], 1);
        addGlow(frame, ox, oy, 18, pal[4], 0.6);
      }
      const radius = 3 + ease * 21;
      drawRing(frame, ox, oy, radius, Math.max(1.2, 4 * fade), pal[2], fade);
      drawRing(frame, ox, oy, Math.max(1, radius - 1.5), 1.4, pal[3], fade);
      addGlow(frame, ox, oy, radius + 4, pal[3], 0.35 * fade);

      const rng = mulberry32(seed + 202);
      for (let i = 0; i < 10; i++) {
        const ang = (i / 10) * TAU + (rng() - 0.5) * 0.2;
        const dist = radius * (0.75 + rng() * 0.35);
        const sx = ox + Math.cos(ang) * dist;
        const sy = oy + Math.sin(ang) * dist * 0.72;
        drawDisc(frame, sx, sy, 1.4 * fade, i % 2 ? pal[4] : pal[3], fade);
      }
    },
  },

  "arcane/portal": {
    meta: {
      size: [48, 48],
      origin: [24, 24],
      fps: 18,
      duration: 1.0,
      loop: true,
      palette: "arcane",
      tags: ["arcane", "loop", "portal"],
    },
    draw(frame, phase, pal, seed) {
      const ox = 24;
      const oy = 24;
      addGlow(frame, ox, oy, 18, pal[2], 0.42);
      drawDisc(frame, ox, oy, 11, pal[0], 0.92);
      drawRing(frame, ox, oy, 12 + Math.sin(phase * TAU) * 0.8, 2.2, pal[2], 1);
      drawRing(frame, ox, oy, 9.5, 1.3, pal[3], 0.85);
      const rng = mulberry32(seed + 303);
      for (let i = 0; i < 12; i++) {
        const baseA = (i / 12) * TAU + rng() * 0.3;
        const a = baseA + phase * TAU;
        const r = 6 + (i % 3) * 3.5;
        const x = ox + Math.cos(a) * r;
        const y = oy + Math.sin(a) * r;
        setPixel(frame, x, y, i % 3 === 0 ? pal[4] : pal[3], 1);
      }
    },
  },

  "impact/slash-arc": {
    meta: {
      size: [56, 44],
      origin: [24, 24],
      fps: 24,
      duration: 0.42,
      loop: false,
      palette: "holy",
      tags: ["impact", "melee", "slash"],
      act: { windup: 0.1, hits: [{ t: 0.04, freeze: 0.1 }], recovery: 0.16 },
    },
    draw(frame, u, pal, seed) {
      if (u >= 0.999) return;
      const ox = 24;
      const oy = 22;
      const ease = 1 - (1 - u) ** 3;
      const fade = u < 0.4 ? 1 : Math.max(0, 1 - (u - 0.4) / 0.6);
      const startA = -1.25 + ease * 0.9;
      const endA = -0.3 + ease * 1.95;
      const r = 15;
      const samples = 40;
      for (let i = 0; i <= samples; i++) {
        const f = i / samples;
        const a = startA + (endA - startA) * f;
        const thick = Math.sin(f * Math.PI) * 4.2 * fade;
        const x = ox + Math.cos(a) * r;
        const y = oy + Math.sin(a) * r;
        const col = u < 0.2 ? pal[4] : f > 0.65 ? pal[3] : pal[2];
        drawDisc(frame, x, y, Math.max(0.8, thick), col, fade);
      }
      addGlow(frame, ox + Math.cos(endA) * r, oy + Math.sin(endA) * r, 10, pal[3], 0.45 * fade);
      const rng = mulberry32(seed + 404);
      for (let s = 0; s < 6; s++) {
        const a = endA + (rng() - 0.5) * 0.8;
        const d = r + u * (8 + rng() * 10);
        setPixel(frame, ox + Math.cos(a) * d, oy + Math.sin(a) * d, pal[4], fade);
      }
    },
  },

  "ui/level-up": {
    meta: {
      size: [48, 48],
      origin: [24, 34],
      fps: 20,
      duration: 0.75,
      loop: false,
      palette: "holy",
      tags: ["ui", "buff", "level-up"],
    },
    draw(frame, u, pal, seed) {
      if (u >= 0.999) return;
      const ox = 24;
      const fade = u < 0.65 ? 1 : Math.max(0, 1 - (u - 0.65) / 0.35);
      // Two rising chevrons
      for (let c = 0; c < 2; c++) {
        const cy = 34 - u * 22 + c * 7;
        for (let dx = -7; dx <= 7; dx++) {
          const y = cy + Math.abs(dx) * 0.65;
          setPixel(frame, ox + dx, y, c === 0 ? pal[4] : pal[3], fade);
          setPixel(frame, ox + dx, y + 1, pal[2], fade);
        }
      }
      addGlow(frame, ox, 28 - u * 16, 13, pal[3], 0.38 * fade);
      const rng = mulberry32(seed + 505);
      for (let i = 0; i < 8; i++) {
        const sx = ox + (rng() - 0.5) * 24;
        const sy = 36 - u * (16 + rng() * 18);
        setPixel(frame, sx, sy, pal[4], fade);
      }
    },
  },

  "shadow/void-pulse": {
    meta: {
      size: [48, 48],
      origin: [24, 24],
      fps: 20,
      duration: 0.6,
      loop: false,
      palette: "shadow",
      tags: ["shadow", "pulse", "debuff"],
      act: { windup: 0.14, hits: [{ t: 0.18, freeze: 0.07 }], recovery: 0.18 },
    },
    draw(frame, u, pal) {
      if (u >= 0.999) return;
      const ox = 24;
      const oy = 24;
      if (u < 0.3) {
        const k = 1 - u / 0.3;
        drawRing(frame, ox, oy, 4 + k * 14, 1.8, pal[3], 1 - k * 0.4);
        drawDisc(frame, ox, oy, 3 + (1 - k) * 3, pal[0], 1);
      } else {
        const k = (u - 0.3) / 0.7;
        const fade = Math.max(0, 1 - k);
        const r = 4 + (1 - (1 - k) ** 3) * 16;
        drawRing(frame, ox, oy, r, Math.max(1, 3.2 * fade), pal[2], fade);
        drawRing(frame, ox, oy, Math.max(1, r - 1.5), 1.2, pal[4], fade * 0.9);
        addGlow(frame, ox, oy, r + 4, pal[3], 0.4 * fade);
      }
    },
  },
};

export function renderEffect(id, opts = {}) {
  const effect = EFFECTS[id];
  if (!effect) throw new Error(`Unknown effect id: ${id}`);
  const { meta } = effect;
  const [w, h] = meta.size;
  const fps = opts.fps ?? meta.fps;
  const seed = opts.seed ?? 1;
  const paletteName = opts.palette ?? meta.palette;
  const pal = resolvePalette(paletteName);
  const count = Math.max(2, Math.round(meta.duration * fps) + (meta.loop ? 0 : 1));
  const frame = createFrame(w, h);
  const bgDark = [12, 16, 28];

  const frames = [];
  for (let i = 0; i < count; i++) {
    const phase = meta.loop ? i / count : i / (count - 1);
    clearFrame(frame);
    effect.draw(frame, phase, pal, seed);
    frames.push({
      index: i,
      t: i / fps,
      shown: composite(frame, bgDark),
      clear: composite(frame, null),
    });
  }
  return { id, w, h, fps, count, seed, paletteName, meta, frames };
}

export function buildSpriteSheet(rendered, scale = 1) {
  const cols = Math.min(rendered.count, 8);
  const rows = Math.ceil(rendered.count / cols);
  const fw = rendered.w * scale;
  const fh = rendered.h * scale;
  const sheetW = cols * fw;
  const sheetH = rows * fh;
  const clearOut = new Uint8ClampedArray(sheetW * sheetH * 4);
  const shownOut = new Uint8ClampedArray(sheetW * sheetH * 4);
  for (let i = 0; i < sheetW * sheetH; i++) {
    const p = i * 4;
    shownOut[p] = 12;
    shownOut[p + 1] = 16;
    shownOut[p + 2] = 28;
    shownOut[p + 3] = 255;
  }
  const frameMeta = {};

  for (let i = 0; i < rendered.count; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const ox = col * fw;
    const oy = row * fh;
    const scClear = scaleNearest(rendered.frames[i].clear, rendered.w, rendered.h, scale);
    const scShown = scaleNearest(rendered.frames[i].shown, rendered.w, rendered.h, scale);

    for (let y = 0; y < fh; y++) {
      const srcRow = y * fw * 4;
      const dstRow = ((oy + y) * sheetW + ox) * 4;
      clearOut.set(scClear.rgba.subarray(srcRow, srcRow + fw * 4), dstRow);
      shownOut.set(scShown.rgba.subarray(srcRow, srcRow + fw * 4), dstRow);
    }
    frameMeta[`${rendered.id}#${String(i).padStart(3, "0")}`] = {
      frame: { x: ox, y: oy, w: fw, h: fh },
      sourceSize: { w: fw, h: fh },
      duration: Math.round(1000 / rendered.fps),
    };
  }

  const atlas = {
    frames: frameMeta,
    meta: {
      app: "shadow-illustration/pixelfx_engine",
      format: "RGBA8888",
      size: { w: sheetW, h: sheetH },
      scale: String(scale),
      pixelfx: {
        id: rendered.id,
        fps: rendered.fps,
        loop: rendered.meta.loop,
        frameSize: [fw, fh],
        columns: cols,
        pivot: [rendered.meta.origin[0] * scale, rendered.meta.origin[1] * scale],
        palette: rendered.paletteName,
        seed: rendered.seed,
        ...(rendered.meta.act ? { act: rendered.meta.act } : {}),
      },
    },
  };
  return {
    contactPng: encodePNG(shownOut, sheetW, sheetH),
    sheetPng: encodePNG(clearOut, sheetW, sheetH),
    atlas,
  };
}

export function buildPreviewHtml(rendered, built, defaultScale = 4) {
  const sheetB64 = built.sheetPng.toString("base64");
  const contactB64 = built.contactPng.toString("base64");
  const metaJson = JSON.stringify(built.atlas.meta.pixelfx).replace(/</g, "\\u003c");
  const safeId = String(rendered.id).replace(/[<>&"]/g, "");
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PixelFX Preview — ${safeId}</title>
  <style>
    :root { --bg: #0b1020; --panel: #121930; --border: #243052; --fg: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 24px; background: var(--bg); color: var(--fg); font: 14px/1.5 system-ui, -apple-system, Segoe UI, sans-serif; }
    .wrap { max-width: 960px; margin: 0 auto; display: grid; gap: 16px; }
    .header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px; }
    .header h1 { margin: 0; font-size: 20px; }
    .meta { font: 12px/1.4 ui-monospace, Consolas, monospace; color: var(--muted); }
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px; display: grid; gap: 14px; }
    .stage-wrap { display: grid; place-items: center; min-height: 260px; border-radius: 10px; border: 1px solid var(--border); overflow: auto; padding: 16px; }
    .bg-dark { background: #0c101c; }
    .bg-light { background: #f1f5f9; }
    .bg-checker { background: repeating-conic-gradient(#1e293b 0% 25%, #334155 0% 50%) 50% / 16px 16px; }
    canvas { image-rendering: pixelated; image-rendering: crisp-edges; }
    .controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    button, select { cursor: pointer; background: #1a2442; color: var(--fg); border: 1px solid var(--border); border-radius: 8px; padding: 7px 12px; font: 600 12.5px/1 system-ui, sans-serif; }
    button:hover, select:hover { border-color: var(--accent); }
    button:focus-visible, select:focus-visible, input:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
    label { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--muted); }
    input[type="range"] { accent-color: var(--accent); cursor: pointer; }
    .contact img { display: block; max-width: 100%; height: auto; image-rendering: pixelated; border-radius: 8px; border: 1px solid var(--border); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>${safeId}</h1>
      <div class="meta" id="meta-line"></div>
    </div>
    <div class="card">
      <div class="stage-wrap bg-dark" id="stage-wrap">
        <canvas id="stage"></canvas>
      </div>
      <div class="controls">
        <button id="play-btn" type="button">Pause</button>
        <button id="prev-btn" type="button" aria-label="Previous frame">&lt; Frame</button>
        <button id="next-btn" type="button" aria-label="Next frame">Frame &gt;</button>
        <label>Frame <input id="scrub" type="range" min="0" value="0" step="1"><span id="frame-label" class="meta"></span></label>
        <label>Speed
          <select id="speed">
            <option value="0.25">0.25x</option>
            <option value="0.5">0.5x</option>
            <option value="1" selected>1x</option>
            <option value="2">2x</option>
          </select>
        </label>
        <label>Zoom
          <select id="zoom">
            <option value="2">2x</option>
            <option value="4" ${defaultScale === 4 ? "selected" : ""}>4x</option>
            <option value="6" ${defaultScale === 6 ? "selected" : ""}>6x</option>
            <option value="8" ${defaultScale === 8 ? "selected" : ""}>8x</option>
          </select>
        </label>
        <label>BG
          <select id="bg">
            <option value="bg-dark" selected>Dark</option>
            <option value="bg-checker">Transparent Checker</option>
            <option value="bg-light">Light</option>
          </select>
        </label>
      </div>
    </div>
    <div class="card contact">
      <div class="meta">Contact Sheet (all frames, nearest-neighbor)</div>
      <img alt="${safeId} contact sheet" src="data:image/png;base64,${contactB64}">
    </div>
  </div>
  <script>
    const META = ${metaJson};
    const TOTAL = ${rendered.count};
    const SHEET_SRC = "data:image/png;base64,${sheetB64}";
    const canvas = document.getElementById("stage");
    const ctx = canvas.getContext("2d");
    const scrub = document.getElementById("scrub");
    const frameLabel = document.getElementById("frame-label");
    const playBtn = document.getElementById("play-btn");
    const speedSel = document.getElementById("speed");
    const zoomSel = document.getElementById("zoom");
    const bgSel = document.getElementById("bg");
    const stageWrap = document.getElementById("stage-wrap");
    scrub.max = String(TOTAL - 1);
    document.getElementById("meta-line").textContent =
      META.frameSize[0] + "x" + META.frameSize[1] + " px · " + TOTAL + " frames · " + META.fps + " fps · " +
      (META.loop ? "loop" : "one-shot") + " · palette=" + META.palette + " · seed=" + META.seed +
      (META.act ? " · hit-stop=" + JSON.stringify(META.act.hits) : "");

    const img = new Image();
    let playing = true, idx = 0, acc = 0, last = performance.now();
    const fw = META.frameSize[0], fh = META.frameSize[1], cols = META.columns;

    function resize() {
      const z = Number(zoomSel.value) / Number(${built.atlas.meta.scale});
      canvas.width = Math.max(1, Math.round(fw * z));
      canvas.height = Math.max(1, Math.round(fh * z));
      ctx.imageSmoothingEnabled = false;
      draw();
    }
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const c = idx % cols, r = Math.floor(idx / cols);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(img, c * fw, r * fh, fw, fh, 0, 0, canvas.width, canvas.height);
      scrub.value = String(idx);
      frameLabel.textContent = (idx + 1) + "/" + TOTAL;
    }
    function tick(now) {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      if (playing) {
        acc += dt * Number(speedSel.value);
        const step = 1 / META.fps;
        while (acc >= step) {
          acc -= step;
          idx = (idx + 1) % TOTAL;
        }
        draw();
      }
      requestAnimationFrame(tick);
    }
    playBtn.addEventListener("click", () => { playing = !playing; playBtn.textContent = playing ? "Pause" : "Play"; });
    document.getElementById("prev-btn").addEventListener("click", () => { playing = false; playBtn.textContent = "Play"; idx = (idx - 1 + TOTAL) % TOTAL; draw(); });
    document.getElementById("next-btn").addEventListener("click", () => { playing = false; playBtn.textContent = "Play"; idx = (idx + 1) % TOTAL; draw(); });
    scrub.addEventListener("input", () => { playing = false; playBtn.textContent = "Play"; idx = Number(scrub.value); draw(); });
    zoomSel.addEventListener("change", resize);
    bgSel.addEventListener("change", () => { stageWrap.className = "stage-wrap " + bgSel.value; });
    img.onload = () => { resize(); requestAnimationFrame(tick); };
    img.src = SHEET_SRC;
  </script>
</body>
</html>
`;
}

export function checkEffect(id) {
  const issues = [];
  const r1 = renderEffect(id, { seed: 42 });
  const r2 = renderEffect(id, { seed: 42 });
  for (let i = 0; i < r1.count; i++) {
    const a = r1.frames[i].clear;
    const b = r2.frames[i].clear;
    if (a.length !== b.length || a.some((v, idx) => v !== b[idx])) {
      issues.push(`Non-deterministic output detected on frame ${i}`);
      break;
    }
  }
  // Verify at least one frame has visible pixels
  const totalAlpha = r1.frames.reduce((acc, f) => {
    let s = 0;
    for (let i = 3; i < f.clear.length; i += 4) s += f.clear[i];
    return acc + s;
  }, 0);
  if (totalAlpha === 0) issues.push("Effect produced completely empty frames");

  // One-shot must end completely empty on its final frame
  if (!r1.meta.loop) {
    const last = r1.frames[r1.count - 1].clear;
    let lastAlpha = 0;
    for (let i = 3; i < last.length; i += 4) lastAlpha += last[i];
    if (lastAlpha !== 0) issues.push(`One-shot did not end empty (final alpha sum=${lastAlpha})`);
  }

  // Validate act timing ordering if declared
  if (r1.meta.act) {
    const hits = r1.meta.act.hits ?? [];
    for (let i = 1; i < hits.length; i++) {
      if (hits[i].t <= hits[i - 1].t) issues.push("act.hits timestamps are not strictly increasing");
    }
  }
  return { id, status: issues.length ? "FAIL" : "PASS", frames: r1.count, issues };
}

function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  if (!cmd || cmd === "--help" || cmd === "-h") {
    console.log("usage: node pixelfx_engine.mjs <list|render|check> [args]");
    process.exit(0);
  }
  if (cmd === "list") {
    console.log(
      JSON.stringify(
        {
          palettes: Object.keys(PALETTES),
          effects: Object.entries(EFFECTS).map(([id, e]) => ({
            id,
            size: e.meta.size,
            fps: e.meta.fps,
            loop: e.meta.loop,
            palette: e.meta.palette,
            tags: e.meta.tags,
          })),
        },
        null,
        2
      )
    );
    return;
  }
  if (cmd === "check") {
    const ids = rest.length ? rest : Object.keys(EFFECTS);
    const results = ids.map((id) => checkEffect(id));
    const failed = results.filter((r) => r.status !== "PASS").length;
    console.log(JSON.stringify({ total: results.length, passed: results.length - failed, failed, results }, null, 2));
    process.exit(failed ? 1 : 0);
  }
  if (cmd === "render") {
    const flags = {};
    let id = null;
    for (let i = 0; i < rest.length; i++) {
      const a = rest[i];
      if (!a.startsWith("--") && !id) id = a;
      else if (a === "--sheet") flags.sheet = true;
      else if (a === "--preview") flags.preview = true;
      else flags[a.slice(2)] = rest[++i];
    }
    if (!id || !flags.out) {
      console.error("usage: node pixelfx_engine.mjs render <id> --out <dir> [--sheet] [--preview] [--palette name] [--seed N] [--scale N]");
      process.exit(2);
    }
    const rendered = renderEffect(id, {
      palette: flags.palette,
      seed: flags.seed ? Number.parseInt(flags.seed, 10) : 1,
    });
    const scale = flags.scale ? Math.max(1, Math.min(8, Number.parseInt(flags.scale, 10))) : 2;
    const outDir = resolve(flags.out, ...id.split("/"));
    mkdirSync(outDir, { recursive: true });
    const built = buildSpriteSheet(rendered, scale);
    const written = [];
    const contactPath = join(outDir, "contact.png");
    writeFileSync(contactPath, built.contactPng);
    written.push(contactPath);
    if (flags.sheet) {
      const base = id.split("/")[1];
      const sheetPath = join(outDir, `${base}.png`);
      const jsonPath = join(outDir, `${base}.json`);
      writeFileSync(sheetPath, built.sheetPng);
      writeFileSync(jsonPath, JSON.stringify(built.atlas, null, 2));
      written.push(sheetPath, jsonPath);
    }
    if (flags.preview) {
      const previewPath = join(outDir, "preview.html");
      writeFileSync(previewPath, buildPreviewHtml(rendered, built, Math.max(4, scale)));
      written.push(previewPath);
    }
    console.log(JSON.stringify({ status: "RENDERED", id, frames: rendered.count, written }, null, 2));
    return;
  }
  console.error(`Unknown command: ${cmd}`);
  process.exit(2);
}

main();
