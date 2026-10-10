import os, json
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import webserver

def test_save_report_creates_file(tmp_path, monkeypatch):
    # Monkeypatch the directory resolution to use a temporary path
    monkeypatch.setattr(os.path, "dirname", lambda _: str(tmp_path))
    # Ensure the reports subdirectory exists
    reports_dir = os.path.join(str(tmp_path), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    # Prepare report data
    report = {"type": "bug", "description": "Test bug", "tab": "home"}
    filename = webserver._save_report(report, "127.0.0.1")
    # Verify file exists and content matches
    file_path = os.path.join(str(tmp_path), "reports", filename)
    assert os.path.isfile(file_path)
    data = json.loads(open(file_path, "r", encoding="utf-8").read())
    assert data["type"] == "bug"
    assert data["description"] == "Test bug"
    # client_ip is added by the endpoint; the core save function only writes given dict
