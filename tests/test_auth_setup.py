"""Tests for tools/auth_setup.py (Phase 6)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools.auth_setup as auth_setup
from rpi_dashboard.auth import AuthStore


def _read_auth(path: Path) -> dict:
    return AuthStore(path).load()


def test_expert_creates_auth_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """expert subcommand creates auth.json with expert hash."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth_setup, "_prompt_password", lambda *a, **k: "expert-pw")
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    rc = auth_setup.main(["--auth-file", str(auth_file), "expert"])
    assert rc == 0
    assert auth_file.exists()

    data = _read_auth(auth_file)
    assert "expert" in data
    assert "password_hash" in data["expert"]
    assert "salt" in data["expert"]
    assert "iterations" in data["expert"]


def test_admin_creates_auth_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """admin subcommand creates auth.json with admin hash."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth_setup, "_prompt_password", lambda *a, **k: "admin-pw")
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    rc = auth_setup.main(["--auth-file", str(auth_file), "admin"])
    assert rc == 0

    data = _read_auth(auth_file)
    assert "admin" in data


def test_second_write_creates_mode_0600_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Second write creates mode-0600 backup with first credentials."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth_setup, "_prompt_password", lambda *a, **k: "first")
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    auth_setup.main(["--auth-file", str(auth_file), "expert"])
    first_hash = _read_auth(auth_file)["expert"]["password_hash"]
    backup = auth_file.with_name("auth.json.bak")
    assert not backup.exists()

    monkeypatch.setattr(auth_setup, "_prompt_password", lambda *a, **k: "second")
    auth_setup.main(["--auth-file", str(auth_file), "expert"])
    second_hash = _read_auth(auth_file)["expert"]["password_hash"]

    assert backup.exists()
    assert second_hash != first_hash
    backup_data = _read_auth(backup)
    assert backup_data["expert"]["password_hash"] == first_hash
    assert backup.stat().st_mode & 0o777 == 0o600


def test_api_key_raw_token_prints_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    """API key raw token appears exactly once on stdout."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    rc = auth_setup.main(["--auth-file", str(auth_file), "api-key", "test-label", "expert"])
    assert rc == 0

    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    raw = out[0]
    assert len(raw) >= 32  # token_urlsafe(32)


def test_api_key_raw_token_absent_from_auth_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture):
    """Raw token is not present in auth.json; only SHA-256 digest stored."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    rc = auth_setup.main(["--auth-file", str(auth_file), "api-key", "no-plain", "admin"])
    assert rc == 0

    raw = capsys.readouterr().out.strip()
    data = _read_auth(auth_file)
    assert "api_keys" in data
    digest = next(iter(data["api_keys"]))
    assert len(digest) == 64  # sha256 hex
    # raw token not in file content
    assert raw not in auth_file.read_text(encoding="utf-8")
    assert data["api_keys"][digest]["role"] == "admin"
    assert data["api_keys"][digest]["label"] == "no-plain"


def test_askpass_selected_when_display_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """DISPLAY set -> ssh-askpass selected and invoked (no password in argv)."""
    auth_file = tmp_path / "auth.json"
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return type("R", (), {"stdout": "askpass-pw\n", "returncode": 0})()

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setenv("DISPLAY", ":0")
    # Make /usr/bin/ssh-askpass look like executable file
    monkeypatch.setattr(Path, "is_file", lambda self: str(self) == "/usr/bin/ssh-askpass")
    monkeypatch.setattr("os.access", lambda p, m: True)
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    rc = auth_setup.main(["--auth-file", str(auth_file), "expert"])
    assert rc == 0
    assert any("ssh-askpass" in c[0] for c in calls)
    for cmd in calls:
        assert isinstance(cmd, list)
        assert all("askpass-pw" not in arg for arg in cmd)


def test_askpass_selected_when_ssh_askpass_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """SSH_ASKPASS set -> custom askpass selected and invoked."""
    auth_file = tmp_path / "auth.json"
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return type("R", (), {"stdout": "custom-pw\n", "returncode": 0})()

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setenv("SSH_ASKPASS", "/custom/askpass")
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)
    # Make custom askpass look like executable file
    monkeypatch.setattr(Path, "is_file", lambda self: str(self) == "/custom/askpass")
    monkeypatch.setattr("os.access", lambda p, m: True)

    rc = auth_setup.main(["--auth-file", str(auth_file), "admin"])
    assert rc == 0
    assert any("/custom/askpass" in c[0] for c in calls)
    for cmd in calls:
        assert all("custom-pw" not in arg for arg in cmd)


def test_no_askpass_fallback_to_getpass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When neither DISPLAY nor SSH_ASKPASS, getpass.getpass is called once."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("SSH_ASKPASS", raising=False)
    monkeypatch.setattr(auth_setup, "_detect_askpass", lambda: None)

    calls = []
    def fake_getpass(prompt: str) -> str:
        calls.append(prompt)
        return "getpass-secret"
    monkeypatch.setattr("getpass.getpass", fake_getpass)

    pw = auth_setup._prompt_password("Test prompt", confirm=False)
    assert pw == "getpass-secret"
    assert len(calls) == 1
    assert calls[0] == "Test prompt: "


def test_file_mode_0600(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Created auth.json and parent dir have mode 0600/0700."""
    auth_file = tmp_path / "secure" / "auth.json"
    monkeypatch.setattr(auth_setup, "_prompt_password", lambda *a, **k: "pw")
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    auth_setup.main(["--auth-file", str(auth_file), "expert"])

    assert auth_file.stat().st_mode & 0o777 == 0o600
    assert auth_file.parent.stat().st_mode & 0o777 == 0o700


