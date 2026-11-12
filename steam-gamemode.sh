#!/usr/bin/env bash
# Launcher for SteamOS Game Mode (Steam Machine / Steam Deck).
# Add this file to Steam as a non-Steam game; see README.md.
# Any arguments are passed on to heroic_autotag.py (e.g. --language de).

DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
SCRIPT="$DIR/heroic_autotag.py"
LOG="$HOME/.cache/heroic-autotag/last-run.log"
WAIT=${WAIT:-20}

# Without a visible terminal (Game Mode), re-open this script inside Konsole.
if [ -z "$HEROIC_CAT_TERMINAL" ] && [ ! -t 1 ] && command -v konsole >/dev/null 2>&1; then
    export HEROIC_CAT_TERMINAL=1
    exec konsole --fullscreen --hide-menubar --hide-tabbar -e "$0" "$@"
fi

mkdir -p "$(dirname "$LOG")"
python3 "$SCRIPT" "$@" 2>&1 | tee "$LOG"
STATUS=${PIPESTATUS[0]}

UI_LANG="${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}"
PREV=""
for ARG in "$@"; do
    case "$PREV" in --language|--sprache) UI_LANG="$ARG" ;; esac
    case "$ARG" in --language=*|--sprache=*) UI_LANG="${ARG#*=}" ;; esac
    PREV="$ARG"
done
case "$UI_LANG" in
    de*) MSG="Fenster schließt sich in" ; LOGMSG="Protokoll" ;;
    es*) MSG="La ventana se cierra en" ; LOGMSG="Registro" ;;
    it*) MSG="La finestra si chiude tra" ; LOGMSG="Registro" ;;
    fr*) MSG="La fenêtre se ferme dans" ; LOGMSG="Journal" ;;
    *)   MSG="Window closes in" ; LOGMSG="Log" ;;
esac
echo
echo "$LOGMSG: $LOG"
for i in $(seq "$WAIT" -1 1); do
    printf "\r%s %2d s " "$MSG" "$i"
    sleep 1
done
echo
exit "$STATUS"
