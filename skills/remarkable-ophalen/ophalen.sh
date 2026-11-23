#!/bin/bash
# Gebruik:
#   ophalen.sh [--dry-run] "<pad op je reMarkable>" [uitmap]   haal een document met je aantekeningen op
#   ophalen.sh --zoek "<deel van de naam>"                      zoek het pad van een document
#   ophalen.sh --pdf "<bestand.pdf>" [uitmap]                    zet een PDF die je zelf exporteerde om naar PNG's
# Resultaat: een PDF met je aantekeningen en per pagina een PNG (pagina-1.png, ...),
# zodat Claude je handschrift kan lezen.
set -euo pipefail
HIER="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$HIER/../remarkable-sturen/laadenv.sh"

DRY=0; MODUS=ophalen
case "${1:-}" in
  --dry-run) DRY=1; shift ;;
  --zoek) MODUS=zoek; shift ;;
  --pdf) MODUS=pdf; shift ;;
esac
DOEL="${1:-}"
if [ -z "$DOEL" ]; then
  echo "Geef een pad, zoekwoord of PDF mee. Zie de eerste regels van dit script." >&2; exit 1
fi
case "$DOEL" in -*) echo "Een pad mag niet met - beginnen." >&2; exit 1 ;; esac

heb_rmapi() {
  command -v rmapi >/dev/null 2>&1 || { echo "rmapi is niet geïnstalleerd. Zie de README, stap 4." >&2; exit 1; }
}

if [ "$MODUS" = zoek ]; then
  heb_rmapi
  # < /dev/null: rmapi mag nooit blijven wachten op invoer.
  rmapi find / "$DOEL" < /dev/null
  exit 0
fi

command -v pdftoppm >/dev/null 2>&1 || { echo "poppler ontbreekt (pdftoppm). Op een Mac: brew install poppler" >&2; exit 1; }

NAAM="$(basename "$DOEL")"; NAAM="${NAAM%.pdf}"; NAAM="${NAAM%.PDF}"
VEILIG="$(printf '%s' "$NAAM" | tr -c 'A-Za-z0-9._-' '-' | sed 's/--*/-/g; s/^-//; s/-$//')"
UIT="${2:-${PWD}/uitvoer/opgehaald-${VEILIG:-document}-$(date +%Y%m%d-%H%M%S)}"

if [ "$DRY" = 1 ]; then
  echo "[dry-run] Ik zou ophalen: reMarkable:$DOEL (met aantekeningen, alle pagina's)"
  echo "[dry-run] Commando: rmapi geta --a \"$DOEL\" < /dev/null"
  echo "[dry-run] Daarna PNG's per pagina in: $UIT"
  command -v rmapi >/dev/null 2>&1 || echo "[dry-run] Let op: rmapi is nog niet geïnstalleerd (zie README, stap 4)."
  exit 0
fi

mkdir -p "$UIT"
if [ "$MODUS" = pdf ]; then
  [ -f "$DOEL" ] || { echo "Bestand niet gevonden: $DOEL" >&2; exit 1; }
  PDF="$UIT/$(basename "$DOEL")"
  cp "$DOEL" "$PDF"
else
  heb_rmapi
  WERK="$(mktemp -d)"; trap 'rm -rf "$WERK"' EXIT
  # geta maakt een PDF met je aantekeningen erop. --a: ook pagina's zonder aantekeningen.
  if ! (cd "$WERK" && rmapi geta --a "$DOEL" < /dev/null >/dev/null); then
    echo "Ophalen lukte niet. Klopt het pad? Zoek het met: ophalen.sh --zoek \"deel van de naam\"" >&2
    exit 1
  fi
  PDF_GEVONDEN="$(find "$WERK" -maxdepth 1 -iname '*.pdf' | head -n 1)"
  if [ -z "$PDF_GEVONDEN" ]; then
    echo "rmapi gaf geen PDF met aantekeningen terug. Exporteer het document dan zelf als PDF" >&2
    echo "(reMarkable-app: Delen > PDF) en draai: ophalen.sh --pdf bestand.pdf" >&2
    exit 1
  fi
  PDF="$UIT/${VEILIG:-document}-met-aantekeningen.pdf"
  mv "$PDF_GEVONDEN" "$PDF"
fi

# Per pagina een PNG, groot genoeg om handschrift te lezen.
pdftoppm -png -scale-to 1600 "$PDF" "$UIT/pagina"
AANTAL="$(find "$UIT" -maxdepth 1 -name 'pagina-*.png' | wc -l | tr -d ' ')"
echo "Klaar: $AANTAL pagina's in $UIT"
echo "PDF: $PDF"
