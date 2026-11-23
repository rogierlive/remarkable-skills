---
name: remarkable-ophalen
description: Haalt een document terug van de reMarkable, met de aantekeningen die de gebruiker erop schreef, en zet elke pagina om naar een afbeelding zodat Claude het handschrift kan lezen en de punten kan verwerken. Gebruik bij "ik heb hem nagelezen, haal mijn comments op", "haal mijn aantekeningen van de reMarkable", "verwerk wat ik op de briefing schreef", "lees mijn notities van de reMarkable".
---

# Aantekeningen ophalen van je reMarkable

Je stuurt een briefing naar je reMarkable, leest hem met de pen in de hand en schrijft erop. Daarna haalt Claude het document terug, leest je handschrift en verwerkt je punten.

## De flow

1. **Sturen.** Claude maakt een briefing (skill `remarkable-briefing`) en zet hem op je tablet (skill `remarkable-sturen`).
2. **Lezen en schrijven.** Je leest op je reMarkable. Je onderstreept, zet pijlen en schrijft je commentaar in de kantlijn.
3. **Ophalen.** Je zegt: "Ik heb hem nagelezen en comments gezet, haal ze op." Claude haalt het document op met je aantekeningen en maakt van elke pagina een PNG.
4. **Verwerken.** Claude bekijkt de pagina's, leest je handschrift en verwerkt de punten: in de tekst, in een lijstje acties of in een nieuwe versie.

## Zo gebruik je het

1. Zoek het pad op de reMarkable. Weet je het niet precies? Zoek op een deel van de naam:

```bash
bash <pad-naar-skill>/ophalen.sh --zoek "briefing"
```

2. Haal het document op (met je aantekeningen, alle pagina's):

```bash
bash <pad-naar-skill>/ophalen.sh "/Briefings/Mijn briefing"
```

   Het script draait `rmapi geta --a` en zet daarna elke pagina om met `pdftoppm`. Je krijgt een map met de PDF en `pagina-1.png`, `pagina-2.png`, enzovoort.

3. Eerst kijken wat er zou gebeuren, zonder iets op te halen:

```bash
bash <pad-naar-skill>/ophalen.sh --dry-run "/Briefings/Mijn briefing"
```

4. Lukt het ophalen met aantekeningen niet? Exporteer het document dan zelf als PDF (in de reMarkable-app: Delen, dan PDF) en zet die om:

```bash
bash <pad-naar-skill>/ophalen.sh --pdf "/pad/naar/export.pdf"
```

## Zo leest Claude de pagina's

- Bekijk elke PNG. Begin bij pagina 1, sla geen pagina over.
- Let op alles wat met de hand is gezet: tekst in de kantlijn, onderstrepingen, omcirkelde woorden, pijlen, doorhalingen en vraagtekens.
- Maak eerst een lijstje: per pagina wat er staat en waar het bij hoort ("p. 3, bij de tabel: 'klopt niet, check Q3'").
- Kun je een woord niet lezen? Zet het tussen [haken] met je beste gok en vraag het na. Verzin niets.
- Laat het lijstje zien en vraag of je het mag verwerken. Verwerk daarna de punten.

## Regels

- Haal alleen iets op als de gebruiker erom vraagt.
- Elke aanroep van `rmapi` krijgt `< /dev/null`, zodat hij nooit blijft wachten op invoer. Het script doet dat al.
- Het ophalen werkt met `rmapi` van ddvk (zie de README, stap 4). De aantekeningen-export van rmapi is eenvoudig: niet elke pen of kleur komt er perfect uit. Ontbreekt er iets? Gebruik dan de export uit de reMarkable-app (stap 4 hierboven).
- De opgehaalde bestanden blijven op je eigen computer, in de map `uitvoer/`.
