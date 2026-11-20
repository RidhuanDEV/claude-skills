# Scene authoring

Authoritative schema: `video-pipeline/src/schema.ts` (zod). `npm run validate` rejects anything that does not match.

## File shape

```json
{
  "title": "02 - Membuat Usulan",
  "recordLogin": false,
  "session": "storageState",
  "localStorage": { "app_tourShown": "true" },
  "backgroundColor": "#FFFFFF",
  "viewport": { "width": 1920, "height": 1080 },
  "scenes": [
    { "id": "s01-buka-menu", "narration": "Teks narasi persis seperti di naskah.",
      "actions": [ { "type": "goto", "url": "/dashboard" }, { "type": "click", "selector": "role=button[name=\"Usulan\"]" } ] }
  ]
}
```

Rules the validator enforces: unique scene ids; `goto` only as the first action of the first scene (later
navigation is by clicking, like a person); the first action must be `goto`.

Tutorial options: `recordLogin` (the login is part of the video, no saved session), `session` / `saveSession`
(reuse or store `auth/<name>.json`), `viewport` (mobile: `{"width":390,"height":844,"isMobile":true,"hasTouch":true}`
with `"cursor":"touch"`), `canvas` (mobile is centred on a 1920x1080 canvas), `localStorage` (skip first-visit
tours), `backgroundColor` (the app page colour, avoids a white flash), `voice`, `rate`.

## Actions

| Action | Use |
|---|---|
| `goto` | First action only. |
| `click` (`nth`, `expect`, `retries`) | Human click. `expect` = element that must appear; the click is retried if it does not (re-render races). |
| `type` (`clear`, `pressEnter`, `atCaret`) | Types per character. `{{LOGIN_EMAIL}}` style placeholders come from `.env`. `atCaret` for rich-text editors. |
| `hover` (`ms`) | Point and rest while narrating. Works on disabled controls. |
| `scroll` (`to` or `deltaY`, `within`) | Smooth wheel scroll; `within` for inner scroll panels. |
| `select` (`value` or `label`) | Native `<select>` only. Custom dropdowns: two clicks (`pick()` in `naskah.py`). |
| `waitFor` (`selector`+`state`, `url`, `networkIdle`) | Condition wait, never a fixed sleep. `url` is a substring or `/regex/flags`. |
| `pause` (`ms`) | Tempo for narration. Shortened to 300 ms in E2E. |
| `upload` (`trigger` or `selector`, `files`) | Files from `assets/`. With `trigger`, the native chooser is replaced by a blurred fake picker in the video. |
| `setValue` | Native date/time inputs only. |
| `press` (`key`) | Keyboard key such as `Escape`, `Tab`. |
| `manual` (`untilUrl` or `untilSelector`) | Operator solves a captcha/OTP in a headed browser; the wait is cut from the video. |
| `capture` (`clipboard`, `text`, `attr`, `url`) | Stores a value as `{{NAME}}` for later tutorials (`cache/vars.json`, never printed). |
| `fetchMail` (`otp` or `link`) | Reads the staging mail catcher (`MAILPIT_URL`) without showing it; the wait is cut. |
| `openUrl` | Opens a URL mid-recording (e.g. a reset link); the navigation is cut. |
| `maskText` | Blurs every on-screen occurrence of a text from now on (e.g. a generated password in a dialog). |
| any action: `optional: true` | Skip on failure, for dialogs that only sometimes appear. |

Built-in placeholders: `LOGIN_EMAIL`, `LOGIN_PASSWORD`, `<PREFIX>_*` for each `rolePrefixes` entry in
`video.config.json`, `TOMORROW_DATE`, `TOMORROW_0800`, `NOW_PLUS_1H`, `NOW_PLUS_2H`, and captured names.

## Selectors

Priority: `#id` / `[name=...]` > `role=button[name="Label"]` (substring) or `role=button[name=/^Label$/i]`
(exact) > `aria-label` / `title` > text. Get accessible names from `npm run snapshot` output, not from guesses.

- Locators are **strict**: a selector matching two elements fails in both E2E and recording. Narrow it with a
  container (`main >> ...`), `:visible` (responsive layouts keep a hidden mobile copy), `:has-text()`, or `nth`.
- `button:text-is("X")` fails on custom buttons with icons; use `role=button[name=...]`.
- SPA navigation does not fire `load`: after a click that changes route, wait for a text or element of the new page
  rather than `waitFor url`.
- Empty states: a hover on `table tbody tr` fails on a fresh account; point at `table, :text-is("Belum ada ...")`.
- A click right after a dialog closes can be swallowed by the closing animation: add `pause` or use `expect`.
- Async work that may finish instantly (imports, uploads): mark the "processing" step `optional` and wait for
  the final state.

## Single-source build scripts

Write scenes in `tools/build-NN.py` (copy `tools/build-01.example.py`). Each scene is a tuple
`(id, visual, on-screen action, narration, actions)`. Helpers in `naskah.py`: `button`, `button_prefix`,
`link`, `option`, `textbox`, `checkbox`, `menu_item`, `pick`. Put project-specific shared selectors (main
navigation, profile menu) in the project's own `tools/` module, not in `naskah.py`.

## Dependent modules

Modules that build on each other's data (create → revise → report) are recorded in order. Document the required
data state at the top of each build script ("Prasyarat data: ..."). If the project has a resettable recording
database with named snapshots, record which snapshot each module starts from.
