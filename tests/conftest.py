from pathlib import Path

import pytest


@pytest.fixture
def isolated_report_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from rpi_dashboard.api import handlers

    repo_root = tmp_path / "report-test-repo"
    repo_root.mkdir()
    handlers_path = Path(handlers.__file__)
    isolated_handlers_path = repo_root / "rpi_dashboard" / "api" / "handlers.py"
    original_resolve = Path.resolve

    def resolve_test_paths(path: Path, *args, **kwargs) -> Path:
        if path == handlers_path:
            return isolated_handlers_path
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve_test_paths)
    return repo_root / "reports"
