import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { z } from "zod";
import { PATHS } from "./config.ts";

/**
 * Selector = any Playwright selector string: CSS (`input[name="username"]`),
 * `text=Masuk`, `role=button[name="Masuk"]`, `internal:label="Password"`, `xpath=...`.
 * Selectors MUST come from the narration script or the app source, never guessed.
 */
const selector = z.string().min(1, "selector must not be empty");
const timeout = z.number().int().positive().max(120_000).optional();
const nth = z.number().int().min(0).optional();

const goto = z.strictObject({ type: z.literal("goto"), optional: z.boolean().optional(), url: z.string().min(1), timeout });
const click = z.strictObject({
  type: z.literal("click"), optional: z.boolean().optional(), selector, nth, timeout,
  /** Element that must appear after the click; if it doesn't within ~5 s the click is retried (re-render races). */
  expect: selector.optional(),
  retries: z.number().int().min(0).max(3).optional(),
});
const type = z.strictObject({
  type: z.literal("type"), optional: z.boolean().optional(),
  selector,
  nth,
  /** Literal text. `{{LOGIN_EMAIL}}` / `{{LOGIN_PASSWORD}}` are replaced from .env (masked in logs). */
  text: z.string(),
  /** Select-all + Backspace before typing. */
  clear: z.boolean().optional(),
  pressEnter: z.boolean().optional(),
  /** Type at the current caret without clicking the element first (rich-text editors: keeps caret position). */
  atCaret: z.boolean().optional(),
  timeout,
});
const hover = z.strictObject({
  type: z.literal("hover"), optional: z.boolean().optional(),
  selector,
  nth,
  /** How long the cursor rests on the element (default 200–400 ms random). */
  ms: z.number().int().min(0).max(30_000).optional(),
  timeout,
});
const scroll = z
  .strictObject({
    type: z.literal("scroll"), optional: z.boolean().optional(),
    /** Scroll until this element is in view (smooth wheel). */
    to: selector.optional(),
    /** Or: scroll by this many pixels (positive = down) in small wheel steps. */
    deltaY: z.number().int().optional(),
    /** Move the cursor over this scroll container first (for inner scrollable panels). */
    within: selector.optional(),
    timeout,
  })
  .refine((a) => (a.to === undefined) !== (a.deltaY === undefined), {
    message: "scroll needs exactly one of `to` or `deltaY`",
  });
const select = z
  .strictObject({
    type: z.literal("select"), optional: z.boolean().optional(),
    /** Native <select> only. For custom dropdowns (Radix/shadcn), use click actions instead. */
    selector,
    nth,
    value: z.string().optional(),
    label: z.string().optional(),
    timeout,
  })
  .refine((a) => (a.value === undefined) !== (a.label === undefined), {
    message: "select needs exactly one of `value` or `label`",
  });
const waitFor = z
  .strictObject({
    type: z.literal("waitFor"), optional: z.boolean().optional(),
    selector: selector.optional(),
    state: z.enum(["visible", "hidden", "attached", "detached"]).optional(),
    /** Substring or /regex/ the page URL must match. */
    url: z.string().optional(),
    networkIdle: z.boolean().optional(),
    timeout,
  })
  .refine((a) => a.selector !== undefined || a.url !== undefined || a.networkIdle === true, {
    message: "waitFor needs at least one of `selector`, `url`, `networkIdle: true`",
  });
const pause = z.strictObject({ type: z.literal("pause"), optional: z.boolean().optional(), ms: z.number().int().min(0).max(60_000) });
const upload = z.strictObject({
  type: z.literal("upload"), optional: z.boolean().optional(),
  /** The <input type="file"> (may be hidden). Used when `trigger` is not given. */
  selector: selector.optional(),
  /** Visible button/dropzone the cursor clicks; the native file chooser is intercepted. */
  trigger: selector.optional(),
  /** Paths relative to video-pipeline/assets/. */
  files: z.array(z.string().min(1)).min(1),
  timeout,
}).refine((a) => a.selector !== undefined || a.trigger !== undefined, {
  message: "upload needs `selector` (file input) or `trigger` (button that opens the file chooser)",
});

