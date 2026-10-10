import json

from scripts import create_receipt


def test_create_receipt_writes_verify_done_compatible_report(tmp_path, monkeypatch):
    sha = "a" * 40
    tree = "b" * 40

    def fake_check_output(command, text):
        if command == ["git", "rev-parse", "HEAD"]:
            return f"{sha}\n"
        if command == ["git", "rev-parse", "HEAD^{tree}"]:
            return f"{tree}\n"
        if command == ["hostname"]:
            return "ci-runner\n"
        raise AssertionError(command)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(create_receipt.subprocess, "check_output", fake_check_output)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    create_receipt.main()

    receipt_path = next((tmp_path / "conductor/ci/receipts").glob("*.json"))
    receipt = json.loads(receipt_path.read_text())
    report = (tmp_path / receipt["ci_report"]).read_text()

    assert report.splitlines()[0] == "PASS"
    assert receipt["status"] == "done"
    assert receipt["commit_sha"] == sha
    assert receipt["tree_hash"] == tree
