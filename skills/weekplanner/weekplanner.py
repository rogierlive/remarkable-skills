#!/usr/bin/env python3
"""Weekplanner voor je reMarkable (PDF, 12 pagina's).

Opbouw:
  1. Voorpagina: rustige cover (of je eigen foto) met weeknummer en datums.
  2-11. Per werkdag (maandag t/m vrijdag) twee lange pagina's:
     - Dagpagina: agenda per uur met een kader om de werkdag, je weekdoelen,
       vier prioriteiten met afvinkrondjes, kladlijnen en notitieruimte.
     - Dagboek: OCHTEND (dankbaar, wat maakt vandaag geweldig, affirmatie)
       en AVOND (drie mooie dingen, learnings, vrije regels).
  12. Weekend: een kort dagboek voor zaterdag en zondag plus vrije regels.

De dag- en dagboekpagina's zijn extra lang: je scrolt erdoor op je reMarkable.
Standaard is de planner liggend (breed scherm). Wil je staand? Gebruik
--stand staand of WEEKPLANNER_STAND=staand.

Voorbeelden:
  python3 weekplanner.py --ics ../../examples/demo-agenda.ics --doelen "Offerte sturen|Twee keer sporten|Tuin opruimen"
  python3 weekplanner.py --cover-image mijn-foto.jpg --ics agenda.ics
  python3 weekplanner.py            # leest alles uit ~/.remarkable-skills.env
"""
import argparse
import math
import os
import re
import sys
import urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, Color
    from reportlab.lib.utils import ImageReader
except ImportError:
    sys.exit("reportlab ontbreekt. Zie de README, stap 3 (venv).")

# Emoji weghalen: het lettertype in de PDF kent geen emoji, anders komen er
# lege vakjes. Ook tekens buiten Latin-1 vallen weg om dezelfde reden.
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002300-\U000023FF"
    "\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U000020E3"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text):
    if not text:
        return ""
    t = _EMOJI_RE.sub("", str(text)).replace("\u2014", "-").replace("\u2013", "-")
    t = t.encode("latin-1", "ignore").decode("latin-1")
    return re.sub(r"\s{2,}", " ", t).strip()


# ── Paginamaten ──────────────────────────────────────────────────────────────
# Staand: breedte A4, voorpagina 4:3 (zoals het reMarkable-scherm), de lange
# pagina's twee schermen hoog. Liggend: alles even breed als het liggende
# scherm, de lange pagina's twee liggende schermen hoog.

PAGE_W = 595.276
PAGE_H_COVER = 793.7
PAGE_H_SPREAD = 1683.78
MARGIN_LEFT = 39.685
MARGIN_RIGHT = 566.929
LEFT_COL_X1 = 39.685
LEFT_COL_X2 = 291.969
RIGHT_COL_X1 = 314.646
RIGHT_COL_X2 = 566.929

ORIENTATION = 'landscape'
PORTRAIT_SPREAD_H = 1683.78
LANDSCAPE_DAY_H = 1308.0        # hoogte dagpagina in liggend
LANDSCAPE_SMALL_ROW_H = 16.0    # uren buiten de kerntijd (08-17) in liggend
LANDSCAPE_CORE_HOURS = range(8, 17)
LANDSCAPE_ROW_H = 42.0          # uurrij in de kerntijd, liggend


def configure_orientation(orientation):
    """'portrait' (staand) of 'landscape' (liggend, standaard)."""
    global ORIENTATION, PAGE_W, PAGE_H_COVER, PAGE_H_SPREAD
    global MARGIN_LEFT, MARGIN_RIGHT
    global LEFT_COL_X1, LEFT_COL_X2, RIGHT_COL_X1, RIGHT_COL_X2
    o = (orientation or '').strip().lower()
    o = {'staand': 'portrait', 'liggend': 'landscape'}.get(o, o)
    if o not in ('', 'portrait', 'landscape'):
        print(f"Let op: onbekende stand {orientation!r}, ik kies liggend.", file=sys.stderr)
    o = 'portrait' if o == 'portrait' else 'landscape'
    ORIENTATION = o
    if o == 'portrait':
        PAGE_W, PAGE_H_COVER, PAGE_H_SPREAD = 595.276, 793.7, PORTRAIT_SPREAD_H
        MARGIN_LEFT, MARGIN_RIGHT = 39.685, 566.929
        LEFT_COL_X1, LEFT_COL_X2 = 39.685, 291.969
        RIGHT_COL_X1, RIGHT_COL_X2 = 314.646, 566.929
    else:
        PAGE_W, PAGE_H_COVER = 793.7, 595.276
        PAGE_H_SPREAD = 2 * 595.276
        MARGIN_LEFT = 39.685
        MARGIN_RIGHT = PAGE_W - (595.276 - 566.929)
        gap = 314.646 - 291.969
        col_w = (MARGIN_RIGHT - MARGIN_LEFT - gap) / 2
        LEFT_COL_X1, LEFT_COL_X2 = MARGIN_LEFT, MARGIN_LEFT + col_w
        RIGHT_COL_X1, RIGHT_COL_X2 = LEFT_COL_X2 + gap, MARGIN_RIGHT


