"""
Referee Match Report Card customiser.

Keeps the original GAA PDF and lets you:
  1. Set a sport title under "Referee's Match Record Card" on the cover
  2. Type separate notes for the two wallet-flap cards (top / bottom after cutting)
  3. Type notes into the Nótaí columns on the team/notes page

Run:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from pdf_overlay import (
    DEFAULT_FOOTBALL_NOTAI,
    DEFAULT_FOOTBALL_WALLET_CARD1,
    DEFAULT_FOOTBALL_WALLET_CARD2,
    TEMPLATE,
    build_custom_card,
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

with st.sidebar:
    st.header("How it works")
    st.markdown(
        """
1. Enter a **title** (e.g. Football)  
2. Type notes for **Card 1** (top) and **Card 2** (bottom)  
3. Type **Nótaí** notes  
4. Click **Generate PDF**  
5. Download and print — cut along the crop marks  

After cutting the wallet page you get **two cards** (top row + bottom row).
"""
    )
    st.divider()
    preset = st.selectbox(
        "Start from preset notes",
        ["Blank", "Football (from your handwritten notes)"],
        index=1,
    )
    if st.button("Load preset into editors"):
        if "Football" in preset:
            st.session_state["wallet_notes_card1"] = DEFAULT_FOOTBALL_WALLET_CARD1
            st.session_state["wallet_notes_card2"] = DEFAULT_FOOTBALL_WALLET_CARD2
            st.session_state["notai_notes"] = DEFAULT_FOOTBALL_NOTAI
            st.session_state["card_title"] = "Football"
        else:
            st.session_state["wallet_notes_card1"] = ""
            st.session_state["wallet_notes_card2"] = ""
            st.session_state["notai_notes"] = ""
        st.rerun()

if "wallet_notes_card1" not in st.session_state:
    st.session_state["wallet_notes_card1"] = DEFAULT_FOOTBALL_WALLET_CARD1
if "wallet_notes_card2" not in st.session_state:
    st.session_state["wallet_notes_card2"] = DEFAULT_FOOTBALL_WALLET_CARD2
if "notai_notes" not in st.session_state:
    st.session_state["notai_notes"] = DEFAULT_FOOTBALL_NOTAI
if "card_title" not in st.session_state:
    st.session_state["card_title"] = "Football"

title = st.text_input(
    "Sport / card title",
    key="card_title",
    help='Printed under "Referee\'s Match Record Card" on the front cover.',
    placeholder="e.g. Football, LGFA, Camogie, Hurling",
)

st.subheader("Wallet flap notes")
st.caption("Blank “Please slide into flap of wallet” page — two cards after you cut.")

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
with w2:
    st.markdown("**Card 2 (bottom of page)**")
    wallet_notes_card2 = st.text_area(
        "Card 2 wallet notes",
        key="wallet_notes_card2",
        height=260,
        label_visibility="collapsed",
        placeholder="Notes for the bottom card…",
    )

st.subheader("Nótaí notes")
st.caption("Right-hand Nótaí column on the team / notes page (both card copies).")
notai_notes = st.text_area(
    "Nótaí notes",
    key="notai_notes",
    height=280,
    label_visibility="collapsed",
    placeholder="Type match / rule notes here…",
)

st.divider()

generate = st.button("Generate PDF", type="primary", use_container_width=True)

if generate:
    if not title.strip():
        st.warning("Please enter a title (e.g. Football).")
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
        st.info(f"Also saved next to the app:\n`{out.resolve()}`")

with st.expander("Tips"):
    st.markdown(
        """
- **Title** appears on both cover card copies.
- **Card 1** wallet notes go on the **top** row; **Card 2** on the **bottom** row.
- **Nótaí** text starts under the printed “Nótaí:” heading, clear of the cut marks.
- Switch the sidebar preset to **Blank** for LGFA / Camogie / Hurling and type your own.
"""
    )
