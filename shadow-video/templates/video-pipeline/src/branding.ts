import { existsSync } from "node:fs";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { bins, PATHS } from "./config.ts";
import { probeDurationMs, runOrThrow } from "./media.ts";
import { project, type Chapter } from "./project.ts";

/** Chapters and combined guides come from video.config.json (one intro card per chapter, before its first video). */
const CHAPTERS = (): Chapter[] => project().chapters;
const GUIDES = () => project().guides;

/** File-name slug for per-module outputs, e.g. "02-membuat-laporan". */
export const chapterSlug = (c: { no: string; title: string }) =>
  `${c.no}-${c.title.toLowerCase().replace(/&/g, "dan").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;

const BRAND_DIR = path.join(PATHS.output, "branding");
const INTRO_MS = 3500;
// Brand images for title cards/thumbnails: video.config.json brand, optionally overridden in .env.
// Paths are relative to video-pipeline/ or absolute.
const brandPath = (envName: string, fallback: string) => path.resolve(PATHS.root, process.env[envName]?.trim() || fallback);
const LOGO_S = () => brandPath("BRAND_LOGO_ICON", project().brand.logoIcon);
const LOGO_FULL = () => brandPath("BRAND_LOGO_FULL", project().brand.logoFull);

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const dataUri = async (file: string, mime: string) => `data:${mime};base64,${(await readFile(file)).toString("base64")}`;

const BASE_CSS = () => `
  * { margin: 0; box-sizing: border-box; }
  html, body { width: 100%; height: 100%; font-family: "Segoe UI", system-ui, sans-serif; }
  .bg { position: absolute; inset: 0; background: radial-gradient(120% 120% at 85% 20%, ${project().brand.backgroundFrom} 0%, ${project().brand.backgroundTo} 100%); overflow: hidden; }
  .bg .s { position: absolute; right: -6%; top: 50%; transform: translateY(-50%); height: 118%; opacity: .10; }
  .bg .bar { position: absolute; left: 0; bottom: 0; height: 1.2%; width: 100%; background: ${project().brand.accent}; }
  .bg .foot { position: absolute; left: 6%; bottom: 5%; color: #94a3b8; font-size: 1.45vw; letter-spacing: .02em; }
`;

/** Static PNG layers rendered with Chromium: background, and a transparent title layer that ffmpeg slides in. */
async function renderLayers(): Promise<void> {
  await mkdir(BRAND_DIR, { recursive: true });
  const s = await dataUri(LOGO_S(), "image/png");
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
    await page.setContent(`<style>${BASE_CSS()}</style><div class="bg"><img class="s" src="${s}"><div class="bar"></div>
      <div class="foot">${esc(project().cardFooter)}</div></div>`);
    await page.screenshot({ path: path.join(BRAND_DIR, "card-bg.png") });
    for (const c of CHAPTERS()) {
      await page.setContent(`<style>${BASE_CSS()}
        .t { position: absolute; left: 6%; top: 50%; transform: translateY(-50%); width: 70%; }
        .no { color: ${project().brand.accent}; font-weight: 700; font-size: 34px; letter-spacing: .32em; }
        .line { width: 120px; height: 6px; background: ${project().brand.accent}; border-radius: 3px; margin: 22px 0 30px; }
        h1 { color: #fff; font-size: 92px; line-height: 1.08; font-weight: 700; }
        p { color: #cbd5e1; font-size: 38px; margin-top: 26px; }
        </style><div class="t"><div class="no">${esc(project().chapterLabel)} ${c.no}</div><div class="line"></div><h1>${esc(c.title)}</h1><p>${esc(c.subtitle)}</p></div>`);
      await page.screenshot({ path: path.join(BRAND_DIR, `title-${c.no}.png`), omitBackground: true });
    }
  } finally {
    await browser.close();
  }
}

/** 3.5 s intro per chapter: fade in, title slides in from the left (ease-out), fade out. Same codec params as merge.ts. */
async function renderIntros(): Promise<void> {
  const d = (INTRO_MS / 1000).toFixed(2);
  for (const c of readyChapters()) {
    const out = path.join(BRAND_DIR, `intro-${c.no}.mp4`);
    await runOrThrow(bins.ffmpeg(), [
      "-y", "-hide_banner", "-loglevel", "error",
      "-loop", "1", "-framerate", "25", "-t", d, "-i", path.join(BRAND_DIR, "card-bg.png"),
      "-loop", "1", "-framerate", "25", "-t", d, "-i", path.join(BRAND_DIR, `title-${c.no}.png`),
      "-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo",
      "-filter_complex",
      `[0:v]format=yuv420p[bg];[1:v]format=rgba[tt];` +
        `[bg][tt]overlay=x='-W*0.45*pow(1-min(t/0.9\\,1)\\,3)':y=0:format=auto,` +
        `fade=t=in:st=0:d=0.35,fade=t=out:st=${(INTRO_MS / 1000 - 0.45).toFixed(2)}:d=0.45,fps=25,format=yuv420p[v]`,
      "-map", "[v]", "-map", "2:a",
      "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high", "-video_track_timescale", "12800",
      "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
      "-t", d, "-movflags", "+faststart", out,
    ], `intro ${c.no}`, 120_000);
  }
}

/** Thumbnails (1280x720): one per chapter + one for the full guide, using a real frame from the module video. */
async function renderThumbnails(): Promise<void> {
  const logo = await dataUri(LOGO_FULL(), "image/png");
  const s = await dataUri(LOGO_S(), "image/png");
  const frames: Record<string, string> = {};
  for (const c of readyChapters()) {
    const video = path.join(PATHS.output, `${c.videos[0]}.mp4`);
    const jpg = path.join(BRAND_DIR, `frame-${c.no}.jpg`);
    const at = Math.round((await probeDurationMs(video)) * 0.45) / 1000;
    await runOrThrow(bins.ffmpeg(), ["-y", "-hide_banner", "-loglevel", "error", "-ss", String(at), "-i", video, "-frames:v", "1", "-q:v", "3", jpg], `frame ${c.no}`, 60_000);
    frames[c.no] = await dataUri(jpg, "image/jpeg");
  }
  const css = `${BASE_CSS()}
    .logo { position: absolute; left: 6%; top: 8%; height: 9%; background: #fff; border-radius: 14px; padding: 10px 18px; }
    .t { position: absolute; left: 6%; top: 27%; width: 44%; }
    .no { color: ${project().brand.accent}; font-weight: 700; font-size: 26px; letter-spacing: .3em; }
    h1 { color: #fff; font-size: 60px; line-height: 1.07; font-weight: 800; margin-top: 16px; }
    p { color: #cbd5e1; font-size: 26px; margin-top: 18px; }
    .shot { position: absolute; right: 4%; top: 50%; width: 46%; transform: translateY(-50%) perspective(1400px) rotateY(-9deg);
            border-radius: 14px; box-shadow: 0 30px 70px rgba(0,0,0,.55); border: 3px solid rgba(255,255,255,.18); }
    .stack .shot:nth-child(1) { top: 34%; right: 12%; width: 38%; } .stack .shot:nth-child(2) { top: 52%; right: 6%; width: 38%; } .stack .shot:nth-child(3) { top: 70%; right: 0%; width: 38%; }`;
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
    const shell = (body: string) => `<style>${css}</style><div class="bg"><img class="s" src="${s}"><div class="bar"></div></div>${body}`;
    for (const c of readyChapters()) {
      await page.setContent(shell(`<img class="logo" src="${logo}"><div class="t"><div class="no">${esc(project().chapterLabel)} ${c.no}</div><h1>${esc(c.title)}</h1><p>${esc(c.subtitle)}</p></div><img class="shot" src="${frames[c.no]}">`));
      await page.screenshot({ path: path.join(BRAND_DIR, `thumbnail-${c.no}.png`) });
    }
    for (const guide of GUIDES()) {
      // The first chapter is usually login/orientation, so prefer frames from the chapters after it.
      const shots = guide.chapters.slice(guide.chapters.length > 1 ? 1 : 0).filter((no) => frames[no]).slice(-3);
      await page.setContent(shell(`<img class="logo" src="${logo}"><div class="t"><div class="no">${esc(project().guideLabel)}</div><h1>${esc(guide.title)}</h1><p>${esc(guide.subtitle)}</p></div>
        <div class="stack">${shots.map((no) => `<img class="shot" src="${frames[no]}">`).join("")}</div>`));
      await page.screenshot({ path: path.join(PATHS.output, `${guide.slug}-thumbnail.png`) });
    }
  } finally {
    await browser.close();
  }
}

/** Chapters whose videos all exist (lets you build before every module is recorded; missing ones are listed). */
export function readyChapters() {
  const ready = CHAPTERS().filter((c) => c.videos.every((v) => existsSync(path.join(PATHS.output, `${v}.mp4`))));
  const missing = CHAPTERS().filter((c) => !ready.includes(c)).map((c) => c.no);
  if (missing.length) console.warn(`[branding] skipping chapter(s) without videos yet: ${missing.join(", ")}`);
  return ready;
}

/** Kartu judul dan thumbnail untuk semua bab yang videonya sudah ada. */
export async function buildBranding(): Promise<void> {
  await renderLayers();
  await renderIntros();
  await renderThumbnails();
  console.log(`[branding] intros + thumbnails -> ${BRAND_DIR}`);
}

/**
 * Video lengkap yang semua modulnya sudah direkam, dengan urutan concat (kartu judul lalu rekaman modul)
 * dan daftar bab untuk penanda waktu YouTube. Ids relatif terhadap output/.
 */
export function readyGuides(): Array<{ slug: string; title: string; ids: string[]; chapters: Array<{ title: string; ids: string[] }> }> {
  const ready = new Map(readyChapters().map((c) => [c.no, c]));
  return GUIDES().filter((guide) => {
    const missing = guide.chapters.filter((no) => !ready.has(no));
    if (missing.length) console.warn(`[branding] ${guide.slug} dilewati, modul belum direkam: ${missing.join(", ")}`);
    return missing.length === 0;
  }).map((guide) => {
    const chapters = guide.chapters.flatMap((no) => {
      const c = ready.get(no);
      return c ? [{ title: `${project().chapterLabel.charAt(0)}${project().chapterLabel.slice(1).toLowerCase()} ${c.no} - ${c.title.replace(/&/g, "dan")}`, ids: [`branding/intro-${c.no}`, ...c.videos] }] : [];
    });
    return { slug: guide.slug, title: guide.title, ids: chapters.flatMap((c) => c.ids), chapters };
  });
}
