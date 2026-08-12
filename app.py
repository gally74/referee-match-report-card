"""
Referee Match Report Card customiser.

Keeps the original GAA PDF and lets you:
  1. Set a sport title under "Referee's Match Record Card" on the cover
  2. Type separate notes for the two wallet-flap cards (top / bottom after cutting)
  3. Type notes into the Nótaí columns on the team/notes page
  4. Save / reload notes (browser + downloadable JSON file)

Run:
    streamlit run app.py
"""

from __future__ import annotations

import json
import re

import streamlit as st

from notes_store import (
    BUILTIN_PRESETS,
    STORAGE_KEY,
    apply_notes_to_session,
    bundle_to_json,
    current_notes_from_session,
    empty_browser_store,
    notes_from_json,
    parse_browser_store,
)
from pdf_overlay import TEMPLATE, build_custom_card, notai_line_budget, wallet_line_budget


def _show_line_budget(label: str, budget: dict) -> None:
    used = budget["used"]
    maximum = budget["max"]
    remaining = budget["remaining"]
    if remaining >= 4:
        st.caption(f"{label}: **{remaining}** lines left ({used}/{maximum} used)")
    elif remaining >= 0:
        st.warning(f"{label}: only **{remaining}** lines left ({used}/{maximum} used)")
    else:
        st.error(
            f"{label}: **{-remaining}** lines over — text will be cut off on the PDF "
            f"({used}/{maximum} used)"
        )

st.set_page_config(
    page_title="Referee Card Customiser",
    page_icon="📒",
    layout="centered",
)

st.title("Referee Match Report Card")
st.caption(
    "Keeps your original PDF. Adds a sport title on the cover and your typed notes "
    "onto the blank wallet flaps and Nótaí pages."
)

if not TEMPLATE.exists():
    st.error(f"Original template not found: {TEMPLATE.name}")
    st.stop()


def _get_local_storage():
    try:
        from streamlit_local_storage import LocalStorage

        return LocalStorage()
    except Exception:
        return None


def _read_browser_store(local_storage) -> dict:
    if local_storage is None:
        return empty_browser_store()
    try:
        raw = local_storage.getItem(STORAGE_KEY)
        return parse_browser_store(raw)
    except Exception:
        return empty_browser_store()


def _write_browser_store(local_storage, store: dict) -> bool:
    if local_storage is None:
        return False
    try:
        local_storage.setItem(STORAGE_KEY, json.dumps(store, ensure_ascii=False))
        return True
    except Exception:
        return False


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", name.strip()) or "notes"
    return f"referee_notes_{cleaned}.json"


# Init default editor values once per session
if "wallet_notes_card1" not in st.session_state:
    football = BUILTIN_PRESETS["Football (from your handwritten notes)"]
    st.session_state["card_title"] = football["title"]
    st.session_state["wallet_notes_card1"] = football["wallet_notes_card1"]
    st.session_state["wallet_notes_card2"] = football["wallet_notes_card2"]
    st.session_state["notai_notes"] = football["notai_notes"]

local_storage = _get_local_storage()
browser_store = _read_browser_store(local_storage)
saved_preset_names = sorted(browser_store.get("presets", {}).keys())

# Offer restore of last-used browser notes once per browser session
if (
    local_storage is not None
    and not st.session_state.get("_restored_browser_notes")
    and browser_store.get("last_used")
    and browser_store["last_used"] in browser_store.get("presets", {})
):
    st.info(
        f"Saved notes found in this browser: **{browser_store['last_used']}**. "
        "Load them from the sidebar under **Your saved presets**."
    )
    st.session_state["_restored_browser_notes"] = True