# Kleuren
GREEN = HexColor('#799a7c')
BLACK = HexColor('#1a1a1a')
DARK_GREY = HexColor('#333333')
MID_GREY = HexColor('#545454')
LIGHT_GREY = HexColor('#888888')
VERY_LIGHT_GREY = HexColor('#dddddd')
WHITE = HexColor('#ffffff')

BAND_HEIGHT = 28.27  # regelafstand van de schrijflijnen

MONTHS_NL = {
    1: 'JANUARI', 2: 'FEBRUARI', 3: 'MAART', 4: 'APRIL',
    5: 'MEI', 6: 'JUNI', 7: 'JULI', 8: 'AUGUSTUS',
    9: 'SEPTEMBER', 10: 'OKTOBER', 11: 'NOVEMBER', 12: 'DECEMBER',
}
DAYS_NL = {
    0: 'MAANDAG', 1: 'DINSDAG', 2: 'WOENSDAG', 3: 'DONDERDAG',
    4: 'VRIJDAG', 5: 'ZATERDAG', 6: 'ZONDAG',
}


# ── Tekst ────────────────────────────────────────────────────────────────────

def draw_text_spaced(c, text, x, y, font, size, char_spacing_em=0.25, color=None):
    if color:
        c.setFillColor(color)
    c.setFont(font, size)
    extra = size * char_spacing_em
    cx = x
    for ch in text:
        c.drawString(cx, y, ch)
        cx += c.stringWidth(ch, font, size) + extra


def text_spaced_width(c, text, font, size, char_spacing_em=0.25):
    extra = size * char_spacing_em
    total = sum(c.stringWidth(ch, font, size) + extra for ch in text)
    return total - extra if text else 0.0


def draw_centered_spaced(c, text, y, font, size, char_spacing_em=0.25, color=None):
    w = text_spaced_width(c, text, font, size, char_spacing_em)
    draw_text_spaced(c, text, (PAGE_W - w) / 2, y, font, size, char_spacing_em, color)


def _fit_text(c, text, font, size, max_w):
    """Kap tekst af op echte breedte, met ... als het niet past."""
    if c.stringWidth(text, font, size) <= max_w:
        return text
    while text and c.stringWidth(text.rstrip() + '...', font, size) > max_w:
        text = text[:-1]
    return text.rstrip() + '...'


# ── Lijnen en vormen ─────────────────────────────────────────────────────────

def accent_line(c, x1, y, x2, color=GREEN, width=1.5):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y, x2, y)


def divider_line(c, x1, y, x2, color=BLACK, width=0.75):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y, x2, y)


def ruled_lines(c, x1, x2, y_top, y_bottom, color=LIGHT_GREY, line_width=0.5, band_height=None):
    """Vult het vlak met schrijflijnen. Geeft de y van de laatste lijn terug."""
    if band_height is None:
        band_height = BAND_HEIGHT
    c.setStrokeColor(color)
    c.setLineWidth(line_width)
    y = y_top - band_height
    while y >= y_bottom - 1:
        c.line(x1, y, x2, y)
        y -= band_height
    return y + band_height


def draw_track_row(c, y, x2=None, color=None):
    """Voortgangsspoor: vakje, zes rondjes, vakje (rechts uitgelijnd)."""
    if x2 is None:
        x2 = RIGHT_COL_X2
    if color is None:
        color = GREEN
    box_size, circle_r, spacing = 11, 5.5, 18
    start_x = x2 - (7 * spacing + box_size)
    c.setStrokeColor(color)
    c.setFillColor(WHITE)
    c.setLineWidth(0.9)
    c.rect(start_x, y, box_size, box_size, fill=1, stroke=1)
    for i in range(6):
        c.circle(start_x + box_size + spacing / 2 + i * spacing, y + box_size / 2,
                 circle_r, fill=1, stroke=1)
    c.rect(x2 - box_size, y, box_size, box_size, fill=1, stroke=1)


def fmt_date_nl(d):
    return f"{d.day} {MONTHS_NL[d.month]}"


def week_number(d):
    return d.isocalendar()[1]


def draw_page_title(c, text, H):
    c.setFillColor(BLACK)
    c.setFont('Courier-Bold', 11)
    w = c.stringWidth(text, 'Courier-Bold', 11)
    c.drawString((PAGE_W - w) / 2, H - 36.605, text)
    accent_line(c, MARGIN_LEFT, H - 45.247, MARGIN_RIGHT, color=GREEN, width=1.0)


