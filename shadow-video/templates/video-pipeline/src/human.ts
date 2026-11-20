import type { Locator, Page } from "playwright";
import { settings } from "./config.ts";

const rand = (min: number, max: number) => min + Math.random() * (max - min);
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
// Sinus: puncak kecepatan lebih rendah daripada kubik, sehingga gerakan panjang tidak terlihat menyentak di video 25 fps.
const easeInOutSine = (t: number) => -(Math.cos(Math.PI * t) - 1) / 2;
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, Math.max(0, ms)));

interface Point {
  x: number;
  y: number;
}

/**
 * Human-like input driver. Keeps the authoritative cursor position in Node so it survives
 * navigations: after every main-frame load the overlay is re-synced to `pos`.
 */
export class Human {
  pos: Point;
  private readonly slow = settings.slowFactor();

  constructor(
    private readonly page: Page,
    start: Point,
  ) {
    this.pos = { ...start };
  }

  wait(ms: number) {
    return sleep(ms * this.slow);
  }

  /** Re-apply the Node-side cursor position to the (possibly new) document. */
  async syncCursor(): Promise<void> {
    const { x, y } = this.pos;
    await this.page
      .evaluate(([px, py]) => (window as unknown as { __pwCursor?: { set(a: number, b: number): void } }).__pwCursor?.set(px!, py!), [x, y])
      .catch(() => undefined); // page may be mid-navigation; next load event re-syncs
    await this.page.mouse.move(x, y).catch(() => undefined);
  }

