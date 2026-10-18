from pathlib import Path

import pytest


@pytest.fixture
def isolated_report_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from rpi_dashboard.api import handlers

    repo_root = tmp_path / "report-test-repo"
    repo_root.mkdir()
    handlers_path = Path(handlers.__file__)
    isolated_handlers_path = repo_root / "rpi_dashboard" / "api" / "handlers.py"
    isolated_handlers_path.parent.mkdir(parents=True)
    monkeypatch.setattr(handlers, "__file__", str(isolated_handlers_path))
    return repo_root / "reports"
