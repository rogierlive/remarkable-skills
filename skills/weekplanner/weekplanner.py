#!/usr/bin/env python3
"""Weekplanner voor je reMarkable (4:3 formaat, PDF, 14 paginas).

Opbouw: voorpagina, weekoverzicht, dan per werkdag een dagpagina (agenda per uur
met een kader om de werkdag, je weekdoelen en drie prioriteiten) met een
notitiepagina erachter, en tot slot een weekreview en een weekendpagina.

Voorbeelden:
  python3 weekplanner.py --ics ../../examples/demo-agenda.ics --doelen "Offerte sturen|Twee keer sporten|Tuin opruimen"
  python3 weekplanner.py --cover-image mijn-foto.jpg --ics agenda.ics
  python3 weekplanner.py --ical-url "https://calendar.google.com/.../basic.ics"
  python3 weekplanner.py            # leest alles uit ~/.remarkable-skills.env
"""
import argparse, os, re, sys, urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, Color
    from reportlab.lib.utils import ImageReader
except ImportError:
    sys.exit("reportlab ontbreekt. Zie de README, stap 3 (venv).")

PAGE_W, PAGE_H = 595.276, 793.7          # 4:3, zoals het reMarkable-scherm
MARGE = 40
L1, L2 = 39.685, 291.969                  # linkerkolom (agenda)
R1, R2 = 314.646, 566.929                 # rechterkolom (doelen, prioriteiten)
DAGEN = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
           "september", "oktober", "november", "december"]
INK, GRIJS, LICHT = HexColor("#1a1a1a"), HexColor("#666666"), HexColor("#aaaaaa")
ZEER_LICHT, GROEN = HexColor("#dddddd"), HexColor("#799a7c")
WIT = HexColor("#ffffff")
UUR_START, UUR_EIND = 5, 23               # raster van 05:00 tot 23:00
KADER_START, KADER_EIND = 5, 17           # kader voor timeboxing (de werkdag)
BAND = 28.27                              # lijnafstand voor schrijfruimte

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF"
                    "\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0000200D]+")


def schoon(t):
    """Helvetica kent geen emoji of em-dash: haal ze weg zodat er geen vakjes komen."""
    t = _EMOJI.sub("", str(t or "")).replace("\u2014", "-").replace("\u2013", "-")
    t = t.encode("latin-1", "ignore").decode("latin-1")
    return re.sub(r"\s{2,}", " ", t).strip()


BEKENDE_KEYS = {"REMARKABLE_NAAM", "REMARKABLE_MAP", "REMARKABLE_BROWSER", "REMARKABLE_PYTHON",
                "WEEKPLANNER_ICAL_URL", "WEEKPLANNER_DOELEN", "WEEKPLANNER_MAP", "WEEKPLANNER_TZ",
                "WEEKPLANNER_COVER"}


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
                    if k in BEKENDE_KEYS:
                        os.environ.setdefault(k, v)
            return


def lees_agenda(ics_pad, url, maandag, tz):
    """Geeft {datum: {'hele_dag': [titels], 'afspraken': [(start, eind, titel)]}}."""
    if not ics_pad and not url:
        return {}
    import icalendar, recurring_ical_events
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
    uit = {maandag + timedelta(days=i): {"hele_dag": [], "afspraken": []} for i in range(7)}
    for ev in recurring_ical_events.of(cal).between(van, tot):
        titel = schoon(ev.get("SUMMARY")) or "(zonder titel)"
        s, e = ev["DTSTART"].dt, ev.get("DTEND").dt if ev.get("DTEND") else None
        if not isinstance(s, datetime):                      # hele dag
            eind = e if isinstance(e, date) else s + timedelta(days=1)
            d = s
            while d < eind:
                if d in uit:
                    uit[d]["hele_dag"].append(titel)
                d += timedelta(days=1)
            continue
        s = s.astimezone(tz) if s.tzinfo else s.replace(tzinfo=tz)
        e = (e.astimezone(tz) if e.tzinfo else e.replace(tzinfo=tz)) if isinstance(e, datetime) else s + timedelta(hours=1)
        if s.date() in uit:
            uit[s.date()]["afspraken"].append((s, max(e, s + timedelta(minutes=15)), titel))
    for v in uit.values():
        v["afspraken"].sort(key=lambda x: x[0])
    return uit


