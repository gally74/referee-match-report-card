"""
Overlay a sport title and typed notes onto the original Referee Match Report Card PDF.
Keeps all original artwork, forms, and crop marks — only stamps text into blank areas.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

TEMPLATE = Path(__file__).with_name("Referee Match Report Card.pdf")

PAGE_W = 595.0
CARD_W = 297.5
CARD_H = 410.0
TOP_Y0 = 5.5
BOTTOM_Y0 = 426.5

INSET = 32.0
RIGHT_INSET = 40.0

COVER_TITLE_SLOTS = [
    (452.8, 324.0),
    (452.8, 745.0),
]

NOTAI_LEFT = 342.0
NOTAI_RIGHT = PAGE_W - 42.0

_LINE_HEIGHT_FACTOR = 1.2
_WALLET_FONT_MAX = 7.2
_WALLET_FONT_MIN = 5.5
_NOTAI_FONT_MAX = 7.2
_NOTAI_FONT_MIN = 5.5


def _wallet_rects() -> tuple[list[fitz.Rect], list[fitz.Rect]]:
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

NOTAI_RECTS = [
    fitz.Rect(NOTAI_LEFT, TOP_Y0 + 52, NOTAI_RIGHT, TOP_Y0 + CARD_H - INSET),
    fitz.Rect(NOTAI_LEFT, BOTTOM_Y0 + 52, NOTAI_RIGHT, BOTTOM_Y0 + CARD_H - INSET),
]


def _max_lines_for_rect(rect: fitz.Rect, fontsize: float) -> int:
    leading = fontsize * _LINE_HEIGHT_FACTOR
    if leading <= 0:
        return 0
    return max(0, int(rect.height / leading))


def _chars_per_line(width: float, fontsize: float) -> int:
    avg_char = fontsize * 0.5
    if avg_char <= 0:
        return 1
    return max(8, int(width / avg_char))


def count_wrapped_lines(text: str, width: float, fontsize: float) -> int:
    if not text.strip():
        return 0
    cpl = _chars_per_line(width, fontsize)
    total = 0
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw == "":
            total += 1
            continue
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
                while line_len > cpl:
                    lines += 1
                    line_len -= cpl
        total += lines
    return total


def _wallet_capacity(fontsize: float) -> int:
    above = WALLET_PANELS[0]
    below = WALLET_PANELS_BELOW[0]
    return _max_lines_for_rect(above, fontsize) + _max_lines_for_rect(below, fontsize)


def _wallet_used(text: str, fontsize: float) -> int:
    above = WALLET_PANELS[0]
    width = above.width
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if text else []
    if len(lines) <= 8:
        # Short notes only use the top box at this font
        return count_wrapped_lines(text, width, fontsize)
    mid = max(1, len(lines) // 2)
    return count_wrapped_lines("\n".join(lines[:mid]), width, fontsize) + count_wrapped_lines(
        "\n".join(lines[mid:]), width, fontsize
    )


def _fit_fontsize(
    text: str,
    used_fn,
    capacity_fn,
    font_max: float,
    font_min: float,
) -> tuple[float, dict]:
    """Pick the largest font that fits; return (fontsize, budget dict)."""
    if not text.strip():
        maximum = capacity_fn(font_max)
        return font_max, {"used": 0, "max": maximum, "remaining": maximum, "ok": True, "fontsize": font_max}

    fontsize = font_max
    while fontsize >= font_min - 0.05:
        used = used_fn(text, fontsize)
        maximum = capacity_fn(fontsize)
        if used <= maximum:
            return round(fontsize, 1), {
                "used": used,
                "max": maximum,
                "remaining": maximum - used,
                "ok": True,
                "fontsize": round(fontsize, 1),
            }
        fontsize -= 0.3

    used = used_fn(text, font_min)
    maximum = capacity_fn(font_min)
    return font_min, {
        "used": used,
        "max": maximum,
        "remaining": maximum - used,
        "ok": used <= maximum,
        "fontsize": font_min,
    }


def wallet_line_budget(text: str) -> dict:
    _, budget = _fit_fontsize(
        text, _wallet_used, _wallet_capacity, _WALLET_FONT_MAX, _WALLET_FONT_MIN
    )
    return budget


def notai_line_budget(text: str) -> dict:
    rect = NOTAI_RECTS[0]

    def used_fn(t: str, fs: float) -> int:
        return count_wrapped_lines(t, rect.width, fs)

    def cap_fn(fs: float) -> int:
        return _max_lines_for_rect(rect, fs)

    _, budget = _fit_fontsize(text, used_fn, cap_fn, _NOTAI_FONT_MAX, _NOTAI_FONT_MIN)
    return budget


def _insert_centered_title(page: fitz.Page, text: str, center_x: float, y: float, fontsize: float = 11) -> None:
    if not text.strip():
        return
    tw = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
    x = center_x - tw / 2
    page.insert_text((x, y), text, fontsize=fontsize, fontname="helv", color=(0, 0, 0))


def _insert_textbox(page: fitz.Page, rect: fitz.Rect, text: str, fontsize: float = 7.5) -> float:
    if not text.strip():
        return 0.0
    return page.insert_textbox(
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
    fontsize: float,
) -> None:
    if not notes.strip():
        return
    lines = notes.strip().splitlines()
    for i in panel_indices:
        above = WALLET_PANELS[i]
        below = WALLET_PANELS_BELOW[i]
        if len(lines) <= 8:
            _insert_textbox(page, above, notes, fontsize=fontsize)
        else:
            mid = max(1, len(lines) // 2)
            _insert_textbox(page, above, "\n".join(lines[:mid]), fontsize=fontsize)
            _insert_textbox(page, below, "\n".join(lines[mid:]), fontsize=fontsize)


def build_custom_card(
    title: str,
    wallet_notes_left: str = "",
    wallet_notes_right: str = "",
    notai_notes: str = "",
    template: Path | str = TEMPLATE,
    output: Path | str | None = None,
    apply_title_to_both_covers: bool = True,
    *,
    # Back-compat aliases (old top/bottom card split)
    wallet_notes_card1: str = "",
    wallet_notes_card2: str = "",
    wallet_notes: str = "",
) -> Path:
    """
    Stamp title + notes onto the original template.

    Same sport on both cut cards:
      - left flap notes -> top-left + bottom-left panels
      - right flap notes -> top-right + bottom-right panels
      - Nótaí -> both Nótaí columns
    """
    if not wallet_notes_left and not wallet_notes_right:
        if wallet_notes_card1 or wallet_notes_card2:
            wallet_notes_left = wallet_notes_card1
            wallet_notes_right = wallet_notes_card2
        elif wallet_notes:
            wallet_notes_left = wallet_notes
            wallet_notes_right = wallet_notes

    template = Path(template)
    if output is None:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in title.strip()) or "Custom"
        output = Path(__file__).with_name(f"Referee_Match_Report_Card_{safe}.pdf")
    else:
        output = Path(output)

    left_font, _ = _fit_fontsize(
        wallet_notes_left, _wallet_used, _wallet_capacity, _WALLET_FONT_MAX, _WALLET_FONT_MIN
    )
    right_font, _ = _fit_fontsize(
        wallet_notes_right, _wallet_used, _wallet_capacity, _WALLET_FONT_MAX, _WALLET_FONT_MIN
    )
    notai_font = notai_line_budget(notai_notes)["fontsize"]

    doc = fitz.open(template)

    cover_pages = [0]
    if apply_title_to_both_covers and len(doc) > 2:
        cover_pages.append(2)
    for page_index in cover_pages:
        page = doc[page_index]
        for cx, cy in COVER_TITLE_SLOTS:
            _insert_centered_title(page, title.strip(), cx, cy, fontsize=11)

    if len(doc) > 1:
        page = doc[1]
        # Left flaps on both cut cards; right flaps on both cut cards
        _stamp_wallet_notes(page, wallet_notes_left, (0, 2), left_font)
        _stamp_wallet_notes(page, wallet_notes_right, (1, 3), right_font)

    if notai_notes.strip() and len(doc) > 3:
        page = doc[3]
        for rect in NOTAI_RECTS:
            _insert_textbox(page, rect, notai_notes, fontsize=notai_font)

    doc.save(output)
    doc.close()
    return output


def render_pdf_preview_pages(
    pdf_path: Path | str,
    page_indices: tuple[int, ...] = (0, 1, 3),
    zoom: float = 1.35,
) -> list[tuple[str, bytes]]:
    """Return (label, png_bytes) previews for selected pages."""
    labels = {0: "Cover", 1: "Wallet flaps", 3: "Nótaí / team page"}
    doc = fitz.open(pdf_path)
    out: list[tuple[str, bytes]] = []
    matrix = fitz.Matrix(zoom, zoom)
    for i in page_indices:
        if i >= len(doc):
            continue
        pix = doc[i].get_pixmap(matrix=matrix, alpha=False)
        out.append((labels.get(i, f"Page {i + 1}"), pix.tobytes("png")))
    doc.close()
    return out


# --- Default Football notes (left / right flaps from your handwritten card) ---
DEFAULT_FOOTBALL_WALLET_LEFT = """Solo & go.
within 4m.
NOT Inside 20
NOT GO BACKWARDS = take a normal free
NOT challenged WITHIN 4m = 50m ADV

