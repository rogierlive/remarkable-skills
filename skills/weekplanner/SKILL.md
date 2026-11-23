---
name: weekplanner
description: Maakt een weekplanner-PDF voor de reMarkable (12 pagina's): voorpagina, per werkdag een dagpagina (agenda per uur, weekdoelen, vier prioriteiten, notities) en een dagboekpagina (ochtend en avond), plus een weekend-dagboek. De agenda komt uit Google Agenda of Outlook (via een iCal/ICS-link) of uit een .ics-bestand. Gebruik bij "maak mijn weekplanner", "weekplanner voor volgende week", "zet mijn week op de reMarkable".
---

# Weekplanner voor je reMarkable

Twaalf pagina's. De dag- en dagboekpagina's zijn extra lang: op je reMarkable scroll je er gewoon doorheen.

1. **Voorpagina**: rustige cover met weeknummer en datums. Wil je een eigen afbeelding? Zet `WEEKPLANNER_COVER=/pad/naar/foto.jpg` of geef `--cover-image` mee.
2. **Maandag t/m vrijdag, twee pagina's per dag**:
   - *Dagpagina*: links je agenda per uur (05:00-23:00), met een kader om de werkdag (05:00-17:00) voor timeboxing. Rechts "Deze week" met je weekdoelen, vier prioriteiten met afvinkrondjes, en kladlijnen. Onderaan ruimte voor notities.
   - *Dagboek*: OCHTEND (Ik ben dankbaar voor, Wat maakt vandaag geweldig, Daily affirmation) en AVOND (Drie mooie dingen, Learnings, vrije regels). Kort en snel in te vullen.
3. **Weekend**: een kort dagboek voor zaterdag en zondag, met vrije regels onderaan.

## Liggend of staand

Standaard is de planner **liggend**: hij vult je scherm als je de reMarkable dwars houdt. Open de planner op je reMarkable en zet de weergave van het document op liggend (in het menu van het document). Liever staand? Zet `WEEKPLANNER_STAND=staand` of geef `--stand staand` mee.

## Wat het doet

- Leest je agenda via een iCal/ICS-link (Google Agenda of Outlook) of een `.ics`-bestand.
- Snapt terugkerende afspraken en hele-dag-afspraken.
- Zet je weekdoelen (maximaal 3) op elke dagpagina. Geen doelen? Dan krijg je twee lege regels om zelf in te vullen.
- Haalt emoji uit titels weg, zodat er geen lege vakjes in de PDF komen.

## Wat het niet doet (bewust simpel)

Geen quotes, geen klantenteller of jaardoel-bolletjes, geen koppeling met taken- of CRM-systemen, geen automatische taak elke vrijdag. Zie "Extra opties".

## Zo gebruik je het

1. Haal de gegevens op. Vraag de gebruiker, als het niet in `~/.remarkable-skills.env` staat:
   - **Weekdoelen**: hooguit drie doelen voor deze week. Zet ze in `WEEKPLANNER_DOELEN` (gescheiden door `|`) of geef ze mee met `--doelen`.
   - **Agenda**: de iCal/ICS-link (`WEEKPLANNER_ICAL_URL`) of een `.ics`-bestand (`--ics`).
2. Welke week? Standaard is dat de komende week (vanaf vrijdag) of de huidige week. Een andere week? Geef `--week-start JJJJ-MM-DD` (een maandag).
3. Maak de PDF:

```bash
bash <pad-naar-skill>/maak.sh --doelen "Doel een|Doel twee|Doel drie"
bash <pad-naar-skill>/maak.sh --ics "/pad/naar/agenda.ics" --week-start 2026-11-30
```

4. Naar de reMarkable sturen? Alleen als de gebruiker dat vraagt. Zet dan `--sturen` vooraan:

```bash
bash <pad-naar-skill>/maak.sh --sturen
```

## Je agenda-link vinden

### Google Agenda

1. Open Google Agenda in je browser, op een computer.
2. Klik op het tandwiel, dan op Instellingen.
3. Kies links je agenda onder "Instellingen voor mijn agenda's".
4. Scroll naar "Geheim adres in iCal-indeling" en kopieer dat adres.
5. Plak het in `~/.remarkable-skills.env` achter `WEEKPLANNER_ICAL_URL=`.

### Outlook (Outlook.com of Microsoft 365)

1. Open Outlook in je browser (outlook.com of outlook.office.com).
2. Klik op het tandwiel, dan op Agenda en daarna op Gedeelde agenda's.
3. Kies bij "Een agenda publiceren" je agenda en "Kan alle details weergeven". Klik op Publiceren.
4. Kopieer de **ICS**-link (niet de HTML-link).
5. Plak hem in `~/.remarkable-skills.env` achter `WEEKPLANNER_ICAL_URL=`.

Zie je "Een agenda publiceren" niet bij een werkaccount? Dan heeft je beheerder het uitgezet. Gebruik dan een `.ics`-bestand.

### Een .ics-bestand

Exporteer je agenda als `.ics` (kan in bijna elke agenda-app) en geef het mee met `--ics /pad/naar/agenda.ics`.

### Geheim houden

Een agenda-link is als een wachtwoord. Deel hem niet en zet hem niet in een publieke repo. Alleen links die met `https://` (of `webcal://`) beginnen werken. Claude: toon of herhaal deze link nooit in je antwoord, en geef hem niet mee met `--ical-url` op de commandoregel. Laat hem in het instellingenbestand staan.

## Extra opties (op aanvraag)

Wil je meer dan dit? Dit kan allemaal op aanvraag:

- quotes op de dagpagina's;
- een klantenteller of andere cijfers (KPI's) op de dagpagina;
- eigen covers, met een eigen foto of huisstijl;
- automatisch elke vrijdag een nieuwe planner op je reMarkable, via een geplande taak.

Wil je dit ook? Stuur Rogier een appje via rogier.live.
