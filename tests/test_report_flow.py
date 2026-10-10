import os
import json
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.process_reports import process_reports

def test_report_flow_end_to_end(tmp_path, monkeypatch):
    # Setup temporary directory structure for reports and conductor tracks
    reports_dir = tmp_path / "reports"
    tracks_dir = tmp_path / "conductor" / "tracks"
    tracks_md = tmp_path / "conductor" / "tracks.md"
    
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(tracks_dir, exist_ok=True)
    with open(tracks_md, "w", encoding="utf-8") as f:
        f.write("# Tracks\n")
        
    # Patch paths in process_reports module
    import tools.process_reports
    monkeypatch.setattr(tools.process_reports, "REPORTS_DIR", str(reports_dir))
    monkeypatch.setattr(tools.process_reports, "PROCESSED_DIR", str(reports_dir / "processed"))
    monkeypatch.setattr(tools.process_reports, "TRACKS_DIR", str(tracks_dir))
    monkeypatch.setattr(tools.process_reports, "TRACKS_MD", str(tracks_md))
    
    # Save a report to reports/
    report_data = {
        "type": "bug",
        "description": "Integration test user report",
        "timestamp": 123456789
    }
    
    with open(reports_dir / "report_123456789_bug.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f)
        
    # Run the worker
    process_reports()
    
    # Verify the report JSON was moved to processed/
    assert os.path.exists(reports_dir / "processed" / "report_123456789_bug.json")
    assert not os.path.exists(reports_dir / "report_123456789_bug.json")
    
    # Verify conductor files were generated
    track_dir = tracks_dir / "report_123456789_bug"
    assert os.path.isdir(track_dir)
    assert os.path.isfile(track_dir / "metadata.json")
    assert os.path.isfile(track_dir / "spec.md")
    assert os.path.isfile(track_dir / "plan.md")
    
    # Check plan content
    with open(track_dir / "plan.md", "r", encoding="utf-8") as f:
        plan_content = f.read()
    assert "Integration test user report" in plan_content
    
    # Check tracks.md content
    with open(tracks_md, "r", encoding="utf-8") as f:
        tracks_md_content = f.read()
    assert "report_123456789_bug" in tracks_md_content
