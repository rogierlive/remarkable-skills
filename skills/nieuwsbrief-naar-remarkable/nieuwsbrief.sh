#!/bin/bash
# Gebruik: nieuwsbrief.sh [--sturen] <url | bestand | -> [uit.pdf]
# Maakt van een artikel of nieuwsbrief een leesgids-PDF. Met --sturen gaat hij
# daarna naar je reMarkable. Een "-" leest geplakte tekst uit stdin.
set -euo pipefail
HIER="$(cd "$(dirname "$0")" && pwd)"
LEES="$HIER/../remarkable-leesgids/assets"
STUUR="$HIER/../remarkable-sturen/sturen.sh"
# shellcheck disable=SC1091
. "$LEES/laadenv.sh"

STUREN=0; [ "${1:-}" = "--sturen" ] && { STUREN=1; shift; }
BRON="${1:?Geef een URL, een bestand of - mee}"; UIT="${2:-}"
PY="${REMARKABLE_PYTHON:-python3}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

"$PY" "$HIER/artikel_naar_md.py" "$BRON" "$TMP/gids.md"
if [ -z "$UIT" ]; then
  TITEL=$(sed -n 's/^titel: "\(.*\)"$/\1/p' "$TMP/gids.md" | head -1 | tr -cd '[:alnum:] ._-' | cut -c1-60)
  mkdir -p "${PWD}/uitvoer"; UIT="${PWD}/uitvoer/${TITEL:-artikel}.pdf"
fi
bash "$LEES/render.sh" "$TMP/gids.md" "$UIT"
if [ "$STUREN" = 1 ]; then bash "$STUUR" "$UIT"; fi
