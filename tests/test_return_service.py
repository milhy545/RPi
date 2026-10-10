import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rpi_dashboard.services import return_service


def test_return_to_dashboard_idempotent():
    # Test when no mode switcher active
    return_service.set_mode_switcher(None)
    result = return_service.return_to_dashboard(reason="test", source="unit_test")
    assert result is False

    last_return = return_service.get_last_return()
    assert last_return["reason"] == "test"
    assert last_return["source"] == "unit_test"
    assert last_return["timestamp"] > 0


def test_return_to_dashboard_with_mock_switcher():
    mock_ms = MagicMock()
    mock_ms.request_stop.return_value = True
    return_service.set_mode_switcher(mock_ms)

    result = return_service.return_to_dashboard(reason="user_request", source="webui")
    assert result is True
    mock_ms.request_stop.assert_called_once()


def test_return_config_get_set(tmp_path, monkeypatch):
    config_file = tmp_path / "return_config.json"
    monkeypatch.setattr(return_service, "_CONFIG_PATH", config_file)

    # Reset cached config so the test reads from the fresh tmp_path file.
    monkeypatch.setattr(return_service, "_config", {})

    cfg = return_service.get_config()
    assert cfg["keyboard_shortcut_enabled"] is True
    assert cfg["xbox_b_hold_enabled"] is True

    # get_config must return a defensive copy -- mutating it must not
    # affect the internal cache.
    cfg["keyboard_shortcut_enabled"] = False
    cfg2 = return_service.get_config()
    assert cfg2["keyboard_shortcut_enabled"] is True

    updated = return_service.update_config({"xbox_b_hold_duration_sec": 3.5})
    assert updated["xbox_b_hold_duration_sec"] == 3.5
    assert config_file.exists()

    # Verify type conversion for bool keys.
    updated2 = return_service.update_config({"xbox_b_hold_enabled": 0})
    assert updated2["xbox_b_hold_enabled"] is False
    assert isinstance(updated2["xbox_b_hold_enabled"], bool)

    # Unknown keys are silently ignored.
    updated3 = return_service.update_config({"unknown_key": 42})
    assert "unknown_key" not in updated3


def test_request_stop_alias():
    mock_ms = MagicMock()
    mock_ms.request_stop.return_value = True
    return_service.set_mode_switcher(mock_ms)

    return_service.request_stop()
    last_return = return_service.get_last_return()
    assert last_return["reason"] == "request_stop"
    assert last_return["source"] == "return_service"