/** Operator step (captcha / OTP). Requires a headed browser; the waiting segment is CUT from the final video. */
const manual = z
  .strictObject({
    type: z.literal("manual"), optional: z.boolean().optional(),
    message: z.string().min(1),
    /** Done when the URL matches (substring or /regex/) ... */
    untilUrl: z.string().optional(),
    /** ... or when this selector becomes visible. */
    untilSelector: selector.optional(),
    /** Extra settle time after the condition, still inside the cut. */
    settleMs: z.number().int().min(0).max(30_000).optional(),
    timeout: z.number().int().positive().max(900_000).optional(),
  })
  .refine((a) => a.untilUrl !== undefined || a.untilSelector !== undefined, { message: "manual needs untilUrl or untilSelector" });
/** Store a value for later tutorials as {{NAME}} (cache/vars.json). Values are never printed. */
const capture = z
  .strictObject({
    type: z.literal("capture"), optional: z.boolean().optional(),
    name: z.string().regex(/^[A-Z][A-Z0-9_]*$/, "capture name: UPPER_SNAKE"),
    from: z.enum(["clipboard", "text", "attr", "url"]),
    selector: selector.optional(),
    attr: z.string().optional(),
    timeout,
  })
  .refine((a) => (a.from === "text" || a.from === "attr" ? a.selector !== undefined : true), { message: "capture from text/attr needs selector" })
  .refine((a) => (a.from === "attr" ? a.attr !== undefined : true), { message: "capture from attr needs attr" });
/** Date/time inputs only (native pickers can't be typed reliably): cursor clicks the field, then the value is set. */
const setValue = z.strictObject({ type: z.literal("setValue"), optional: z.boolean().optional(), selector, nth, value: z.string(), timeout });
/** From now on, blur every on-screen occurrence of this text (e.g. "{{KOOR_PASSWORD}}" in a success dialog). */
const maskText = z.strictObject({ type: z.literal("maskText"), optional: z.boolean().optional(), text: z.string().min(1) });
/**
 * Read an email from the staging mail catcher (MAILPIT_URL) WITHOUT showing it: waits for a message to `to`
 * received after this action started, extracts a 6-digit OTP or a link, stores it as {{name}}. The wait is cut.
 */
const fetchMail = z.strictObject({
  type: z.literal("fetchMail"), optional: z.boolean().optional(),
  name: z.string().regex(/^[A-Z][A-Z0-9_]*$/),
  to: z.string().min(3),
  subject: z.string().optional(),
  extract: z.enum(["otp", "link"]),
  linkContains: z.string().optional(),
  timeout: z.number().int().positive().max(300_000).optional(),
});
/** Navigate mid-recording (e.g. the link from an email). The navigation is cut, so it looks like the link was opened. */
const openUrl = z.strictObject({ type: z.literal("openUrl"), optional: z.boolean().optional(), url: z.string().min(1), timeout });
/** Keyboard key, e.g. "Escape", "Tab". */
const press = z.strictObject({ type: z.literal("press"), optional: z.boolean().optional(), key: z.string().min(1) });

export const actionSchema = z.union([goto, click, type, hover, scroll, select, waitFor, pause, upload, manual, capture, setValue, press, maskText, fetchMail, openUrl]);
export type Action = z.infer<typeof actionSchema>;

export const sceneSchema = z.strictObject({
  id: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_-]*$/, "scene id: letters, digits, - and _ only"),
  /** Narration in Bahasa Indonesia. Empty string = silent scene. */
  narration: z.string(),
  actions: z.array(actionSchema),
});
export type Scene = z.infer<typeof sceneSchema>;

const size = z.strictObject({
  width: z.number().int().min(200).max(3840),
  height: z.number().int().min(200).max(2160),
});

