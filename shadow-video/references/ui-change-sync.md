# UI change sync

Applies to any project that has a `video-pipeline/` folder. When a feature, label, validation, or flow in the app
changes, existing tutorials may now lie or fail. Write a change note and adjust the scripts in the same task.

## Change note

Create `video-pipeline/PERUBAHAN-UI-YYYYMMDD.md` (or the project's agreed location) with:

1. **Berkas yang diubah**: table of app files and what changed for the user.
2. **Label UI dan validasi baru**: exact new or changed texts, messages, disabled-state rules.
3. **Selector DOM baru**: selector and the element it targets (accessible names, roles, dialogs).
4. **Dampak ke tutorial**: per affected module, which scenes change (`tools/build-NN.py`, `tutorial/NN-*.md`,
   `scenes/NN-*.json`) and whether narration, actions, or only selectors change.
5. **Langkah verifikasi**: `python tools/build-NN.py`, `npm run e2e -- <id>`, and whether a re-record is needed.

## Deciding the re-work

| Change | Action |
|---|---|
| Selector only (same label on screen) | Update build script, `e2e` PASS; old video is still correct, re-record optional |
| Visible label or message changed | Update narration and selector, `e2e`, re-record (the old video shows the old text) |
| Flow changed (steps added, removed, reordered) | Update the script table first, get approval, then scenes, `e2e`, re-record |
| Narration-only wording fix | `tts` then `merge`, no re-record when the new audio fits the old scene slot |

Find affected modules by searching the build scripts and `tutorial/*.md` `SUMBER TEKS UI` lines for the changed
file paths and labels. Record in the note which modules were checked and found unaffected.