def kort(c, tekst, font, maat, breedte):
    """Kap een tekst af zodat hij in de breedte past."""
    if c.stringWidth(tekst, font, maat) <= breedte:
        return tekst
    while tekst and c.stringWidth(tekst + "...", font, maat) > breedte:
        tekst = tekst[:-1]
    return tekst.rstrip() + "..."


def gespatieerd(c, tekst, x, y, font, maat, em=0.25):
    """Tekst met extra letterafstand. Geeft de breedte terug."""
    c.setFont(font, maat)
    extra, cx = maat * em, x
    for ch in tekst:
        c.drawString(cx, y, ch)
        cx += c.stringWidth(ch, font, maat) + extra
    return cx - x - extra


def midden(c, tekst, y, font, maat, em=0.0):
    c.setFont(font, maat)
    w = sum(c.stringWidth(ch, font, maat) + maat * em for ch in tekst) - maat * em
    gespatieerd(c, tekst, (PAGE_W - w) / 2, y, font, maat, em)


def lijn(c, x1, y, x2, kleur=INK, dik=0.75):
    c.setStrokeColor(kleur); c.setLineWidth(dik); c.line(x1, y, x2, y)


def schrijflijnen(c, x1, x2, y_top, y_bodem, kleur=LICHT, band=BAND, dik=0.5):
    """Vult het vlak met schrijflijnen. Geeft de y van de laatste lijn terug."""
    y = y_top - band
    while y >= y_bodem - 1:
        lijn(c, x1, y, x2, kleur, dik)
        y -= band
    return y + band


def titel(c, tekst):
    """Paginakop: gecentreerd, met groene lijn eronder."""
    c.setFillColor(INK); midden(c, tekst, PAGE_H - 46, "Courier-Bold", 11)
    lijn(c, MARGE, PAGE_H - 55, PAGE_W - MARGE, GROEN, 1.0)


def kopje(c, x1, x2, y, tekst, groen=False):
    c.setFillColor(INK); c.setFont("Courier-Bold", 9); c.drawString(x1, y, tekst)
    lijn(c, x1, y - 8, x2, GROEN if groen else INK, 0.75)


def spoor(c, y, x2=R2):
    """Voortgangsspoor: vakje, zes afvinkrondjes, vakje (rechts uitgelijnd)."""
    box, r, stap = 11, 5.5, 18
    x0 = x2 - (7 * stap + box)
    c.setStrokeColor(GROEN); c.setFillColor(WIT); c.setLineWidth(0.9)
    c.rect(x0, y, box, box, fill=1, stroke=1)
    for i in range(6):
        c.circle(x0 + box + stap / 2 + i * stap, y + box / 2, r, fill=1, stroke=1)
    c.rect(x2 - box, y, box, box, fill=1, stroke=1)


def doelen_lijst(c, x1, x2, y, doelen, maat=9.5, rij=22):
    """Drie weekdoelen met een afvinkrondje. Geeft de y onder het blok terug."""
    for i in range(3):
        y -= rij
        c.setStrokeColor(GROEN); c.setFillColor(WIT); c.setLineWidth(0.9)
        c.circle(x1 + 5, y + 3, 5, fill=1, stroke=1)
        t = schoon(doelen[i]) if i < len(doelen) else ""
        if t:
            c.setFillColor(INK); c.setFont("Helvetica", maat)
            c.drawString(x1 + 17, y, kort(c, t, "Helvetica", maat, x2 - x1 - 17))
        else:
            lijn(c, x1 + 17, y - 2, x2, LICHT, 0.5)
    return y - 8


