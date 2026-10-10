"""Tests for explicit BlueZ pairing challenge authorization."""

import asyncio

import pytest
from dbus_fast.errors import DBusError

from rpi_dashboard.services.bluetooth.pairing import PairingAgent


@pytest.mark.asyncio
async def test_confirmation_waits_for_visible_user_response():
    agent = PairingAgent(timeout=0.2)
    path = "/org/bluez/hci0/dev_AA_BB"
    agent.prepare(path)

    request = asyncio.create_task(agent._request("confirmation", path, passkey=12345))
    await asyncio.sleep(0)

    assert agent.challenge == {
        "type": "confirmation",
        "device_path": path,
        "passkey": 12345,
        "service_uuid": None,
        "state": "waiting_for_user",
    }
    assert agent.respond(True) is True
    await request
    assert agent.challenge["state"] == "accepted"


@pytest.mark.asyncio
async def test_agent_rejects_device_outside_explicit_pairing_target():
    agent = PairingAgent(timeout=0.1)
    agent.prepare("/org/bluez/hci0/dev_AA")

    with pytest.raises(DBusError):
        await agent._request("authorization", "/org/bluez/hci1/dev_BB")


@pytest.mark.asyncio
async def test_pin_code_is_supplied_only_after_user_entry():
    agent = PairingAgent(timeout=0.2)
    path = "/org/bluez/hci0/dev_AA"
    agent.prepare(path)
    request = asyncio.create_task(agent._request("pin_code", path))
    await asyncio.sleep(0)

    assert agent.challenge["type"] == "pin_code"
    agent.respond(True, "2468")

    assert (await request)["value"] == "2468"


@pytest.mark.asyncio
async def test_agent_cancel_rejects_pending_challenge():
    agent = PairingAgent(timeout=0.2)
    path = "/org/bluez/hci0/dev_AA"
    agent.prepare(path)
    request = asyncio.create_task(agent._request("authorization", path))
    await asyncio.sleep(0)

    agent.reject_pending("BlueZ cancelled pairing")

    with pytest.raises(DBusError):
        await request
