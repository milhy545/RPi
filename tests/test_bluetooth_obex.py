"""Security and lifecycle tests for Bluetooth Object Push."""

from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

import pytest

from rpi_dashboard.api import handlers
from rpi_dashboard.services.bluetooth import obex
from rpi_dashboard.services.bluetooth import service as bluetooth_service
from rpi_dashboard.services.bluetooth.fake import FakeBluetoothBackend, fake_device


OPP_UUID = "00001105-0000-1000-8000-00805f9b34fb"


def test_sanitize_filename_blocks_traversal_controls_and_empty_names():
    assert obex.sanitize_filename("../../secret.txt") == "secret.txt"
    assert obex.sanitize_filename("..\\..\\bad\x00\nname?.txt") == "badname_.txt"
    assert obex.sanitize_filename("../..") == "bluetooth-file"


def test_collision_safe_path_stays_in_downloads(tmp_path):
    first = tmp_path / "photo.jpg"
    first.write_bytes(b"first")

    destination = obex.collision_safe_path(tmp_path, "../../photo.jpg")

    assert destination == tmp_path / "photo (1).jpg"
    assert destination.parent == tmp_path


def test_transfer_limits_reject_oversize_and_low_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("RPI_BLUETOOTH_MAX_TRANSFER_BYTES", "10")
    with pytest.raises(ValueError, match="configured limit"):
        obex.validate_size_and_space(tmp_path, 11)

    monkeypatch.setattr(
        obex.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100, used=99, free=1),
    )
    with pytest.raises(ValueError, match="insufficient free space"):
        obex.validate_size_and_space(tmp_path, 5)


def test_incoming_completion_is_atomic_and_collision_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("RPI_BLUETOOTH_DOWNLOAD_DIR", str(tmp_path))
    manager = obex.BlueZObexManager()
    staging = tmp_path / ".rpi-bt-test.part"
    staging.write_bytes(b"safe payload")
    (tmp_path / "report.txt").write_text("existing", encoding="utf-8")
    record = obex.ObexTransfer(
        id="test",
        direction="inbound",
        address="AA:BB:CC:DD:EE:FF",
        source_adapter="11:22:33:44:55:66",
        name="../../report.txt",
        size=12,
        status="complete",
        path=str(staging),
    )

    completed = manager._finalize_incoming(record)

    assert completed.status == "complete"
    assert completed.path == str(tmp_path / "report (1).txt")
    assert Path(completed.path).read_bytes() == b"safe payload"
    assert not staging.exists()
    assert (tmp_path / "report.txt").read_text(encoding="utf-8") == "existing"


@pytest.mark.asyncio
async def test_start_send_passes_explicit_source_adapter(tmp_path):
    source = tmp_path / "hello.txt"
    source.write_text("hello", encoding="utf-8")
    manager = obex.BlueZObexManager()
    calls = []

    async def call(path, interface, member, **kwargs):
        calls.append((path, interface, member, kwargs))
        if member == "CreateSession":
            return SimpleNamespace(body=["/session/1"])
        return SimpleNamespace(body=["/transfer/1", {}])

    manager._call = call
    manager._monitor = lambda _transfer_id: _never()

    transfer = await manager.start_send(
        "AA:BB:CC:DD:EE:FF",
        str(source),
        "11:22:33:44:55:66",
    )
    manager._tasks[transfer.id].cancel()

    options = calls[0][3]["body"][1]
    assert options["Target"].value == "opp"
    assert options["Source"].value == "11:22:33:44:55:66"
    assert transfer.status == "active"


@pytest.mark.asyncio
async def test_incoming_authorization_rejects_untrusted_sender(monkeypatch, tmp_path):
    monkeypatch.setenv("RPI_BLUETOOTH_DOWNLOAD_DIR", str(tmp_path))
    manager = obex.BlueZObexManager()
    replies = [
        {
            "Session": SimpleNamespace(value="/session/1"),
            "Name": SimpleNamespace(value="hello.txt"),
            "Size": SimpleNamespace(value=5),
        },
        {
            "Destination": SimpleNamespace(value="AA:BB:CC:DD:EE:FF"),
            "Source": SimpleNamespace(value="11:22:33:44:55:66"),
        },
    ]

    async def get_all(_path, _interface):
        return replies.pop(0)

    async def trusted_owner(_source, _address):
        return False

    manager._get_all = get_all
    manager._trusted_owner = trusted_owner

    with pytest.raises(obex.ObexError, match="not paired and trusted") as error:
        await manager.authorize_incoming("/transfer/1")

    assert error.value.code == "permission_denied"