# ── Pagina 1: voorpagina ─────────────────────────────────────────────────────

def _draw_calm_cover(c):
    """Eigen rustige cover zonder foto: zachte lucht en heuvels in saliegroen."""
    W, H = PAGE_W, PAGE_H_COVER
    top, bottom = (0.93, 0.94, 0.91), (0.80, 0.85, 0.79)
    steps = 60
    for i in range(steps):
        t = i / (steps - 1)
        c.setFillColorRGB(*[top[k] + (bottom[k] - top[k]) * (1 - t) for k in range(3)])
        c.rect(0, H * i / steps, W, H / steps + 1, fill=1, stroke=0)
    # Zon
    c.setFillColor(Color(1, 1, 1, alpha=0.55))
    c.circle(W * 0.68, H * 0.70, min(W, H) * 0.085, fill=1, stroke=0)
    # Heuvels, van ver (licht) naar dichtbij (donker)
    layers = [
        ('#b7c6b4', 0.58, 0.040, 1.3, 0.4),
        ('#9db39f', 0.50, 0.045, 1.8, 2.1),
        ('#799a7c', 0.40, 0.050, 1.1, 4.0),
        ('#5f7f63', 0.30, 0.040, 2.4, 1.0),
        ('#46604a', 0.19, 0.035, 1.6, 5.2),
    ]
    for hexc, base, amp, freq, phase in layers:
        c.setFillColor(HexColor(hexc))
        p = c.beginPath()
        p.moveTo(0, 0)
        n = 80
        for k in range(n + 1):
            x = W * k / n
            y = H * (base + amp * math.sin(freq * math.pi * k / n * 2 + phase)
                     + amp * 0.4 * math.sin(freq * 3.1 * math.pi * k / n + phase * 1.7))
            p.lineTo(x, y)
        p.lineTo(W, 0)
        p.close()
        c.drawPath(p, stroke=0, fill=1)


def draw_voorblad(c, week_start, cover_image_path=None):
    c.setPageSize((PAGE_W, PAGE_H_COVER))
    wn = week_number(week_start)
    week_end = week_start + timedelta(days=6)

    drawn = False
    if cover_image_path and Path(cover_image_path).is_file():
        try:
            img = ImageReader(str(cover_image_path))
            iw, ih = img.getSize()
            scale = max(PAGE_W / iw, PAGE_H_COVER / ih)
            dw, dh = iw * scale, ih * scale
            c.drawImage(img, (PAGE_W - dw) / 2, (PAGE_H_COVER - dh) / 2, dw, dh,
                        preserveAspectRatio=False, mask='auto')
            drawn = True
        except Exception:
            print("Let op: je coverafbeelding kon niet worden gelezen. Er komt een rustige cover.",
                  file=sys.stderr)
    if not drawn:
        _draw_calm_cover(c)

    # Zacht donker verloop onderaan, voor contrast met de witte tekst.
    gradient_h, steps = 220, 60
    for i in range(steps):
        alpha = (i / steps) ** 1.4 * 0.62
        y_band = gradient_h * (1 - i / steps)
        c.setFillColor(Color(0, 0, 0, alpha=alpha))
        c.rect(0, y_band - gradient_h / steps, PAGE_W, gradient_h / steps + 0.6, fill=1, stroke=0)

    draw_centered_spaced(c, "WEEK", 175, 'Courier-Bold', 9, char_spacing_em=0.5, color=WHITE)
    c.setFillColor(WHITE)
    c.setFont('Courier-Bold', 48)
    wn_str = str(wn)
    c.drawString((PAGE_W - c.stringWidth(wn_str, 'Courier-Bold', 48)) / 2, 100, wn_str)
    cx = PAGE_W / 2
    accent_line(c, cx - 57, 80, cx + 57, color=GREEN, width=1.5)
    date_range = f"{fmt_date_nl(week_start)}  -  {fmt_date_nl(week_end)}"
    draw_centered_spaced(c, date_range, 43, 'Courier', 13, char_spacing_em=0.1, color=WHITE)


# ── Dagpagina ────────────────────────────────────────────────────────────────

def draw_notities_block(c, x1, x2, y_top, bottom_y):
    c.setFillColor(BLACK)
    c.setFont('Courier-Bold', 9)
    c.drawString(x1, y_top, 'NOTITIES')
    accent_line(c, x1, y_top - 8, x2, color=GREEN, width=0.75)
    return ruled_lines(c, x1, x2, y_top - 12, bottom_y)


