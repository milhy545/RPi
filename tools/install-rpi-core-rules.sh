#!/usr/bin/env bash
# install-rpi-core-rules.sh — Idempotent installer for repository-managed RPi core-rules SKILL.md template.
# Targets the actual CodeX skill system: ~/.agents/skills/core-rules/SKILL.md
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/.agents/core-rules/SKILL.rpi.template.md"

# Default target: the actual core-rules skill directory
DEFAULT_SKILL_DIR="$HOME/.agents/skills/core-rules"
TARGET_SKILL_DIR="${SKILL_DIR:-$DEFAULT_SKILL_DIR}"
TARGET_FILE="$TARGET_SKILL_DIR/SKILL.md"

# Allowed skill boundary: must be under ~/.agents/skills/ or ~/.codex/skills/
ALLOWED_BOUNDARY_AGENTS="$HOME/.agents/skills"
ALLOWED_BOUNDARY_CODEX="$HOME/.codex/skills"
REAL_ALLOWED_BOUNDARY_AGENTS="$(readlink -f "$ALLOWED_BOUNDARY_AGENTS" 2>/dev/null || echo "$ALLOWED_BOUNDARY_AGENTS")"
REAL_ALLOWED_BOUNDARY_CODEX="$(readlink -f "$ALLOWED_BOUNDARY_CODEX" 2>/dev/null || echo "$ALLOWED_BOUNDARY_CODEX")"

usage() {
  cat <<USAGE
Usage: tools/install-rpi-core-rules.sh [SKILL_DIR]

Installs the repository-managed RPi core-rules SKILL.md template into the CodeX skill system.
SKILL_DIR defaults to ~/.agents/skills/core-rules

Creates a timestamped backup before updating if the destination already exists and differs.
Refuses installation if the destination is outside the allowed skill boundary.

Environment:
  SKILL_DIR    Target skill directory (default: ~/.agents/skills/core-rules)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ge 1 ]]; then
  TARGET_SKILL_DIR="$1"
  TARGET_FILE="$TARGET_SKILL_DIR/SKILL.md"
fi

# Validate template exists
if [[ ! -f "$TEMPLATE" ]]; then
  echo "FATAL: Template file '$TEMPLATE' does not exist." >&2
  exit 1
fi

# Resolve the target directory to its real path (follow symlinks)
if [[ -L "$TARGET_SKILL_DIR" || -L "$TARGET_FILE" || -e "$TARGET_SKILL_DIR" ]]; then
  REAL_TARGET_SKILL_DIR="$(readlink -f "$TARGET_SKILL_DIR" 2>/dev/null || echo "$TARGET_SKILL_DIR")"
  REAL_TARGET_FILE="$REAL_TARGET_SKILL_DIR/SKILL.md"
else
  REAL_TARGET_SKILL_DIR="$TARGET_SKILL_DIR"
  REAL_TARGET_FILE="$TARGET_FILE"
fi

# Validate resolved target is within allowed boundary
IS_ALLOWED=0
for b in "$ALLOWED_BOUNDARY_AGENTS" "$ALLOWED_BOUNDARY_CODEX" "$REAL_ALLOWED_BOUNDARY_AGENTS" "$REAL_ALLOWED_BOUNDARY_CODEX"; do
  if [[ "$REAL_TARGET_SKILL_DIR" == "$b"/* || "$REAL_TARGET_SKILL_DIR" == "$b" ]]; then
    IS_ALLOWED=1
    break
  fi
done

if [[ $IS_ALLOWED -eq 0 ]]; then
  echo "FATAL: Destination '$TARGET_SKILL_DIR' (resolves to '$REAL_TARGET_SKILL_DIR') is outside allowed boundary '$ALLOWED_BOUNDARY_AGENTS' / '$ALLOWED_BOUNDARY_CODEX'." >&2
  echo "Refusing to install outside skill directory." >&2
  exit 1
fi

# Ensure target directory exists
mkdir -p "$REAL_TARGET_SKILL_DIR"

# Check if destination exists and matches template
if [[ -f "$REAL_TARGET_FILE" ]]; then
  if cmp -s "$TEMPLATE" "$REAL_TARGET_FILE"; then
    echo "OK: RPi core-rules SKILL.md at '$REAL_TARGET_FILE' are already up-to-date (idempotent)."
    exit 0
  fi

  # Create timestamped backup before updating
  BACKUP_FILE="${REAL_TARGET_FILE}.bak-$(date +%Y%m%d-%H%M%S)"
  echo "Creating timestamped backup of existing SKILL.md: $BACKUP_FILE"
  cp -p "$REAL_TARGET_FILE" "$BACKUP_FILE"
fi

# Validate we're not overwriting ~/AGENTS.md or other runtime files
if [[ "$REAL_TARGET_FILE" == "$HOME/AGENTS.md" ]]; then
  echo "FATAL: Refusing to overwrite ~/AGENTS.md. Use ~/.agents/skills/core-rules/SKILL.md instead." >&2
  exit 1
fi

# Install the template atomically
echo "Installing repository-managed RPi core-rules SKILL.md to '$REAL_TARGET_FILE'..."
cp -p "$TEMPLATE" "$REAL_TARGET_FILE"

# Verification check
if cmp -s "$TEMPLATE" "$REAL_TARGET_FILE"; then
  echo "SUCCESS: Installed RPi core-rules SKILL.md verified at '$REAL_TARGET_FILE'."
  echo "NOTE: ~/AGENTS.md and other runtime files were NOT modified."
  exit 0
else
  echo "FATAL: Verification failed — installed file at '$REAL_TARGET_FILE' does not match template." >&2
  # Attempt rollback to backup if it exists
  if [[ -f "$BACKUP_FILE" ]]; then
    echo "Attempting rollback to backup: $BACKUP_FILE" >&2
    cp -p "$BACKUP_FILE" "$REAL_TARGET_FILE"
    echo "Rolled back to previous SKILL.md. Manual intervention required." >&2
  fi
  exit 1
fi