export const tutorialSchema = z
  .strictObject({
    id: z.string().optional(),
    title: z.string().optional(),
    voice: z.string().optional(),
    rate: z.string().regex(/^[+-]\d+%$/, 'rate like "+0%" or "-10%"').optional(),
    viewport: size
      .extend({ isMobile: z.boolean().optional(), hasTouch: z.boolean().optional() })
      .default({ width: 1920, height: 1080 }),
    /** Output canvas; the recording is centered on it (mobile 390x844 -> padded onto 1920x1080). */
    canvas: z
      .strictObject({
        width: z.number().int().default(1920),
        height: z.number().int().default(1080),
        background: z.string().default("#1f2933"),
        /** contain = scale the recording up/down to fit inside canvas minus padding; none = native size. */
        fit: z.enum(["contain", "none"]).default("contain"),
        padding: z.number().int().min(0).default(24),
      })
      .default({ width: 1920, height: 1080, background: "#1f2933", fit: "contain", padding: 24 }),
    /** true = do NOT reuse auth/storageState.json; the login itself is part of the video. */
    recordLogin: z.boolean().default(false),
    /** Session file (auth/<name>.json) reused when recordLogin is false. */
    session: z.string().regex(/^[A-Za-z0-9-]+$/).default("storageState"),
    /** Save the browser session at the end of the recording to auth/<name>.json (e.g. after a recorded login). */
    saveSession: z.string().regex(/^[A-Za-z0-9-]+$/).optional(),
    /** html/body background injected before first paint; match the app's page background token to avoid a flash. */
    backgroundColor: z.string().default("#FFFFFF"),
    hideScrollbars: z.boolean().default(true),
    /** localStorage keys seeded before the app boots (e.g. kunci localStorage aplikasi bila ada modal kunjungan pertama). */
    localStorage: z.record(z.string(), z.string()).default({}),
    cursor: z.enum(["arrow", "touch"]).default("arrow"),
    /** Where the fake cursor rests before scene 1, as fraction of viewport. */
    cursorStart: z.strictObject({ x: z.number().min(0).max(1), y: z.number().min(0).max(1) }).default({ x: 0.5, y: 0.6 }),
    scenes: z.array(sceneSchema).min(1),
  })
  .superRefine((t, ctx) => {
    const seen = new Set<string>();
    t.scenes.forEach((s, si) => {
      if (seen.has(s.id)) ctx.addIssue({ code: "custom", path: ["scenes", si, "id"], message: `duplicate scene id "${s.id}"` });
      seen.add(s.id);
      s.actions.forEach((a, ai) => {
        if (a.type === "goto" && !(si === 0 && ai === 0)) {
          ctx.addIssue({
            code: "custom",
            path: ["scenes", si, "actions", ai],
            message: "goto is only allowed as the FIRST action of the FIRST scene. Navigate by clicking menus afterwards.",
          });
        }
      });
    });
    const first = t.scenes[0]?.actions[0];
    if (!first || first.type !== "goto") {
      ctx.addIssue({ code: "custom", path: ["scenes", 0, "actions", 0], message: "first action of first scene must be goto" });
    }
    if (t.canvas.width < t.viewport.width || t.canvas.height < t.viewport.height) {
      if (t.canvas.fit === "none") {
        ctx.addIssue({ code: "custom", path: ["canvas"], message: "canvas smaller than viewport requires fit: contain" });
      }
    }
  });
export type Tutorial = z.infer<typeof tutorialSchema> & { id: string };

/** Resolve "01-login" or "01" or "01-login.json" to a file in scenes/. */
export function resolveTutorialFile(arg: string): string {
  const direct = path.isAbsolute(arg) ? arg : path.join(PATHS.scenes, arg.endsWith(".json") ? arg : `${arg}.json`);
  if (existsSync(direct)) return direct;
  const files = existsSync(PATHS.scenes) ? readdirSync(PATHS.scenes).filter((f) => f.endsWith(".json")) : [];
  const matches = files.filter((f) => f.startsWith(`${arg}-`) || f.startsWith(arg));
  if (matches.length === 1) return path.join(PATHS.scenes, matches[0]!);
  if (matches.length > 1) throw new Error(`"${arg}" is ambiguous: ${matches.join(", ")}`);
  throw new Error(`No scene file for "${arg}" in ${PATHS.scenes}. Available: ${files.join(", ") || "(none)"}`);
}

export function parseTutorial(raw: unknown, fallbackId: string): Tutorial {
  const input = Array.isArray(raw) ? { scenes: raw } : raw; // spec allows a bare [{id, narration, actions}] array
  const result = tutorialSchema.safeParse(input);
  if (!result.success) {
    throw new Error(`Invalid scene file "${fallbackId}":\n${z.prettifyError(result.error)}`);
  }
  return { ...result.data, id: result.data.id ?? fallbackId };
}

export function loadTutorial(arg: string): Tutorial {
  const file = resolveTutorialFile(arg);
  const id = path.basename(file, ".json");
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(file, "utf8"));
  } catch (e) {
    throw new Error(`Cannot parse ${file}: ${(e as Error).message}`);
  }
  return parseTutorial(raw, id);
}
