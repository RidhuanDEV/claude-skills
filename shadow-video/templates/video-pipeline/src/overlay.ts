/**
 * Browser-side init script (passed to context.addInitScript). Must be fully self-contained:
 * it is serialized and runs in every document before the app's own scripts.
 *  - anti white-flash background on html/body (low specificity, app CSS still wins once loaded)
 *  - optional hidden scrollbars
 *  - fake cursor overlay that follows real mousemove events (headless video has no cursor)
 *  - click ripple at the overlay cursor position on mousedown (no press animation on the cursor)
 *  - cursor position restored on new documents from sessionStorage; Node re-syncs it too
 */
export interface OverlayOptions {
  background: string;
  hideScrollbars: boolean;
  cursor: "arrow" | "touch";
  start: { x: number; y: number }; // fraction of viewport
}

export function overlayInitScript(o: OverlayOptions): void {
  if (window.top !== window) return; // top frame only
  const w = window as unknown as Record<string, unknown>;
  if (w.__pwCursor) return;
  const KEY = "__pwCursorPos";

  let pos = { x: Math.round(innerWidth * o.start.x), y: Math.round(innerHeight * o.start.y) };
  try {
    const saved = sessionStorage.getItem(KEY);
    if (saved) pos = JSON.parse(saved) as { x: number; y: number };
  } catch {
    /* storage may be blocked; fall back to start position */
  }

  const css = `
    :where(html, body) { background-color: ${o.background}; }
    #__pw-cursor, #__pw-cursor * , .__pw-ripple { pointer-events: none !important; }
    #__pw-cursor { position: fixed; left: 0; top: 0; z-index: 2147483647; will-change: transform; }
    #__pw-cursor svg { display: block; filter: drop-shadow(0 2px 3px rgba(0,0,0,.45)); }
    #__pw-cursor.__touch > div {
      width: 34px; height: 34px; margin: -17px 0 0 -17px; border-radius: 50%;
      background: rgba(255,255,255,.55); border: 3px solid rgba(17,24,39,.85);
      box-shadow: 0 2px 6px rgba(0,0,0,.4);
    }
    .__pw-ripple {
      position: fixed; z-index: 2147483646; width: 44px; height: 44px; margin: -22px 0 0 -22px;
      border-radius: 50%; border: 3px solid rgba(37,99,235,.9); background: rgba(59,130,246,.25);
      animation: __pw-ripple 520ms ease-out forwards;
    }
    @keyframes __pw-ripple { from { transform: scale(.3); opacity: 1; } to { transform: scale(1.6); opacity: 0; } }
    ${o.hideScrollbars ? `* { scrollbar-width: none !important; } *::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }` : ""}
  `;

  const ARROW =
    '<svg width="36" height="36" viewBox="3 2.2 24 24" overflow="visible" xmlns="http://www.w3.org/2000/svg">' +
    '<path d="M3 2.2 L3 19.6 L7.6 15.3 L10.6 22 L13.7 20.6 L10.8 14.1 L17.2 14.1 Z" ' +
    'fill="#111827" stroke="#ffffff" stroke-width="1.6" stroke-linejoin="round"/></svg>';

  const el = document.createElement("div");
  el.id = "__pw-cursor";
  el.setAttribute("aria-hidden", "true");
  if (o.cursor === "touch") {
    el.className = "__touch";
    el.appendChild(document.createElement("div"));
  } else {
    el.innerHTML = ARROW;
  }
  const style = document.createElement("style");
  style.textContent = css;

  const paint = () => {
    el.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
  };
  const set = (x: number, y: number) => {
    pos = { x, y };
    paint();
    try {
      sessionStorage.setItem(KEY, JSON.stringify(pos));
    } catch {
      /* ignore */
    }
  };
  const ripple = (x = pos.x, y = pos.y) => {
    const r = document.createElement("div");
    r.className = "__pw-ripple";
    r.style.left = `${x}px`;
    r.style.top = `${y}px`;
    (document.documentElement ?? document).appendChild(r);
    setTimeout(() => r.remove(), 600);
  };

  const mount = () => {
    const root = document.documentElement;
    if (!root) return false;
    if (!style.isConnected) (document.head ?? root).appendChild(style);
    // Child of <html>, after <body>: sits above app content with max z-index.
    if (!el.isConnected) root.appendChild(el);
    paint();
    return true;
  };
  if (!mount()) {
    const mo = new MutationObserver(() => {
      if (mount()) mo.disconnect();
    });
    mo.observe(document, { childList: true, subtree: true });
  }
  // Some apps replace <head>/<html> children; re-mount cheaply when that happens.
  document.addEventListener("DOMContentLoaded", () => mount());

  // Matikan pemeriksa ejaan browser: garis merah di bawah kata Bahasa Indonesia mengganggu rekaman.
  const noSpellcheck = (node: ParentNode) => {
    node.querySelectorAll("input, textarea, [contenteditable]").forEach((field) => field.setAttribute("spellcheck", "false"));
  };
  new MutationObserver(() => noSpellcheck(document)).observe(document, { childList: true, subtree: true });
  document.addEventListener("focusin", (e) => {
    if (e.target instanceof HTMLElement) e.target.setAttribute("spellcheck", "false");
  }, { capture: true });

  addEventListener("mousemove", (e) => set(e.clientX, e.clientY), { capture: true, passive: true });
  // Klik hanya ditandai gelombang di ujung kursor overlay; kursor sendiri tidak bergerak atau mengecil.
  addEventListener("mousedown", () => ripple(), { capture: true, passive: true });

  w.__pwCursor = { set, ripple, get: () => ({ ...pos }) };
}
