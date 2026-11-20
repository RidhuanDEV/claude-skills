import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Load .env once (Node >= 20.12 built-in; no dotenv dependency). Missing .env is fine.
const envFile = path.join(ROOT, ".env");
if (existsSync(envFile)) process.loadEnvFile(envFile);

export const PATHS = {
  root: ROOT,
  scenes: path.join(ROOT, "scenes"),
  assets: path.join(ROOT, "assets"),
  auth: path.join(ROOT, "auth"),
  storageState: path.join(ROOT, "auth", "storageState.json"),
  cache: path.join(ROOT, "cache"),
  ttsCache: path.join(ROOT, "cache", "tts"),
  recordCache: path.join(ROOT, "cache", "record"),
  snapshotAuth: path.join(ROOT, "cache", "snapshot-auth"),
  output: path.join(ROOT, "output"),
  errors: path.join(ROOT, "output", "errors"),
  e2e: path.join(ROOT, "output", "e2e"),
};

function env(name: string): string | undefined {
  const v = process.env[name]?.trim();
  return v ? v : undefined;
}

function num(name: string, fallback: number): number {
  const raw = env(name);
  if (raw === undefined) return fallback;
  const n = Number(raw);
  if (!Number.isFinite(n)) throw new Error(`Env ${name} must be a number, got "${raw}"`);
  return n;
}

export function baseUrl(): string {
  const raw = env("BASE_URL");
  if (!raw) throw new Error("BASE_URL is not set. Copy .env.example to .env and fill it in.");
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(`BASE_URL is not a valid URL: "${raw}"`);
  }
  const blocked = (env("BLOCKED_HOSTS") ?? "")
    .split(",")
    .map((h) => h.trim().toLowerCase())
    .filter(Boolean);
  if (blocked.includes(url.hostname.toLowerCase())) {
    throw new Error(`BASE_URL host "${url.hostname}" is in BLOCKED_HOSTS. Refusing to run (staging only).`);
  }
  return raw.replace(/\/+$/, "");
}

export function resolveUrl(base: string, target: string): string {
  if (/^(https?:|data:|about:|file:)/i.test(target)) return target;
  return base + (target.startsWith("/") ? target : `/${target}`);
}

export const credentials = {
  email: () => env("LOGIN_EMAIL"),
  password: () => env("LOGIN_PASSWORD"),
};

export const settings = {
  voice: () => env("TTS_VOICE") ?? "id-ID-GadisNeural",
  rate: () => env("TTS_RATE") ?? "+0%",
  pitch: () => env("TTS_PITCH") ?? "+0Hz",
  headed: () => env("HEADED") === "1",
  /**
   * Login yang direkam (recordLogin) dan `login --auto` dibuka headed secara bawaan karena
   * Cloudflare Turnstile menolak browser headless. Aplikasi tanpa captcha dapat memakai
   * RECORD_LOGIN_HEADED=0. Isi video tidak berubah karena diambil dari recordVideo viewport.
   */
  recordLoginHeaded: () => env("RECORD_LOGIN_HEADED") !== "0",
  slowFactor: () => Math.max(0.1, num("SLOW_FACTOR", 1)),
  avOffsetMs: () => num("AV_OFFSET_MS", 0),
  outputFps: () => num("OUTPUT_FPS", 25),
  crf: () => num("X264_CRF", 18),
  preset: () => env("X264_PRESET") ?? "slow",
};

export const bins = {
  ffmpeg: () => env("FFMPEG_PATH") ?? "ffmpeg",
  ffprobe: () => env("FFPROBE_PATH") ?? "ffprobe",
  python: () => {
    const explicit = env("PYTHON_PATH");
    if (explicit) return explicit;
    const venv = path.join(ROOT, ".venv", "Scripts", "python.exe");
    if (existsSync(venv)) return venv;
    const venvPosix = path.join(ROOT, ".venv", "bin", "python");
    if (existsSync(venvPosix)) return venvPosix;
    return "python";
  },
};

/**
 * Browser launch options. Cloudflare Turnstile on the login page rejects Playwright's bundled
 * Chromium (error 600010, headless AND headed) and headless Chrome; only headed Google Chrome with
 * the automation flag off passes. So default to the installed Chrome (BROWSER_CHANNEL=chromium to opt out).
 */
export function launchOptions(headless: boolean) {
  const channel = env("BROWSER_CHANNEL") ?? "chrome";
  const real = channel !== "chromium";
  return {
    headless,
    channel: real ? channel : undefined,
    ignoreDefaultArgs: real ? ["--enable-automation"] : undefined,
    args: [
      ...(real ? ["--disable-blink-features=AutomationControlled"] : []),
      // Bahasa antarmuka browser (misalnya tombol input berkas "Pilih File") mengikuti Bahasa Indonesia.
      // Tidak memakai emulasi locale context karena Turnstile menolaknya (lihat recorder.ts).
      `--lang=${env("BROWSER_LANG") ?? "id-ID"}`,
      // Headed recordings: pin window size/position and ignore Windows display scaling (125% etc.),
      // otherwise a resize/DPI change mid-recording zooms the page and leaves a grey band in the video.
      ...(headless ? [] : ["--force-device-scale-factor=1", "--window-position=0,0", "--window-size=1940,1200"]),
    ],
  };
}

/** Pause added after every scene, on top of max(action, audio). */
export const SCENE_GAP_MS = 300;
