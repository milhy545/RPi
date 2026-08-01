import json
from typing import Any, Dict


from .common import _run

def bluetooth_audio_profiles() -> Dict[str, Any]:
    """Return BlueZ PipeWire cards and their negotiated profile choices."""
    try:
        result = _run(["pactl", "--format=json", "list", "cards"], t=10)
    except Exception as exc:
        return {"ok": False, "error": f"pactl card query failed: {exc}", "cards": []}
    if result.returncode != 0:
        return {
            "ok": False,
            "error": (result.stderr or result.stdout or "pactl card query failed").strip(),
            "cards": [],
        }
    try:
        payload = json.loads(result.stdout or "[]")
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": f"invalid pactl JSON: {exc}", "cards": []}

    cards = []
    for card in payload if isinstance(payload, list) else []:
        name = str(card.get("name", ""))
        if not name.startswith("bluez_card."):
            continue
        properties = card.get("properties") or {}
        raw_profiles = card.get("profiles") or {}
        profile_items = raw_profiles.items() if isinstance(raw_profiles, dict) else []
        profiles = []
        for profile_id, details in profile_items:
            values = details if isinstance(details, dict) else {}
            profiles.append({
                "id": str(profile_id),
                "description": str(values.get("description", profile_id)),
                "available": str(values.get("available", "unknown")),
                "sinks": int(values.get("sinks", 0) or 0),
                "sources": int(values.get("sources", 0) or 0),
                "priority": int(values.get("priority", 0) or 0),
            })
        cards.append({
            "name": name,
            "address": properties.get("api.bluez5.address"),
            "device_path": properties.get("api.bluez5.path"),
            "description": properties.get("device.description") or properties.get("device.alias") or name,
            "active_profile": card.get("active_profile") or "off",
            "profiles": profiles,
        })
    return {"ok": True, "cards": cards}

def audio_set_bluetooth_profile(card_name: str, profile_id: str) -> Dict[str, Any]:
    """Select one PipeWire Bluetooth card profile after capability validation."""
    if not card_name.startswith("bluez_card."):
        return {"ok": False, "code": "invalid_card", "error": "a BlueZ card name is required"}
    profile_state = bluetooth_audio_profiles()
    card = next((item for item in profile_state.get("cards", []) if item["name"] == card_name), None)
    if card is None:
        return {"ok": False, "code": "card_missing", "error": "Bluetooth audio card is not present"}
    profile = next((item for item in card["profiles"] if item["id"] == profile_id), None)
    if profile is None or profile.get("available") == "no":
        return {
            "ok": False,
            "code": "profile_unavailable",
            "error": "Bluetooth audio profile is not currently available",
        }
    result = _run(["pactl", "set-card-profile", card_name, profile_id], t=10)
    return {
        "ok": result.returncode == 0,
        "card": card_name,
        "profile": profile_id,
        "error": (result.stderr or result.stdout).strip() if result.returncode else None,
    }

__all__ = [
    "bluetooth_audio_profiles",
    "audio_set_bluetooth_profile"
]

