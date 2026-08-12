#!/usr/bin/env python3
"""
Generate wallet-sized referee rule cards for GAA Football, LGFA, Camogie, and Hurling.

Layout matches the original "Referee Match Report Card.pdf":
  - Page size 595 x 842 pt (A4)
  - 2x2 grid of cards, each 297.5 x 410 pt
  - ~11 pt gap between rows; crop marks at panel corners
  - Content inset aligned to the original wallet inserts

Handwritten notes (IMG_6039, IMG_6040, IMG_6042) are transcribed into
HANDWRITTEN_NOTES below. GAA Football uses those notes across two panels
(same fold style as your wallet card).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Prefer a Unicode TTF so Irish headings (Nótaí) render correctly.
FONT_REG = "CardSans"
FONT_BOLD = "CardSans-Bold"
_FONT_CANDIDATES = [
    (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")),
    (Path(r"C:\Windows\Fonts\calibri.ttf"), Path(r"C:\Windows\Fonts\calibrib.ttf")),
    (Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\segoeuib.ttf")),
]


def _register_fonts() -> tuple[str, str]:
    for regular, bold in _FONT_CANDIDATES:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont(FONT_REG, str(regular)))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold)))
            return FONT_REG, FONT_BOLD
    return "Helvetica", "Helvetica-Bold"


BODY_FONT, BOLD_FONT = _register_fonts()

# ---------------------------------------------------------------------------
# Page / card geometry (from original PDF mediabox + panel rects)
# ---------------------------------------------------------------------------
PAGE_W = 595.0
PAGE_H = 842.0
CARD_W = 297.5
CARD_H = 410.0
ROW_GAP = 11.0  # 426.5 - 415.5
TOP_Y = 5.5
BOTTOM_Y = TOP_Y + CARD_H + ROW_GAP  # 426.5

MARGIN = 14.0
INNER_TOP = 12.0

INK = HexColor("#1a1a1a")
RULE = HexColor("#333333")
MUTED = HexColor("#555555")
HEADER_BG = HexColor("#1a1a1a")
LINE = HexColor("#222222")
SECTION = HexColor("#111111")
GUIDE = HexColor("#bbbbbb")
RULED = HexColor("#888888")

OUTPUT = Path(__file__).with_name("Referee_Rule_Cards.pdf")

# ---------------------------------------------------------------------------
# Exact transcription of handwritten notes (source photos)
# ---------------------------------------------------------------------------
HANDWRITTEN_NOTES = {
    "source_images": ["IMG_6039.JPG", "IMG_6040.JPG", "IMG_6042.jpg"],
    # IMG_6039 — left wallet panel
    "match_setup": {
        "ball": "Size 5 Fe16",
        "subs": "Subs - 5 - Slips",
    },
    "penalty": {
        "distance": "Penalty = 11m.",
        "positioning": "Players outside 20 + Arc",
        "occasions_label": "3 occasions =",
        "occasions": [
            "1 Goal scoring opp",
            "2 Any foul in small inside rect",
            "3 Aggressive in large",
        ],
    },
    "technical": [
        "Technical 13m fouls used",
        "Large Rect",
        "-> Technical foul in large",
    ],
    # IMG_6040 — Nótaí page
    "kickout_and_adv": {
        "header": "Nótaí:",
        "kickout": [
            "KO - 20M  FORWARD = Throw in",
            "- 13m players. = 13m adv opponent or free",
            "- 40M Travel Outside = free.  Players outside = free.",
            "4m rule KO mark = free.",
            "opponent fails to retreat = 50m. ADV",
        ],
        "fifty_metre_adv": [
            "50m ADV = Time wasting.",
            "Not handing ball back",
            "Kicking or throwing.",
            "failing to retreat",
            "Distract free taker.",
        ],
        "solo_and_go_notes": [
            "Can Solo & Go for free up to 13m",
            "can drive outside 40",
        ],
    },
    # IMG_6042 — folded wallet card (left + right)
    "solo_and_go": [
        "Solo & go.",
        "within 4m.",
        "NOT Inside 20",
        "NOT GO BACKWARDS = take a normal free",
        "NOT challenged WITHIN 4m = 50m ADV",
    ],
    "discipline": [
        "Captains Only Dissent.",
        "50m ADVANCED TO offending player Goal up to 13m.",
        "U18 = Black Card. 10 min Sin Bin",
        "Team Official. 20m FREE on their 13m",
        "YELLOW CARD",
    ],
    "four_v_three": [
        "4 v 3.",
        "Free on the halfway while carrying, receiving or intercepting.",
        "free on 20 NOT 13 for any other breach",
    ],
    "goalkeeper": [
        "Goalkeeper receive the ball",
        "1 Both are inside Large Rect.",
        "2 Opposition half.",
        "1 = Ball was kicked in by an opponent & both GK & teammate were in large rect",
    ],
}

# ---------------------------------------------------------------------------
# Card panels — Football split across two panels to fit full notes
# ---------------------------------------------------------------------------
SPORT_PAGES: list[list[dict]] = [
    # Page 1: Football (2 panels) + LGFA + Camogie
    [
        {
            "id": "gaa_football_a",
            "title": "GAA FOOTBALL",
            "subtitle": "Your notes — Solo & Go / Penalty / Discipline",
            "sections": [
                {
                    "heading": "Match setup",
                    "lines": [
                        HANDWRITTEN_NOTES["match_setup"]["ball"],
                        HANDWRITTEN_NOTES["match_setup"]["subs"],
                    ],
                },
                {
                    "heading": "Solo & Go",
                    "lines": HANDWRITTEN_NOTES["solo_and_go"],
                },
                {
                    "heading": "Penalty",
                    "lines": [
                        HANDWRITTEN_NOTES["penalty"]["distance"],
                        HANDWRITTEN_NOTES["penalty"]["positioning"],
                        HANDWRITTEN_NOTES["penalty"]["occasions_label"],
                        *[f"   {o}" for o in HANDWRITTEN_NOTES["penalty"]["occasions"]],
                    ],
                },
                {
                    "heading": "Discipline",
                    "lines": HANDWRITTEN_NOTES["discipline"],
                },
                {
                    "heading": "Technical",
                    "lines": HANDWRITTEN_NOTES["technical"],
                },
            ],
            "notes_lines": 4,
        },
        {
            "id": "gaa_football_b",
            "title": "GAA FOOTBALL",
            "subtitle": "Your notes — Kick-out / 4 v 3 / Goalkeeper",
            "sections": [
                {
                    "heading": "Kick-out / ADV",
                    "lines": (
                        HANDWRITTEN_NOTES["kickout_and_adv"]["kickout"]
                        + HANDWRITTEN_NOTES["kickout_and_adv"]["fifty_metre_adv"]
                        + HANDWRITTEN_NOTES["kickout_and_adv"]["solo_and_go_notes"]
                    ),
                },
                {
                    "heading": "4 v 3",
                    "lines": HANDWRITTEN_NOTES["four_v_three"],
                },
                {
                    "heading": "Goalkeeper",
                    "lines": HANDWRITTEN_NOTES["goalkeeper"],
                },
            ],
            "notes_lines": 5,
        },
        {
            "id": "lgfa",
            "title": "LGFA",
            "subtitle": "Ladies Football — quick reference",
            "sections": [
                {
                    "heading": "Match setup",
                    "lines": [
                        "Ball: Size 4 (younger) / Size 5 (adult)",
                        "Subs: check competition (slips required)",
                        "Halves: typically 30 mins (check bye-laws)",
                    ],
                },
                {
                    "heading": "Restarts",
                    "lines": [
                        "Kick-out from 20m (as per current LGFA rules)",
                        "All players outside 20m + arc until kicked",
                        "Forward underhand = throw-in / restart as ruled",
                    ],
                },
                {
                    "heading": "Penalty",
                    "lines": [
                        "Penalty = 11m",
                        "Players outside 20 + Arc",
                        "3 occasions: goal-scoring opp / foul in small rect / aggressive in large",
                    ],
                },
                {
                    "heading": "Frees & ADV",
                    "lines": [
                        "Technical fouls -> 13m free (as applicable)",
                        "Fail to retreat / time wasting -> advance free",
                        "Distract free-taker -> advance",
                        "Captains only for dissent (competition rules)",
                    ],
                },
                {
                    "heading": "Cards",
                    "lines": [
                        "Yellow / Red as per LGFA rule book",
                        "Sin bin / black card: apply competition directive",
                        "Team official misconduct -> free + card",
                    ],
                },
            ],
            "notes_lines": 6,
        },
        {
            "id": "camogie",
            "title": "CAMOGIE",
            "subtitle": "Quick reference",
            "sections": [
                {
                    "heading": "Match setup",
                    "lines": [
                        "Sliotar: Size 4 (check grade)",
                        "15-a-side / 12-a-side / 11-a-side per competition",
                        "Subs: check competition (slips)",
                        "Halves: typically 30 mins (check bye-laws)",
                    ],
                },
                {
                    "heading": "Restarts",
                    "lines": [
                        "Puck-out from hand — from small square / as ruled",
                        "45m free for wide / over end line by defender",
                        "Sideline cut — from the ground",
                    ],
                },
                {
                    "heading": "Penalty / frees",
                    "lines": [
                        "Penalty: 11m (Camogie)",
                        "Players outside 20m + arc for penalty",
                        "Foul in small square / denying goal -> penalty occasions",
                        "Technical foul in large rect -> free as ruled",
                    ],
                },
                {
                    "heading": "Discipline",
                    "lines": [
                        "Yellow / Red as per Camogie rules",
                        "Persistent fouling / dangerous play -> escalate",
                        "Team official: free + caution / send-off as ruled",
                        "Captains for approach / dissent control",
                    ],
                },
            ],
            "notes_lines": 6,
        },
    ],
    # Page 2: Hurling + blank write-in card (+ two spare note cards)
    [
        {
            "id": "hurling",
            "title": "HURLING",
            "subtitle": "Quick reference",
            "sections": [
                {
                    "heading": "Match setup",
                    "lines": [
                        "Sliotar: Size 5 (adult) / check underage size",
                        "Subs: check competition (slips / temporary replacement)",
                        "Halves: typically 30 / 35 mins (competition)",
                    ],
                },
                {
                    "heading": "Restarts",
                    "lines": [
                        "Puck-out from 20m line (current rules)",
                        "Must travel outside large / as per current directive",
                        "65m free for wide / over end line by defender",
                        "Sideline cut — from the ground",
                    ],
                },
                {
                    "heading": "Penalty / frees",
                    "lines": [
                        "Penalty: 20m (Hurling)",
                        "Players outside 20m + arc for penalty",
                        "Foul in small square / cynical denial -> penalty occasions",
                        "Advantage: play on when clear; return if lost",
                    ],
                },
                {
                    "heading": "Discipline",
                    "lines": [
                        "Yellow / Red as per Hurling rules",
                        "Cynical foul / pull-down -> black card / sin bin if directed",
                        "Team official misconduct -> free + card",
                        "Captains only for dissent",
                    ],
                },
            ],
            "notes_lines": 6,
        },
        {
            "id": "notes_blank",
            "title": "NÓTAÍ",
            "subtitle": "Write-in rule notes / match reminders",
            "sections": [
                {
                    "heading": "Use this card",
                    "lines": [
                        "Slide into flap of wallet after cutting along crop marks.",
                        "Jot competition-specific directives, ages, and bye-laws here.",
                    ],
                },
            ],
            "notes_lines": 18,
        },
        {
            "id": "notes_blank_2",
            "title": "NÓTAÍ",
            "subtitle": "Extra write-in card",
            "sections": [],
            "notes_lines": 22,
        },
        {
            "id": "notes_blank_3",
            "title": "NÓTAÍ",
            "subtitle": "Extra write-in card",
            "sections": [],
            "notes_lines": 22,
        },
    ],
]


def card_origins() -> list[tuple[float, float]]:
    """Bottom-left origin of each card panel (TL, TR, BL, BR)."""
    return [
        (0.0, PAGE_H - TOP_Y - CARD_H),
        (CARD_W, PAGE_H - TOP_Y - CARD_H),
        (0.0, PAGE_H - BOTTOM_Y - CARD_H),
        (CARD_W, PAGE_H - BOTTOM_Y - CARD_H),
    ]


def draw_crop_marks(c: canvas.Canvas, ox: float, oy: float) -> None:
    c.setStrokeColor(black)
    c.setLineWidth(0.27)
    mark = 16.0
    inset_x = 22.5
    inset_y = 22.5

    for y in (oy + CARD_H - inset_y, oy + inset_y):
        c.line(ox, y, ox + mark, y)
        c.line(ox + CARD_W - mark, y, ox + CARD_W, y)

    for x in (ox + inset_x, ox + CARD_W - inset_x):
        c.line(x, oy + CARD_H, x, oy + CARD_H - mark)
        c.line(x, oy, x, oy + mark)


def draw_wrapped_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font: str,
    size: float,
    leading: float,
    color=INK,
) -> float:
    c.setFillColor(color)
    c.setFont(font, size)
    words = text.split()
    if not words:
        return y
    line = words[0]
    for word in words[1:]:
        trial = f"{line} {word}"
        if c.stringWidth(trial, font, size) <= max_width:
            line = trial
        else:
            c.drawString(x, y, line)
            y -= leading
            line = word
    c.drawString(x, y, line)
    return y - leading


def draw_section_heading(c: canvas.Canvas, text: str, x: float, y: float, width: float) -> float:
    c.setFillColor(SECTION)
    c.setFont(BOLD_FONT, 7.5)
    c.drawString(x, y, text.upper())
    y -= 3
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(x, y, x + width, y)
    return y - 8


def draw_notes_box(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    line_count: int,
    line_gap: float = 11.0,
) -> None:
    c.setFillColor(SECTION)
    c.setFont(BOLD_FONT, 7.5)
    c.drawString(x, y, "NÓTAÍ / NOTES")
    y -= 3
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(x, y, x + width, y)
    y -= 10

    c.setStrokeColor(RULED)
    c.setLineWidth(0.4)
    for _ in range(line_count):
        c.line(x, y, x + width, y)
        y -= line_gap


def draw_wallet_cue(c: canvas.Canvas, content_x: float, content_w: float, cue_y: float, arrow_right: bool) -> None:
    c.setFillColor(MUTED)
    c.setFont(BODY_FONT, 6.5)
    cue = "Please slide into flap of wallet"
    tw = c.stringWidth(cue, BODY_FONT, 6.5)
    c.drawString(content_x + (content_w - tw) / 2, cue_y, cue)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.9)
    arrow_y = cue_y - 5
    ax0 = content_x + 18
    ax1 = content_x + content_w - 18
    c.line(ax0, arrow_y, ax1, arrow_y)
    if arrow_right:
        c.line(ax1, arrow_y, ax1 - 5, arrow_y + 2.5)
        c.line(ax1, arrow_y, ax1 - 5, arrow_y - 2.5)
    else:
        c.line(ax0, arrow_y, ax0 + 5, arrow_y + 2.5)
        c.line(ax0, arrow_y, ax0 + 5, arrow_y - 2.5)


def draw_card(c: canvas.Canvas, ox: float, oy: float, sport: dict, arrow_right: bool) -> None:
    draw_crop_marks(c, ox, oy)

    content_x = ox + MARGIN
    content_w = CARD_W - 2 * MARGIN
    y = oy + CARD_H - INNER_TOP

    header_h = 28
    c.setFillColor(HEADER_BG)
    c.rect(content_x, y - header_h + 6, content_w, header_h, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(BOLD_FONT, 11)
    c.drawString(content_x + 6, y - 8, sport["title"])
    c.setFont(BODY_FONT, 6.5)
    c.drawString(content_x + 6, y - 18, sport["subtitle"])
    y -= header_h + 6

    notes_reserved = 14 + sport["notes_lines"] * 11 + 8
    min_y = oy + MARGIN + notes_reserved

    for section in sport["sections"]:
        if y < min_y + 28:
            break
        y = draw_section_heading(c, section["heading"], content_x, y, content_w)
        for line in section["lines"]:
            if y < min_y + 12:
                break
            y = draw_wrapped_text(
                c, line, content_x, y, content_w, BODY_FONT, 6.4, 8.2, INK
            )
        y -= 3

    cue_y = max(y - 2, oy + MARGIN + notes_reserved + 10)
    draw_wallet_cue(c, content_x, content_w, cue_y, arrow_right)

    notes_top = oy + MARGIN + notes_reserved - 4
    draw_notes_box(c, content_x, notes_top, content_w, sport["notes_lines"])


def draw_fold_guide(c: canvas.Canvas) -> None:
    c.setStrokeColor(GUIDE)
    c.setDash(2, 2)
    c.setLineWidth(0.4)
    c.line(CARD_W, 0, CARD_W, PAGE_H)
    mid_y = PAGE_H - (TOP_Y + CARD_H + ROW_GAP / 2)
    c.line(0, mid_y, PAGE_W, mid_y)
    c.setDash()


def build_pdf(path: Path = OUTPUT) -> Path:
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("Referee Rule Cards — GAA Football / LGFA / Camogie / Hurling")
    c.setAuthor("Referee Match Report Card generator")

    origins = card_origins()
    for page_cards in SPORT_PAGES:
        draw_fold_guide(c)
        for i, sport in enumerate(page_cards):
            ox, oy = origins[i]
            draw_card(c, ox, oy, sport, arrow_right=(i % 2 == 1))
        c.showPage()

    c.save()
    return path


def print_transcription() -> None:
    import sys

    def _out(msg: str) -> None:
        try:
            print(msg)
        except UnicodeEncodeError:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))

    _out("=== HANDWRITTEN NOTES (structured) ===\n")
    for key, value in HANDWRITTEN_NOTES.items():
        if key == "source_images":
            _out(f"Sources: {', '.join(value)}\n")
            continue
        _out(f"[{key}]")
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, list):
                    _out(f"  {k}:")
                    for item in v:
                        _out(f"    - {item}")
                else:
                    _out(f"  {k}: {v}")
        elif isinstance(value, list):
            for item in value:
                _out(f"  - {item}")
        _out("")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate referee rule cards PDF")
    parser.add_argument(
        "--print-notes",
        action="store_true",
        help="Print structured handwritten transcription and exit",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT,
        help=f"Output PDF path (default: {OUTPUT.name})",
    )
    args = parser.parse_args()

    if args.print_notes:
        print_transcription()
    else:
        out = build_pdf(args.output)
        print(f"Wrote {out.resolve()}")
        print("Pages: 2  |  Card size: 297.5 x 410 pt (matches original wallet panels)")
        print("Page 1: GAA Football (2 panels) + LGFA + Camogie")
        print("Page 2: Hurling + blank Notai write-in cards")
