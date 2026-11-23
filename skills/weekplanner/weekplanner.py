#!/usr/bin/env python3
"""Simpele weekplanner voor je reMarkable (4:3 formaat, PDF).

Bevat een weekoverzicht en een pagina per dag met je agenda per uur.
Bovenaan elke pagina staan je weekdoelen.

Voorbeelden:
  python3 weekplanner.py --ics ../../examples/demo-agenda.ics --doelen "Offerte sturen|Twee keer sporten|Tuin opruimen"
  python3 weekplanner.py --ical-url "https://calendar.google.com/.../basic.ics"
  python3 weekplanner.py            # leest alles uit ~/.remarkable-skills.env
"""
import argparse, os, re, sys, urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
except ImportError:
    sys.exit("reportlab ontbreekt. Zie de README, stap 3 (venv).")

PAGE_W, PAGE_H = 595.276, 793.7          # 4:3, zoals het reMarkable-scherm
MARGE = 40
DAGEN = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
           "september", "oktober", "november", "december"]
INK, GRIJS, LICHT = HexColor("#000000"), HexColor("#666666"), HexColor("#BBBBBB")
UUR_START, UUR_EIND = 7, 22               # raster van 07:00 tot 22:00

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF"
                    "\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0000200D]+")


def schoon(t):
    """Helvetica kent geen emoji of em-dash: haal ze weg zodat er geen vakjes komen."""
    t = _EMOJI.sub("", str(t or "")).replace("\u2014", "-").replace("\u2013", "-")
    t = t.encode("latin-1", "ignore").decode("latin-1")
    return re.sub(r"\s{2,}", " ", t).strip()


BEKENDE_KEYS = {"REMARKABLE_NAAM", "REMARKABLE_MAP", "REMARKABLE_BROWSER", "REMARKABLE_PYTHON",
                "WEEKPLANNER_ICAL_URL", "WEEKPLANNER_DOELEN", "WEEKPLANNER_MAP", "WEEKPLANNER_TZ"}


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


def doelen_blok(c, y, doelen, titel="Weekdoelen", klein=False):
    """Tekent de weekdoelen met afvinkvakjes. Geeft de nieuwe y terug."""
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 9 if klein else 11)
    c.drawString(MARGE, y, titel.upper())
    y -= 6 if klein else 8
    c.setStrokeColor(INK); c.setLineWidth(0.8); c.line(MARGE, y, PAGE_W - MARGE, y)
    y -= 4 if klein else 6
    rij = 17 if klein else 26
    for i in range(3):
        y -= rij - (2 if klein else 4)
        t = schoon(doelen[i]) if i < len(doelen) else ""
        c.setStrokeColor(INK); c.setLineWidth(0.8)
        c.rect(MARGE, y - 1, 9 if klein else 12, 9 if klein else 12, stroke=1, fill=0)
        c.setFont("Helvetica", 10 if klein else 13); c.setFillColor(INK)
        if t:
            c.drawString(MARGE + (16 if klein else 20), y, kort(c, t, "Helvetica", 10 if klein else 13, PAGE_W - 2 * MARGE - 24))
        else:
            c.setStrokeColor(LICHT); c.setLineWidth(0.5)
            c.line(MARGE + 20, y - 2, PAGE_W - MARGE, y - 2)
        y -= 4 if not klein else 0
    return y - (6 if klein else 4)


