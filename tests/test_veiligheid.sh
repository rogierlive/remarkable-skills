#!/bin/bash
# Gebruik: bash tests/test_veiligheid.sh
# Bewijst dat een kwaadaardige webpagina niets kan uitvoeren of insluiten in je briefing.
# Toets 1: tekst van een pagina wordt platte tekst (geen script, iframe, afbeelding of link).
# Toets 2: zelfs als er toch een script in de HTML komt, voert de browser het niet uit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
. "$ROOT/skills/remarkable-briefing/assets/laadenv.sh"
PY="${REMARKABLE_PYTHON:-python3}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
FOUT=0
zeg() { echo "$1"; }
mis() { echo "FOUT: $1"; FOUT=1; }

# Een 'geheim' bestand dat een iframe zou kunnen tonen.
echo "IFRAMEINHOUD" > "$TMP/geheim.txt"

# Toets 1: kwaadaardige pagina (echte tags + tags als tekst die na het parsen weer < en > worden).
cat > "$TMP/pagina.html" <<HTML
<html><head><title>Test</title><script>document.title='x'</script></head><body><article>
<h1>Kwaadaardige test &lt;img src=x onerror=alert(1)&gt;</h1>
<p>Gewone alinea.</p>
<p>&lt;script&gt;document.body.append(['UITGE','VOERD'].join(''))&lt;/script&gt;</p>
<p>&lt;img src=x onerror="document.body.append(['ONERR','OR-UIT'].join(''))"&gt;</p>
<p>&lt;iframe src="file://$TMP/geheim.txt"&gt;&lt;/iframe&gt;</p>
<p>![pixel](https://voorbeeld.invalid/pixel.png) en [klik](javascript:alert(1))</p>
<p>{naam} {p1}</p>
<blockquote>&lt;iframe src="file://$TMP/geheim.txt"&gt;&lt;/iframe&gt;</blockquote>
<iframe src="file://$TMP/geheim.txt"></iframe>
<img src="x" onerror="document.body.append('ECHTE-IMG')">
</article></body></html>
HTML

"$PY" "$ROOT/skills/nieuwsbrief-naar-remarkable/artikel_naar_md.py" "$TMP/pagina.html" "$TMP/gids.md" >/dev/null
REMARKABLE_NAAM=Test "$PY" -I "$ROOT/skills/remarkable-briefing/assets/build.py" "$TMP/gids.md" "$TMP/gids.html" ""
for verboden in '<script' '<iframe' '<img' '<a ' '<[a-z][^>]* on[a-z]+='; do
  if grep -qiE -- "$verboden" "$TMP/gids.html"; then mis "HTML bevat $verboden"; else zeg "ok: geen $verboden in de HTML"; fi
done
bash "$ROOT/skills/remarkable-briefing/assets/render.sh" "$TMP/gids.md" "$TMP/gids.pdf" >/dev/null
TEKST="$(pdftotext "$TMP/gids.pdf" -)"
for verboden in UITGEVOERD ONERROR-UIT ECHTE-IMG IFRAMEINHOUD; do
  if grep -q "$verboden" <<<"$TEKST"; then mis "PDF bevat $verboden"; else zeg "ok: $verboden komt niet in de PDF"; fi
done
if grep -qF "<script>" <<<"$TEKST"; then zeg "ok: <script> staat er als gewone tekst"; else mis "<script> staat niet als tekst in de PDF"; fi
if grep -qF "![pixel]" <<<"$TEKST"; then zeg "ok: markdown-afbeelding staat er als gewone tekst"; else mis "markdown-afbeelding is niet als tekst getoond"; fi

# Toets 2: ruwe HTML met een script direct in de markdown. De browser moet het negeren.
cat > "$TMP/ruw.md" <<'MD'
---
titel: Ruw
---

## 1. Ruw

<p id="x">Voor</p>

<script>document.getElementById('x').textContent = ['SCRIPT','LIEP'].join('');</script>

<img src="x" onerror="document.body.append(['IMG','LIEP'].join(''))">
MD
bash "$ROOT/skills/remarkable-briefing/assets/render.sh" "$TMP/ruw.md" "$TMP/ruw.pdf" >/dev/null
TEKST="$(pdftotext "$TMP/ruw.pdf" -)"
for verboden in SCRIPTLIEP IMGLIEP; do
  if grep -q "$verboden" <<<"$TEKST"; then mis "JavaScript liep in de browser ($verboden)"; else zeg "ok: JavaScript uit ($verboden niet gevonden)"; fi
done

if [ "$FOUT" = 0 ]; then echo "Alles veilig."; else echo "Er ging iets mis."; exit 1; fi