Captains Only Dissent.
50m ADVANCED TO offending player Goal up to 13m.
U18 = Black Card. 10 min Sin Bin
Team Official. 20m FREE on their 13m
YELLOW CARD"""

DEFAULT_FOOTBALL_WALLET_RIGHT = """4 v 3.
Free on the halfway while carrying, receiving or intercepting.
free on 20 NOT 13 for any other breach

Goalkeeper receive the ball
1 Both are inside Large Rect.
2 Opposition half.
1 = Ball was kicked in by an opponent & both GK & teammate were in large rect"""

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

# Back-compat names
DEFAULT_FOOTBALL_WALLET_CARD1 = DEFAULT_FOOTBALL_WALLET_LEFT
DEFAULT_FOOTBALL_WALLET_CARD2 = DEFAULT_FOOTBALL_WALLET_RIGHT
DEFAULT_FOOTBALL_WALLET = (
    DEFAULT_FOOTBALL_WALLET_LEFT.rstrip() + "\n\n" + DEFAULT_FOOTBALL_WALLET_RIGHT
)

DEFAULT_LGFA_WALLET_LEFT = """Match setup
Ball: Size 4 (younger) / Size 5 (adult)
Subs: check competition (slips)
Halves: typically 30 mins (bye-laws)

Penalty = 11m
Players outside 20 + Arc
3 occasions:
  goal-scoring opp
  foul in small rect
  aggressive in large"""

DEFAULT_LGFA_WALLET_RIGHT = """Kick-out from 20m
Players outside 20 + arc until kicked
Forward underhand = throw-in / as ruled