def weekpagina(c, maandag, agenda, doelen, naam):
    weeknr = maandag.isocalendar()[1]
    zondag = maandag + timedelta(days=6)
    y = PAGE_H - MARGE - 6
    c.setFillColor(GRIJS); c.setFont("Helvetica", 10)
    c.drawString(MARGE, y, (f"WEEKPLANNER VOOR {schoon(naam).upper()}" if naam else "WEEKPLANNER"))
    y -= 36
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 34)
    c.drawString(MARGE, y, f"Week {weeknr}")
    c.setFont("Helvetica", 12); c.setFillColor(GRIJS)
    c.drawRightString(PAGE_W - MARGE, y + 4,
                      f"{maandag.day} {MAANDEN[maandag.month-1]} - {zondag.day} {MAANDEN[zondag.month-1]} {zondag.year}")
    y -= 34
    y = doelen_blok(c, y, doelen, "Weekdoelen")
    y -= 14
    # Overzicht per dag
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGE, y, "DEZE WEEK"); y -= 8
    c.setStrokeColor(INK); c.setLineWidth(0.8); c.line(MARGE, y, PAGE_W - MARGE, y)
    onder = MARGE + 10
    hoogte = (y - onder) / 7
    for i in range(7):
        d = maandag + timedelta(days=i)
        top = y - i * hoogte
        c.setStrokeColor(LICHT); c.setLineWidth(0.5); c.line(MARGE, top - hoogte, PAGE_W - MARGE, top - hoogte)
        c.setFillColor(INK); c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGE, top - 15, DAGEN[i])
        c.setFont("Helvetica", 9); c.setFillColor(GRIJS)
        c.drawString(MARGE, top - 27, f"{d.day} {MAANDEN[d.month-1]}")
        regels = [("", t) for t in agenda.get(d, {}).get("hele_dag", [])]
        regels += [(s.strftime("%H:%M"), t) for s, _, t in agenda.get(d, {}).get("afspraken", [])]
        maxr = max(1, int((hoogte - 6) // 12))
        c.setFillColor(INK); c.setFont("Helvetica", 9)
        for j, (tijd, titel) in enumerate(regels[:maxr]):
            if j == maxr - 1 and len(regels) > maxr:
                c.setFillColor(GRIJS); c.drawString(MARGE + 90, top - 14 - j * 12, f"+ {len(regels) - maxr + 1} meer")
                break
            c.setFillColor(GRIJS); c.drawString(MARGE + 90, top - 14 - j * 12, tijd)
            c.setFillColor(INK)
            c.drawString(MARGE + 125, top - 14 - j * 12, kort(c, titel, "Helvetica", 9, PAGE_W - 2 * MARGE - 125))
    c.showPage()


def dagpagina(c, d, agenda, doelen):
    dag = agenda.get(d, {"hele_dag": [], "afspraken": []})
    y = PAGE_H - MARGE - 6
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 30)
    c.drawString(MARGE, y - 24, DAGEN[d.weekday()])
    c.setFont("Helvetica", 12); c.setFillColor(GRIJS)
    c.drawRightString(PAGE_W - MARGE, y - 20, f"{d.day} {MAANDEN[d.month-1]} {d.year}")
    y -= 40
    y = doelen_blok(c, y, doelen, "Weekdoelen", klein=True)
    # Hele-dag-strook
    if dag["hele_dag"]:
        c.setFont("Helvetica", 9); c.setFillColor(INK)
        c.drawString(MARGE, y - 6, kort(c, "Hele dag: " + ", ".join(dag["hele_dag"]), "Helvetica", 9, PAGE_W - 2 * MARGE))
        y -= 14
    # Uurraster
    boven = y - 6
    onder = MARGE + 8
    uren = UUR_EIND - UUR_START
    uurh = (boven - onder) / uren
    x0, x1 = MARGE + 38, PAGE_W - MARGE
    for i in range(uren + 1):
        yy = boven - i * uurh
        c.setStrokeColor(LICHT if i else INK); c.setLineWidth(0.5 if i else 0.8)
        c.line(x0, yy, x1, yy)
        if i < uren:
            c.setFillColor(GRIJS); c.setFont("Helvetica", 9)
            c.drawString(MARGE, yy - 10, f"{UUR_START + i:02d}:00")
            c.setStrokeColor(HexColor("#E3E3E3")); c.setLineWidth(0.3)
            c.line(x0, yy - uurh / 2, x1, yy - uurh / 2)
    c.setStrokeColor(LICHT); c.setLineWidth(0.5); c.line(x0, boven, x0, onder - 0)
    # Afspraken: overlappende naast elkaar
    items = []
    for s, e, t in dag["afspraken"]:
        sm = max(s.hour + s.minute / 60, UUR_START)
        em = min(e.hour + e.minute / 60 if e.date() == d else UUR_EIND, UUR_EIND)
        if em > sm:
            items.append([sm, em, t, s.strftime("%H:%M"), 0, 1])
    groep = []
    for it in items:                               # simpele kolomverdeling per overlap-groep
        if groep and it[0] >= max(g[1] for g in groep):
            _verdeel(groep); groep = []
        groep.append(it)
    _verdeel(groep)
    for sm, em, t, tijd, kol, n in items:
        w = (x1 - x0 - 4) / n
        xx = x0 + 2 + kol * w
        top, hoog = boven - (sm - UUR_START) * uurh, (em - sm) * uurh
        c.setFillColor(HexColor("#EDEDED")); c.setStrokeColor(INK); c.setLineWidth(0.8)
        c.rect(xx, top - hoog + 1, w - 3, hoog - 2, stroke=1, fill=1)
        c.setFillColor(INK)
        if hoog >= 26:
            c.setFont("Helvetica-Bold", 9); c.drawString(xx + 5, top - 12, kort(c, t, "Helvetica-Bold", 9, w - 14))
            c.setFont("Helvetica", 8); c.setFillColor(GRIJS); c.drawString(xx + 5, top - 22, tijd)
        else:
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(xx + 5, top - hoog / 2 - 3, kort(c, f"{tijd} {t}", "Helvetica-Bold", 8.5, w - 14))
    c.showPage()


def _verdeel(groep):
    kolommen = []
    for it in groep:
        for k, laatste in enumerate(kolommen):
            if it[0] >= laatste:
                kolommen[k] = it[1]; it[4] = k; break
        else:
            kolommen.append(it[1]); it[4] = len(kolommen) - 1
    for it in groep:
        it[5] = max(1, len(kolommen))


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
    weekpagina(c, maandag, agenda, doelen, a.naam)
    for i in range(7):
        dagpagina(c, maandag + timedelta(days=i), agenda, doelen)
    c.save()
    print(f"Klaar: {uit} (8 paginas, week {maandag.isocalendar()[1]})")


if __name__ == "__main__":
    main()