with st.sidebar:
    st.header("How it works")
    st.markdown(
        """
1. Enter a **title** (e.g. Football)  
2. Type notes for **Card 1** (top) and **Card 2** (bottom)  
3. Type **Nótaí** notes  
4. **Save** your notes (sidebar) so they’re there next time  
5. Click **Generate PDF** and download  

After cutting the wallet page you get **two cards** (top row + bottom row).
"""
    )
    st.divider()

    st.subheader("Built-in presets")
    builtin_name = st.selectbox(
        "Start from preset notes",
        list(BUILTIN_PRESETS.keys()),
        index=1,
        label_visibility="collapsed",
    )
    if st.button("Load built-in preset", use_container_width=True):
        apply_notes_to_session(st.session_state, BUILTIN_PRESETS[builtin_name])
        st.rerun()

    st.divider()
    st.subheader("Your saved presets")
    st.caption("Stored in this browser, and/or as a downloadable file.")

    save_name = st.text_input(
        "Name for current notes",
        value=st.session_state.get("card_title") or "My notes",
        placeholder="e.g. Football U16, LGFA",
    )
    if st.button("Save notes", type="primary", use_container_width=True):
        name = (save_name or "").strip()
        if not name:
            st.warning("Enter a name for these notes.")
        else:
            notes = current_notes_from_session(st.session_state)
            browser_store.setdefault("presets", {})[name] = notes
            browser_store["last_used"] = name
            ok = _write_browser_store(local_storage, browser_store)
            if ok:
                st.session_state["_flash"] = f"Saved **{name}** in this browser."
            else:
                st.session_state["_flash"] = (
                    f"Named **{name}** — browser save unavailable. "
                    "Use **Download notes file** below to keep a copy."
                )
            st.rerun()

    if st.session_state.get("_flash"):
        st.success(st.session_state.pop("_flash"))

    if saved_preset_names:
        chosen_saved = st.selectbox("Load saved preset", saved_preset_names)
        if st.button("Load saved preset", use_container_width=True):
            apply_notes_to_session(
                st.session_state, browser_store["presets"][chosen_saved]
            )
            browser_store["last_used"] = chosen_saved
            _write_browser_store(local_storage, browser_store)
            st.rerun()
        if st.button("Delete saved preset", use_container_width=True):
            browser_store["presets"].pop(chosen_saved, None)
            if browser_store.get("last_used") == chosen_saved:
                browser_store["last_used"] = None
            _write_browser_store(local_storage, browser_store)
            st.rerun()
    else:
        st.caption("No browser-saved presets yet.")

    st.divider()
    st.subheader("Notes file")
    st.caption("Best for work laptop / backup — download here, upload there.")

    notes_now = current_notes_from_session(st.session_state)
    st.download_button(
        "Download notes file",
        data=bundle_to_json(notes_now, save_name.strip() if save_name else ""),
        file_name=_safe_filename(save_name or notes_now.get("title") or "notes"),
        mime="application/json",
        use_container_width=True,
    )

    uploaded = st.file_uploader("Upload notes file", type=["json"])
    if uploaded is not None and st.button("Load uploaded file", use_container_width=True):
        try:
            loaded = notes_from_json(uploaded.read())
            apply_notes_to_session(st.session_state, loaded)
            # Also keep a browser copy under the file name / title
            name = (loaded.get("title") or uploaded.name.replace(".json", "")).strip()
            if name:
                browser_store.setdefault("presets", {})[name] = loaded
                browser_store["last_used"] = name
                _write_browser_store(local_storage, browser_store)
            st.success("Notes loaded.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not read notes file: {exc}")

title = st.text_input(
    "Sport / card title",
    key="card_title",
    help='Printed under "Referee\'s Match Record Card" on the front cover.',
    placeholder="e.g. Football, LGFA, Camogie, Hurling",
)

st.subheader("Wallet flap notes")
st.caption(
    "Blank “Please slide into flap of wallet” page — two cards after you cut. "
    "Click outside a box (or Ctrl+Enter) to refresh the line count."
)

w1, w2 = st.columns(2)
with w1:
    st.markdown("**Card 1 (top of page)**")
    wallet_notes_card1 = st.text_area(
        "Card 1 wallet notes",
        key="wallet_notes_card1",
        height=260,
        label_visibility="collapsed",
        placeholder="Notes for the top card…",
    )
    _show_line_budget("Card 1", wallet_line_budget(wallet_notes_card1))
with w2:
    st.markdown("**Card 2 (bottom of page)**")
    wallet_notes_card2 = st.text_area(
        "Card 2 wallet notes",
        key="wallet_notes_card2",
        height=260,
        label_visibility="collapsed",
        placeholder="Notes for the bottom card…",
    )
    _show_line_budget("Card 2", wallet_line_budget(wallet_notes_card2))

st.subheader("Nótaí notes")
st.caption("Right-hand Nótaí column on the team / notes page (both card copies).")
notai_notes = st.text_area(
    "Nótaí notes",
    key="notai_notes",
    height=280,
    label_visibility="collapsed",
    placeholder="Type match / rule notes here…",
)
_show_line_budget("Nótaí", notai_line_budget(notai_notes))

st.divider()

generate = st.button("Generate PDF", type="primary", use_container_width=True)

if generate:
    budgets = [
        ("Card 1", wallet_line_budget(wallet_notes_card1)),
        ("Card 2", wallet_line_budget(wallet_notes_card2)),
        ("Nótaí", notai_line_budget(notai_notes)),
    ]
    over = [name for name, b in budgets if not b["ok"]]
    if not title.strip():
        st.warning("Please enter a title (e.g. Football).")
    elif over:
        st.error(
            "Shorten your notes first — these won’t fully fit on the PDF: "
            + ", ".join(over)
        )
    else:
        with st.spinner("Stamping your title and notes onto the original card…"):
            out = build_custom_card(
                title=title.strip(),
                wallet_notes_card1=wallet_notes_card1,
                wallet_notes_card2=wallet_notes_card2,
                notai_notes=notai_notes,
            )
        st.success(f"Created **{out.name}**")
        data = out.read_bytes()
        st.download_button(
            label="Download customised PDF",
            data=data,
            file_name=out.name,
            mime="application/pdf",
            use_container_width=True,
        )

with st.expander("Tips"):
    st.markdown(
        """
- **Save notes** in the sidebar stores them in **this browser**.
- **Download notes file** to move notes to your work laptop (upload there).
- **Card 1** = top wallet card; **Card 2** = bottom wallet card after cutting.
- Built-in **Football** preset is always available even if you clear saved notes.
- Line counters under each box show how much PDF space is left; Generate is blocked if you go over.
"""
    )
