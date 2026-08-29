"""Tests for audio service module."""

from unittest.mock import patch, MagicMock
import json


def test_gmrender_procfs_parsing():
    """Test native procfs parsing for gmediarender pid and status."""
    from rpi_dashboard.services.audio_dlna import _gmrender_running, _gmrender_pid

    def fake_listdir(path):
        if path == "/proc":
            return ["100", "200", "not-a-pid"]
        return []

    def fake_open(path, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if path == "/proc/100/cmdline":
            mock = MagicMock()
            mock.__enter__.return_value.read.return_value = "systemd\x00"
            return mock
        elif path == "/proc/200/cmdline":
            mock = MagicMock()
            mock.__enter__.return_value.read.return_value = "/usr/bin/gmediarender\x00-f\x00MyDevice"
            return mock
        raise OSError("File not found")

    with patch("os.listdir", side_effect=fake_listdir), patch("builtins.open", side_effect=fake_open):
        assert _gmrender_running() is True
        assert _gmrender_pid() == 200

def test_gmrender_procfs_parsing_not_found():
    """Test native procfs parsing when gmediarender is not running."""
    from rpi_dashboard.services.audio_dlna import _gmrender_running, _gmrender_pid

    def fake_listdir(path):
        if path == "/proc":
            return ["100"]
        return []

    def fake_open(path, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if path == "/proc/100/cmdline":
            mock = MagicMock()
            mock.__enter__.return_value.read.return_value = "systemd\x00"
            return mock
        raise OSError("File not found")

    with patch("os.listdir", side_effect=fake_listdir), patch("builtins.open", side_effect=fake_open):
        assert _gmrender_running() is False
        assert _gmrender_pid() is None


def test_classify_sink_hdmi():
    """Test HDMI sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("alsa_output.platform-hdmi-audio.0.hdmi-stereo") == "hdmi"
    assert _classify_sink("HDMI Output") == "hdmi"


def test_classify_sink_bluetooth():
    """Test Bluetooth sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("bluez_output.00_00_00_00_00_00.a2dp_sink") == "bt"
    assert _classify_sink("bluez_sink") == "bt"


def test_classify_sink_dlna():
    """Test DLNA sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("gmrender-output") == "dlna_output"
    assert _classify_sink("gmediarender-sink") == "dlna_output"


def test_classify_sink_usb():
    """Test USB sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("usb-audio-output") == "usb_output"


def test_classify_source_monitor():
    """Test monitor source classification."""
    from rpi_dashboard.services.audio import _classify_source
    assert _classify_source("monitor of hdmi") == "monitor"


def test_classify_source_usb():
    """Test USB source classification."""
    from rpi_dashboard.services.audio import _classify_source
    # USB Alexa source has a specific prefix
    from rpi_dashboard.services.audio import USB_ALEXA_SRC
    assert _classify_source(USB_ALEXA_SRC) == "usb_input"


def test_load_audio_latency_default():
    """Test loading default audio latency."""
    from rpi_dashboard.services.audio import _load_audio_latency
    with patch("os.path.exists", return_value=False):
        result = _load_audio_latency()
        assert result == {"dlna_output_offset_ms": 0, "default_latency_ms": 0}


def test_audio_set_volume_clamp():
    """Test volume clamping."""
    from rpi_dashboard.services.audio import audio_set_volume
    with patch("rpi_dashboard.services.audio.mixer._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = audio_set_volume("sink", "test", 200)
        assert result["volume"] == 150  # Clamped to max
        
        result = audio_set_volume("sink", "test", -10)
        assert result["volume"] == 0  # Clamped to min


def test_audio_set_latency():
    """Test setting audio latency."""
    from rpi_dashboard.services.audio import audio_set_latency
    with patch("rpi_dashboard.services.audio.latency._save_audio_latency") as mock_save:
        with patch("rpi_dashboard.services.audio.latency._apply_dlna_delay"):
            result = audio_set_latency("dlna_output_offset_ms", 100)
            assert result["ok"] is True
            mock_save.assert_called_once()


def test_get_audio_matrix():
    """Test getting audio matrix."""
    from rpi_dashboard.services.audio import get_audio_matrix
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout='[{"type": "PipeWire:Interface:Node", "id": 1, "info": {"props": {"node.name": "test", "media.class": "Audio/Sink"}}}]',
            returncode=0
        )
        result = get_audio_matrix()
        assert "nodes" in result
        assert "links" in result


def test_audio_matrix_link():
    """Test audio matrix linking via module-loopback and fallback."""
    from rpi_dashboard.services.audio import audio_matrix_link
    with patch("subprocess.run") as mock_run:
        # Mock module check (not loaded) and pactl load-module success
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="12345", returncode=0),
        ]
        res = audio_matrix_link("src_node", "snk_node", "1")
        assert res["ok"] is True
        assert "loopback module loaded" in res["out"]

    with patch("subprocess.run") as mock_run:
        # Mock unlinking: pactl list modules contains loopback
        mock_run.side_effect = [
            MagicMock(stdout="12345 module-loopback source=src_node sink=snk_node", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", returncode=0),
        ]
        res = audio_matrix_link("src_node", "snk_node", "0")
        assert res["ok"] is True
        assert res["out"] == "unloaded"



def test_diagnose_bt_audio_stutter():
    """Test BT audio stutter diagnostics."""
    from rpi_dashboard.services.audio import diagnose_bt_audio_stutter
    with patch("rpi_dashboard.services.audio_diagnostics.audio._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = diagnose_bt_audio_stutter()
        assert "pipewire_quantum" in result
        assert "recommendations" in result


def test_fix_bt_audio_stutter():
    """Test BT audio stutter fix."""
    from rpi_dashboard.services.audio import fix_bt_audio_stutter
    with patch("rpi_dashboard.services.audio_diagnostics.audio._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = fix_bt_audio_stutter()
        assert "ok" in result
        assert "fixes_applied" in result
        assert result["applied"] is False


def test_bt_stutter_diagnostics_parse_real_pw_metadata_shape():
    from rpi_dashboard.services.audio import diagnose_bt_audio_stutter

    metadata = MagicMock(
        returncode=0,
        stdout="update: id:0 key:'clock.rate' value:'48000' type:''\n"
        "update: id:0 key:'clock.quantum' value:'1024' type:''\n",
    )
    wifi = MagicMock(returncode=0, stdout="Not connected.\n")
    with patch("rpi_dashboard.services.audio_diagnostics.audio._run", side_effect=[metadata, wifi]):
        result = diagnose_bt_audio_stutter()

    assert result["pipewire_quantum"] == 1024
    assert result["pipewire_rate"] == 48000


def test_bt_stutter_diagnostics_flags_2_4ghz_overlap_and_low_quantum():
    from rpi_dashboard.services.audio import diagnose_bt_audio_stutter

    metadata = MagicMock(
        returncode=0,
        stdout="update: id:0 key:'clock.rate' value:'44100' type:''\n"
        "update: id:0 key:'clock.quantum' value:'512' type:''\n",
    )
    wifi = MagicMock(returncode=0, stdout="Connected to AP freq: 2412\n")
    with patch("rpi_dashboard.services.audio_diagnostics.audio._run", side_effect=[metadata, wifi]):
        result = diagnose_bt_audio_stutter()

    assert result["frequency_overlap"] is True
    assert result["pipewire_quantum"] == 512
    assert any("5GHz" in rec for rec in result["recommendations"])
    assert any("quantum" in rec.lower() for rec in result["recommendations"])


def test_bt_stutter_fix_does_not_mutate_an_already_stable_baseline():
    from rpi_dashboard.services.audio import fix_bt_audio_stutter

    with patch(
        "rpi_dashboard.services.audio_diagnostics.diagnose_bt_audio_stutter",
        return_value={"pipewire_quantum": 1024, "pipewire_rate": 48000},
    ), patch("rpi_dashboard.services.audio_diagnostics.audio._run") as run:
        result = fix_bt_audio_stutter(apply=True)

    assert result["fixes_applied"] == []
    assert "already active" in result["next_step"]
    run.assert_not_called()


def test_audio_multi_output_requires_two_bluetooth_sinks():
    """A combine sink must never silently collapse to one physical output."""
    from rpi_dashboard.services.audio import audio_multi_output

    with patch("rpi_dashboard.services.audio.multi_output._find_multi_output_module", return_value=None), \
         patch("rpi_dashboard.services.audio.multi_output._bluetooth_output_sinks", return_value=["bluez_output.one.1"]):
        result = audio_multi_output("start")

    assert result["ok"] is False
    assert "at least two" in result["error"]


def test_audio_multi_output_creates_combined_sink_and_selects_it():
    """Starting multi-output should create the PipeWire sink and make it default."""
    from rpi_dashboard.services.audio import MULTI_OUTPUT_SINK, audio_multi_output

    sinks = ["bluez_output.soundbar.1", "bluez_output.tibo.1"]
    run_result = MagicMock(returncode=0, stdout="77\n", stderr="")
    with patch("rpi_dashboard.services.audio.multi_output._find_multi_output_module", return_value=None), \
         patch("rpi_dashboard.services.audio.multi_output._bluetooth_output_sinks", return_value=sinks), \
         patch("rpi_dashboard.services.audio.multi_output._attach_bluetooth_inputs", return_value=([], [])), \
         patch("rpi_dashboard.services.audio.multi_output._multi_output_status", return_value={"ok": True, "active": True}) as status, \
         patch("rpi_dashboard.services.audio.multi_output._run", return_value=run_result) as run:
        result = audio_multi_output("start")

    assert result["ok"] is True
    assert result["created"] is True
    assert status.called
    commands = [call.args[0] for call in run.call_args_list]
    assert [
        "pactl", "load-module", "module-combine-sink",
        f"sink_name={MULTI_OUTPUT_SINK}",
        f"slaves={','.join(sinks)}",
        "adjust_time=1",
        "format=s16le",
        "rate=44100",
    ] in commands
    assert ["pactl", "set-default-sink", MULTI_OUTPUT_SINK] in commands


def test_audio_multi_output_sync_is_idempotent_and_attaches_inputs():
    """Syncing an existing route should not reload it and should attach new BT input."""
    from rpi_dashboard.services.audio import audio_multi_output

    sinks = ["bluez_output.soundbar.1", "bluez_output.tibo.1"]
    module = {"id": "77", "slaves": sinks}
    run_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("rpi_dashboard.services.audio.multi_output._find_multi_output_module", return_value=module), \
         patch("rpi_dashboard.services.audio.multi_output._bluetooth_output_sinks", return_value=sinks), \
         patch("rpi_dashboard.services.audio.multi_output._attach_bluetooth_inputs", return_value=(["bluez_input.phone.0"], [])), \
         patch("rpi_dashboard.services.audio.multi_output._multi_output_status", return_value={"ok": True, "active": True}), \
         patch("rpi_dashboard.services.audio.multi_output._run", return_value=run_result) as run:
        result = audio_multi_output("sync")

    assert result["ok"] is True
    assert result["created"] is False
    assert result["attached_inputs"] == ["bluez_input.phone.0"]
    commands = [call.args[0] for call in run.call_args_list]
    assert not any(command[:3] == ["pactl", "load-module", "module-combine-sink"] for command in commands)


def test_audio_multi_output_stop_restores_a_physical_sink():
    """Stopping should switch away before unloading the virtual combine sink."""
    from rpi_dashboard.services.audio import audio_multi_output

    sinks = ["bluez_output.soundbar.1", "bluez_output.tibo.1"]
    module = {"id": "77", "slaves": sinks}
    run_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("rpi_dashboard.services.audio.multi_output._find_multi_output_module", side_effect=[module, None]), \
         patch("rpi_dashboard.services.audio.multi_output._bluetooth_output_sinks", return_value=sinks), \
         patch("rpi_dashboard.services.audio.multi_output._find_loopbacks", return_value=[]), \
         patch("rpi_dashboard.services.audio.multi_output._multi_output_status", return_value={"ok": True, "active": False}), \
         patch("rpi_dashboard.services.audio.multi_output._run", return_value=run_result) as run:
        result = audio_multi_output("stop")

    assert result["ok"] is True
    assert result["fallback_sink"] == sinks[0]
    commands = [call.args[0] for call in run.call_args_list]
    assert commands.index(["pactl", "set-default-sink", sinks[0]]) < commands.index(["pactl", "unload-module", "77"])


def test_audio_multi_output_reconcile_removes_stale_virtual_sink_but_keeps_intent():
    """A disconnected speaker must not leave a dead combine sink as default."""
    from rpi_dashboard.services.audio import MULTI_OUTPUT_SINK, audio_multi_output

    intent = {
        "enabled": True,
        "slaves": ["bluez_output.soundbar.1", "bluez_output.tibo.1"],
    }
    module = {"id": "77", "slaves": intent["slaves"]}
    run_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("rpi_dashboard.services.audio.multi_output._find_multi_output_module", return_value=module), \
         patch("rpi_dashboard.services.audio.multi_output._bluetooth_output_sinks", return_value=[]), \
         patch("rpi_dashboard.services.audio.multi_output._load_multi_output_intent", return_value=intent), \
         patch("rpi_dashboard.services.audio.multi_output._find_loopbacks", return_value=[]), \
         patch("rpi_dashboard.services.audio.multi_output._physical_fallback_sink", return_value="alsa_output.hdmi"), \
         patch("rpi_dashboard.services.audio.state._get_default_sink", return_value=MULTI_OUTPUT_SINK), \
         patch("rpi_dashboard.services.audio.multi_output._multi_output_status", return_value={"ok": True, "active": False}), \
         patch("rpi_dashboard.services.audio.multi_output._save_multi_output_intent") as save, \
         patch("rpi_dashboard.services.audio.multi_output._run", return_value=run_result) as run:
        result = audio_multi_output("reconcile")

    assert result["ok"] is True
    assert result["waiting_for_outputs"] is True
    assert result["intent"] == intent
    save.assert_not_called()
    commands = [call.args[0] for call in run.call_args_list]
    assert commands.index(["pactl", "set-default-sink", "alsa_output.hdmi"]) < commands.index(
        ["pactl", "unload-module", "77"]
    )


def test_audio_multi_output_reconcile_restores_route_when_both_outputs_return():
    """Persisted output ownership should recreate the route after reconnect."""
    from rpi_dashboard.services.audio import audio_multi_output

    sinks = ["bluez_output.soundbar.1", "bluez_output.tibo.1"]
    intent = {"enabled": True, "slaves": sinks}
    run_result = MagicMock(returncode=0, stdout="77\n", stderr="")
    with patch("rpi_dashboard.services.audio.multi_output._find_multi_output_module", return_value=None), \
         patch("rpi_dashboard.services.audio.multi_output._bluetooth_output_sinks", return_value=sinks), \
         patch("rpi_dashboard.services.audio.multi_output._load_multi_output_intent", return_value=intent), \
         patch("rpi_dashboard.services.audio.multi_output._attach_bluetooth_inputs", return_value=([], [])), \
         patch("rpi_dashboard.services.audio.multi_output._multi_output_status", return_value={"ok": True, "active": True}), \
         patch("rpi_dashboard.services.audio.multi_output._save_multi_output_intent") as save, \
         patch("rpi_dashboard.services.audio.multi_output._run", return_value=run_result) as run:
        result = audio_multi_output("reconcile")

    assert result["ok"] is True
    assert result["reconciled"] is True
    assert result["reason"] == "requested outputs available"
    save.assert_called_once_with(True, sinks)
    commands = [call.args[0] for call in run.call_args_list]
    assert [
        "pactl", "load-module", "module-combine-sink",
        "sink_name=rpi_bt_multi_output",
        f"slaves={','.join(sinks)}",
        "adjust_time=1",
        "format=s16le",
        "rate=44100",
    ] in commands


def test_audio_multi_output_status_never_mutates_pipewire():
    """Polling state remains read-only even when the virtual route is stale."""
    from rpi_dashboard.services.audio import audio_multi_output

    with patch(
        "rpi_dashboard.services.audio.multi_output._multi_output_status",
        return_value={"ok": True, "active": True, "healthy": False},
    ), patch("rpi_dashboard.services.audio.multi_output._run") as run:
        result = audio_multi_output("status")

    assert result == {"ok": True, "active": True, "healthy": False}
    run.assert_not_called()


def test_bluetooth_audio_profiles_report_negotiated_pipewire_roles():
    """Profile state should come from PipeWire rather than device-name guesses."""
    from rpi_dashboard.services.audio import bluetooth_audio_profiles

    cards = [
        {
            "name": "bluez_card.1C_D1_07_52_E1_1A",
            "properties": {
                "api.bluez5.address": "1C:D1:07:52:E1:1A",
                "device.description": "Phone",
            },
            "profiles": {
                "off": {"description": "Off", "available": "yes", "sinks": 0, "sources": 0},
                "audio-gateway": {
                    "description": "Audio Gateway",
                    "available": "yes",
                    "sinks": 0,
                    "sources": 1,
                },
            },
            "active_profile": "audio-gateway",
        }
    ]
    with patch("rpi_dashboard.services.audio.profiles._run") as run:
        run.return_value = MagicMock(returncode=0, stdout=json.dumps(cards), stderr="")
        result = bluetooth_audio_profiles()

    assert result["ok"] is True
    assert result["cards"][0]["active_profile"] == "audio-gateway"
    assert result["cards"][0]["profiles"][1]["sources"] == 1


def test_set_bluetooth_audio_profile_validates_card_and_profile():
    """Only a currently advertised profile on a BlueZ card may be selected."""
    from rpi_dashboard.services.audio import audio_set_bluetooth_profile

    state = {
        "ok": True,
        "cards": [
            {
                "name": "bluez_card.phone",
                "profiles": [
                    {"id": "audio-gateway", "available": "yes"},
                    {"id": "off", "available": "yes"},
                ],
            }
        ],
    }
    with patch("rpi_dashboard.services.audio.profiles.bluetooth_audio_profiles", return_value=state), \
         patch("rpi_dashboard.services.audio.profiles._run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as run:
        result = audio_set_bluetooth_profile("bluez_card.phone", "audio-gateway")
        missing = audio_set_bluetooth_profile("bluez_card.phone", "not-advertised")

    assert result["ok"] is True
    run.assert_called_once_with(
        ["pactl", "set-card-profile", "bluez_card.phone", "audio-gateway"],
        t=10,
    )

    assert missing["ok"] is False
    assert missing["code"] == "profile_unavailable"


def test_audio_set_mute_rejects_invalid_kind():
    from rpi_dashboard.services.audio import audio_set_mute

    assert audio_set_mute("card", "bluez_card.phone", True)["ok"] is False


def test_set_global_master_volume():
    from rpi_dashboard.services.audio import set_global_master_volume

    mock_state = {
        "sinks": [
            {"name": "alsa_output.pci-0000_00_1b.0.analog-stereo"},
            {"name": "bluez_output.00_00_00_00_00_00.a2dp_sink"},
        ]
    }
    with patch("rpi_dashboard.services.audio.state.audio_state", return_value=mock_state), \
         patch("rpi_dashboard.services.audio.mixer._run", return_value=MagicMock(returncode=0)), \
         patch("rpi_dashboard.services.bluetooth.service.bluetooth_state", return_value={}), \
         patch("rpi_dashboard.services.bluetooth.service.media_action"):
        res = set_global_master_volume(75)
        assert res["ok"] is True
        assert res["volume"] == 75
        assert len(res["updated_sinks"]) == 2


def test_bt_sink_volume_sets_pactl_and_propagates_input():
    """BlueZ sink volume request invokes pactl set-sink-volume and propagates to input routing."""
    from rpi_dashboard.services.audio import audio_set_volume

    bt_sink = "bluez_output.00_11_22_33_44_55.a2dp_sink"

    with patch("rpi_dashboard.services.audio.mixer._run") as mock_run, \
         patch("rpi_dashboard.services.bluetooth.service.bluetooth_state", return_value={"devices": [{"address": "00:11:22:33:44:55", "adapter_id": "adapter-0", "key": "adapter-0/00:11:22:33:44:55"}]}), \
         patch("rpi_dashboard.services.bluetooth.service.media_action") as mock_media_action:
        mock_run.return_value = MagicMock(returncode=0)
        result = audio_set_volume("sink", bt_sink, 80)
        assert result["ok"] is True
        assert result["volume"] == 80
        all_calls = [call.args[0] for call in mock_run.call_args_list]
        assert ["pactl", "set-sink-volume", bt_sink, "80%"] in all_calls
        mock_media_action.assert_called_once_with("volume", value=int((80 / 100.0) * 127), adapter_id="adapter-0", device_key="adapter-0/00:11:22:33:44:55")

    with patch("rpi_dashboard.services.audio.mixer._run") as mock_run, \
         patch("rpi_dashboard.services.bluetooth.service.bluetooth_state", return_value={}), \
         patch("rpi_dashboard.services.bluetooth.service.media_action") as mock_media_action:
        mock_run.return_value = MagicMock(returncode=0)
        result = audio_set_volume("sink", bt_sink, 200)
        assert result["volume"] == 150
        result = audio_set_volume("sink", bt_sink, -10)
        assert result["volume"] == 0

