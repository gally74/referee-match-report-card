"""
Referee Match Report Card customiser.

Keeps the original GAA PDF and lets you:
  1. Set a sport title under "Referee's Match Record Card" on the cover
  2. Type different notes for left / right wallet flaps (same sport, two cut cards)
  3. Type Nótaí notes
  4. Autosave in this browser + optional named presets / JSON file
  5. Preview and download the PDF

Run:
    streamlit run app.py
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

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
from pdf_overlay import (
    TEMPLATE,
    build_custom_card,
    notai_line_budget,
    render_pdf_preview_pages,
    wallet_line_budget,
)

st.set_page_config(
    page_title="Referee Card Customiser",
    page_icon="📒",
    layout="centered",
)


def _show_line_budget(label: str, budget: dict) -> None:
    used = budget["used"]
    maximum = budget["max"]
    remaining = budget["remaining"]
    fs = budget.get("fontsize", 7.2)
    suffix = f" · font {fs}pt" if fs < 7.2 else ""
    if remaining >= 4:
        st.caption(f"{label}: **{remaining}** lines left ({used}/{maximum} used){suffix}")
    elif remaining >= 0:
        st.warning(
            f"{label}: only **{remaining}** lines left ({used}/{maximum} used){suffix}"
        )
    else:
        st.error(
            f"{label}: **{-remaining}** lines over even at smallest font "
            f"({used}/{maximum} used){suffix}"
        )


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
        return parse_browser_store(local_storage.getItem(STORAGE_KEY))
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


def _autosave_notes(local_storage, store: dict) -> None:
    notes = current_notes_from_session(st.session_state)
    store["autosave"] = notes
    store["last_used"] = "autosave"
    _write_browser_store(local_storage, store)


st.title("Referee Match Report Card")
st.caption(
    "Keeps your original PDF. Same sport on both cut cards — different notes on "
    "left and right wallet flaps. Notes autosave in this browser."
)

if not TEMPLATE.exists():
    st.error(f"Original template not found: {TEMPLATE.name}")
    st.stop()

local_storage = _get_local_storage()
browser_store = _read_browser_store(local_storage)

# Restore autosaved notes once per browser session (or fall back to Football)
if "wallet_notes_left" not in st.session_state:
    if browser_store.get("autosave"):
        apply_notes_to_session(st.session_state, browser_store["autosave"])
        st.session_state["_show_autosave_banner"] = True
    else:
        apply_notes_to_session(st.session_state, BUILTIN_PRESETS["Football"])

if st.session_state.pop("_show_autosave_banner", False):
    st.success("Restored your last notes from this browser.")

saved_preset_names = sorted(
    n for n in browser_store.get("presets", {}) if n != "Last session"
)

with st.sidebar:
    st.header("How it works")
    st.markdown(
        """
1. Pick a **preset** (Football / LGFA / Camogie / Hurling)  
2. Edit **left** and **right** wallet notes + **Nótaí**  
3. Notes **autosave** in this browser  
4. **Generate PDF** → preview → download  
5. Cut along the marks — you get **two identical sport cards**
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
        st.session_state["_flash"] = f"Loaded **{builtin_name}** preset."
        st.rerun()

    st.divider()
    st.subheader("Your notes")
    st.caption("Autosaves whenever you edit. Optional named copies below.")

    save_name = st.text_input(
        "Save current as named preset",
        value=st.session_state.get("card_title") or "My notes",
        placeholder="e.g. Football U16",
    )
    if st.button("Save named preset", use_container_width=True):
        name = (save_name or "").strip()
        if not name:
            st.warning("Enter a name.")
        else:
            notes = current_notes_from_session(st.session_state)
            browser_store.setdefault("presets", {})[name] = notes
            browser_store["autosave"] = notes
            browser_store["last_used"] = name
            ok = _write_browser_store(local_storage, browser_store)
            st.session_state["_flash"] = (
                f"Saved **{name}**." if ok else f"Could not save **{name}** in browser."
            )
            st.rerun()

    if st.session_state.get("_flash"):
        st.success(st.session_state.pop("_flash"))

    if saved_preset_names:
        chosen_saved = st.selectbox("Load named preset", saved_preset_names)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Load", use_container_width=True):
                apply_notes_to_session(
                    st.session_state, browser_store["presets"][chosen_saved]
                )
                browser_store["autosave"] = browser_store["presets"][chosen_saved]
                browser_store["last_used"] = chosen_saved
                _write_browser_store(local_storage, browser_store)
                st.rerun()
        with c2:
            if st.button("Delete", use_container_width=True):
                browser_store["presets"].pop(chosen_saved, None)
                _write_browser_store(local_storage, browser_store)
                st.rerun()

    st.divider()
    st.subheader("Notes file backup")
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
            browser_store["autosave"] = loaded
            name = (loaded.get("title") or uploaded.name.replace(".json", "")).strip()
            if name:
                browser_store.setdefault("presets", {})[name] = loaded
            _write_browser_store(local_storage, browser_store)
            st.session_state["_flash"] = "Notes file loaded."
            st.rerun()
        except Exception as exc:
            st.error(f"Could not read notes file: {exc}")

