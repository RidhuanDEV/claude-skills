import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SCAFFOLD = path.join(SKILL, "scripts", "scaffold.mjs");
const TEMPLATE = path.join(SKILL, "templates", "video-pipeline");

function run(...args) {
  return spawnSync(process.execPath, [SCAFFOLD, ...args], { encoding: "utf8", timeout: 60_000 });
}

function withTempDir(fn) {
  const dir = mkdtempSync(path.join(tmpdir(), "shadow-video-scaffold-"));
  try {
    fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test("creates video-pipeline in an empty project", () => {
  withTempDir((dir) => {
    const res = run(dir);
    assert.equal(res.status, 0, res.stderr);
    const target = path.join(dir, "video-pipeline");
    assert.ok(existsSync(path.join(target, "video.config.json")));
    assert.ok(existsSync(path.join(target, "src", "cli.ts")));
    assert.ok(existsSync(path.join(target, "assets", "brand")));
    assert.match(res.stdout, /Created /);
  });
});

test("refuses to overwrite an existing video-pipeline directory", () => {
  withTempDir((dir) => {
    const target = path.join(dir, "video-pipeline");
    mkdirSync(target);
    const sentinel = path.join(target, "video.config.json");
    writeFileSync(sentinel, "PROJECT-OWNED");
    const res = run(dir);
    assert.equal(res.status, 1);
    assert.match(res.stderr, /REFUSED/);
    assert.equal(readFileSync(sentinel, "utf8"), "PROJECT-OWNED");
    assert.ok(!existsSync(path.join(target, "src")), "nothing may be copied on refusal");
  });
});

test("refuses when video-pipeline exists as a file", () => {
  withTempDir((dir) => {
    const target = path.join(dir, "video-pipeline");
    writeFileSync(target, "not a dir");
    const res = run(dir);
    assert.equal(res.status, 1);
    assert.equal(readFileSync(target, "utf8"), "not a dir");
  });
});

test("second scaffold run into the same project is refused", () => {
  withTempDir((dir) => {
    assert.equal(run(dir).status, 0);
    const cfg = path.join(dir, "video-pipeline", "video.config.json");
    writeFileSync(cfg, "EDITED");
    const res = run(dir);
    assert.equal(res.status, 1);
    assert.equal(readFileSync(cfg, "utf8"), "EDITED");
  });
});

test("missing project argument exits 2", () => {
  const res = run();
  assert.equal(res.status, 2);
  assert.match(res.stderr, /Usage/);
});

test("--update-engine refuses when the pipeline does not exist", () => {
  withTempDir((dir) => {
    const res = run(dir, "--update-engine", "--apply");
    assert.equal(res.status, 1);
    assert.match(res.stderr, /REFUSED/);
    assert.ok(!existsSync(path.join(dir, "video-pipeline")));
  });
});

test("--update-engine dry run changes nothing; --apply touches engine files only", () => {
  withTempDir((dir) => {
    assert.equal(run(dir).status, 0);
    const target = path.join(dir, "video-pipeline");
    const engineFile = path.join(target, "tsconfig.json");
    const cfg = path.join(target, "video.config.json");
    const scene = path.join(target, "scenes", "00-sample.json");
    writeFileSync(engineFile, "LOCAL-ENGINE-EDIT");
    writeFileSync(cfg, "PROJECT-CONFIG");
    writeFileSync(scene, "PROJECT-SCENE");

    const dry = run(dir, "--update-engine");
    assert.equal(dry.status, 0, dry.stderr);
    assert.match(dry.stdout, /tsconfig\.json/);
    assert.match(dry.stdout, /Dry run only/);
    assert.equal(readFileSync(engineFile, "utf8"), "LOCAL-ENGINE-EDIT");

    const applied = run(dir, "--update-engine", "--apply");
    assert.equal(applied.status, 0, applied.stderr);
    assert.deepEqual(readFileSync(engineFile), readFileSync(path.join(TEMPLATE, "tsconfig.json")));
    assert.equal(readFileSync(cfg, "utf8"), "PROJECT-CONFIG");
    assert.equal(readFileSync(scene, "utf8"), "PROJECT-SCENE");
  });
});
