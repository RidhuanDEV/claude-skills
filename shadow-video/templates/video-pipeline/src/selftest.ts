import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { merge } from "./merge.ts";
import { record } from "./recorder.ts";
import { parseTutorial } from "./schema.ts";
import { runTts } from "./tts/index.ts";
import { e2e, type E2eOptions } from "./e2e.ts";

/**
 * Offline end-to-end check (no staging, no credentials): serves two local pages on 127.0.0.1,
 * then runs tts -> record -> merge. Exercises cursor overlay, ripple, typing, native select,
 * smooth scroll, click-navigation and cursor persistence across page loads.
 */
const PAGE_STYLE = `
  body { font-family: system-ui, sans-serif; margin: 0; background: #F3F5F7; color: #111827; }
  header { background: #0f3d7a; color: #fff; padding: 24px 48px; display: flex; gap: 32px; align-items: center; }
  header a { color: #fff; font-size: 22px; }
  main { padding: 48px; max-width: 900px; }
  label { display: block; margin: 24px 0 8px; font-size: 20px; }
  input, select { font-size: 22px; padding: 10px 14px; width: 420px; border: 1px solid #9ca3af; border-radius: 8px; }
  button { font-size: 22px; padding: 12px 28px; border-radius: 8px; border: 0; background: #2563eb; color: #fff; cursor: pointer; }
  .spacer { height: 1800px; background: repeating-linear-gradient(#F3F5F7 0 120px, #e5e7eb 120px 240px); margin: 32px 0; }
`;
const PAGES: Record<string, string> = {
  "/": `<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Uji 1</title><style>${PAGE_STYLE}</style></head><body>
    <header><strong style="font-size:26px">Video Selftest</strong><a id="nav-two" href="/dua">Halaman Dua</a></header>
    <main><h1>Halaman Satu</h1>
      <label for="nama">Nama</label><input id="nama" placeholder="Masukan nama">
      <label for="kota">Kota</label><select id="kota"><option>Jakarta</option><option>Surabaya</option><option>Kupang</option></select>
      <div class="spacer"></div>
      <button id="bawah" onclick="this.textContent='Tersimpan'">Simpan</button>
      <div style="height:400px"></div></main></body></html>`,
  "/dua": `<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Uji 2</title><style>${PAGE_STYLE}</style></head><body>
    <header><strong style="font-size:26px">Video Selftest</strong><a href="/">Halaman Satu</a></header>
    <main><h1 id="judul-dua">Halaman Dua</h1><p style="font-size:22px">Navigasi berhasil tanpa page.goto.</p>
      <button id="ok">Selesai</button></main></body></html>`,
};

function serve(): Promise<Server> {
  const server = createServer((req, res) => {
    const body = PAGES[(req.url ?? "/").split("?")[0]!];
    if (!body) {
      res.writeHead(404).end();
      return;
    }
    setTimeout(() => res.writeHead(200, { "content-type": "text/html; charset=utf-8" }).end(body), 150); // simulate latency
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}

export const SELFTEST_SCENES = {
  id: "selftest",
  title: "Selftest lokal",
  scenes: [
    {
      id: "intro",
      narration: "Ini adalah uji coba pipeline video. Perhatikan gerakan kursor di layar.",
      actions: [{ type: "goto", url: "/" }, { type: "hover", selector: "h1" }],
    },
    {
      id: "isi-nama",
      narration: "Klik kolom nama, lalu ketik nama secara perlahan.",
      actions: [{ type: "type", selector: "#nama", text: "Demo – Budi" }],
    },
    {
      id: "pilih-kota",
      narration: "Pilih kota Surabaya pada daftar.",
      actions: [{ type: "select", selector: "#kota", label: "Surabaya" }],
    },
    {
      id: "simpan",
      narration: "Gulir ke bawah dengan halus, lalu klik tombol simpan.",
      actions: [{ type: "scroll", to: "#bawah" }, { type: "click", selector: "#bawah" }, { type: "waitFor", selector: "text=Tersimpan" }],
    },
    {
      id: "pindah-halaman",
      narration: "Kembali ke atas dan buka halaman dua lewat menu. Posisi kursor tetap terjaga.",
      actions: [
        { type: "scroll", deltaY: -2400 },
        { type: "click", selector: "#nav-two" },
        { type: "waitFor", url: "/dua" },
        { type: "hover", selector: "#ok" },
      ],
    },
  ],
};

/**
 * Offline E2E check (no TTS, no ffmpeg, no credentials): runs the same scenes through the GUI E2E runner.
 * Fails (exit 1) when any step fails, so it is a quick proof that the engine works on this host.
 */
export async function selftestE2e(opts: E2eOptions): Promise<boolean> {
  const server = await serve();
  const base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  try {
    const t = parseTutorial({ ...SELFTEST_SCENES, recordLogin: true }, "selftest");
    return (await e2e(t, opts, base)).status === "PASS";
  } finally {
    server.close();
  }
}

export async function selftest(): Promise<void> {
  const server = await serve();
  const base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  try {
    const t = parseTutorial({ ...SELFTEST_SCENES, recordLogin: true }, "selftest");
    const manifest = await runTts(t);
    const tl = await record(t, manifest, { baseUrl: base });
    await merge(tl, manifest);
  } finally {
    server.close();
  }
}
