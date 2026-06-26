import sys, os
import json
import subprocess
import builtins

# Import the webserver module to access audio_set_default
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import webserver

class DummyResult:
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def test_audio_set_default_success(monkeypatch):
    # Mock subprocess.run used inside _run (which webserver uses)
    def fake_run(cmd, capture_output=False, text=False, timeout=None):
        # Ensure the command contains 'set-default-sink'
        assert 'set-default-sink' in cmd
        return DummyResult(returncode=0, stdout='OK', stderr='')
    monkeypatch.setattr(webserver, '_run', fake_run)
    result = webserver.audio_set_default('bluez_sink.XX_XX_XX')
    assert result['ok'] is True
    assert 'bluez_sink' in result['name']