def test_api_key_default_role_basic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """api-key defaults to Basic role when role omitted."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    auth_setup.main(["--auth-file", str(auth_file), "api-key", "default-role"])

    data = _read_auth(auth_file)
    digest = next(iter(data["api_keys"]))
    assert data["api_keys"][digest]["role"] == "basic"


def test_api_key_invalid_role_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """api-key rejects invalid role with non-zero exit."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    rc = auth_setup.main(["--auth-file", str(auth_file), "api-key", "label", "invalid"])
    assert rc != 0  # argparse returns 2 for invalid choice


def test_api_key_empty_label_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """api-key rejects empty label (argparse validates)."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    rc = auth_setup.main(["--auth-file", str(auth_file), "api-key", ""])
    assert rc != 0


def test_mismatched_passwords_returns_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Mismatched confirm in _prompt_password raises ValueError."""
    auth_file = tmp_path / "auth.json"
    call_count = [0]

    def fake_getpass(prompt: str) -> str:
        call_count[0] += 1
        if call_count[0] == 1:
            return "first"
        return "second"  # mismatch

    monkeypatch.setattr(auth_setup, "_detect_askpass", lambda: None)
    monkeypatch.setattr("getpass.getpass", fake_getpass)
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    with pytest.raises(ValueError, match="do not match"):
        auth_setup._prompt_password("Test password")


def test_existing_credentials_preserved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Creating API key preserves existing expert/admin credentials."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth_setup, "_prompt_password", lambda *a, **k: "expert-pw")
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    auth_setup.main(["--auth-file", str(auth_file), "expert"])
    assert _read_auth(auth_file).get("expert")

    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)
    auth_setup.main(["--auth-file", str(auth_file), "api-key", "new-key", "admin"])

    data = _read_auth(auth_file)
    assert "expert" in data
    assert "api_keys" in data
    assert len(data["api_keys"]) == 1


def test_detect_askpass_requires_executable_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Custom SSH_ASKPASS must be executable regular file."""
    monkeypatch.delenv("DISPLAY", raising=False)

    # Not executable
    not_exec = tmp_path / "askpass"
    not_exec.write_text("#!/bin/sh\necho test")
    monkeypatch.setenv("SSH_ASKPASS", str(not_exec))
    assert auth_setup._detect_askpass() is None

    # Make executable
    not_exec.chmod(0o755)
    assert auth_setup._detect_askpass() == str(not_exec)

    # Directory not file
    dir_path = tmp_path / "dir"
    dir_path.mkdir()
    monkeypatch.setenv("SSH_ASKPASS", str(dir_path))
    assert auth_setup._detect_askpass() is None


def test_detect_askpass_default_when_display_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """DISPLAY set -> /usr/bin/ssh-askpass if executable file."""
    monkeypatch.delenv("SSH_ASKPASS", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")

    # Exists and executable
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/ssh-askpass" if x == "ssh-askpass" else None)
    monkeypatch.setattr(Path, "is_file", lambda self: str(self) == "/usr/bin/ssh-askpass")
    monkeypatch.setattr("os.access", lambda p, m: True)
    assert auth_setup._detect_askpass() == "/usr/bin/ssh-askpass"

    # Not executable
    monkeypatch.setattr("os.access", lambda p, m: False)
    assert auth_setup._detect_askpass() is None


def test_subprocess_run_never_gets_password_in_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify no password ever appears in subprocess argv."""
    auth_file = tmp_path / "auth.json"
    captured: list[list[str]] = []

    def capture_run(cmd, **kwargs):
        captured.append(cmd)
        return type("R", (), {"stdout": "pw\n", "returncode": 0})()

    monkeypatch.setattr("subprocess.run", capture_run)
    monkeypatch.setenv("DISPLAY", ":0")
    # Make /usr/bin/ssh-askpass look like executable file
    monkeypatch.setattr(Path, "is_file", lambda self: str(self) == "/usr/bin/ssh-askpass")
    monkeypatch.setattr("os.access", lambda p, m: True)
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    auth_setup.main(["--auth-file", str(auth_file), "expert"])

    for cmd in captured:
        assert isinstance(cmd, list)
        assert all("pw" not in arg for arg in cmd)


def test_main_returns_zero_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """All three subcommands return 0 on success."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth_setup, "_prompt_password", lambda *a, **k: "pw")
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda *a, **k: 100_000)

    assert auth_setup.main(["--auth-file", str(auth_file), "expert"]) == 0
    assert auth_setup.main(["--auth-file", str(auth_file), "admin"]) == 0
    assert auth_setup.main(["--auth-file", str(auth_file), "api-key", "k", "expert"]) == 0