Technical fouls -> 13m free
Fail to retreat / time wasting -> advance
Distract free-taker -> advance
Captains only for dissent
Yellow / Red / sin bin as directed"""

DEFAULT_LGFA_NOTAI = """LGFA quick notes
Check bye-laws for grade
Subs / slips as competition requires
Sin bin / black card: competition directive
Team official misconduct -> free + card
Write match-specific reminders below:"""

DEFAULT_CAMOGIE_WALLET_LEFT = """Match setup
Sliotar: Size 4 (check grade)
15 / 12 / 11-a-side per competition
Subs: check competition (slips)
Halves: typically 30 mins (bye-laws)

Penalty: 11m
Players outside 20m + arc
Foul in small square / denying goal"""

DEFAULT_CAMOGIE_WALLET_RIGHT = """Puck-out from hand / small square as ruled
45m free for wide / over end line by defender
Sideline cut — from the ground
Technical foul in large rect -> free as ruled

Yellow / Red as per Camogie rules
Persistent / dangerous play -> escalate
Team official: free + caution / send-off
Captains for approach / dissent"""

DEFAULT_CAMOGIE_NOTAI = """Camogie quick notes
Confirm grade / team size before throw-in
Check competition sub rules
Write match-specific reminders below:"""

DEFAULT_HURLING_WALLET_LEFT = """Match setup
Sliotar: Size 5 (adult) / check underage
Subs: slips / temporary replacement
Halves: typically 30 / 35 mins

Penalty: 20m
Players outside 20m + arc
Foul in small square / cynical denial"""

DEFAULT_HURLING_WALLET_RIGHT = """Puck-out from 20m line (current rules)
Travel outside large / as directed
65m free for wide / over end line by defender
Sideline cut — from the ground
Advantage: play on when clear

Yellow / Red as per Hurling rules
Cynical foul / pull-down -> card / sin bin if directed
Team official misconduct -> free + card
Captains only for dissent"""

DEFAULT_HURLING_NOTAI = """Hurling quick notes
Confirm competition directives
Temporary replacement / blood sub rules
Write match-specific reminders below:"""


if __name__ == "__main__":
    out = build_custom_card(
        title="Football",
        wallet_notes_left=DEFAULT_FOOTBALL_WALLET_LEFT,
        wallet_notes_right=DEFAULT_FOOTBALL_WALLET_RIGHT,
        notai_notes=DEFAULT_FOOTBALL_NOTAI,
    )
    print(f"Wrote {out.resolve()}")