def voorpagina(c, maandag, naam, cover):
    weeknr = maandag.isocalendar()[1]
    zondag = maandag + timedelta(days=6)
    foto = False
    if cover and Path(cover).is_file():
        try:
            img = ImageReader(str(cover))
            iw, ih = img.getSize()
            s = max(PAGE_W / iw, PAGE_H / ih)
            c.drawImage(img, (PAGE_W - iw * s) / 2, (PAGE_H - ih * s) / 2, iw * s, ih * s, mask="auto")
            foto = True
        except Exception:
            print("Let op: je coverafbeelding kon niet worden gelezen. Er komt een rustige cover.", file=sys.stderr)
    if foto:
        stappen, hoogte = 60, 260
        for i in range(stappen):
            c.setFillColor(Color(0, 0, 0, alpha=(i / stappen) ** 1.4 * 0.62))
            c.rect(0, hoogte * (1 - i / stappen) - hoogte / stappen, PAGE_W, hoogte / stappen + 0.6, fill=1, stroke=0)
        kleur, sub = WIT, WIT
        y_week, y_nr, y_lijn, y_dat, y_naam = 190, 112, 90, 52, 30
    else:
        c.setFillColor(HexColor("#fafaf7")); c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        c.setStrokeColor(GROEN); c.setLineWidth(1.0)
        c.rect(MARGE, MARGE, PAGE_W - 2 * MARGE, PAGE_H - 2 * MARGE, fill=0, stroke=1)
        c.rect(MARGE + 6, MARGE + 6, PAGE_W - 2 * MARGE - 12, PAGE_H - 2 * MARGE - 12, fill=0, stroke=1)
        kleur, sub = INK, GRIJS
        y_week, y_nr, y_lijn, y_dat, y_naam = 470, 380, 350, 315, 280
    c.setFillColor(kleur); midden(c, "WEEK", y_week, "Courier-Bold", 10, 0.5)
    c.setFillColor(kleur); midden(c, str(weeknr), y_nr, "Courier-Bold", 56)
    cx = PAGE_W / 2
    lijn(c, cx - 57, y_lijn, cx + 57, GROEN, 1.5)
    c.setFillColor(kleur)
    midden(c, f"{maandag.day} {MAANDEN[maandag.month-1]} - {zondag.day} {MAANDEN[zondag.month-1]} {zondag.year}",
           y_dat, "Courier", 13, 0.1)
    if naam:
        c.setFillColor(sub); midden(c, schoon(naam).upper(), y_naam, "Courier", 9, 0.3)
    c.showPage()


