# SA-DOC-ENGINE-002 — Unresolved Issues & Known Limitations

1. **External Node Diagram CLIs (`mmdc`, `@dbml/cli`)**:
   - Host environment does not bundle `mmdc` or DBML diagram-image CLI globally; live `mmdc` rendering paths are verified via isolated Python subprocess test fixtures (`T54`) covering valid SVG, failure, timeout, and corrupt asset recovery.
2. **Linux / macOS Runtime Font & Symlink Parity**:
   - Cross-platform font paths (`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`, `/System/Library/Fonts/Supplemental/Arial.ttf`) are implemented conservatively with Helvetica fallback, but **only Windows execution (`arial.ttf` + `consola.ttf`) was measured locally**.
   - On Windows without Administrator / Developer Mode privileges, `T57` (NTFS directory symlink creation) reports `NOT_RUN` if OS denies `symlink_to` privilege (`os.islink` ancestor guard remains covered in code inspection and triggers cleanly when symlinks exist).
3. **Global Sync & Remote Git Push**:
   - Deferred pending explicit Monarch authorization (`L4`).
