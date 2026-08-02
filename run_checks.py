import subprocess
from pathlib import Path
from typing import Sequence


def run_cmd(cmd: Sequence[str], out_file: str) -> None:
    with Path(out_file).open("w", encoding="utf-8") as output:
        subprocess.run(cmd, check=False, stdout=output, stderr=subprocess.STDOUT)


run_cmd(["uv", "run", "ruff", "check", "rpi_dashboard", "tests"], "ruff.log")
run_cmd(["uv", "run", "mypy", "rpi_dashboard", "tests"], "mypy.log")
run_cmd(["uv", "run", "pytest", "tests/"], "pytest.log")
