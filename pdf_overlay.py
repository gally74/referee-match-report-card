"""
Overlay a sport title and typed notes onto the original Referee Match Report Card PDF.
Keeps all original artwork, forms, and crop marks — only stamps text into blank areas.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

TEMPLATE = Path(__file__).with_name("Referee Match Report Card.pdf")

# Card geometry (matches original template)
PAGE_W = 595.0
CARD_W = 297.5
CARD_H = 410.0
TOP_Y0 = 5.5
BOTTOM_Y0 = 426.5

# Keep notes inside the cut lines (crop marks sit ~22.5pt in from panel edges)
INSET = 32.0
RIGHT_INSET = 40.0

# Cover title sits under "Record Card" on the right-hand panels of page 0
COVER_TITLE_SLOTS = [
    (452.8, 324.0),
    (452.8, 745.0),
]

# Printed "Nótaí:" label starts ~336.2 — keep body text under that, clear of both cuts
NOTAI_LEFT = 342.0
NOTAI_RIGHT = PAGE_W - 42.0  # ~553 — clear of right crop marks


def _wallet_rects() -> tuple[list[fitz.Rect], list[fitz.Rect]]:
    """Above / below the printed wallet cue, inset from cut lines (TL, TR, BL, BR)."""
    above = [
        fitz.Rect(INSET, TOP_Y0 + INSET, CARD_W - RIGHT_INSET, TOP_Y0 + 168),
        fitz.Rect(CARD_W + INSET, TOP_Y0 + INSET, PAGE_W - RIGHT_INSET, TOP_Y0 + 168),
        fitz.Rect(INSET, BOTTOM_Y0 + INSET, CARD_W - RIGHT_INSET, BOTTOM_Y0 + 168),
        fitz.Rect(CARD_W + INSET, BOTTOM_Y0 + INSET, PAGE_W - RIGHT_INSET, BOTTOM_Y0 + 168),
    ]
    below = [
        fitz.Rect(INSET, TOP_Y0 + 225, CARD_W - RIGHT_INSET, TOP_Y0 + CARD_H - INSET),
        fitz.Rect(CARD_W + INSET, TOP_Y0 + 225, PAGE_W - RIGHT_INSET, TOP_Y0 + CARD_H - INSET),
        fitz.Rect(INSET, BOTTOM_Y0 + 225, CARD_W - RIGHT_INSET, BOTTOM_Y0 + CARD_H - INSET),
        fitz.Rect(CARD_W + INSET, BOTTOM_Y0 + 225, PAGE_W - RIGHT_INSET, BOTTOM_Y0 + CARD_H - INSET),
    ]
    return above, below


WALLET_PANELS, WALLET_PANELS_BELOW = _wallet_rects()

# Page 3: Nótaí columns — start under "Nótaí:", inset from both cut edges
NOTAI_RECTS = [
    fitz.Rect(NOTAI_LEFT, TOP_Y0 + 52, NOTAI_RIGHT, TOP_Y0 + CARD_H - INSET),
    fitz.Rect(NOTAI_LEFT, BOTTOM_Y0 + 52, NOTAI_RIGHT, BOTTOM_Y0 + CARD_H - INSET),
]

# Line-budget estimates for the UI (must stay in sync with stamp boxes / fonts)
_LINE_HEIGHT_FACTOR = 1.2  # PyMuPDF textbox leading ≈ fontsize * 1.2


def _max_lines_for_rect(rect: fitz.Rect, fontsize: float) -> int:
    leading = fontsize * _LINE_HEIGHT_FACTOR
    if leading <= 0:
        return 0
    return max(0, int(rect.height / leading))


def _chars_per_line(width: float, fontsize: float) -> int:
    # Average Helvetica glyph width ≈ 0.5em for mixed case
    avg_char = fontsize * 0.5
    if avg_char <= 0:
        return 1
    return max(8, int(width / avg_char))


def count_wrapped_lines(text: str, width: float, fontsize: float) -> int:
    """Estimate how many visual lines text will use in a PDF textbox."""
    if not text.strip():
        return 0
    cpl = _chars_per_line(width, fontsize)
    total = 0
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw == "":
            total += 1
            continue
        # Word-aware wrap approximation
        words = raw.split(" ")
        line_len = 0
        lines = 1
        for i, word in enumerate(words):
            piece = word if i == 0 or line_len == 0 else f" {word}"
            if line_len + len(piece) <= cpl:
                line_len += len(piece)
            else:
                lines += 1
                line_len = len(word)
                # Hard-break very long tokens
                while line_len > cpl:
                    lines += 1
                    line_len -= cpl
        total += lines
    return total


def wallet_line_budget(text: str) -> dict:
    """Return used/max/remaining lines for one wallet card's notes."""
    above = WALLET_PANELS[0]
    below = WALLET_PANELS_BELOW[0]
    width = above.width
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if text else []
    # Matches _stamp_wallet_notes: short notes stay in the top box only
    if len(lines) <= 8:
        fontsize = 7.2
        used = count_wrapped_lines(text, width, fontsize)
        maximum = _max_lines_for_rect(above, fontsize)
    else:
        fontsize = 7.0
        mid = max(1, len(lines) // 2)
        top_text = "\n".join(lines[:mid])
        bot_text = "\n".join(lines[mid:])
        used = count_wrapped_lines(top_text, width, fontsize) + count_wrapped_lines(
            bot_text, width, fontsize
        )
        maximum = _max_lines_for_rect(above, fontsize) + _max_lines_for_rect(below, fontsize)
    remaining = maximum - used
    return {
        "used": used,
        "max": maximum,
        "remaining": remaining,
        "ok": remaining >= 0,
    }


def notai_line_budget(text: str) -> dict:
    """Return used/max/remaining lines for the Nótaí column."""
    rect = NOTAI_RECTS[0]
    fontsize = 7.2
    used = count_wrapped_lines(text, rect.width, fontsize)
    maximum = _max_lines_for_rect(rect, fontsize)
    remaining = maximum - used
    return {
        "used": used,
        "max": maximum,
        "remaining": remaining,
        "ok": remaining >= 0,
    }


def _insert_centered_title(page: fitz.Page, text: str, center_x: float, y: float, fontsize: float = 11) -> None:
    if not text.strip():
        return
    tw = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
    x = center_x - tw / 2
    page.insert_text(
        (x, y),
        text,
        fontsize=fontsize,
        fontname="helv",
        color=(0, 0, 0),
    )


def _insert_textbox(page: fitz.Page, rect: fitz.Rect, text: str, fontsize: float = 7.5) -> None:
    if not text.strip():
        return
    page.insert_textbox(
        rect,
        text.strip(),
        fontsize=fontsize,
        fontname="helv",
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_LEFT,
    )


def _stamp_wallet_notes(
    page: fitz.Page,
    notes: str,
    panel_indices: tuple[int, ...],
) -> None:
    """Stamp notes onto selected panels (0=TL, 1=TR, 2=BL, 3=BR)."""
    if not notes.strip():
        return
    lines = notes.strip().splitlines()
    for i in panel_indices:
        above = WALLET_PANELS[i]
        below = WALLET_PANELS_BELOW[i]
        if len(lines) <= 8:
            _insert_textbox(page, above, notes, fontsize=7.2)
        else:
            mid = max(1, len(lines) // 2)
            _insert_textbox(page, above, "\n".join(lines[:mid]), fontsize=7.0)
            _insert_textbox(page, below, "\n".join(lines[mid:]), fontsize=7.0)


def build_custom_card(
    title: str,
    wallet_notes_card1: str = "",
    wallet_notes_card2: str = "",
    notai_notes: str = "",
    template: Path | str = TEMPLATE,
    output: Path | str | None = None,
    apply_title_to_both_covers: bool = True,
    *,
    wallet_notes: str = "",  # backwards-compatible: used for both cards if set alone
) -> Path:
    """
    Copy the original PDF and stamp:
      - title under "Referee's Match Record Card" on the front cover(s)
      - wallet_notes_card1 onto the TOP card (left + right panels)
      - wallet_notes_card2 onto the BOTTOM card (left + right panels)
      - notai_notes into the Nótaí columns (page 3)
    """
    if wallet_notes and not wallet_notes_card1 and not wallet_notes_card2:
        wallet_notes_card1 = wallet_notes
        wallet_notes_card2 = wallet_notes

    template = Path(template)
    if output is None:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in title.strip()) or "Custom"
        output = Path(__file__).with_name(f"Referee_Match_Report_Card_{safe}.pdf")
    else:
        output = Path(output)

    doc = fitz.open(template)

    # --- Page 0 (and optionally page 2): cover title ---
    cover_pages = [0]
    if apply_title_to_both_covers and len(doc) > 2:
        cover_pages.append(2)

    for page_index in cover_pages:
        page = doc[page_index]
        for cx, cy in COVER_TITLE_SLOTS:
            _insert_centered_title(page, title.strip(), cx, cy, fontsize=11)

    # --- Page 1: blank wallet panels (two cards after cutting) ---
    if len(doc) > 1:
        page = doc[1]
        _stamp_wallet_notes(page, wallet_notes_card1, (0, 1))  # top card
        _stamp_wallet_notes(page, wallet_notes_card2, (2, 3))  # bottom card

    # --- Page 3: Nótaí columns ---
    if notai_notes.strip() and len(doc) > 3:
        page = doc[3]
        for rect in NOTAI_RECTS:
            _insert_textbox(page, rect, notai_notes, fontsize=7.2)

    doc.save(output)
    doc.close()
    return output


# Defaults split across the two cut cards (from your handwritten notes)
DEFAULT_FOOTBALL_WALLET_CARD1 = """Solo & go.
within 4m.
NOT Inside 20
NOT GO BACKWARDS = take a normal free
NOT challenged WITHIN 4m = 50m ADV

Captains Only Dissent.
50m ADVANCED TO offending player Goal up to 13m.
U18 = Black Card. 10 min Sin Bin
Team Official. 20m FREE on their 13m
YELLOW CARD"""

DEFAULT_FOOTBALL_WALLET_CARD2 = """4 v 3.
Free on the halfway while carrying, receiving or intercepting.
free on 20 NOT 13 for any other breach

Goalkeeper receive the ball
1 Both are inside Large Rect.
2 Opposition half.
1 = Ball was kicked in by an opponent & both GK & teammate were in large rect"""

# Kept for older imports / single-box fallback
DEFAULT_FOOTBALL_WALLET = (
    DEFAULT_FOOTBALL_WALLET_CARD1.rstrip() + "\n\n" + DEFAULT_FOOTBALL_WALLET_CARD2
)

DEFAULT_FOOTBALL_NOTAI = """Size 5 Fe16
Subs - 5 - Slips

Penalty = 11m.
Players outside 20 + Arc
3 occasions =
  1 Goal scoring opp
  2 Any foul in small inside rect
  3 Aggressive in large

Technical 13m fouls used
Large Rect -> Technical foul in large

KO - 20M  FORWARD = Throw in
- 13m players. = 13m adv opponent or free
- 40M Travel Outside = free. Players outside = free.
4m rule KO mark = free.
opponent fails to retreat = 50m. ADV

50m ADV = Time wasting.
Not handing ball back
Kicking or throwing.
failing to retreat
Distract free taker.
Can Solo & Go for free up to 13m
can drive outside 40"""


if __name__ == "__main__":
    out = build_custom_card(
        title="Football",
        wallet_notes_card1=DEFAULT_FOOTBALL_WALLET_CARD1,
        wallet_notes_card2=DEFAULT_FOOTBALL_WALLET_CARD2,
        notai_notes=DEFAULT_FOOTBALL_NOTAI,
    )
    print(f"Wrote {out.resolve()}")
