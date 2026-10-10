import json
from pathlib import Path


def test_pwa_manifest_valid_json():
    project_root = Path(__file__).resolve().parents[1]
    manifest_path = project_root / "rpi_dashboard" / "static" / "manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["short_name"] == "RPi TV"
    assert "share_target" in data


def test_pwa_service_worker_exists():
    project_root = Path(__file__).resolve().parents[1]
    sw_path = project_root / "rpi_dashboard" / "static" / "sw.js"
    assert sw_path.exists()
    assert "CACHE_NAME" in sw_path.read_text()
