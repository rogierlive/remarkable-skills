#!/bin/bash
# Gebruik: sturen.sh [--dry-run] <bestand.pdf> [map-op-reMarkable]
# Stuurt een PDF naar je reMarkable Cloud via rmapi. De map is optioneel
# (standaard REMARKABLE_MAP uit ~/.remarkable-skills.env, anders de hoofdmap).
set -euo pipefail
HIER="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$HIER/laadenv.sh"

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi
PDF="${1:-}"; MAP="${2:-${REMARKABLE_MAP:-/}}"

if [ -z "$PDF" ] || [ ! -f "$PDF" ]; then
  echo "Geef een bestaand PDF-bestand mee. Gebruik: sturen.sh [--dry-run] bestand.pdf [map]" >&2; exit 1
fi
case "$PDF" in *.pdf|*.PDF) ;; *) echo "Dit is geen PDF: $PDF" >&2; exit 1;; esac
case "$MAP" in /*) ;; *) MAP="/$MAP";; esac

if [ "$DRY" = 1 ]; then
  echo "[dry-run] Ik zou sturen: $PDF -> reMarkable:$MAP"
  command -v rmapi >/dev/null 2>&1 || echo "[dry-run] Let op: rmapi is nog niet geïnstalleerd (zie README, stap 4)."
  exit 0
fi
if ! command -v rmapi >/dev/null 2>&1; then
  echo "rmapi is niet geïnstalleerd. Zie de README, stap 4." >&2; exit 1
fi

# Map aanmaken als die nog niet bestaat (fouten negeren: bestaat vaak al).
# < /dev/null: rmapi mag nooit blijven wachten op invoer.
if [ "$MAP" != "/" ]; then rmapi mkdir "$MAP" >/dev/null 2>&1 < /dev/null || true; fi
rmapi put --force "$PDF" "$MAP" < /dev/null
echo "Klaar: $(basename "$PDF") staat in $MAP op je reMarkable. Synchroniseer even op je tablet."
