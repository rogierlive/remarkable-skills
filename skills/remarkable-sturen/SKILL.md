---
name: remarkable-sturen
description: Stuurt een PDF naar de reMarkable van de gebruiker via rmapi. Gebruik bij "stuur dit naar mijn reMarkable", "zet dit op mijn reMarkable", "upload deze pdf naar de remarkable". De map op de reMarkable is optioneel.
---

# PDF naar je reMarkable sturen

Deze skill zet een PDF-bestand in de reMarkable Cloud. Op je tablet verschijnt het na een sync.

## Wat je nodig hebt

- `rmapi` is geïnstalleerd en gekoppeld (zie de README van deze repo).
- Een PDF-bestand op de computer.

## Zo gebruik je het

1. Zoek het PDF-bestand. Weet je het pad niet? Vraag het de gebruiker.
2. Vraag niet naar een map, tenzij de gebruiker er zelf over begint. De standaardmap staat in `~/.remarkable-skills.env` als `REMARKABLE_MAP`.
3. Draai het script:

```bash
bash <pad-naar-skill>/sturen.sh "/pad/naar/bestand.pdf" "/Optionele map"
```

4. Wil je eerst testen zonder te uploaden? Gebruik `--dry-run` voor het bestandspad:

```bash
bash <pad-naar-skill>/sturen.sh --dry-run "/pad/naar/bestand.pdf"
```

## Regels

- Stuur nooit iets naar de reMarkable zonder dat de gebruiker erom vroeg.
- Bestaat een bestand met dezelfde naam al? Dan wordt het overschreven. Zeg dat erbij als je het weet.
- Komt er een fout over inloggen? Laat de gebruiker `rmapi` eenmalig in de terminal draaien en een nieuwe code van my.remarkable.com invullen.
- Wil je eerst een mooie leesbare PDF maken van tekst? Gebruik dan de skill `remarkable-briefing`.