def draw_dagplanning(c, day_date, events_by_day, doelen):
    DAY_H = PAGE_H_SPREAD if ORIENTATION == 'portrait' else LANDSCAPE_DAY_H
    c.setPageSize((PAGE_W, DAY_H))
    events = events_by_day.get(day_date.isoformat(), [])

    draw_page_title(c, f"{DAYS_NL[day_date.weekday()]} - {fmt_date_nl(day_date)}", DAY_H)

    # ── Links: agenda per uur (05:00 - 23:00) ──
    if ORIENTATION == 'portrait':
        AGENDA_TOP, AGENDA_BOTTOM = 1615.296, 900.0
    else:
        AGENDA_TOP, AGENDA_BOTTOM = DAY_H - 68.484, None
    HOUR_START, HOUR_END = 5, 23
    N_HOURS = HOUR_END - HOUR_START
    ROW_H = (AGENDA_TOP - AGENDA_BOTTOM) / N_HOURS if AGENDA_BOTTOM is not None else LANDSCAPE_ROW_H

    events_by_hour = {}
    for evt in events:
        try:
            h = int(evt.get('time', '').split(':')[0])
        except Exception:
            h = HOUR_START
        h = max(HOUR_START, min(HOUR_END - 1, h))
        events_by_hour.setdefault(h, []).append(evt)

    # Rijen. Staand: vaste hoogte. Liggend: de kerntijd (08-17) krijgt volle
    # rijen, de uren daarbuiten zijn lager; een uur met veel afspraken groeit mee.
    row_tops, row_small = [], []
    if ORIENTATION == 'portrait':
        for i in range(N_HOURS + 1):
            row_tops.append(AGENDA_TOP - i * ROW_H)
            row_small.append(False)
    else:
        y_cur = AGENDA_TOP
        for i in range(N_HOURS + 1):
            hour = HOUR_START + i
            row_tops.append(y_cur)
            small = hour not in LANDSCAPE_CORE_HOURS
            row_small.append(small)
            n_ev = len(events_by_hour.get(hour, []))
            h_row = LANDSCAPE_SMALL_ROW_H if small else LANDSCAPE_ROW_H
            if n_ev:
                h_row = max(h_row, 10 + 7 + 3 + (n_ev - 1) * 11.5 + 3.0)
            y_cur -= h_row
        AGENDA_BOTTOM = row_tops[N_HOURS]

    HOUR_LABEL_COLOR = HexColor('#666666')
    DIVIDER_COLOR = HexColor('#aaaaaa')
    EVENT_COLOR = HexColor('#333333')
    HOUR_LABEL_X = LEFT_COL_X1 + 3
    if ORIENTATION == 'landscape':
        HOUR_FONT, DIVIDER_W = 9.5, 0.4
        DIVIDER_COLOR = HexColor('#cccccc')
        HOUR_LABEL_COLOR = HexColor('#555555')
    else:
        HOUR_FONT, DIVIDER_W = 7.5, 0.5

    for i in range(N_HOURS + 1):
        hour = HOUR_START + i
        row_top = row_tops[i]
        if hour == HOUR_END:
            continue
        small_row = row_small[i]
        c.setFillColor(HexColor('#999999') if small_row else HOUR_LABEL_COLOR)
        c.setFont('Courier', 7.0 if small_row else HOUR_FONT)
        c.drawString(HOUR_LABEL_X, row_top - 8, f"{hour:02d}:00")

        line_y = row_top - 10
        c.setStrokeColor(HexColor('#dddddd') if small_row else DIVIDER_COLOR)
        c.setLineWidth(0.3 if small_row else DIVIDER_W)
        c.line(LEFT_COL_X1, line_y, LEFT_COL_X2, line_y)

        if hour in events_by_hour and i < N_HOURS:
            EV_FONT, EV_LEAD = 9.0, 11.5
            c.setFillColor(EVENT_COLOR)
            row_h = row_top - row_tops[i + 1]
            capacity = max(1, 1 + int((row_h - 10 - 7 - 3) // EV_LEAD))
            evs = events_by_hour[hour]
            if len(evs) > capacity:
                shown = evs[:capacity - 1]
                extra = len(evs) - len(shown)
            else:
                shown, extra = evs, 0
            ev_x = LEFT_COL_X1 + 3
            ev_max_w = LEFT_COL_X2 - ev_x - 4
            ey = line_y - 9.5
            for evt in shown:
                time_str = evt.get('time', '')
                title_evt = _strip_emoji(evt.get('title', ''))
                x = ev_x
                if time_str:
                    c.setFont('Helvetica-Bold', EV_FONT)
                    c.drawString(x, ey, time_str)
                    x += c.stringWidth(time_str + ' ', 'Helvetica-Bold', EV_FONT)
                c.setFont('Helvetica', EV_FONT)
                c.drawString(x, ey, _fit_text(c, title_evt, 'Helvetica', EV_FONT,
                                              ev_max_w - (x - ev_x)))
                ey -= EV_LEAD
            if extra:
                c.setFont('Helvetica-Oblique', EV_FONT)
                c.drawString(ev_x, ey, f"+{extra} meer")

    # Kader om de werkdag (05:00 - 17:00), om in te kleuren bij timeboxing.
    WORKDAY_START_HOUR, WORKDAY_END_HOUR, LINE_OFFSET = 5, 17, 10
    kader_top = row_tops[WORKDAY_START_HOUR - HOUR_START] - LINE_OFFSET
    kader_bottom = row_tops[WORKDAY_END_HOUR - HOUR_START] - LINE_OFFSET
    c.setStrokeColor(BLACK)
    c.setLineWidth(1.5)
    c.rect(LEFT_COL_X1, kader_bottom, LEFT_COL_X2 - LEFT_COL_X1,
           kader_top - kader_bottom, fill=0, stroke=1)

    # ── Rechts: deze week, vier prioriteiten, kladlijnen ──
    AGENDA_ROW_H = 39.738
    TRACK_OFFSET, TRACK_BOX_SIZE = 3.0, 11.0

    def _section_header(y, label, printed):
        c.setFillColor(BLACK)
        c.setFont('Courier-Bold', 9)
        c.drawString(RIGHT_COL_X1, y, label)
        if printed:
            accent_line(c, RIGHT_COL_X1, y - 8.37, RIGHT_COL_X2, color=GREEN, width=0.75)
        else:
            divider_line(c, RIGHT_COL_X1, y - 8.37, RIGHT_COL_X2, color=BLACK, width=0.75)

    def _draw_priority_row(task_num, write_y_1, write_y_2):
        num_font, num_size = 'Courier', 7.5
        c.setFillColor(HexColor('#888888'))
        c.setFont(num_font, num_size)
        c.drawString(RIGHT_COL_X1, write_y_1 + 2, str(task_num))
        line_x_start = RIGHT_COL_X1 + c.stringWidth(str(task_num), num_font, num_size) + 4
        c.setStrokeColor(HexColor('#888888'))
        c.setLineWidth(0.75)
        c.line(line_x_start, write_y_1, RIGHT_COL_X2, write_y_1)
        c.line(RIGHT_COL_X1, write_y_2, RIGHT_COL_X2, write_y_2)
        track_bottom_y = write_y_2 - TRACK_OFFSET - TRACK_BOX_SIZE
        draw_track_row(c, track_bottom_y, x2=RIGHT_COL_X2, color=GREEN)
        return track_bottom_y

    # DEZE WEEK: je weekdoelen uit de instellingen (groene lijn = voorgedrukt).
    # Zonder weekdoelen: twee lege regels om zelf in te vullen.
    cursor = AGENDA_TOP - 10
    _section_header(cursor, 'DEZE WEEK', printed=bool(doelen))
    c.setStrokeColor(LIGHT_GREY)
    c.setLineWidth(0.75)
    if doelen:
        y_line = cursor - 34
        for k, doel in enumerate(doelen[:3]):
            y_line = cursor - 34 - k * BAND_HEIGHT
            c.setStrokeColor(GREEN)
            c.setFillColor(WHITE)
            c.setLineWidth(0.9)
            c.circle(RIGHT_COL_X1 + 5, y_line + 6.5, 4.5, fill=1, stroke=1)
            c.setFillColor(DARK_GREY)
            c.setFont('Helvetica', 9.5)
            c.drawString(RIGHT_COL_X1 + 16, y_line + 3.5,
                         _fit_text(c, _strip_emoji(doel), 'Helvetica', 9.5,
                                   RIGHT_COL_X2 - RIGHT_COL_X1 - 16))
            c.setStrokeColor(LIGHT_GREY)
            c.setLineWidth(0.75)
            c.line(RIGHT_COL_X1, y_line, RIGHT_COL_X2, y_line)
        cursor = y_line - 30
    else:
        write_y_week_1 = cursor - 34
        write_y_week_2 = write_y_week_1 - BAND_HEIGHT
        c.line(RIGHT_COL_X1, write_y_week_1, RIGHT_COL_X2, write_y_week_1)
        c.line(RIGHT_COL_X1, write_y_week_2, RIGHT_COL_X2, write_y_week_2)
        cursor = write_y_week_2 - 30

    # Vier genummerde prioriteiten, alle vier gelijk.
    ITEM_TOP_GAP, ITEM_GAP = 26, 30
    write_y_1 = cursor - ITEM_TOP_GAP
    track_bottom = _draw_priority_row(1, write_y_1, write_y_1 - AGENDA_ROW_H)
    for task_num in (2, 3, 4):
        write_y_1 = track_bottom - ITEM_GAP
        track_bottom = _draw_priority_row(task_num, write_y_1, write_y_1 - AGENDA_ROW_H)
    cursor = track_bottom - 34

    # Kladlijnen tot vlak boven de scheidingslijn.
    UPPER_LOWER_DIVIDER_Y = 867.51 if ORIENTATION == 'portrait' else AGENDA_BOTTOM - 32.49
    ruled_lines(c, RIGHT_COL_X1, RIGHT_COL_X2, cursor, UPPER_LOWER_DIVIDER_Y + 8.0,
                color=VERY_LIGHT_GREY, line_width=0.5, band_height=20.0)

    accent_line(c, MARGIN_LEFT, UPPER_LOWER_DIVIDER_Y, MARGIN_RIGHT, color=GREEN, width=1.5)

    # Onderste helft: NOTITIES.
    NOTITIES_TOP = 843.0 if ORIENTATION == 'portrait' else UPPER_LOWER_DIVIDER_Y - 24.51
    draw_notities_block(c, MARGIN_LEFT, MARGIN_RIGHT, NOTITIES_TOP, 28.0)


# ── Dagboek (tweede pagina per dag) ─────────────────────────────────────────

EVENING_BAND_COLOR = HexColor('#f0f0f0')


def _draw_sun(c, cx, cy):
    c.saveState()
    c.setStrokeColor(BLACK)
    c.setLineWidth(0.9)
    c.circle(cx, cy, 5.2, stroke=1, fill=0)
    for k in range(8):
        ang = math.radians(k * 45)
        c.line(cx + 7.6 * math.cos(ang), cy + 7.6 * math.sin(ang),
               cx + 10.8 * math.cos(ang), cy + 10.8 * math.sin(ang))
    c.restoreState()


def _draw_moon(c, cx, cy):
    c.saveState()
    c.translate(cx, cy)
    c.rotate(28)
    c.setStrokeColor(BLACK)
    c.setFillColor(EVENING_BAND_COLOR)
    c.setLineWidth(0.9)
    R, r = 7.94, 6.2
    cx2 = math.sqrt(R * R - r * r)
    a0 = 180 + math.degrees(math.atan2(r, cx2))
    p = c.beginPath()
    p.arc(-r, -r, r, r, 90, 180)
    p.arcTo(cx2 - R, -R, cx2 + R, R, a0, -2 * (a0 - 180))
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    c.restoreState()


def _journal_section(c, y, label, icon_fn):
    icon_fn(c, MARGIN_LEFT + 11, y + 3.5)
    draw_text_spaced(c, label, MARGIN_LEFT + 30, y, 'Courier-Bold', 9, char_spacing_em=0.25,
                     color=BLACK)
    accent_line(c, MARGIN_LEFT, y - 8.37, MARGIN_RIGHT, GREEN, 0.75)


def _prompt_block(c, y_label, label, n_lines, band):
    c.setFillColor(DARK_GREY)
    c.setFont('Courier', 9.5)
    c.drawString(MARGIN_LEFT, y_label, label)
    c.setStrokeColor(LIGHT_GREY)
    c.setLineWidth(0.75)
    y = y_label
    for k in range(n_lines):
        y = y_label - (band - 4) - k * band
        c.line(MARGIN_LEFT, y, MARGIN_RIGHT, y)
    return y


def draw_dagboek(c, day_date):
    c.setPageSize((PAGE_W, PAGE_H_SPREAD))
    H = PAGE_H_SPREAD
    draw_page_title(c, f"{DAYS_NL[day_date.weekday()]} - {fmt_date_nl(day_date)}", H)

    y_avond = H - max(646.0, H / 2 + 50)
    c.setFillColor(EVENING_BAND_COLOR)
    c.rect(0, 0, PAGE_W, y_avond + 30, fill=1, stroke=0)

    y = H - 86.0
    _journal_section(c, y, 'OCHTEND', _draw_sun)
    last = _prompt_block(c, y - 42, 'Ik ben dankbaar voor...', 3, 38)
    last = _prompt_block(c, last - 46, 'Wat maakt vandaag geweldig?', 3, 38)
    last = _prompt_block(c, last - 46, 'Daily affirmation', 1, 38)

    _journal_section(c, y_avond, 'AVOND', _draw_moon)
    last = _prompt_block(c, y_avond - 42, 'Drie mooie dingen van vandaag', 3, 40)
    last = _prompt_block(c, last - 48, 'Learnings van vandaag', 3, 40)
    ruled_lines(c, MARGIN_LEFT, MARGIN_RIGHT, last - 26, 24, color=LIGHT_GREY,
                line_width=0.5, band_height=BAND_HEIGHT)


# ── Weekend ──────────────────────────────────────────────────────────────────

def _numbered_prompt(c, y_label, label, n_lines, band=26):
    c.setFillColor(DARK_GREY)
    c.setFont('Courier', 9.5)
    c.drawString(MARGIN_LEFT, y_label, label)
    num_font, num_size = 'Courier', 7.5
    y = y_label
    for k in range(n_lines):
        y = y_label - (band - 2) - k * band
        c.setFillColor(HexColor('#888888'))
        c.setFont(num_font, num_size)
        c.drawString(MARGIN_LEFT, y + 2, str(k + 1))
        x0 = MARGIN_LEFT + c.stringWidth(str(k + 1), num_font, num_size) + 4
        c.setStrokeColor(LIGHT_GREY)
        c.setLineWidth(0.75)
        c.line(x0, y, MARGIN_RIGHT, y)
    return y


def draw_weekend(c, week_start):
    c.setPageSize((PAGE_W, PAGE_H_SPREAD))
    H = PAGE_H_SPREAD
    zaterdag = week_start + timedelta(days=5)
    zondag = week_start + timedelta(days=6)
    draw_page_title(c, f"WEEKEND - {fmt_date_nl(zaterdag)} / {fmt_date_nl(zondag)}", H)

    y = H - 78.0
    for day in (zaterdag, zondag):
        label = f"{DAYS_NL[day.weekday()]} {fmt_date_nl(day)}"
        draw_text_spaced(c, label, MARGIN_LEFT, y, 'Courier-Bold', 11, char_spacing_em=0.25,
                         color=BLACK)
        accent_line(c, MARGIN_LEFT, y - 8.37, MARGIN_RIGHT, GREEN, 1.0)
        y -= 34
        _journal_section(c, y, 'OCHTEND', _draw_sun)
        last = _numbered_prompt(c, y - 30, 'Ik ben dankbaar voor', 3)
        last = _numbered_prompt(c, last - 24, 'Wat maakt vandaag geweldig?', 3)
        last = _numbered_prompt(c, last - 24, 'Ik ben...', 1)
        y = last - 34
        _journal_section(c, y, 'AVOND', _draw_moon)
        last = _numbered_prompt(c, y - 30, 'Drie mooie dingen van vandaag', 3)
        last = _numbered_prompt(c, last - 24, 'Wat had vandaag nog beter gemaakt?', 1)
        y = last - 44
    ruled_lines(c, MARGIN_LEFT, MARGIN_RIGHT, y + 10, 18)


# ── Instellingen en agenda ───────────────────────────────────────────────────

BEKENDE_KEYS = {"REMARKABLE_NAAM", "REMARKABLE_MAP", "REMARKABLE_BROWSER", "REMARKABLE_PYTHON",
                "WEEKPLANNER_ICAL_URL", "WEEKPLANNER_DOELEN", "WEEKPLANNER_MAP", "WEEKPLANNER_TZ",
                "WEEKPLANNER_COVER", "WEEKPLANNER_STAND"}


def laad_env():
    """Leest je instellingen uit $REMARKABLE_SKILLS_ENV of ~/.remarkable-skills.env.
    Alleen bekende KEY=waarde-regels. Wat al in je omgeving staat, wint."""
    for f in [os.environ.get("REMARKABLE_SKILLS_ENV"), str(Path.home() / ".remarkable-skills.env")]:
        if f and Path(f).is_file():
            for regel in Path(f).read_text().splitlines():
                regel = regel.strip()
                if regel and not regel.startswith("#") and "=" in regel:
                    k, v = regel.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                        v = v[1:-1]
                    if v.startswith("~/"):
                        v = str(Path.home() / v[2:])
                    if k in BEKENDE_KEYS:
                        os.environ.setdefault(k, v)
            return


def lees_agenda(ics_pad, url, maandag, tz):
    """Geeft {'JJJJ-MM-DD': [{'time': 'HH:MM' of '', 'title': ...}]}.
    Hele-dag-afspraken krijgen geen tijd en staan bovenaan."""
    if not ics_pad and not url:
        return {}
    import icalendar
    import recurring_ical_events
    if ics_pad:
        data = Path(ics_pad).read_bytes()
    else:
        if url.lower().startswith("webcal://"):
            url = "https://" + url[len("webcal://"):]
        if not url.lower().startswith("https://"):
            raise ValueError("het iCal-adres moet beginnen met https://")
        req = urllib.request.Request(url, headers={"User-Agent": "weekplanner"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    cal = icalendar.Calendar.from_ical(data)
    van = datetime.combine(maandag, time.min, tz)
    tot = van + timedelta(days=7)
    dagen = {maandag + timedelta(days=i) for i in range(7)}
    hele_dag, met_tijd = {}, {}
    for ev in recurring_ical_events.of(cal).between(van, tot):
        titel = _strip_emoji(ev.get("SUMMARY")) or "(zonder titel)"
        s = ev["DTSTART"].dt
        e = ev.get("DTEND").dt if ev.get("DTEND") else None
        if not isinstance(s, datetime):
            eind = e if isinstance(e, date) and not isinstance(e, datetime) else s + timedelta(days=1)
            d = s
            while d < eind:
                if d in dagen:
                    hele_dag.setdefault(d, []).append(titel)
                d += timedelta(days=1)
            continue
        s = s.astimezone(tz) if s.tzinfo else s.replace(tzinfo=tz)
        if s.date() in dagen:
            met_tijd.setdefault(s.date(), []).append((s, titel))
    uit = {}
    for d in sorted(dagen):
        lijst = [{"time": "", "title": t} for t in hele_dag.get(d, [])]
        lijst += [{"time": s.strftime("%H:%M"), "title": t}
                  for s, t in sorted(met_tijd.get(d, []), key=lambda x: x[0])]
        if lijst:
            uit[d.isoformat()] = lijst
    return uit


def standaard_maandag(vandaag):
    """Maandag van de komende week als het vrijdag t/m zondag is, anders van deze week."""
    m = vandaag - timedelta(days=vandaag.weekday())
    return m + timedelta(days=7) if vandaag.weekday() >= 4 else m


def main():
    laad_env()
    ap = argparse.ArgumentParser(description="Maak een weekplanner-PDF voor je reMarkable.")
    ap.add_argument("--week-start", help="Maandag van de week, JJJJ-MM-DD (standaard: komende of huidige week)")
    ap.add_argument("--ics", help="Pad naar een .ics-bestand")
    ap.add_argument("--ical-url", default=os.environ.get("WEEKPLANNER_ICAL_URL", ""),
                    help="Geheim iCal-adres (Google Agenda) of ICS-link (Outlook)")
    ap.add_argument("--doelen", default=os.environ.get("WEEKPLANNER_DOELEN", ""),
                    help="Weekdoelen (maximaal 3), gescheiden door |")
    ap.add_argument("--cover-image", default=os.environ.get("WEEKPLANNER_COVER", ""),
                    help="Eigen afbeelding voor de voorpagina (optioneel)")
    ap.add_argument("--stand", default=os.environ.get("WEEKPLANNER_STAND", "liggend"),
                    help="liggend (standaard) of staand")
    ap.add_argument("--tz", default=os.environ.get("WEEKPLANNER_TZ", "Europe/Amsterdam"))
    ap.add_argument("--output", "-o", help="Pad van de PDF")
    a = ap.parse_args()
    configure_orientation(a.stand)

    maandag = date.fromisoformat(a.week_start) if a.week_start else standaard_maandag(date.today())
    maandag -= timedelta(days=maandag.weekday())
    tz = ZoneInfo(a.tz)
    doelen = [d.strip() for d in a.doelen.split("|") if d.strip()][:3]
    try:
        agenda = lees_agenda(a.ics, (a.ical_url or "").strip() or None, maandag, tz)
    except Exception as ex:
        # Bewust zonder het adres zelf: je iCal-adres is geheim en hoort niet in een log.
        reden = ex.reason if hasattr(ex, "reason") else ex
        if isinstance(ex, ValueError) and "iCal-adres" not in str(ex):
            reden = "het bestand of adres is geen geldige agenda"
        sys.exit(f"Ik kon je agenda niet lezen ({type(ex).__name__}: {reden}). "
                 f"Controleer WEEKPLANNER_ICAL_URL of je .ics-bestand.")
    if not a.ics and not a.ical_url:
        print("Let op: geen agenda opgegeven. Je krijgt een planner zonder afspraken.", file=sys.stderr)

    wn = week_number(maandag)
    uit = Path(a.output or f"uitvoer/weekplanner-week{wn:02d}-{maandag.isoformat()}.pdf")
    uit.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(uit), pagesize=(PAGE_W, PAGE_H_COVER))
    c.setTitle(f"Weekplanner week {wn}")
    c.setAuthor("remarkable-skills")

    draw_voorblad(c, maandag, cover_image_path=a.cover_image)
    c.showPage()
    for i in range(5):
        d = maandag + timedelta(days=i)
        draw_dagplanning(c, d, agenda, doelen)
        c.showPage()
        draw_dagboek(c, d)
        c.showPage()
    draw_weekend(c, maandag)
    c.showPage()
    c.save()
    stand = "staand" if ORIENTATION == "portrait" else "liggend"
    print(f"Klaar: {uit} (12 pagina's, week {wn}, {stand})")


if __name__ == "__main__":
    main()
