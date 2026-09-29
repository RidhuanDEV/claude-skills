# Shadow Monarch — Claude Skills

A senior software engineering skill for Claude. It makes Claude work like an experienced engineer across
architecture, backend, frontend, UI/UX design, database, security, DevOps, testing, debugging, code review and
AI/LLM features, with language guides for **Go, .NET/C#, TypeScript/JavaScript (Node, NestJS, React, Next.js, Vue, Angular), Python,
Java/Kotlin, PHP/Laravel, Rust and Dart/Flutter**.

> Control complexity instead of being controlled by it.

## How it works

The skill uses progressive loading so it stays small in context:

```text
shadow-monarch/
├─ SKILL.md          core rules + router (always loaded when the skill is used)
├─ GLOBAL.md         short version for account-wide instructions
└─ reference/        loaded only when the task needs them
   ├─ CORE.md  ARCHITECTURE.md  BACKEND.md  DATABASE.md  FRONTEND.md  DESIGN.md
   ├─ SECURITY.md  DEVOPS.md  TESTING.md  DEBUGGING.md  CODE-REVIEW.md  AI-LLM.md
   └─ lang-GO.md  lang-DOTNET.md  lang-TYPESCRIPT-NODE.md  lang-PYTHON.md
      lang-JAVA-KOTLIN.md  lang-PHP-LARAVEL.md  lang-RUST.md  lang-DART-FLUTTER.md
evals/               test prompts to check the skill works (not part of the upload)
```

`SKILL.md` tells Claude which reference files to read for each task. For example, a NestJS bug that only happens in Docker
loads CORE + DEBUGGING + BACKEND + DEVOPS + lang-TYPESCRIPT-NODE, and nothing else.

## Install

### Claude Code (all projects on your machine)

**Windows (PowerShell)**
```powershell
git clone https://github.com/RidhuanDEV/claude-skills.git
cd claude-skills
./install.ps1
```

**macOS / Linux**
```bash
git clone https://github.com/RidhuanDEV/claude-skills.git
cd claude-skills
./install.sh
```

The script:
1. copies `shadow-monarch/` to `~/.claude/skills/shadow-monarch/` (replacing an older copy), and
2. adds the contents of `GLOBAL.md` to `~/.claude/CLAUDE.md` between marker comments, backing up any existing file first.
   Running it again updates that block instead of duplicating it.

Manual alternative: copy the folder yourself and paste `GLOBAL.md` into `~/.claude/CLAUDE.md`.

### Claude apps (claude.ai / desktop / mobile)

1. Zip the `shadow-monarch` folder so that the zip contains the folder with `SKILL.md` inside it:
   - Windows: `Compress-Archive -Path shadow-monarch -DestinationPath shadow-monarch.zip -Force`
   - macOS/Linux: `zip -r shadow-monarch.zip shadow-monarch`
2. Make sure **Settings → Capabilities → Code execution and file creation** is on, then go to **Customize → Skills →
   + → Create skill → Upload a skill** and pick the zip (menu names may change over time).
3. Optional: paste the contents of `shadow-monarch/GLOBAL.md` into your profile's personal preferences so the core rules
   apply to every chat. It is about 3k characters, well under the preferences limit.

## Test it

See [`evals/README.md`](evals/README.md): 8 realistic prompts with the points a good answer must hit,
plus how to compare with the skill turned off.

## Updating

After pulling a new version: re-run the install script (Claude Code) and re-upload the zip (Claude apps; the uploaded
copy does not update itself). If `GLOBAL.md` changed, paste it into your profile preferences again.

## Customize

- Edit `GLOBAL.md` / `SKILL.md` for personal working style (language, OS, response format).
- Add a stack: create `reference/lang-<NAME>.md` following the same sections as the others
  (layout, errors, concurrency, data access, security, testing, tooling, common mistakes) and add a row to the
  language table in `SKILL.md`.
- Keep each reference file focused and under about 10k characters so loading stays cheap.

## License

MIT — copy, fork and adapt freely.
