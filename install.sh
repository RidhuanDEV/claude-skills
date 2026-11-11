#!/usr/bin/env bash
# Installs all 36 Shadow Army skills across Claude Code, Codex, Gemini CLI & Antigravity (macOS / Linux)
# and syncs GLOBAL.md between markers in ~/.claude/CLAUDE.md, ~/.codex/AGENTS.md, and ~/.gemini/GEMINI.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/shadow-monarch"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
GEMINI_DIR="$HOME/.gemini"
BEGIN="<!-- BEGIN shadow-monarch -->"
END="<!-- END shadow-monarch -->"

[ -f "$SOURCE/SKILL.md" ] || { echo "error: $SOURCE/SKILL.md not found; run from the repo root" >&2; exit 1; }

TARGET_ROOTS=(
  "$GEMINI_DIR/config/skills"
  "$GEMINI_DIR/skills"
  "$CLAUDE_DIR/skills"
  "$HOME/.agents/skills"
  "$CODEX_DIR/skills"
)

for ROOT in "${TARGET_ROOTS[@]}"; do
  mkdir -p "$ROOT"
  for SKILL_MD in "$SCRIPT_DIR"/*/SKILL.md; do
    FOLDER="$(basename "$(dirname "$SKILL_MD")")"
    rm -rf "$ROOT/$FOLDER"
    cp -R "$SCRIPT_DIR/$FOLDER" "$ROOT/$FOLDER"
  done
  echo "Synced Shadow Army skills to: $ROOT"
done

block="$(printf '%s\n%s\n%s\n' "$BEGIN" "$(cat "$SOURCE/GLOBAL.md")" "$END")"

INSTRUCTION_FILES=(
  "$CLAUDE_DIR/CLAUDE.md"
  "$CODEX_DIR/AGENTS.md"
  "$GEMINI_DIR/GEMINI.md"
)

for INST_FILE in "${INSTRUCTION_FILES[@]}"; do
  mkdir -p "$(dirname "$INST_FILE")"
  if [ -f "$INST_FILE" ]; then
    cp "$INST_FILE" "$INST_FILE.bak.$(date +%Y%m%d%H%M%S)"
    if grep -qF "$BEGIN" "$INST_FILE"; then
      SM_BEGIN="$BEGIN" SM_END="$END" SM_BLOCK="$block" awk '
        $0 == ENVIRON["SM_BEGIN"] { print ENVIRON["SM_BLOCK"]; skip = 1; next }
        $0 == ENVIRON["SM_END"]   { skip = 0; next }
        !skip                     { print }
      ' "$INST_FILE" > "$INST_FILE.tmp" && mv "$INST_FILE.tmp" "$INST_FILE"
      echo "Updated shadow-monarch block in $INST_FILE (backup saved)"
    else
      printf '\n%s\n' "$block" >> "$INST_FILE"
      echo "Appended shadow-monarch block to $INST_FILE (backup saved)"
    fi
  else
    printf '%s\n' "$block" > "$INST_FILE"
    echo "Created $INST_FILE"
  fi
done

echo "Done. All 36 Shadow Army skills and global instruction files are synced."
