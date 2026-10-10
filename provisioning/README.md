# Provisioning Scripts

Automated setup scripts for the Dumb TV Dashboard on Raspberry Pi OS.

## Quick Start

```bash
# Run full provisioning
bash provisioning/provision.sh
```

## Individual Steps

| Script | Purpose |
|--------|---------|
| `01-install-apt-deps.sh` | Install system packages (mpv, python3, git, etc.) |
| `02-install-uv-ytdlp.sh` | Install uv (Python package manager) and yt-dlp |
| `03-clone-repo.sh` | Clone or sync the repository |
| `04-setup-venv.sh` | Initialize virtual environment with uv |
| `05-install-service.sh` | Install and start systemd service |

## Configuration

Environment variables:

- `REPO_URL` — Git repository URL (default: `https://github.com/milhy777/RPi.git`)
- `INSTALL_DIR` — Installation directory (default: `$HOME/rpi-dashboard`)

## Service Management

```bash
# Check status
systemctl status dashboard@$(whoami)

# View logs
journalctl -u dashboard@$(whoami) -f

# Restart
sudo systemctl restart dashboard@$(whoami)

# Stop
sudo systemctl stop dashboard@$(whoami)
```

## Idempotency

All scripts are idempotent — safe to run multiple times. They check for existing installations and skip or update as needed.
