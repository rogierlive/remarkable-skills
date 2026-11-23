# shellcheck shell=bash
# Laadt je instellingen veilig. Het bestand wordt NIET als shellcode uitgevoerd:
# alleen regels KEY=waarde met een bekende KEY worden gelezen.
# Volgorde (eerste die bestaat): $REMARKABLE_SKILLS_ENV, ~/.remarkable-skills.env
# Een variabele die al in je omgeving staat, wint van het bestand. ~/ wordt je thuismap.
_rs_laad_env() {
  local f regel k v
  for f in "${REMARKABLE_SKILLS_ENV:-}" "$HOME/.remarkable-skills.env"; do
    if [ -z "$f" ] || [ ! -f "$f" ]; then continue; fi
    while IFS= read -r regel || [ -n "$regel" ]; do
      regel="${regel%$'\r'}"
      case "$regel" in *=*) ;; *) continue ;; esac
      k="${regel%%=*}"; v="${regel#*=}"
      k="${k#"${k%%[![:space:]]*}"}"; k="${k%"${k##*[![:space:]]}"}"
      v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"
      case "$k" in
        REMARKABLE_NAAM|REMARKABLE_MAP|REMARKABLE_BROWSER|REMARKABLE_PYTHON|\
        WEEKPLANNER_ICAL_URL|WEEKPLANNER_DOELEN|WEEKPLANNER_MAP|WEEKPLANNER_TZ|WEEKPLANNER_COVER|WEEKPLANNER_STAND) ;;
        *) continue ;;
      esac
      if [ "${#v}" -ge 2 ]; then
        case "$v" in \"*\"|\'*\') v="${v:1:${#v}-2}" ;; esac
      fi
      # shellcheck disable=SC2088  # bewust een letterlijke ~/ in de waarde
      case "$v" in "~/"*) v="$HOME/${v#\~/}" ;; esac
      if [ -z "${!k+x}" ]; then export "$k=$v"; fi
    done < "$f"
    break
  done
}
_rs_laad_env
unset -f _rs_laad_env
# Staat er een Python-omgeving op de standaardplek uit de README? Dan gebruiken we die.
if [ -z "${REMARKABLE_PYTHON:-}" ] && [ -x "$HOME/.remarkable-skills-venv/bin/python" ]; then
  export REMARKABLE_PYTHON="$HOME/.remarkable-skills-venv/bin/python"
fi
