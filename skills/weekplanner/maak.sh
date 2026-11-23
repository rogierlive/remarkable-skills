#!/bin/bash
# Gebruik: maak.sh [--sturen] [weekplanner.py-opties...]
# Maakt je weekplanner. Met --sturen gaat hij daarna naar je reMarkable
# (map: WEEKPLANNER_MAP, anders REMARKABLE_MAP).
set -euo pipefail
HIER="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$HIER/../remarkable-briefing/assets/laadenv.sh"
STUREN=0; [ "${1:-}" = "--sturen" ] && { STUREN=1; shift; }

# Geeft de gebruiker zelf een uitvoerpad (-o, --output of --output=...)? Dan gebruiken we dat.
UIT=""; VORIGE=""
for arg in "$@"; do
  case "$VORIGE" in -o|--output) UIT="$arg";; esac
  case "$arg" in --output=*) UIT="${arg#--output=}";; esac
  VORIGE="$arg"
done
if [ -z "$UIT" ]; then
  UIT="${PWD}/uitvoer/weekplanner-$(date +%Y%m%d-%H%M%S).pdf"
  set -- "$@" --output "$UIT"
fi
"${REMARKABLE_PYTHON:-python3}" "$HIER/weekplanner.py" "$@"
if [ "$STUREN" = 1 ]; then
  bash "$HIER/../remarkable-sturen/sturen.sh" "$UIT" "${WEEKPLANNER_MAP:-${REMARKABLE_MAP:-/}}"
fi
