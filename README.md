# Shadow Monarch — Antigravity, Codex, and Claude Skill

A full-spectrum senior engineering and IT peer skill for Antigravity, Codex, and Claude, with source-verified contracts, strict types (`no any`, `no typecasting`), automatic dead-code elimination, and source-driven document rules. It covers **all IT roles, languages, and specialized sub-tasks** through a 3-Tier Foreign Key routing index (44 reference modules loaded strictly on demand):

- **25 Role & Domain Guides**: Core Mindset, Architecture, Pre-Sales/TOR/KAK & Server Sizing, Backend, Database, Frontend, UI/UX Design, Mobile Illustration/Lottie Motion Design (`MOBILE-DESIGN`), Mobile Architecture, Refactoring & Dead Code Cleanup, AppSec, VAPT Pentesting/DevSecOps, DevOps, Cloud/SRE/K8s/Terraform, Enterprise Integration (Kafka/IAM/Payment Ledger), Testing Strategy, Debugging, Code Review, AI/LLM, AI Agents & MCP, PM/System Analysis (PRD/SRS/FSD), IT PMO/Scrum/ITIL/UU PDP Governance, Technical Writing & `.md` → `.docx` Pipelines, Data Automation/ETL, and Data Analytics/BI/`dbt`/ML.
- **9 Language Guides (`lang-*`)**: TypeScript/JavaScript (Node, NestJS, Express, React, Next.js), Go, .NET/C#, Python (FastAPI, Django, Flask), Java/Kotlin (Spring Boot), PHP/Laravel, Rust (`tokio`, `axum`), Dart/Flutter, and Modern C/C++20/Embedded (ESP32/STM32/CMake/Wasm).
- **10 Specialized Sub-Task & Tooling Guides (`sub-*`)**: Vue 3/Nuxt/Angular Signals/Tailwind/React Native/Jetpack Compose/SwiftUI, PostgreSQL/Redis/Elasticsearch/MongoDB, Playwright/Cypress/`k6`/Bruno/TCM/UAT, OpenAPI 3.1/DBML/Strict Mermaid/`python-docx` & Node `docx` Generators, PowerShell/Bash/Taskfiles, OpenTelemetry/PromQL/LogQL/Grafana/Profiling, WebSockets/SSE/WebRTC/MQTT IoT/Electron/Tauri/Chrome MV3, Indonesian Fintech & Gov (SNAP BI, TTE BSrE/e-Meterai, SatuSehat FHIR/BPJS, Tax PPN/PPh), GIS/PostGIS/MapLibre/Vector Tiles, and Computer Vision/OCR/Whisper/FFmpeg.

> Control complexity instead of being controlled by it.

## How it works

The skill uses progressive Foreign Key loading so it stays small in context:

```text
shadow-monarch/
├─ SKILL.md          core rules + 3-tier Foreign Key router (always loaded when the skill is used)
├─ GLOBAL.md         account-wide summary for Claude / global agent instructions
├─ agents/openai.yaml Codex display name and invocation prompt
└─ reference/        44 focused modules loaded only when the active task needs them
   ├─ Role & Domain (25):
   │  CORE.md  ARCHITECTURE.md  PRESALES-PROPOSAL-KAK.md  BACKEND.md  DATABASE.md
   │  FRONTEND.md  DESIGN.md  MOBILE-DESIGN.md  MOBILE.md  REFACTORING.md
   │  SECURITY.md  SECOPS-PENTEST.md  DEVOPS.md  CLOUD-SRE.md
   │  ENTERPRISE-INTEGRATION.md  TESTING.md  DEBUGGING.md  CODE-REVIEW.md
   │  AI-LLM.md  AGENTS-MCP.md  PRODUCT-ANALYSIS.md  IT-PMO-GOVERNANCE.md
   │  DOCS-PIPELINE.md  DATA-AUTOMATION.md  DATA-ANALYTICS-ML.md
   ├─ Languages (9):
   │  lang-TYPESCRIPT-NODE.md  lang-GO.md  lang-DOTNET.md  lang-PYTHON.md
   │  lang-JAVA-KOTLIN.md  lang-PHP-LARAVEL.md  lang-RUST.md  lang-DART-FLUTTER.md
   │  lang-CPP-SYSTEMS.md
   └─ Sub-Task & Tooling Authoring Rules (10):
      sub-FRONTEND-MOBILE-STACKS.md  sub-DATA-STORES.md  sub-QA-AUTOMATION.md
      sub-SPECS-DOCX-CODE.md  sub-SHELL-CLI-AUTOMATION.md  sub-OBSERVABILITY-PROFILING.md
      sub-REALTIME-IOT-DESKTOP.md  sub-FINTECH-ID-ECOSYSTEM.md  sub-GIS-GEOSPATIAL.md
      sub-VISION-OCR-MEDIA.md
evals/               test prompts to check the skill works (not part of the upload)
```

`SKILL.md` tells the agent which reference files to read for each task. For example, a NestJS bug that only happens in Docker
loads `CORE` + `DEBUGGING` + `BACKEND` + `DEVOPS` + `lang-TYPESCRIPT-NODE`, and nothing else.

## Install

### Codex (Windows, all projects)

From this folder run:

```powershell
./install-codex.ps1
```

This creates a directory junction at `%USERPROFILE%\.agents\skills\shadow-monarch` pointing to
the local `shadow-monarch` folder. Edits here become available through the installed link.
It preserves any conflicting installation and does not modify global `AGENTS.md` or `config.toml`.
Running it again with the same source is safe and makes no duplicate installation.

Invoke with `$shadow-monarch`, for example:
`Use $shadow-monarch to fix this endpoint using verified backend contracts and strict types.`
Automatic selection remains enabled. If the skill does not appear, restart Codex.
The user skill directory and link discovery follow the [official skills documentation](https://learn.chatgpt.com/docs/build-skills).

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

See [`evals/README.md`](evals/README.md): realistic prompts with the points a good answer must hit,
plus how to compare with the skill turned off.

## Updating

The Codex junction reads this folder directly; re-run `install-codex.ps1` if you move the source folder.
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
