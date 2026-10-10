import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "tools" / "import_main_receipt.py"
SPEC = importlib.util.spec_from_file_location("import_main_receipt", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
repository_from_origin = MODULE.repository_from_origin
select_successful_main_run = MODULE.select_successful_main_run


def _run(**overrides):
    run = {
        "head_sha": "head",
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "path": ".github/workflows/ci.yml",
        "html_url": "https://github.com/example/repo/actions/runs/1",
    }
    run.update(overrides)
    return run


def test_selects_only_exact_successful_main_push_ci_run() -> None:
    rejected = [
        _run(head_sha="other"),
        _run(head_branch="feature"),
        _run(event="pull_request"),
        _run(conclusion="failure"),
        _run(path=".github/workflows/other.yml"),
    ]

    assert select_successful_main_run([*rejected, _run()], "head") == _run()
    assert select_successful_main_run(rejected, "head") is None


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://github.com/example/repo.git", "example/repo"),
        ("git@github.com:example/repo.git", "example/repo"),
    ],
)
def test_repository_from_origin(origin: str, expected: str) -> None:
    assert repository_from_origin(origin) == expected
