import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { z } from "zod";
import { PATHS } from "./config.ts";

/**
 * Per-project settings in video.config.json. The engine in src/ stays identical across projects;
 * everything that names an app, a login form, a role, or a chapter lives here.
 */
const chapter = z.strictObject({
  no: z.string().regex(/^[0-9]{2}[a-z]?$/, 'chapter no like "01" or "02a"'),
  title: z.string().min(1),
  subtitle: z.string().default(""),
  /** Scene ids (scenes/<id>.json) whose videos make up this chapter, in order. */
  videos: z.array(z.string().min(1)).min(1),
});

const guide = z.strictObject({
  slug: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9-]*$/),
  title: z.string().min(1),
  subtitle: z.string().default(""),
  chapters: z.array(z.string().min(1)).min(1),
});

const projectSchema = z
  .strictObject({
    $schema: z.string().optional(),
    appName: z.string().min(1),
    /** File-name prefix for combined videos, e.g. "ACME-panduan". */
    outputPrefix: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9-]*$/),
    /** Footer line on title cards. Keep the AI-voice disclosure. */
    cardFooter: z.string().min(1),
    /** Label above the chapter title on cards and thumbnails. */
    chapterLabel: z.string().default("MODUL"),
    guideLabel: z.string().default("PANDUAN LENGKAP"),
    brand: z
      .strictObject({
        /** Paths relative to video-pipeline/ (or absolute). PNG. */
        logoIcon: z.string().min(1),
        logoFull: z.string().min(1),
        accent: z.string().default("#f5b000"),
        backgroundFrom: z.string().default("#1e3a8a"),
        backgroundTo: z.string().default("#070d1a"),
      }),
    login: z
      .strictObject({
        path: z.string().startsWith("/").default("/login"),
        /** Selectors taken from the app source (cite file:line in the tutorial). */
        username: z.string().min(1),
        password: z.string().min(1),
        submit: z.string().min(1),
        /** Paths that still count as "not logged in yet" besides login.path. */
        alsoUnauthenticated: z.array(z.string().startsWith("/")).default([]),
        /** Route to open first in `snapshot` (any page behind the login). */
        landing: z.string().startsWith("/").default("/"),
      }),
    /** .env prefixes allowed in {{PREFIX_EMAIL}} / {{PREFIX_PASSWORD}} placeholders and `snapshot <PREFIX>`. */
    rolePrefixes: z.array(z.string().regex(/^[A-Z][A-Z0-9]*$/)).min(1).default(["LOGIN"]),
    chapters: z.array(chapter).default([]),
    guides: z.array(guide).default([]),
  })
  .superRefine((p, ctx) => {
    const nos = new Set(p.chapters.map((c) => c.no));
    if (nos.size !== p.chapters.length) ctx.addIssue({ code: "custom", path: ["chapters"], message: "duplicate chapter no" });
    p.guides.forEach((g, gi) =>
      g.chapters.forEach((no, ci) => {
        if (!nos.has(no)) ctx.addIssue({ code: "custom", path: ["guides", gi, "chapters", ci], message: `unknown chapter "${no}"` });
      }),
    );
    if (!p.rolePrefixes.includes("LOGIN")) ctx.addIssue({ code: "custom", path: ["rolePrefixes"], message: 'must include "LOGIN"' });
  });

export type ProjectConfig = z.infer<typeof projectSchema>;
export type Chapter = ProjectConfig["chapters"][number];

export const projectFile = path.join(PATHS.root, "video.config.json");
let cached: ProjectConfig | undefined;

export function project(): ProjectConfig {
  if (cached) return cached;
  if (!existsSync(projectFile)) throw new Error(`Missing ${projectFile}. Copy it from the shadow-video template and fill it in.`);
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(projectFile, "utf8"));
  } catch (e) {
    throw new Error(`Cannot parse ${projectFile}: ${e instanceof Error ? e.message : String(e)}`);
  }
  const result = projectSchema.safeParse(raw);
  if (!result.success) throw new Error(`Invalid video.config.json:\n${z.prettifyError(result.error)}`);
  cached = result.data;
  return cached;
}

/** True for .env-backed placeholders such as ADMIN_EMAIL, when ADMIN is declared in rolePrefixes. */
export function isRoleVar(name: string): boolean {
  const cut = name.indexOf("_");
  return cut > 0 && project().rolePrefixes.includes(name.slice(0, cut));
}