@pytest.mark.asyncio
async def test_send_failure_is_retained_as_structured_history(tmp_path):
    source = tmp_path / "hello.txt"
    source.write_text("hello", encoding="utf-8")
    manager = obex.BlueZObexManager()

    async def fail_call(*_args, **_kwargs):
        raise RuntimeError("remote OPP refused")

    manager._call = fail_call

    with pytest.raises(obex.ObexError, match="remote OPP refused") as error:
        await manager.start_send("AA:BB:CC:DD:EE:FF", str(source), None)

    assert error.value.code == "connection_failed"
    history = manager.snapshot()["transfers"]
    assert history[-1]["status"] == "failed"
    assert "remote OPP refused" in history[-1]["error"]


@pytest.mark.asyncio
async def test_cancel_active_transfer_calls_bluez_and_cleans_session():
    manager = obex.BlueZObexManager()
    record = obex.ObexTransfer(
        id="cancel-me",
        direction="outbound",
        address="AA:BB:CC:DD:EE:FF",
        source_adapter=None,
        name="hello.txt",
        size=5,
        status="active",
        remote_path="/transfer/1",
        session_path="/session/1",
    )
    manager._remember(record)
    task = __import__("asyncio").create_task(_never())
    manager._tasks[record.id] = task
    calls = []

    async def call(path, interface, member, **_kwargs):
        calls.append((path, interface, member))
        return SimpleNamespace(body=[])

    async def remove_session(path):
        calls.append((path, "session", "remove"))

    manager._call = call
    manager._remove_session = remove_session

    cancelled = await manager.cancel(record.id)

    assert cancelled.status == "cancelled"
    assert task.cancelled() or task.cancelling()
    assert ("/transfer/1", obex.OBEX_TRANSFER, "Cancel") in calls
    assert ("/session/1", "session", "remove") in calls


async def _never():
    await __import__("asyncio").sleep(60)


class _FakeObexManager:
    async def state(self):
        return {"ok": True, "available": True, "transfers": []}

    async def start_send(self, address, path, source):
        return obex.ObexTransfer(
            id="send-1",
            direction="outbound",
            address=address,
            source_adapter=source,
            name=Path(path).name,
            size=Path(path).stat().st_size,
            status="active",
            path=path,
        )

    async def cancel(self, transfer_id):
        return obex.ObexTransfer(
            id=transfer_id,
            direction="outbound",
            address="AA:BB:CC:DD:EE:FF",
            source_adapter=None,
            name="hello.txt",
            size=5,
            status="cancelled",
        )


def test_file_send_requires_trusted_opp_device_and_downloads_path(tmp_path, monkeypatch):
    monkeypatch.setenv("RPI_BLUETOOTH_DOWNLOAD_DIR", str(tmp_path))
    backend = FakeBluetoothBackend.one_adapter()
    adapter = next(iter(backend._adapters.values()))
    device = fake_device(
        adapter.id,
        "AA:BB:CC:DD:EE:FF",
        name="Linux PC",
        uuids=(OPP_UUID,),
        paired=True,
        trusted=True,
    )
    backend.add_device(device)
    bluetooth_service.set_backend_for_tests(backend)
    original_manager = obex.get_manager()
    obex.set_manager_for_tests(_FakeObexManager())
    file_path = tmp_path / "hello.txt"
    file_path.write_text("hello", encoding="utf-8")
    try:
        result = handlers.handle_bt_file_send(
            parse_qs(
                f"path={file_path}"
                f"&adapter_id={adapter.id}"
                f"&device_key={device.key}"
            )
        )
    finally:
        obex.set_manager_for_tests(original_manager)
        bluetooth_service.set_backend_for_tests(None)

    assert result["ok"] is True
    assert result["transfer"]["status"] == "active"
    assert result["transfer"]["source_adapter"] == adapter.address
