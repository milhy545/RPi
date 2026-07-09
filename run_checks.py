import subprocess

def run_cmd(cmd, out_file):
    with open(out_file, "w") as f:
        subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)

run_cmd("uv run ruff check rpi_dashboard tests", "ruff.log")
run_cmd("uv run mypy rpi_dashboard tests", "mypy.log")
run_cmd("uv run pytest tests/", "pytest.log")
