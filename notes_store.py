"""Serialize / restore referee card notes for presets, download, and browser storage."""

from __future__ import annotations

import json
from typing import Any

from pdf_overlay import (
    DEFAULT_FOOTBALL_NOTAI,
    DEFAULT_FOOTBALL_WALLET_CARD1,
    DEFAULT_FOOTBALL_WALLET_CARD2,
)

STORAGE_KEY = "referee_match_report_card_notes_v1"
NOTES_VERSION = 1

BUILTIN_PRESETS: dict[str, dict[str, str]] = {
    "Blank": {
        "title": "",
        "wallet_notes_card1": "",
        "wallet_notes_card2": "",
        "notai_notes": "",
    },
    "Football (from your handwritten notes)": {
        "title": "Football",
        "wallet_notes_card1": DEFAULT_FOOTBALL_WALLET_CARD1,
        "wallet_notes_card2": DEFAULT_FOOTBALL_WALLET_CARD2,
        "notai_notes": DEFAULT_FOOTBALL_NOTAI,
    },
}


def current_notes_from_session(session_state: Any) -> dict[str, str]:
    return {
        "title": session_state.get("card_title", "") or "",
        "wallet_notes_card1": session_state.get("wallet_notes_card1", "") or "",
        "wallet_notes_card2": session_state.get("wallet_notes_card2", "") or "",
        "notai_notes": session_state.get("notai_notes", "") or "",
    }


def apply_notes_to_session(session_state: Any, notes: dict[str, Any]) -> None:
    session_state["card_title"] = str(notes.get("title", "") or "")
    session_state["wallet_notes_card1"] = str(notes.get("wallet_notes_card1", "") or "")
    session_state["wallet_notes_card2"] = str(notes.get("wallet_notes_card2", "") or "")
    session_state["notai_notes"] = str(notes.get("notai_notes", "") or "")


def bundle_to_json(notes: dict[str, str], preset_name: str = "") -> str:
    payload = {
        "version": NOTES_VERSION,
        "preset_name": preset_name,
        "title": notes.get("title", ""),
        "wallet_notes_card1": notes.get("wallet_notes_card1", ""),
        "wallet_notes_card2": notes.get("wallet_notes_card2", ""),
        "notai_notes": notes.get("notai_notes", ""),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def notes_from_json(raw: str | bytes) -> dict[str, str]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Notes file must be a JSON object.")
    return {
        "title": str(data.get("title", "") or ""),
        "wallet_notes_card1": str(data.get("wallet_notes_card1", "") or ""),
        "wallet_notes_card2": str(data.get("wallet_notes_card2", "") or ""),
        "notai_notes": str(data.get("notai_notes", "") or ""),
    }


def empty_browser_store() -> dict[str, Any]:
    return {"version": NOTES_VERSION, "presets": {}, "last_used": None}


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
        cleaned[str(name)] = {
            "title": str(notes.get("title", "") or ""),
            "wallet_notes_card1": str(notes.get("wallet_notes_card1", "") or ""),
            "wallet_notes_card2": str(notes.get("wallet_notes_card2", "") or ""),
            "notai_notes": str(notes.get("notai_notes", "") or ""),
        }
    return {
        "version": NOTES_VERSION,
        "presets": cleaned,
        "last_used": data.get("last_used"),
    }
