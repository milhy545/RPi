#!/usr/bin/env bash
# install-ci-gateway.sh — install user-level systemd units for the RPi ↔ Milhy-PC CI chain.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ROLE="${1:-auto}"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

install_unit() {
  local src="$1"
  local dst="$2"
  install -m 0644 "$src" "$dst"
}

install_unit "$ROOT/systemd/user/rpi-git-handoff.service" "$USER_SYSTEMD_DIR/rpi-git-handoff.service"
install_unit "$ROOT/systemd/user/rpi-git-handoff.timer" "$USER_SYSTEMD_DIR/rpi-git-handoff.timer"
install_unit "$ROOT/systemd/user/rpi-ci-agent.service" "$USER_SYSTEMD_DIR/rpi-ci-agent.service"

systemctl --user daemon-reload

if command -v loginctl >/dev/null 2>&1; then
  sudo -A loginctl enable-linger "$USER" >/dev/null 2>&1 || echo "WARN: could not enable linger for $USER; user units may not survive reboot."
fi

if [[ "$ROLE" == "auto" ]]; then
  case "$(hostname -s 2>/dev/null || hostname)" in
    Milhy-PC|milhy-pc|milhy) ROLE="milhy" ;;
    *) ROLE="rpi" ;;
  esac
fi

case "$ROLE" in
  rpi)
    systemctl --user enable --now rpi-git-handoff.timer
    echo "Enabled rpi-git-handoff.timer"
    ;;
  milhy)
    systemctl --user enable --now rpi-ci-agent.service
    echo "Enabled rpi-ci-agent.service"
    ;;
  *)
    echo "Unknown ROLE: $ROLE" >&2
    exit 2
    ;;
esac

echo "Installed user units into $USER_SYSTEMD_DIR"
