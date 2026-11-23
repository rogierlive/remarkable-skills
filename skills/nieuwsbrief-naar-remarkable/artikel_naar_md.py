#!/usr/bin/env python3
"""Zet een artikel of nieuwsbrief om naar een leesgids in markdown.

Gebruik:
  artikel_naar_md.py <url | bestand.html | bestand.txt | -> uit.md [--titel "..."]

Een "-" leest tekst uit stdin (plak je tekst, of pipe hem erin).
Koppen (h1/h2/h3) worden hoofdstukken. Zonder koppen wordt het een hoofdstuk.
"""
import argparse, html, os, re, sys, urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Module 'beautifulsoup4' ontbreekt. Zie de README, stap 3 (venv).")

MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]


def haal_op(bron):
    if bron == "-":
        return sys.stdin.read(), ""
    if re.match(r"^https?://", bron):
        req = urllib.request.Request(bron, headers={"User-Agent": "Mozilla/5.0 (leesgids)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
        return data.decode(enc, errors="replace"), urlparse(bron).netloc
    return Path(bron).read_text(errors="replace"), "opgeslagen bestand"


def schoon(t):
    t = t.replace("\u2014", " - ").replace("\u2013", "-")  # geen em-dashes
    return re.sub(r"\s+", " ", t).strip()


_MD_TEKENS = re.compile(r"([\\`*_{}\[\]()#+!|])")


def veilig(t):
    """Tekst van buiten (een webpagina, een mail) is onbetrouwbaar. Maak er platte
    tekst van: HTML-tekens worden &lt; &gt; &amp; en markdown-tekens krijgen een
    backslash. Zo kan een pagina geen script, iframe, afbeelding of link in je
    leesgids smokkelen."""
    return _MD_TEKENS.sub(r"\\\1", html.escape(t, quote=True))


def uit_html(raw):
    soup = BeautifulSoup(raw, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header", "form", "aside", "noscript", "svg", "iframe"]):
        t.decompose()
    titel = ""
    if soup.title and soup.title.string:
        titel = schoon(soup.title.string)
    h1 = soup.find("h1")
    if h1 and schoon(h1.get_text()):
        titel = schoon(h1.get_text())
    root = soup.find("article") or soup.find("main") or soup.body or soup
    blokken = []  # (soort, tekst)
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
        if el.name == "li" and el.find_parent("blockquote"):
            continue
        if el.name == "p" and el.find_parent(["li", "blockquote"]):
            continue
        tekst = schoon(el.get_text(" "))
        if not tekst or tekst == titel:
            continue
        blokken.append((el.name, tekst))
    return titel, blokken


def uit_tekst(raw):
    blokken = []
    for deel in re.split(r"\n\s*\n", raw.strip()):
        regel = schoon(deel)
        if regel:
            blokken.append(("p", regel))
    titel = ""
    if blokken and len(blokken[0][1]) < 100:
        titel = blokken.pop(0)[1]
    return titel, blokken


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bron")
    ap.add_argument("uit")
    ap.add_argument("--titel", default="")
    a = ap.parse_args()

    raw, site = haal_op(a.bron)
    if re.search(r"<(p|h1|h2|article|div)[ >]", raw, re.I):
        titel, blokken = uit_html(raw)
    else:
        titel, blokken = uit_tekst(raw)
    titel = a.titel or titel or "Artikel"
    if len(blokken) < 1:
        sys.exit("Ik vond geen leesbare tekst in deze bron.")

    # Hoofdstukken op h1/h2
    hoofdstukken, huidig = [], None
    for soort, tekst in blokken:
        if soort in ("h1", "h2"):
            huidig = [tekst, []]
            hoofdstukken.append(huidig)
        else:
            if huidig is None:
                huidig = [titel if len(hoofdstukken) == 0 else "Verder", []]
                hoofdstukken.append(huidig)
            huidig[1].append((soort, tekst))
    hoofdstukken = [h for h in hoofdstukken if h[1]] or [[titel, []]]

    nu = date.today()
    datum_nl = f"{nu.day} {MAANDEN[nu.month - 1]} {nu.year}"
    woorden = sum(len(t.split()) for _, t in blokken)
    minuten = max(1, round(woorden / 200))
    bron_regel = site or "geplakte tekst"

    titel_fm = titel.replace('"', "'")  # build.py escapet de titel zelf voor HTML
    titel_html = html.escape(titel, quote=True)  # binnen een HTML-blok: alleen HTML-escape
    md = [f'---\ntitel: "{titel_fm}"\ndatum: {nu.isoformat()}\n---\n']
    md.append('<div class="cover" markdown="1">\n\n<div class="kicker">Leesgids voor {naam}</div>\n')
    md.append(f'<div class="title">{titel_html}</div>\n')
    md.append(f'<div class="sub">Bron: {html.escape(bron_regel)}</div>\n')
    md.append(f'<div class="date">{datum_nl}</div>\n')
    md.append(f'<div class="box" markdown="1">\n\n**Zo lees je deze gids**\n\nLezen duurt ongeveer {minuten} {"minuut" if minuten == 1 else "minuten"}. Schrijf gerust in de kantlijn.\n\n</div>\n\n</div>\n')
    md.append('<div class="pb"></div>\n')
    md.append('<div class="toc" markdown="1">\n\n## Inhoud\n\n| | | |\n|---|---|---|')
    for i, (naam, _) in enumerate(hoofdstukken, 1):
        md.append(f"| {i} | {veilig(naam)} | {{p{i}}} |")
    md.append("| | Bronnen | {pb} |\n\n</div>\n")
    for i, (naam, items) in enumerate(hoofdstukken, 1):
        md.append('<div class="pb"></div>\n')
        md.append(f"## {i}. {veilig(naam)}\n")
        for soort, tekst in items:
            if soort in ("h3", "h4"):
                md.append(f"### {veilig(tekst)}\n")
            elif soort == "li":
                md.append(f"- {veilig(tekst)}")
            elif soort == "blockquote":
                md.append(f'\n<div class="quote" markdown="1">\n\n{veilig(tekst)}\n\n</div>\n')
            else:
                md.append(f"\n{veilig(tekst)}\n")
        md.append("")
    md.append('<div class="pb"></div>\n\n## Bronnen\n')
    md.append(f"- {veilig(a.bron if re.match(r'^https?://', a.bron) else bron_regel)}")
    md.append(f"- Opgehaald op {datum_nl}.")
    Path(a.uit).write_text("\n".join(md) + "\n")
    print(f"Markdown klaar: {a.uit} ({len(hoofdstukken)} hoofdstuk(ken), ~{minuten} min lezen)")


if __name__ == "__main__":
    main()
