---
name: nieuwsbrief-naar-remarkable
description: Zet een nieuwsbrief of artikel (URL, geplakte tekst of HTML-bestand) om naar een briefing-PDF en stuurt die naar de reMarkable. Gebruik bij "zet deze nieuwsbrief op mijn reMarkable", "maak een briefing van deze link", "ik wil dit artikel op mijn reMarkable lezen".
---

# Nieuwsbrief of artikel naar je reMarkable

Je geeft een link, een stuk tekst of een HTML-bestand. De skill maakt er een briefing van in de vaste stijl en kan hem naar je reMarkable sturen.

Deze skill gebruikt de skills `remarkable-briefing` en `remarkable-sturen`. Zet alle drie in dezelfde map.

## Zo gebruik je het

1. Kijk wat de gebruiker geeft:
   - een **URL**: gebruik die direct;
   - **geplakte tekst**: sla de tekst op in een tijdelijk `.txt`-bestand, of geef hem door via stdin met `-`;
   - een **HTML-bestand** (bijvoorbeeld een opgeslagen nieuwsbrief): gebruik het pad.
2. Maak de PDF:

```bash
bash <pad-naar-skill>/nieuwsbrief.sh "https://voorbeeld.nl/artikel" "/pad/uit.pdf"
```

3. Zet hem op de reMarkable alleen als de gebruiker dat vraagt. Voeg dan `--sturen` toe:

```bash
bash <pad-naar-skill>/nieuwsbrief.sh --sturen "https://voorbeeld.nl/artikel"
```

Geef je geen uitvoerpad mee, dan komt de PDF in de map `uitvoer/` van de huidige map.

## Hoe het werkt

- `artikel_naar_md.py` haalt de tekst op en zoekt de kern (`article`, `main` of de hele pagina). Menu's, scripts en voetteksten gaan eruit.
- Koppen worden hoofdstukken. Zonder koppen wordt het een hoofdstuk.
- De cover toont "Briefing voor {naam}" (uit `REMARKABLE_NAAM`), de bron, de datum en de leestijd.
- `remarkable-briefing` bouwt de PDF. `remarkable-sturen` zet hem in je reMarkable Cloud.

## Let op

- Afbeeldingen worden niet meegenomen. Het is een briefing, geen kopie van de pagina.
- Alle tekst van de pagina wordt platte tekst. Scripts, iframes en links van de pagina komen er niet in, en de PDF wordt gemaakt zonder JavaScript.
- Sites met een inlog of betaalmuur geven vaak geen tekst. Sla dan de pagina op als HTML-bestand en geef dat bestand, of plak de tekst.
- Controleer bij een nieuwsbrief met veel opmaak even de PDF voordat je hem stuurt.

## Uitbreiding: mail-koppeling

In deze versie plak je een link of tekst zelf. Een koppeling met je mailbox is een uitbreiding. Dan haalt Claude je nieuwsbrieven zelf op, bijvoorbeeld elke ochtend, en zet ze klaar op je reMarkable. Dat is niet ingebouwd. Wil je dit? Zie "Extra opties (op aanvraag)" in de README.
