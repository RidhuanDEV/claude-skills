#!/usr/bin/env bash
# Installs the shadow-monarch skill for Claude Code (macOS / Linux).
# - Copies ./shadow-monarch to ~/.claude/skills/shadow-monarch (replacing an older copy)
# - Inserts GLOBAL.md into ~/.claude/CLAUDE.md between markers (backs up the old file first)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/shadow-monarch"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
TARGET="$CLAUDE_DIR/skills/shadow-monarch"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
BEGIN="<!-- BEGIN shadow-monarch -->"
END="<!-- END shadow-monarch -->"

[ -f "$SOURCE/SKILL.md" ] || { echo "error: $SOURCE/SKILL.md not found; run from the repo root" >&2; exit 1; }

mkdir -p "$CLAUDE_DIR/skills"
rm -rf "$TARGET"
cp -R "$SOURCE" "$TARGET"
echo "Skill installed: $TARGET"

block="$(printf '%s\n%s\n%s\n' "$BEGIN" "$(cat "$SOURCE/GLOBAL.md")" "$END")"

if [ -f "$CLAUDE_MD" ]; then
  cp "$CLAUDE_MD" "$CLAUDE_MD.bak.$(date +%Y%m%d%H%M%S)"
  if grep -qF "$BEGIN" "$CLAUDE_MD"; then
    # Replace the existing block
    # Pass values through the environment: awk -v would mangle backslashes and newlines
    SM_BEGIN="$BEGIN" SM_END="$END" SM_BLOCK="$block" awk '
      $0 == ENVIRON["SM_BEGIN"] { print ENVIRON["SM_BLOCK"]; skip = 1; next }
      $0 == ENVIRON["SM_END"]   { skip = 0; next }
      !skip                     { print }
    ' "$CLAUDE_MD" > "$CLAUDE_MD.tmp" && mv "$CLAUDE_MD.tmp" "$CLAUDE_MD"
    echo "Updated shadow-monarch block in $CLAUDE_MD (backup saved)"
  else
    printf '\n%s\n' "$block" >> "$CLAUDE_MD"
    echo "Appended shadow-monarch block to $CLAUDE_MD (backup saved)"
  fi
else
  printf '%s\n' "$block" > "$CLAUDE_MD"
  echo "Created $CLAUDE_MD"
fi

echo "Done. Restart Claude Code to pick up the changes."
