"""Serialize / restore referee card notes for presets, autosave, and download."""

from __future__ import annotations

import json
from typing import Any

from pdf_overlay import (
    DEFAULT_CAMOGIE_NOTAI,
    DEFAULT_CAMOGIE_WALLET_LEFT,
    DEFAULT_CAMOGIE_WALLET_RIGHT,
    DEFAULT_FOOTBALL_NOTAI,
    DEFAULT_FOOTBALL_WALLET_LEFT,
    DEFAULT_FOOTBALL_WALLET_RIGHT,
    DEFAULT_HURLING_NOTAI,
    DEFAULT_HURLING_WALLET_LEFT,
    DEFAULT_HURLING_WALLET_RIGHT,
    DEFAULT_LGFA_NOTAI,
    DEFAULT_LGFA_WALLET_LEFT,
    DEFAULT_LGFA_WALLET_RIGHT,
)

STORAGE_KEY = "referee_match_report_card_notes_v2"
NOTES_VERSION = 2

BUILTIN_PRESETS: dict[str, dict[str, str]] = {
    "Blank": {
        "title": "",
        "wallet_notes_left": "",
        "wallet_notes_right": "",
        "notai_notes": "",
    },
    "Football": {
        "title": "Football",
        "wallet_notes_left": DEFAULT_FOOTBALL_WALLET_LEFT,
        "wallet_notes_right": DEFAULT_FOOTBALL_WALLET_RIGHT,
        "notai_notes": DEFAULT_FOOTBALL_NOTAI,
    },
    "LGFA": {
        "title": "LGFA",
        "wallet_notes_left": DEFAULT_LGFA_WALLET_LEFT,
        "wallet_notes_right": DEFAULT_LGFA_WALLET_RIGHT,
        "notai_notes": DEFAULT_LGFA_NOTAI,
    },
    "Camogie": {
        "title": "Camogie",
        "wallet_notes_left": DEFAULT_CAMOGIE_WALLET_LEFT,
        "wallet_notes_right": DEFAULT_CAMOGIE_WALLET_RIGHT,
        "notai_notes": DEFAULT_CAMOGIE_NOTAI,
    },
    "Hurling": {
        "title": "Hurling",
        "wallet_notes_left": DEFAULT_HURLING_WALLET_LEFT,
        "wallet_notes_right": DEFAULT_HURLING_WALLET_RIGHT,
        "notai_notes": DEFAULT_HURLING_NOTAI,
    },
}


def _normalize_notes(data: dict[str, Any]) -> dict[str, str]:
    """Accept v2 left/right keys or older card1/card2 keys."""
    left = data.get("wallet_notes_left")
    right = data.get("wallet_notes_right")
    if left is None and right is None:
        left = data.get("wallet_notes_card1", "")
        right = data.get("wallet_notes_card2", "")
    return {
        "title": str(data.get("title", "") or ""),
        "wallet_notes_left": str(left or ""),
        "wallet_notes_right": str(right or ""),
        "notai_notes": str(data.get("notai_notes", "") or ""),
    }


def current_notes_from_session(session_state: Any) -> dict[str, str]:
    return {
        "title": session_state.get("card_title", "") or "",
        "wallet_notes_left": session_state.get("wallet_notes_left", "") or "",
        "wallet_notes_right": session_state.get("wallet_notes_right", "") or "",
        "notai_notes": session_state.get("notai_notes", "") or "",
    }


def apply_notes_to_session(session_state: Any, notes: dict[str, Any]) -> None:
    normalized = _normalize_notes(notes)
    session_state["card_title"] = normalized["title"]
    session_state["wallet_notes_left"] = normalized["wallet_notes_left"]
    session_state["wallet_notes_right"] = normalized["wallet_notes_right"]
    session_state["notai_notes"] = normalized["notai_notes"]


def bundle_to_json(notes: dict[str, str], preset_name: str = "") -> str:
    payload = {
        "version": NOTES_VERSION,
        "preset_name": preset_name,
        **_normalize_notes(notes),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def notes_from_json(raw: str | bytes) -> dict[str, str]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Notes file must be a JSON object.")
    return _normalize_notes(data)


def empty_browser_store() -> dict[str, Any]:
    return {"version": NOTES_VERSION, "presets": {}, "last_used": None, "autosave": None}


def parse_browser_store(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return empty_browser_store()
    if isinstance(raw, dict):
        data = raw
    else:
        data = json.loads(raw)
    if not isinstance(data, dict):
        return empty_browser_store()

    presets = data.get("presets") or {}
    if not isinstance(presets, dict):
        presets = {}
    cleaned = {}
    for name, notes in presets.items():
        if not name or not isinstance(notes, dict):
            continue
        cleaned[str(name)] = _normalize_notes(notes)

    autosave = data.get("autosave")
    if isinstance(autosave, dict):
        autosave = _normalize_notes(autosave)
    else:
        autosave = None

    return {
        "version": NOTES_VERSION,
        "presets": cleaned,
        "last_used": data.get("last_used"),
        "autosave": autosave,
    }
