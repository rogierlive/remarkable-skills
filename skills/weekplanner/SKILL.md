---
name: weekplanner
description: Maakt een weekplanner-PDF voor de reMarkable (14 pagina's): voorpagina, weekoverzicht, per dag een dagpagina met agenda per uur en een notitiepagina, plus weekreview en weekend, met 3 weekdoelen. De agenda komt uit een Google Agenda (geheim iCal-adres) of een .ics-bestand. Gebruik bij "maak mijn weekplanner", "weekplanner voor volgende week", "zet mijn week op de reMarkable".
---

# Weekplanner voor je reMarkable

Een planner in 4:3 formaat (zoals het reMarkable-scherm). Veertien pagina's:

1. **Voorpagina**: rustige cover met weeknummer, datums en (optioneel) je naam. Wil je een eigen afbeelding? Zet `WEEKPLANNER_COVER=/pad/naar/foto.jpg` of geef `--cover-image` mee.
2. **Weekoverzicht**: je 3 weekdoelen met afvinkrondjes en alle dagen met hun afspraken.
3. **Maandag t/m vrijdag, twee pagina's per dag**:
   - *Dagpagina*: links je agenda per uur (05:00-23:00) met een kader om de werkdag (05:00-17:00) voor timeboxing, rechts je weekdoelen, drie prioriteiten met afvinkvakje en -rondjes, en schrijflijnen.
   - *Notitiepagina*: ruimte voor wins en vrije notities.
4. **Weekreview**: drie vragen met schrijfruimte.
5. **Weekend**: een open notitiepagina voor zaterdag en zondag.

## Wat het wel doet

- Leest een Google Agenda via het geheime iCal-adres, of een `.ics`-bestand.
- Snapt terugkerende afspraken en hele-dag-afspraken.
- Toont 3 weekdoelen op de weekpagina en op elke dagpagina.
- Heeft een eigen rustige cover, of jouw afbeelding.
- Haalt emoji uit titels weg, zodat er geen lege vakjes in de PDF komen.

## Wat het niet doet (bewust simpel)

Geen quotes, geen klantenteller of jaardoel-bolletjes, geen koppeling met taken- of CRM-systemen, geen automatische taak elke vrijdag. Zie "Extra opties".

## Zo gebruik je het

1. Haal de gegevens op. Vraag de gebruiker, als het niet in `~/.remarkable-skills.env` staat:
   - **Weekdoelen**: drie doelen voor deze week. Zet ze in `WEEKPLANNER_DOELEN` (gescheiden door `|`) of geef ze mee met `--doelen`.
   - **Agenda**: het geheime iCal-adres (`WEEKPLANNER_ICAL_URL`) of een `.ics`-bestand (`--ics`).
2. Welke week? Standaard is dat de komende week (vanaf vrijdag) of de huidige week. Wil de gebruiker een andere week? Geef `--week-start JJJJ-MM-DD` (een maandag).
3. Maak de PDF:

```bash
bash <pad-naar-skill>/maak.sh --doelen "Doel een|Doel twee|Doel drie"
bash <pad-naar-skill>/maak.sh --ics "/pad/naar/agenda.ics" --week-start 2026-11-30
```

4. Naar de reMarkable sturen? Alleen als de gebruiker dat vraagt. Voeg dan `--sturen` toe:

```bash
bash <pad-naar-skill>/maak.sh --sturen
```

## Het geheime iCal-adres vinden (Google Agenda)

1. Open Google Agenda in je browser, op een computer.
2. Klik op het tandwiel, dan op Instellingen.
3. Kies links je agenda onder "Instellingen voor mijn agenda's".
4. Scroll naar "Geheim adres in iCal-indeling" en kopieer dat adres.
5. Plak het in `~/.remarkable-skills.env` achter `WEEKPLANNER_ICAL_URL=`.

Dit adres is als een wachtwoord. Deel het niet en zet het niet in een publieke repo. Claude: toon of herhaal dit adres nooit in je antwoord, en geef het niet mee met `--ical-url` op de commandoregel. Laat het in het instellingenbestand staan.

## Extra opties (op aanvraag)

Wil je meer dan dit? Dit kan allemaal op aanvraag:

- quotes op de dagpagina's;
- een klantenteller of andere cijfers (KPI's) op de weekpagina;
- eigen covers, met een eigen foto of huisstijl;
- automatisch elke vrijdag een nieuwe planner op je reMarkable, via een geplande taak.

Wil je dit ook? Stuur Rogier een appje via rogier.live.
