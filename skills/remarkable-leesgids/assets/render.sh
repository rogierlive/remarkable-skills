#!/bin/bash
# Gebruik: render.sh <bron.md> <uit.pdf>
# Bouwt de leesgids in twee rondes: eerst zonder paginanummers, dan met de
# echte pagina's van elk "## N." hoofdstuk op {p1}..{p14} (en {pb} voor Bronnen).
# Gebruikt headless Chrome, Brave of Chromium (--headless=new --mute-audio).
set -euo pipefail
if [ $# -ne 2 ]; then echo "Gebruik: render.sh bron.md uit.pdf" >&2; exit 1; fi
MD="$1"; PDF="$2"; DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$MD" ] || { echo "Bestand niet gevonden: $MD" >&2; exit 1; }
# shellcheck disable=SC1091
. "$DIR/laadenv.sh"

PY="${REMARKABLE_PYTHON:-python3}"
"$PY" -c "import markdown" 2>/dev/null || { echo "Python-module 'markdown' ontbreekt. Zie de README, stap 3 (venv)." >&2; exit 1; }

BROWSER="${REMARKABLE_BROWSER:-}"
if [ -z "$BROWSER" ]; then
  for b in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "$(command -v google-chrome || true)" "$(command -v chromium || true)" "$(command -v chromium-browser || true)"; do
    if [ -n "$b" ] && [ -x "$b" ]; then BROWSER="$b"; break; fi
  done
fi
[ -n "$BROWSER" ] || { echo "Geen Chrome, Brave of Chromium gevonden. Installeer er een, of zet REMARKABLE_BROWSER in ~/.remarkable-skills.env." >&2; exit 1; }
command -v pdfinfo >/dev/null && command -v pdftotext >/dev/null || { echo "poppler ontbreekt (pdfinfo/pdftotext). Mac: brew install poppler" >&2; exit 1; }

TMP="$(mktemp -d)"; HTML="$TMP/gids.html"
trap 'rm -rf "$TMP"' EXIT
# Wachthond: stopt de browser na 120 seconden, zodat hij nooit blijft hangen.
WACHT=(); if command -v perl >/dev/null 2>&1; then WACHT=(perl -e 'alarm shift; exec @ARGV' 120); fi
render() {
  "$PY" -I "$DIR/build.py" "$MD" "$HTML" "$1"
  # Zonder venster, zonder geluid en zonder JavaScript.
  ${WACHT[@]+"${WACHT[@]}"} "$BROWSER" --headless=new --mute-audio --no-pdf-header-footer \
    --blink-settings=scriptEnabled=false \
    --print-to-pdf="$PDF" "file://$HTML" >/dev/null 2>&1 < /dev/null \
    || { echo "De browser gaf een fout of deed er te lang over." >&2; exit 1; }
}
render ""
[ -s "$PDF" ] || { echo "De browser maakte geen PDF. Probeer een andere browser via REMARKABLE_BROWSER." >&2; exit 1; }
N=$(pdfinfo "$PDF" | awk '/^Pages/{print $2}')
PAGINAS=""; if [ "$N" -ge 3 ]; then PAGINAS=$(seq 3 "$N"); fi   # pagina 3 en verder (na cover en inhoud)
PAGES="{"; SEP=""
for h in $(grep -oE '^## [0-9]+\.' "$MD" | grep -oE '[0-9]+'); do
  # Kop zoals hij in de PDF staat: zonder markdown-backslashes en HTML-codes.
  # Alleen het begin, want een lange kop loopt over twee regels.
  T=$(grep -E "^## $h\. " "$MD" | head -1 | sed -E "s/^## $h\. //; s/\\\\(.)/\\1/g; s/&lt;/</g; s/&gt;/>/g; s/&quot;/\"/g; s/&#x27;/'/g; s/&amp;/\\&/g" | cut -c1-25)
  for i in $PAGINAS; do
    if pdftotext -f "$i" -l "$i" "$PDF" - | grep -qF "$h. $T"; then PAGES="$PAGES$SEP\"$h\": $i"; SEP=", "; break; fi
  done
done
B=$(for i in $PAGINAS; do pdftotext -f "$i" -l "$i" "$PDF" - | grep -qx "Bronnen" && echo "$i"; done | tail -1)
if [ -n "$B" ]; then PAGES="$PAGES$SEP\"b\": $B"; fi
PAGES="$PAGES}"
render "$PAGES"
echo "Klaar: $PDF ($(pdfinfo "$PDF" | awk '/^Pages/{print $2}') paginas)"
