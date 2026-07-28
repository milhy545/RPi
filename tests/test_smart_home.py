import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rpi_dashboard.api.handlers import handle_ha_config


def test_handle_ha_config():
    res = handle_ha_config({})
    assert res["ok"] is True
    assert "rpi_tv_play" in res["yaml"]
    assert "RPi TV" in res["yaml"]