def weekpagina(c, maandag, agenda, doelen):
    weeknr = maandag.isocalendar()[1]
    zondag = maandag + timedelta(days=6)
    titel(c, f"WEEK {weeknr} - {maandag.day} {MAANDEN[maandag.month-1].upper()} T/M "
             f"{zondag.day} {MAANDEN[zondag.month-1].upper()}")
    y = PAGE_H - 84
    kopje(c, MARGE, PAGE_W - MARGE, y, "WEEKDOELEN", groen=True)
    y = doelen_lijst(c, MARGE, PAGE_W - MARGE, y - 8, doelen, maat=11, rij=26)
    y -= 26
    kopje(c, MARGE, PAGE_W - MARGE, y, "DEZE WEEK")
    top0, onder = y - 8, MARGE + 8
    hoogte = (top0 - onder) / 7
    for i in range(7):
        d = maandag + timedelta(days=i)
        top = top0 - i * hoogte
        lijn(c, MARGE, top - hoogte, PAGE_W - MARGE, LICHT, 0.5)
        c.setFillColor(INK); c.setFont("Courier-Bold", 9.5); c.drawString(MARGE, top - 15, DAGEN[i].upper())
        c.setFont("Courier", 8); c.setFillColor(GRIJS)
        c.drawString(MARGE, top - 27, f"{d.day} {MAANDEN[d.month-1]}")
        dag = agenda.get(d, {})
        regels = [("", t) for t in dag.get("hele_dag", [])]
        regels += [(s.strftime("%H:%M"), t) for s, _, t in dag.get("afspraken", [])]
        maxr = max(1, int((hoogte - 6) // 12))
        for j, (tijd, tekst) in enumerate(regels[:maxr]):
            yy = top - 14 - j * 12
            if j == maxr - 1 and len(regels) > maxr:
                c.setFillColor(GRIJS); c.setFont("Helvetica", 9)
                c.drawString(MARGE + 100, yy, f"+ {len(regels) - maxr + 1} meer")
                break
            c.setFillColor(GRIJS); c.setFont("Helvetica", 9); c.drawString(MARGE + 100, yy, tijd)
            c.setFillColor(INK)
            c.drawString(MARGE + 135, yy, kort(c, tekst, "Helvetica", 9, PAGE_W - 2 * MARGE - 135))
    c.showPage()


def dagpagina(c, d, agenda, doelen):
    dag = agenda.get(d, {"hele_dag": [], "afspraken": []})
    titel(c, f"{DAGEN[d.weekday()].upper()} - {d.day} {MAANDEN[d.month-1].upper()}")
    y_hd = PAGE_H - 70
    if dag["hele_dag"]:
        c.setFillColor(INK); c.setFont("Helvetica", 9)
        c.drawString(L1, y_hd, kort(c, "Hele dag: " + ", ".join(dag["hele_dag"]), "Helvetica", 9, PAGE_W - 2 * MARGE))
    boven = PAGE_H - 84                      # bovenkant van het uurraster
    onder = 54
    uren = UUR_EIND - UUR_START
    rij = (boven - onder) / uren
    per_uur = {}
    for s, e, t in dag["afspraken"]:
        h = max(UUR_START, min(UUR_EIND - 1, s.hour))
        eind = f"-{e.strftime('%H:%M')}" if e.date() == s.date() else ""
        per_uur.setdefault(h, []).append((s.strftime("%H:%M") + eind, t))
    for i in range(uren):
        uur = UUR_START + i
        top = boven - i * rij
        c.setFillColor(GRIJS); c.setFont("Courier", 7.5); c.drawString(L1 + 3, top - 8, f"{uur:02d}:00")
        lijn(c, L1, top - 10, L2, LICHT, 0.5)
        ev = per_uur.get(uur, [])
        maxr = max(1, int((rij - 12) // 11) + 1)
        for j, (tijd, t) in enumerate(ev[:maxr]):
            yy = top - 6.5 - j * 11
            if j == maxr - 1 and len(ev) > maxr:
                c.setFillColor(GRIJS); c.setFont("Helvetica", 9); c.drawString(L1 + 46, yy, f"+ {len(ev) - maxr + 1} meer")
                break
            c.setFillColor(INK); c.setFont("Helvetica", 9)
            c.drawString(L1 + 46, yy, kort(c, f"{tijd} {t}", "Helvetica", 9, L2 - L1 - 50))
    # Kader om de werkdag (timeboxing): van de 05:00-lijn tot de 17:00-lijn.
    k_top = boven - (KADER_START - UUR_START) * rij - 10
    k_bot = boven - (KADER_EIND - UUR_START) * rij - 10
    c.setStrokeColor(INK); c.setLineWidth(1.5)
    c.rect(L1, k_bot, L2 - L1, k_top - k_bot, fill=0, stroke=1)

    # Rechterkolom: weekdoelen, drie prioriteiten met voortgangsspoor, schrijflijnen.
    y = boven - 2
    kopje(c, R1, R2, y, "WEEKDOELEN", groen=True)
    y = doelen_lijst(c, R1, R2, y - 8, doelen, maat=9.5, rij=21)
    y -= 20
    kopje(c, R1, R2, y, "VANDAAG")
    y -= 14
    for n in (1, 2, 3):
        y1, y2 = y - 22, y - 22 - 26
        c.setFillColor(HexColor("#888888")); c.setFont("Courier", 7.5); c.drawString(R1, y1 + 2, str(n))
        nb = c.stringWidth(str(n), "Courier", 7.5) + R1 + 4
        lijn(c, nb, y1, R2, HexColor("#888888"), 0.75)
        lijn(c, R1, y2, R2, HexColor("#888888"), 0.75)
        spoor(c, y2 - 3 - 11)
        y = y2 - 3 - 11 - 6
    y -= 6
    schrijflijnen(c, R1, R2, y, onder, ZEER_LICHT, 20)
    c.showPage()


def notitiepagina(c, d):
    titel(c, f"NOTITIES - {DAGEN[d.weekday()].upper()} {d.day} {MAANDEN[d.month-1].upper()}")
    y = PAGE_H - 84
    kopje(c, MARGE, PAGE_W - MARGE, y, "WINS", groen=True)
    y = schrijflijnen(c, MARGE, PAGE_W - MARGE, y - 8, y - 8 - 4 * BAND)
    y -= 26
    kopje(c, MARGE, PAGE_W - MARGE, y, "NOTITIES")
    schrijflijnen(c, MARGE, PAGE_W - MARGE, y - 8, 24)
    c.showPage()


def reviewpagina(c, maandag):
    titel(c, f"WEEKREVIEW - WEEK {maandag.isocalendar()[1]}")
    y = PAGE_H - 84
    for kop in ("WAT GING GOED", "WAT LEERDE IK", "WAT NEEM IK MEE NAAR VOLGENDE WEEK"):
        kopje(c, MARGE, PAGE_W - MARGE, y, kop, groen=True)
        y = schrijflijnen(c, MARGE, PAGE_W - MARGE, y - 8, y - 8 - 6 * BAND)
        y -= 30
    schrijflijnen(c, MARGE, PAGE_W - MARGE, y + 20, 24)
    c.showPage()


def weekendpagina(c, maandag):
    za, zo = maandag + timedelta(days=5), maandag + timedelta(days=6)
    titel(c, f"WEEKEND - {za.day} {MAANDEN[za.month-1].upper()} / {zo.day} {MAANDEN[zo.month-1].upper()}")
    schrijflijnen(c, MARGE, PAGE_W - MARGE, PAGE_H - 62, 24)
    c.showPage()


def standaard_maandag(vandaag):
    """Maandag van de komende week als het vrijdag t/m zondag is, anders van deze week."""
    m = vandaag - timedelta(days=vandaag.weekday())
    return m + timedelta(days=7) if vandaag.weekday() >= 4 else m


def main():
    laad_env()
    ap = argparse.ArgumentParser(description="Maak een weekplanner-PDF voor je reMarkable.")
    ap.add_argument("--week-start", help="Maandag van de week, JJJJ-MM-DD (standaard: komende of huidige week)")
    ap.add_argument("--ics", help="Pad naar een .ics-bestand")
    ap.add_argument("--ical-url", default=os.environ.get("WEEKPLANNER_ICAL_URL", ""), help="Geheim iCal-adres van je Google Agenda")
    ap.add_argument("--doelen", default=os.environ.get("WEEKPLANNER_DOELEN", ""), help='3 weekdoelen, gescheiden door |')
    ap.add_argument("--naam", default=os.environ.get("REMARKABLE_NAAM", ""))
    ap.add_argument("--cover-image", default=os.environ.get("WEEKPLANNER_COVER", ""),
                    help="Eigen afbeelding voor de voorpagina (optioneel)")
    ap.add_argument("--tz", default=os.environ.get("WEEKPLANNER_TZ", "Europe/Amsterdam"))
    ap.add_argument("--output", "-o", help="Pad van de PDF")
    a = ap.parse_args()

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
        sys.exit(f"Ik kon je agenda niet lezen ({type(ex).__name__}: {reden}). Controleer WEEKPLANNER_ICAL_URL of je .ics-bestand.")
    if not a.ics and not a.ical_url:
        print("Let op: geen agenda opgegeven. Je krijgt een lege planner.", file=sys.stderr)

    uit = Path(a.output or f"uitvoer/weekplanner-week{maandag.isocalendar()[1]:02d}-{maandag.isoformat()}.pdf")
    uit.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(uit), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Weekplanner week {maandag.isocalendar()[1]}")
    voorpagina(c, maandag, a.naam, a.cover_image)
    weekpagina(c, maandag, agenda, doelen)
    for i in range(5):
        d = maandag + timedelta(days=i)
        dagpagina(c, d, agenda, doelen)
        notitiepagina(c, d)
    reviewpagina(c, maandag)
    weekendpagina(c, maandag)
    c.save()
    print(f"Klaar: {uit} (14 paginas, week {maandag.isocalendar()[1]})")


if __name__ == "__main__":
    main()