title = st.text_input(
    "Sport / card title",
    key="card_title",
    help='Printed under "Referee\'s Match Record Card" on both cover copies.',
    placeholder="e.g. Football, LGFA, Camogie, Hurling",
)

st.subheader("Wallet flap notes")
st.caption(
    "Left and right flaps of the wallet card. The same pair is printed on **both** "
    "cut cards (top and bottom of the page). Click outside a box to refresh line counts."
)

w1, w2 = st.columns(2)
with w1:
    st.markdown("**Left flap**")
    wallet_notes_left = st.text_area(
        "Left wallet notes",
        key="wallet_notes_left",
        height=280,
        label_visibility="collapsed",
        placeholder="Notes for the left flap…",
    )
    _show_line_budget("Left", wallet_line_budget(wallet_notes_left))
with w2:
    st.markdown("**Right flap**")
    wallet_notes_right = st.text_area(
        "Right wallet notes",
        key="wallet_notes_right",
        height=280,
        label_visibility="collapsed",
        placeholder="Notes for the right flap…",
    )
    _show_line_budget("Right", wallet_line_budget(wallet_notes_right))

st.subheader("Nótaí notes")
st.caption("Filled on both card copies of the team / notes page.")
notai_notes = st.text_area(
    "Nótaí notes",
    key="notai_notes",
    height=260,
    label_visibility="collapsed",
    placeholder="Type match / rule notes here…",
)
_show_line_budget("Nótaí", notai_line_budget(notai_notes))

# Autosave after edits (this browser)
_autosave_notes(local_storage, browser_store)

st.divider()
generate = st.button("Generate PDF", type="primary", use_container_width=True)

if generate:
    budgets = [
        ("Left flap", wallet_line_budget(wallet_notes_left)),
        ("Right flap", wallet_line_budget(wallet_notes_right)),
        ("Nótaí", notai_line_budget(notai_notes)),
    ]
    over = [name for name, b in budgets if not b["ok"]]
    if not title.strip():
        st.warning("Please enter a title (e.g. Football).")
    elif over:
        st.error(
            "Still too much text even after shrinking the font: " + ", ".join(over)
        )
    else:
        with st.spinner("Building your card…"):
            with tempfile.TemporaryDirectory() as tmp:
                out_path = Path(tmp) / f"Referee_Match_Report_Card_{title.strip()}.pdf"
                build_custom_card(
                    title=title.strip(),
                    wallet_notes_left=wallet_notes_left,
                    wallet_notes_right=wallet_notes_right,
                    notai_notes=notai_notes,
                    output=out_path,
                )
                pdf_bytes = out_path.read_bytes()
                previews = render_pdf_preview_pages(out_path)
        st.session_state["last_pdf_bytes"] = pdf_bytes
        st.session_state["last_pdf_name"] = (
            f"Referee_Match_Report_Card_{title.strip().replace(' ', '_')}.pdf"
        )
        st.session_state["last_pdf_previews"] = previews
        st.success("PDF ready — preview below, then download.")

if st.session_state.get("last_pdf_bytes"):
    st.download_button(
        label="Download customised PDF",
        data=st.session_state["last_pdf_bytes"],
        file_name=st.session_state.get("last_pdf_name", "Referee_Match_Report_Card.pdf"),
        mime="application/pdf",
        use_container_width=True,
    )
    st.subheader("Preview")
    tabs = st.tabs([label for label, _ in st.session_state["last_pdf_previews"]])
    for tab, (label, png) in zip(tabs, st.session_state["last_pdf_previews"]):
        with tab:
            st.image(png, caption=label, use_container_width=True)

with st.expander("Tips"):
    st.markdown(
        """
- Notes **autosave** in this browser — reopen the app later and they come back.
- On another device, use **Download notes file** / **Upload notes file**.
- **Left / right** = the two flaps of one wallet card; top and bottom page rows are two copies.
- Font shrinks slightly if you’re near the limit; Generate blocks only if it still won’t fit.
- Built-in presets: Football, LGFA, Camogie, Hurling (+ Blank).
"""
    )
