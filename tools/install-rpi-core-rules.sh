#!/usr/bin/env bash
# install-rpi-core-rules.sh — Idempotent installer for repository-managed RPi core-rules template.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/.agents/AGENTS.rpi.template.md"
TARGET_DEST="${DEST_FILE:-$HOME/AGENTS.md}"

usage() {
  cat <<USAGE
Usage: tools/install-rpi-core-rules.sh [DEST_FILE]

Installs the repository-managed RPi core-rules template into DEST_FILE (default: ~/AGENTS.md).
Creates a timestamped backup before updating if the destination already exists and differs.

Environment:
  DEST_FILE    Destination path for RPi core-rules (default: $HOME/AGENTS.md)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ge 1 ]]; then
  TARGET_DEST="$1"
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "FATAL: Template file '$TEMPLATE' does not exist." >&2
  exit 1
fi

DEST_DIR="$(dirname "$TARGET_DEST")"
mkdir -p "$DEST_DIR"

# Validate symlink status if present
REAL_DEST="$TARGET_DEST"
if [[ -L "$TARGET_DEST" ]]; then
  REAL_DEST="$(readlink -f "$TARGET_DEST")"
  echo "Destination '$TARGET_DEST' is a symlink resolving to '$REAL_DEST'."
fi

# Check if destination exists and matches template
if [[ -f "$REAL_DEST" ]]; then
  if cmp -s "$TEMPLATE" "$REAL_DEST"; then
    echo "OK: RPi core-rules at '$TARGET_DEST' are already up-to-date (idempotent)."
    exit 0
  fi

  # Create timestamped backup before updating
  BACKUP_FILE="${REAL_DEST}.bak-$(date +%Y%m%d-%H%M%S)"
  echo "Creating timestamped backup of existing core-rules: $BACKUP_FILE"
  cp -p "$REAL_DEST" "$BACKUP_FILE"
fi

echo "Installing repository-managed RPi core-rules to '$TARGET_DEST'..."
cp -p "$TEMPLATE" "$REAL_DEST"

# Validation check
if cmp -s "$TEMPLATE" "$REAL_DEST"; then
  echo "SUCCESS: Installed RPi core-rules verified at '$TARGET_DEST'."
  exit 0
else
  echo "FATAL: Verification failed — installed file at '$TARGET_DEST' does not match template." >&2
  exit 1
fi
