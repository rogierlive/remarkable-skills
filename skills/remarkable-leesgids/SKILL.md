---
name: remarkable-leesgids
description: Maakt van tekst of markdown een rustige leesgids-PDF die goed leest op een reMarkable (cover, inhoud, hoofdstukken, bronnen). Gebruik bij "maak een leesgids van ...", "maak hier een pdf van voor mijn reMarkable", of als je een rapport, onderzoek of gids op de reMarkable wilt lezen. Daarna eventueel sturen met de skill remarkable-sturen.
---

# Leesgids voor je reMarkable

Deze skill maakt van markdown een PDF in een vaste, rustige leesstijl. Het formaat past op het reMarkable-scherm.

## De stijl (zit in `assets/build.py`, pas die niet aan)

- Pagina van 210 x 280 mm, ruime marges voor je pen.
- Tekst in een schreefletter, 12,5 pt, zwart op wit. Koppen in een schreefloos lettertype.
- Een hoofdstuk (`## 1. Titel`) heeft een dikke streep eronder en begint op een nieuwe pagina.
- Paginanummer onderaan, niet op de cover.
- Alleen zwart, grijs en wit.

## Opbouw van een gids

1. **Cover** met kicker "Leesgids voor {naam}", titel, ondertitel, datum en een kader "Zo lees je deze gids".
2. **Inhoud** met paginanummers en een kader "De kern in vijf zinnen".
3. **Hoofdstukken** met `## 1. Titel`, elk op een nieuwe pagina.
4. **Bronnen** als laatste pagina.

De naam in de kicker komt uit `REMARKABLE_NAAM` in `~/.remarkable-skills.env`. Is die leeg? Vraag de gebruiker hoe hij of zij heet en zet het in dat bestand.

## Schrijfregels

- Nederlands op B1-niveau. Korte zinnen. Een gedachte per zin.
- Spreek de lezer aan met "je".
- Liever tabellen en korte lijstjes dan lange alinea's.
- Een `quote` per hoofdstuk voor de kernzin. Een `note` voor een waarschuwing. Een `box` voor een samenvatting.
- Geen em-dashes. Gebruik een gewoon koppelteken.
- Cijfers van anderen label je: "volgens hun eigen site, niet getoetst".
- Geen vragenlijsten of werkbladen achterin, tenzij de gebruiker erom vraagt.

## Bouwen

Begin met dit voorbeeld: `assets/voorbeeld.md`. Kopieer het, vervang de inhoud en houd de blokken (cover, inhoud, `pb`) intact. Zet bovenaan:

```
---
titel: De titel zoals hij op de reMarkable moet heten
datum: JJJJ-MM-DD
---
```

Gebruik in de inhoudstabel `{p1}`, `{p2}`, ... voor de hoofdstukpagina's en `{pb}` voor Bronnen. Een pagina-einde is `<div class="pb"></div>`. HTML-blokken met markdown erin krijgen `markdown="1"`.

Maak de PDF:

```bash
bash <pad-naar-skill>/assets/render.sh bron.md uit.pdf
```

`render.sh` bouwt twee keer: eerst zonder paginanummers, dan met de echte nummers in de inhoud. Het gebruikt headless Chrome, Brave of Chromium (`--headless=new --mute-audio`, dus zonder venster en zonder geluid). Je hebt ook `poppler` nodig (`pdfinfo`, `pdftotext`).

## Sturen naar de reMarkable

Vraagt de gebruiker om de gids op de tablet te zetten? Gebruik dan de skill `remarkable-sturen` met de PDF die je net maakte. Stuur nooit ongevraagd.

## Een gids bijwerken

Begin niet opnieuw. Maak een nieuw bestand met de datum van vandaag, verhoog de versie op de cover en zet "Nieuw sinds versie 1" in het kader "Zo lees je deze gids". Stuur hem als "Titel v2" naast de oude.