  /** Smooth bezier move with ease-in-out at ~60 fps; duration 450–1300 ms by distance. */
  async moveTo(target: Point): Promise<void> {
    const from = this.pos;
    const dx = target.x - from.x;
    const dy = target.y - from.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 2) return;
    const duration = clamp(450 + dist * 0.55, 450, 1300) * rand(0.92, 1.08) * this.slow;
    // Control points: offset perpendicular to the path for a gentle arc (random side, 4–14% of distance).
    const nx = -dy / dist;
    const ny = dx / dist;
    const bend = dist * rand(0.04, 0.14) * (Math.random() < 0.5 ? -1 : 1);
    const c1 = { x: from.x + dx * 0.3 + nx * bend, y: from.y + dy * 0.3 + ny * bend };
    const c2 = { x: from.x + dx * 0.7 + nx * bend * 0.6, y: from.y + dy * 0.7 + ny * bend * 0.6 };
    const vp = this.page.viewportSize() ?? { width: 1920, height: 1080 };
    const steps = Math.max(8, Math.round(duration / (1000 / 60)));
    const t0 = performance.now();
    for (let i = 1; i <= steps; i++) {
      const t = easeInOutSine(i / steps);
      const u = 1 - t;
      const x = u ** 3 * from.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t ** 3 * target.x;
      const y = u ** 3 * from.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t ** 3 * target.y;
      const p = { x: clamp(x, 0, vp.width - 1), y: clamp(y, 0, vp.height - 1) };
      await this.page.mouse.move(p.x, p.y);
      this.pos = p;
      // Schedule against wall clock so slow CDP round-trips don't stretch the motion.
      await sleep(t0 + (duration * i) / steps - performance.now());
    }
    this.pos = { ...target };
  }

  /** Random point near the element's center (inner ~50%), not the exact center. */
  async pointIn(locator: Locator): Promise<Point> {
    const box = await locator.boundingBox();
    if (!box) throw new Error("element has no bounding box (not visible / detached)");
    const jx = Math.min(box.width * 0.25, 40);
    const jy = Math.min(box.height * 0.25, 12);
    return {
      x: box.x + box.width / 2 + rand(-jx, jx),
      y: box.y + box.height / 2 + rand(-jy, jy),
    };
  }

  /** Wait until the element's box stops moving (animations/transitions finished). Non-fatal. */
  async waitStable(locator: Locator, timeoutMs = 2000): Promise<void> {
    const end = Date.now() + timeoutMs;
    let prev = await locator.boundingBox();
    let still = 0;
    while (Date.now() < end) {
      await sleep(50);
      const cur = await locator.boundingBox();
      const same =
        !!prev && !!cur && Math.abs(prev.x - cur.x) < 0.5 && Math.abs(prev.y - cur.y) < 0.5 && Math.abs(prev.width - cur.width) < 0.5;
      still = same ? still + 1 : 0;
      if (still >= 2) return;
      prev = cur;
    }
  }

  /**
   * Elemen di dalam wadah bergulir (misalnya daftar opsi dropdown) bisa terlihat di viewport tetapi terpotong
   * wadahnya, sehingga titik tengahnya berada di luar daftar dan klik menutup dropdown. Gulir wadah itu saja.
   */
  private async revealInScrollParent(locator: Locator): Promise<void> {
    const clipped = await locator
      .evaluate((el) => {
        const r = el.getBoundingClientRect();
        for (let p = el.parentElement; p; p = p.parentElement) {
          const oy = getComputedStyle(p).overflowY;
          if ((oy === "auto" || oy === "scroll") && p.scrollHeight > p.clientHeight) {
            const pr = p.getBoundingClientRect();
            return r.top < pr.top || r.bottom > pr.bottom;
          }
        }
        return false;
      })
      .catch(() => false);
    if (!clipped) return;
    await locator.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" }));
    await this.waitStable(locator, 1500);
  }

  /** Smoothly bring an element into view with small wheel steps; falls back to smooth scrollIntoView. */
  async scrollIntoView(locator: Locator): Promise<void> {
    await this.scrollIntoViewport(locator);
    await this.revealInScrollParent(locator);
  }

  private async scrollIntoViewport(locator: Locator): Promise<void> {
    const vp = this.page.viewportSize() ?? { width: 1920, height: 1080 };
    const margin = Math.round(vp.height * 0.12);
    for (let iter = 0; iter < 80; iter++) {
      const box = await locator.boundingBox();
      if (!box) return;
      if (box.y >= margin && box.y + box.height <= vp.height - margin) return;
      if (box.height > vp.height - 2 * margin && box.y <= margin && box.y + box.height >= vp.height - margin) return; // bigger than view
      const centerOffset = box.y + box.height / 2 - vp.height / 2;
      const step = Math.sign(centerOffset) * Math.min(Math.abs(centerOffset), rand(70, 110));
      await this.page.mouse.wheel(0, step);
      await sleep(rand(14, 22) * this.slow);
      const after = await locator.boundingBox();
      if (after && Math.abs(after.y - box.y) < 1) {
        // The scroll container under the cursor isn't the element's container: let the browser do it smoothly.
        await locator.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" }));
        await this.waitStable(locator, 2500);
        return;
      }
    }
    await this.waitStable(locator, 1000);
  }

  /** Smooth wheel scroll by deltaY px in small increments (scrolls whatever is under the cursor). */
  async wheel(deltaY: number): Promise<void> {
    let remaining = deltaY;
    while (Math.abs(remaining) > 0.5) {
      const step = Math.sign(remaining) * Math.min(Math.abs(remaining), rand(60, 100));
      await this.page.mouse.wheel(0, step);
      remaining -= step;
      await sleep(rand(14, 22) * this.slow);
    }
    await this.wait(250);
  }

  /** Visible + scrolled into view + stable, then glide the cursor onto it. */
  async approach(locator: Locator, timeout: number): Promise<void> {
    await locator.waitFor({ state: "visible", timeout });
    await this.scrollIntoView(locator);
    await this.waitStable(locator);
    await this.moveTo(await this.pointIn(locator));
  }

  async hover(locator: Locator, timeout: number, restMs?: number): Promise<void> {
    await this.approach(locator, timeout);
    await this.wait(restMs ?? rand(200, 400));
  }

  /**
   * Siap diklik tanpa menyentuh mouse: tidak nonaktif, dan titik tengahnya tidak tertutup elemen lain.
   * Jangan memakai `locator.click({ trial: true })`: Playwright memindahkan mouse ke target saat trial,
   * sehingga kursor overlay melompat ke tombol lalu kembali sebelum gerakan halus dimulai.
   */
  private async waitActionable(locator: Locator, timeout: number): Promise<void> {
    const end = Date.now() + timeout;
    let covered = 0;
    for (;;) {
      const state = await locator
        .evaluate((el) => {
          if (el.matches(":disabled") || el.closest("[aria-disabled=\"true\"]")) return "disabled";
          const r = el.getBoundingClientRect();
          const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          if (!hit) return "covered";
          const label = hit.closest("label");
          const labelled = label !== null && "control" in label && label.control === el;
          return el === hit || el.contains(hit) || hit.contains(el) || labelled ? "ready" : "covered";
        })
        .catch(() => "covered");
      if (state === "ready") return;
      // Tertutup sementara (animasi, overlay yang sedang hilang) ditunggu sebentar; klik sungguhan tetap memverifikasi.
      if (state === "covered" && ++covered >= 20) return;
      if (Date.now() > end) throw new Error(`element is ${state} (timeout ${timeout} ms)`);
      await sleep(100);
    }
  }

  async click(locator: Locator, timeout: number): Promise<void> {
    await locator.waitFor({ state: "visible", timeout });
    await this.scrollIntoView(locator);
    await this.waitStable(locator);
    // Pemeriksaan kesiapan SEBELUM kursor tiba, tanpa memindahkan mouse.
    await this.waitActionable(locator, timeout);
    await this.moveTo(await this.pointIn(locator));
    await this.wait(rand(200, 400)); // hover before click; cursor stays exactly here through down/up
    await this.page.mouse.down();
    await sleep(rand(60, 110));
    await this.page.mouse.up();
    await this.wait(rand(250, 450)); // short pause after click
  }

  /** Per-character typing with 60–120 ms random delay (never fill()). */
  async type(
    locator: Locator,
    text: string,
    timeout: number,
    opts: { clear?: boolean; pressEnter?: boolean; atCaret?: boolean } = {},
  ): Promise<void> {
    if (opts.atCaret) {
      // Caret sudah ditempatkan oleh aksi sebelumnya; klik di titik acak akan memindahkannya.
      await locator.waitFor({ state: "visible", timeout });
      for (const ch of text) {
        await this.page.keyboard.type(ch);
        await sleep(rand(60, 120) * this.slow);
      }
      if (opts.pressEnter) {
        await this.wait(rand(200, 350));
        await this.page.keyboard.press("Enter");
      }
      await this.wait(rand(200, 350));
      return;
    }
    await this.click(locator, timeout);
    if (opts.clear) {
      await this.page.keyboard.press("ControlOrMeta+A");
      await this.page.keyboard.press("Backspace");
      await this.wait(150);
    }
    for (const ch of text) {
      await locator.pressSequentially(ch, { timeout });
      await sleep(rand(60, 120) * this.slow);
    }
    if (opts.pressEnter) {
      await this.wait(rand(200, 350));
      await locator.press("Enter");
    }
    await this.wait(rand(200, 350));
  }

  /** Show a click ripple without a real click (used for native <select>, whose popup is not captured). */
  async fakePress(): Promise<void> {
    const { x, y } = this.pos;
    await this.page.evaluate(([px, py]) => (window as unknown as { __pwCursor?: { ripple(a: number, b: number): void } }).__pwCursor?.ripple(px!, py!), [x, y]);
  }
}
