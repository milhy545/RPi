from unittest.mock import patch
from rpi_dashboard.api import handlers

def test_bt_media_volume_syncs_to_pipewire():
    mock_q = {"action": ["volume"], "value": ["64"], "mac": ["00:11:22:33:44:55"]}
    
    with patch("rpi_dashboard.api.handlers.bluetooth_service.media_action", return_value={"ok": True}), \
         patch("rpi_dashboard.api.handlers.audio.audio_set_volume") as mock_set_volume:
        res = handlers.handle_bt_media(mock_q)
        assert res["ok"] is True
        
        # 64 / 127 = ~50%
        mock_set_volume.assert_called_once_with("sink", "bluez_output.00_11_22_33_44_55.a2dp_sink", 50)
