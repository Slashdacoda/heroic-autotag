#!/usr/bin/env python3
"""
heroic_autotag.py - automatically sorts a Heroic Games Launcher library into
categories (controller support, game modes, genres, ratings, Steam Machine / Steam Deck /
SteamOS compatibility) using public data from Steam and PCGamingWiki.

No account, no API key, Python standard library only.
Languages: English, Deutsch, Español, Italiano, Français (--language en|de|es|it|fr).

Run  python3 heroic_autotag.py --help  for all options. See README.md.
"""
import argparse, configparser, difflib, json, os, re, shutil, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

VERSION = "3.3"
LANGS = ("en", "de", "es", "it", "fr")

# ============================================================== paths
FLATPAK_ID = "com.heroicgameslauncher.hgl"
NATIVE = (Path.home() / ".config" / "heroic", Path.home() / ".config" / "legendary")
FLATPAK = (Path.home() / ".var" / "app" / FLATPAK_ID / "config" / "heroic",
           Path.home() / ".var" / "app" / FLATPAK_ID / "config" / "legendary")
HEROIC, LEGENDARY = NATIVE              # switched in main() if needed
CONFIG = HEROIC / "store" / "config.json"
CACHE = Path.home() / ".cache" / "heroic-autotag" / "cache.json"
CONF_DIR = Path.home() / ".config" / "heroic-autotag"
OWN_FILE_NEW = CONF_DIR / "custom_mapping.txt"
OWN_FILE_OLD = CONF_DIR / "eigene_zuordnung.txt"      # name used by older versions
SETTINGS_FILE = CONF_DIR / "categories.ini"
STATE_FILE = Path.home() / ".cache" / "heroic-autotag" / "state.json"

# folder names of older versions: up to 3.1 "heroic-kategorien", then "heroic-categories"
OLD_NAMES = ("heroic-categories", "heroic-kategorien")

def migrate_old_files():
    """Moves data from the old folder names to the new ones (once)."""
    moved = []
    for base, new in ((Path.home() / ".config", CONF_DIR), (Path.home() / ".cache", CACHE.parent)):
        for name in OLD_NAMES:
            old = base / name
            if old.is_dir() and not new.exists():
                new.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(new))
                moved.append(f"{old} -> {new}")
    old_cache = CACHE.parent / "steam_cache.json"
    if old_cache.exists() and not CACHE.exists():
        old_cache.rename(CACHE)
        moved.append(f"{old_cache} -> {CACHE}")
    return moved

def own_file():
    if OWN_FILE_NEW.exists() or not OWN_FILE_OLD.exists():
        return OWN_FILE_NEW
    return OWN_FILE_OLD

GENRE_MIN = 2          # genre categories with fewer games are skipped
RUNNERS = ("legendary", "gog", "nile", "sideload")
UA = {"User-Agent": f"heroic-autotag/{VERSION}"}
ERROR = "__error__"

# ============================================================== category names
GROUPS = {
    "controller": dict(en="Controller", de="Controller", es="Mando", it="Controller", fr="Manette"),
    "mode":       dict(en="Mode", de="Modus", es="Modo", it="Modalità", fr="Mode"),
    "genre":      dict(en="Genre", de="Genre", es="Género", it="Genere", fr="Genre"),
    "machine":    dict(en="Steam Machine", de="Steam Machine", es="Steam Machine", it="Steam Machine", fr="Steam Machine"),
    "deck":       dict(en="Steam Deck", de="Steam Deck", es="Steam Deck", it="Steam Deck", fr="Steam Deck"),
    "steamos":    dict(en="SteamOS", de="SteamOS", es="SteamOS", it="SteamOS", fr="SteamOS"),
    "metacritic": dict(en="Metacritic", de="Metacritic", es="Metacritic", it="Metacritic", fr="Metacritic"),
    "reviews":    dict(en="Steam reviews", de="Steam-Bewertungen", es="Reseñas de Steam",
                       it="Recensioni Steam", fr="Évaluations Steam"),
}
SEP = dict(en=": ", de=": ", es=": ", it=": ", fr=" : ")

def _all(text):
    return {l: text for l in LANGS}

VALUES = {
    "controller.full":    dict(en="full", de="voll", es="completo", it="completo", fr="complète"),
    "controller.partial": dict(en="partial", de="teilweise", es="parcial", it="parziale", fr="partielle"),
    "mode.single":        dict(en="Single-player", de="Einzelspieler", es="Un jugador", it="Giocatore singolo", fr="Solo"),
    "mode.multi":         dict(en="Multiplayer", de="Mehrspieler", es="Multijugador", it="Multigiocatore", fr="Multijoueur"),
    "mode.coop":          dict(en="Co-op", de="Koop", es="Cooperativo", it="Cooperativa", fr="Coopération"),
    "mode.online_coop":   dict(en="Online co-op", de="Online-Koop", es="Cooperativo en línea", it="Cooperativa online", fr="Coop en ligne"),
    "mode.couch_coop":    dict(en="Couch co-op", de="Couch-Koop", es="Cooperativo local", it="Cooperativa locale", fr="Coop locale"),
    "mode.splitscreen":   dict(en="Split screen", de="Splitscreen", es="Pantalla dividida", it="Schermo condiviso", fr="Écran partagé"),
    "mode.pvp":           dict(en="PvP", de="PvP", es="JcJ", it="PvP", fr="JcJ"),
    "mode.rpt":           _all("Remote Play Together"),
    "genre.action":       dict(en="Action", de="Action", es="Acción", it="Azione", fr="Action"),
    "genre.adventure":    dict(en="Adventure", de="Abenteuer", es="Aventura", it="Avventura", fr="Aventure"),
    "genre.rpg":          dict(en="RPG", de="Rollenspiel", es="Rol", it="GDR", fr="RPG"),
    "genre.strategy":     dict(en="Strategy", de="Strategie", es="Estrategia", it="Strategia", fr="Stratégie"),
    "genre.simulation":   dict(en="Simulation", de="Simulationen", es="Simulación", it="Simulazione", fr="Simulation"),
    "genre.racing":       dict(en="Racing", de="Rennspiele", es="Carreras", it="Corse", fr="Course"),
    "genre.sports":       dict(en="Sports", de="Sport", es="Deportes", it="Sport", fr="Sport"),
    "genre.casual":       dict(en="Casual", de="Gelegenheitsspiele", es="Casual", it="Casual", fr="Occasionnel"),
    "genre.indie":        dict(en="Indie", de="Indie", es="Indie", it="Indie", fr="Indépendant"),
    "genre.f2p":          dict(en="Free to Play", de="Kostenlos spielbar", es="Free to Play", it="Free to Play", fr="Free-to-play"),
    "genre.mmo":          dict(en="Massively Multiplayer", de="MMO", es="Multijugador masivo", it="MMO", fr="Massivement multijoueur"),
    "genre.early_access": dict(en="Early Access", de="Early Access", es="Acceso anticipado", it="Accesso anticipato", fr="Accès anticipé"),
    "machine.verified":   dict(en="verified", de="verifiziert", es="verificado", it="verificato", fr="vérifié"),
    "machine.playable":   dict(en="playable", de="spielbar", es="jugable", it="giocabile", fr="jouable"),
    "deck.verified":      dict(en="verified", de="verifiziert", es="verificado", it="verificato", fr="vérifié"),
    "deck.playable":      dict(en="playable", de="spielbar", es="jugable", it="giocabile", fr="jouable"),
    "steamos.compatible": dict(en="compatible", de="kompatibel", es="compatible", it="compatibile", fr="compatible"),
    # ranges, not thresholds: Heroic combines selected categories with OR, so 90+ and 80-89 = "80 or better"
    "metacritic.90":      _all("90+"),
    "metacritic.80":      _all("80–89"),
    "metacritic.70":      _all("70–79"),
    "metacritic.low":     dict(en="under 70", de="unter 70", es="menos de 70", it="sotto 70", fr="moins de 70"),
    # Steam's own review labels (review_score 9..1)
    "reviews.overwhelmingly_positive": dict(en="Overwhelmingly Positive", de="Äußerst positiv",
                                            es="Extremadamente positivas", it="Estremamente positive",
                                            fr="Totalement positives"),
    "reviews.very_positive":   dict(en="Very Positive", de="Sehr positiv", es="Muy positivas",
                                    it="Molto positive", fr="Très positives"),
    "reviews.positive":        dict(en="Positive", de="Positiv", es="Positivas", it="Positive", fr="Positives"),
    "reviews.mostly_positive": dict(en="Mostly Positive", de="Größtenteils positiv", es="Mayormente positivas",
                                    it="Perlopiù positive", fr="Plutôt positives"),
    "reviews.mixed":           dict(en="Mixed", de="Ausgeglichen", es="Variadas", it="Nella media",
                                    fr="Moitié-moitié"),
    "reviews.negative":        dict(en="Negative", de="Negativ", es="Negativas", it="Negative", fr="Négatives"),
}

def cat_name(key, lang):
    if key.startswith("raw:"):
        return key[4:]
    return GROUPS[key.split(".")[0]][lang] + SEP[lang] + VALUES[key][lang]

NAME2KEY = {cat_name(k, l): k for k in VALUES for l in LANGS}
PREFIXES = tuple({GROUPS[g][l] + SEP[l] for g in GROUPS for l in LANGS})
LEGACY = ("Controller", "Controller (teilweise)")    # names from the very first version

def is_script_category(name):
    return name in NAME2KEY or name.startswith(PREFIXES) or name in LEGACY

# Steam genre ids -> internal keys
STEAM_GENRES = {"1": "action", "25": "adventure", "3": "rpg", "2": "strategy", "28": "simulation",
                "9": "racing", "18": "sports", "4": "casual", "23": "indie", "37": "f2p",
                "29": "mmo", "70": "early_access"}
# genre names (any language, older caches, Steam's English names) -> internal keys
GENRE_NAMES = {VALUES[k][l].lower(): k.split(".")[1] for k in VALUES if k.startswith("genre.") for l in LANGS}
GENRE_NAMES.update({"free to play": "f2p", "massively multiplayer": "mmo", "mmo": "mmo",
                    "simulation": "simulation", "sports": "sports", "racing": "racing"})
# PCGamingWiki genres -> internal keys
PCGW_GENRES = {
    "action": "action", "fps": "action", "tps": "action", "shooter": "action", "platform": "action",
    "brawler": "action", "fighting": "action", "hack and slash": "action", "metroidvania": "action",
    "arcade": "action", "stealth": "action", "tactical shooter": "action", "rail shooter": "action",
    "adventure": "adventure", "exploration": "adventure", "visual novel": "adventure",
    "hidden object": "adventure", "interactive book": "adventure", "survival horror": "adventure",
    "rpg": "rpg", "arpg": "rpg", "jrpg": "rpg", "mmorpg": "rpg",
    "strategy": "strategy", "rts": "strategy", "tbs": "strategy", "tactics": "strategy",
    "tower defense": "strategy", "wargame": "strategy", "4x": "strategy",
    "simulation": "simulation", "life sim": "simulation", "vehicle simulator": "simulation",
    "business": "simulation", "building": "simulation",
    "racing": "racing", "driving": "racing", "sports": "sports",
    "puzzle": "casual", "casual": "casual", "card/tile": "casual", "board": "casual",
    "party game": "casual", "tile matching": "casual", "mmo": "mmo",
}

# Steam category ids -> mode keys
MODES = {
    "mode.single":      {2},
    "mode.multi":       {1, 36, 38, 49, 27},
    "mode.coop":        {9, 38, 39, 48},
    "mode.online_coop": {38},
    "mode.couch_coop":  {39},
    "mode.splitscreen": {24, 37, 39},
    "mode.pvp":         {49, 36, 37, 47},
    "mode.rpt":         {44},
}
CTRL_FULL, CTRL_PARTIAL = 28, 18
GROUP_ALIASES = {"controller": "controller", "mode": "mode", "modus": "mode", "genre": "genre",
                 "machine": "machine", "steammachine": "machine", "deck": "deck", "steamos": "steamos",
                 "metacritic": "metacritic", "reviews": "reviews", "rating": "reviews"}
REVIEW_KEYS = {9: "reviews.overwhelmingly_positive", 8: "reviews.very_positive", 7: "reviews.positive",
               6: "reviews.mostly_positive", 5: "reviews.mixed", 4: "reviews.negative",
               3: "reviews.negative", 2: "reviews.negative", 1: "reviews.negative"}

def metacritic_key(score):
    if not isinstance(score, int) or score <= 0:
        return None
    return ("metacritic.90" if score >= 90 else "metacritic.80" if score >= 80
            else "metacritic.70" if score >= 70 else "metacritic.low")

# ============================================================== program messages
MSG = {
    "found_heroic": dict(en="Heroic ({kind}): {path}", de="Heroic ({kind}): {path}", es="Heroic ({kind}): {path}",
                         it="Heroic ({kind}): {path}", fr="Heroic ({kind}) : {path}"),
    "kind_native": dict(en="native", de="nativ", es="nativo", it="nativo", fr="natif"),
    "kind_flatpak": _all("Flatpak"),
    "no_heroic": dict(
        en="No Heroic installation found (neither ~/.config/heroic nor Flatpak).\nStart Heroic once and log in, then try again.",
        de="Keine Heroic-Installation gefunden (weder ~/.config/heroic noch Flatpak).\nHeroic einmal starten und einloggen, dann erneut versuchen.",
        es="No se encontró ninguna instalación de Heroic (ni ~/.config/heroic ni Flatpak).\nInicia Heroic una vez, inicia sesión y vuelve a intentarlo.",
        it="Nessuna installazione di Heroic trovata (né ~/.config/heroic né Flatpak).\nAvvia Heroic una volta, effettua l'accesso e riprova.",
        fr="Aucune installation de Heroic trouvée (ni ~/.config/heroic ni Flatpak).\nLancez Heroic une fois, connectez-vous, puis réessayez."),
    "no_games": dict(
        en="No games found. Open Heroic once, let the library load, then try again.",
        de="Keine Spiele gefunden. Heroic einmal öffnen, Bibliothek laden lassen, dann erneut versuchen.",
        es="No se encontraron juegos. Abre Heroic una vez, deja que cargue la biblioteca y vuelve a intentarlo.",
        it="Nessun gioco trovato. Apri Heroic una volta, lascia caricare la libreria e riprova.",
        fr="Aucun jeu trouvé. Ouvrez Heroic une fois, laissez la bibliothèque se charger, puis réessayez."),
    "games_cached": dict(en="{n} games in Heroic, {c} of them already in the cache.",
                         de="{n} Spiele in Heroic, {c} davon schon im Cache.",
                         es="{n} juegos en Heroic, {c} de ellos ya en la caché.",
                         it="{n} giochi in Heroic, {c} dei quali già nella cache.",
                         fr="{n} jeux dans Heroic, dont {c} déjà en cache."),
    "own_loaded": dict(en="{n} custom mappings from {path}", de="{n} eigene Zuordnungen aus {path}",
                       es="{n} asignaciones propias de {path}", it="{n} associazioni personalizzate da {path}",
                       fr="{n} associations personnalisées depuis {path}"),
    "refresh": dict(en="{n} entries older than {d} days will be fetched again.",
                    de="{n} Einträge älter als {d} Tage werden neu abgefragt.",
                    es="Se volverán a consultar {n} entradas con más de {d} días.",
                    it="{n} voci più vecchie di {d} giorni verranno richieste di nuovo.",
                    fr="{n} entrées de plus de {d} jours seront de nouveau interrogées."),
    "all_cached": dict(en="All games are already in the cache.", de="Alle Spiele sind schon im Cache.",
                       es="Todos los juegos ya están en la caché.", it="Tutti i giochi sono già nella cache.",
                       fr="Tous les jeux sont déjà en cache."),
    "fetching": dict(en="Fetching {n} games ({t} threads), roughly {m} minutes.",
                     de="{n} Spiele werden abgefragt ({t} Threads), geschätzt ca. {m} Minuten.",
                     es="Consultando {n} juegos ({t} hilos), unos {m} minutos.",
                     it="Richiesta di {n} giochi ({t} thread), circa {m} minuti.",
                     fr="Interrogation de {n} jeux ({t} threads), environ {m} minutes."),
    "ctrl_c": dict(en="You can stop at any time with Ctrl+C, progress is kept.\n",
                   de="Abbrechen mit Strg+C ist jederzeit möglich, der Fortschritt bleibt erhalten.\n",
                   es="Puedes detenerlo en cualquier momento con Ctrl+C; el progreso se conserva.\n",
                   it="Puoi interrompere in qualsiasi momento con Ctrl+C; i progressi vengono mantenuti.\n",
                   fr="Vous pouvez arrêter à tout moment avec Ctrl+C, la progression est conservée.\n"),
    "throttled": dict(en="   Steam/PCGW is throttling ({ep}, HTTP {code}), all threads wait {s}s …",
                      de="   Drosselung ({ep}, HTTP {code}), alle Threads warten {s}s …",
                      es="   Limitación de solicitudes ({ep}, HTTP {code}), todos los hilos esperan {s}s …",
                      it="   Limitazione delle richieste ({ep}, HTTP {code}), tutti i thread attendono {s}s …",
                      fr="   Limitation des requêtes ({ep}, HTTP {code}), tous les threads attendent {s}s …"),
    "aborting": dict(en="\nAborting … saving cache.", de="\nAbbruch … speichere Cache.",
                     es="\nCancelando … guardando la caché.", it="\nInterruzione … salvataggio della cache.",
                     fr="\nInterruption … enregistrement du cache."),
    "aborted": dict(en="\nAborted. Results so far are saved in the cache.",
                    de="\nAbgebrochen. Bisherige Ergebnisse sind im Cache gespeichert.",
                    es="\nCancelado. Los resultados obtenidos se guardaron en la caché.",
                    it="\nInterrotto. I risultati finora ottenuti sono salvati nella cache.",
                    fr="\nInterrompu. Les résultats obtenus sont enregistrés dans le cache."),
    "st_neterr": dict(en="network error, will retry next time", de="Netzfehler, nächstes Mal erneut",
                      es="error de red, se reintentará", it="errore di rete, riprova la prossima volta",
                      fr="erreur réseau, nouvel essai la prochaine fois"),
    "st_notfound": dict(en="not found", de="nicht gefunden", es="no encontrado", it="non trovato", fr="introuvable"),
    "st_ok": dict(en="ok ({src})", de="ok ({src})", es="ok ({src})", it="ok ({src})", fr="ok ({src})"),
    "own_id": dict(en="custom ID", de="eigene ID", es="ID propio", it="ID personalizzato", fr="ID personnalisé"),
    "src_own": dict(en="custom mapping", de="eigene Zuordnung", es="asignación propia",
                    it="associazione personalizzata", fr="association personnalisée"),
    "categories": dict(en="\nCategories:", de="\nKategorien:", es="\nCategorías:", it="\nCategorie:", fr="\nCatégories :"),
    "n_games": dict(en="{n:>4} games", de="{n:>4} Spiele", es="{n:>4} juegos", it="{n:>4} giochi", fr="{n:>4} jeux"),
    "source": dict(en="(source: {q})", de="(Quelle: {q})", es="(fuente: {q})", it="(fonte: {q})", fr="(source : {q})"),
    "nowhere": dict(en="(not found anywhere)", de="(nirgends gefunden)", es="(no encontrado en ninguna fuente)",
                    it="(non trovato da nessuna parte)", fr="(introuvable partout)"),
    "pending": dict(en="(not fetched yet)", de="(noch nicht abgefragt)", es="(aún sin consultar)",
                    it="(non ancora richiesti)", fr="(pas encore interrogés)"),
    "pending_hint": dict(en="-> run --collect again later", de="-> später erneut --collect",
                         es="-> ejecuta --collect más tarde", it="-> esegui di nuovo --collect più tardi",
                         fr="-> relancez --collect plus tard"),
    "dry_run": dict(en="\nDry run: nothing written.", de="\nDry-Run: nichts geschrieben.",
                    es="\nSimulación: no se escribió nada.", it="\nSimulazione: nulla è stato scritto.",
                    fr="\nSimulation : rien n'a été écrit."),
    "heroic_running": dict(
        en="Heroic is still running. Close it completely (including the tray icon) and run again.",
        de="Heroic läuft noch. Bitte komplett schließen (auch aus dem Tray) und erneut starten.",
        es="Heroic sigue en ejecución. Ciérralo por completo (también el icono de la bandeja) y vuelve a ejecutar.",
        it="Heroic è ancora in esecuzione. Chiudilo completamente (anche dall'area di notifica) e riprova.",
        fr="Heroic est toujours en cours d'exécution. Fermez-le complètement (y compris l'icône de la barre des tâches) et relancez."),
    "heroic_running_write": dict(
        en="\nHeroic is still running. Close it, then run  --write  (takes only seconds).",
        de="\nHeroic läuft noch. Bitte schließen und dann  --write  ausführen (dauert nur Sekunden).",
        es="\nHeroic sigue en ejecución. Ciérralo y ejecuta  --write  (tarda solo unos segundos).",
        it="\nHeroic è ancora in esecuzione. Chiudilo ed esegui  --write  (richiede pochi secondi).",
        fr="\nHeroic est toujours en cours d'exécution. Fermez-le puis lancez  --write  (quelques secondes)."),
    "bad_config": dict(en="Unexpected format in config.json – aborting.", de="Unerwartetes Format in config.json – Abbruch.",
                       es="Formato inesperado en config.json – cancelando.", it="Formato inatteso in config.json – interruzione.",
                       fr="Format inattendu dans config.json – abandon."),
    "done": dict(en="\nDone! Backup: {path}", de="\nFertig! Sicherung: {path}", es="\n¡Listo! Copia de seguridad: {path}",
                 it="\nFatto! Backup: {path}", fr="\nTerminé ! Sauvegarde : {path}"),
    "unknown_hint": dict(en="{n} games not found anywhere – list them with  --list-unknown",
                         de="{n} Spiele nirgends gefunden – Liste mit  --list-unknown",
                         es="{n} juegos no encontrados – lístalos con  --list-unknown",
                         it="{n} giochi non trovati – elencali con  --list-unknown",
                         fr="{n} jeux introuvables – listez-les avec  --list-unknown"),
    "template_head": dict(
        en="# Custom mappings for heroic_autotag.py\n# Remove the '#' in front of a line and add after '=':\n#   a Steam AppID (number from store.steampowered.com/app/NUMBER/) or the Steam link\n#   or categories separated by commas, e.g.:  Controller: full, Genre: Action\n\n",
        de="# Eigene Zuordnungen für heroic_autotag.py\n# Raute (#) vor einer Zeile entfernen und hinter '=' eintragen:\n#   Steam-AppID (Zahl aus store.steampowered.com/app/ZAHL/) oder Steam-Link\n#   oder Kategorien, mit Komma getrennt, z. B.:  Controller: voll, Genre: Action\n\n",
        es="# Asignaciones propias para heroic_autotag.py\n# Quita el '#' al inicio de una línea y añade tras '=':\n#   un AppID de Steam (número de store.steampowered.com/app/NÚMERO/) o el enlace de Steam\n#   o categorías separadas por comas, p. ej.:  Mando: completo, Género: Acción\n\n",
        it="# Associazioni personalizzate per heroic_autotag.py\n# Rimuovi il '#' all'inizio di una riga e aggiungi dopo '=':\n#   un AppID di Steam (numero da store.steampowered.com/app/NUMERO/) o il link di Steam\n#   oppure categorie separate da virgole, ad es.:  Controller: completo, Genere: Azione\n\n",
        fr="# Associations personnalisées pour heroic_autotag.py\n# Supprimez le '#' en début de ligne et ajoutez après '=' :\n#   un AppID Steam (nombre de store.steampowered.com/app/NOMBRE/) ou le lien Steam\n#   ou des catégories séparées par des virgules, p. ex. :  Manette : complète, Genre : Action\n\n"),
    "template_done": dict(en="{n} games added to: {path}", de="{n} Spiele eingetragen in: {path}",
                          es="{n} juegos añadidos a: {path}", it="{n} giochi aggiunti a: {path}",
                          fr="{n} jeux ajoutés à : {path}"),
    "t_variants": dict(en="Search variants:", de="Suchvarianten:", es="Variantes de búsqueda:",
                       it="Varianti di ricerca:", fr="Variantes de recherche :"),
    "t_appid": dict(en="Steam AppID:", de="Steam-AppID:", es="AppID de Steam:", it="AppID di Steam:", fr="AppID Steam :"),
    "t_steam": dict(en="Steam data:", de="Steam-Daten:", es="Datos de Steam:", it="Dati di Steam:", fr="Données Steam :"),
    "t_page": dict(en="PCGamingWiki page:", de="PCGamingWiki-Seite:", es="Página de PCGamingWiki:",
                   it="Pagina di PCGamingWiki:", fr="Page PCGamingWiki :"),
    "t_wikitext": dict(en="Wikitext: {n} characters", de="Wikitext: {n} Zeichen", es="Wikitexto: {n} caracteres",
                       it="Wikitesto: {n} caratteri", fr="Wikitexte : {n} caractères"),
    "t_nowikitext": dict(en="Wikitext: no answer ->", de="Wikitext: keine Antwort ->", es="Wikitexto: sin respuesta ->",
                         it="Wikitesto: nessuna risposta ->", fr="Wikitexte : pas de réponse ->"),
    "t_genres": dict(en="  Genres: {g} | Modes: {m}", de="  Genres: {g} | Modi: {m}", es="  Géneros: {g} | Modos: {m}",
                     it="  Generi: {g} | Modalità: {m}", fr="  Genres : {g} | Modes : {m}"),
    "t_pcgw": dict(en="PCGamingWiki data:", de="PCGamingWiki-Daten:", es="Datos de PCGamingWiki:",
                   it="Dati di PCGamingWiki:", fr="Données PCGamingWiki :"),
    "t_cats": dict(en="Resulting categories:", de="Ergebnis-Kategorien:", es="Categorías resultantes:",
                   it="Categorie risultanti:", fr="Catégories obtenues :"),
    # --help texts
    "h_desc": dict(en="Create Heroic Games Launcher categories automatically",
                   de="Heroic-Games-Launcher-Kategorien automatisch anlegen",
                   es="Crear categorías de Heroic Games Launcher automáticamente",
                   it="Creare automaticamente le categorie di Heroic Games Launcher",
                   fr="Créer automatiquement des catégories pour Heroic Games Launcher"),
    "h_collect": dict(en="only fetch data (Heroic may stay open)", de="nur Daten holen (Heroic darf offen bleiben)",
                      es="solo obtener datos (Heroic puede seguir abierto)", it="solo recuperare i dati (Heroic può restare aperto)",
                      fr="récupérer uniquement les données (Heroic peut rester ouvert)"),
    "h_write": dict(en="only write from the cache (seconds, Heroic closed)", de="nur aus dem Cache schreiben (Sekunden, Heroic zu)",
                    es="solo escribir desde la caché (segundos, Heroic cerrado)",
                    it="solo scrivere dalla cache (pochi secondi, Heroic chiuso)",
                    fr="écrire uniquement depuis le cache (quelques secondes, Heroic fermé)"),
    "h_list": dict(en="list games that were not found", de="nicht gefundene Spiele auflisten",
                   es="listar los juegos no encontrados", it="elencare i giochi non trovati", fr="lister les jeux introuvables"),
    "h_template": dict(en="add unknown games as a template to the custom mapping file",
                       de="nicht gefundene Spiele als Vorlage in die Datei für eigene Zuordnungen eintragen",
                       es="añadir los juegos no encontrados como plantilla al archivo de asignaciones propias",
                       it="aggiungere i giochi non trovati come modello al file delle associazioni personalizzate",
                       fr="ajouter les jeux introuvables comme modèle au fichier d'associations personnalisées"),
    "h_test": dict(en="show what Steam and PCGamingWiki return for a title", de="zeigt, was Steam und PCGamingWiki zu einem Titel liefern",
                   es="muestra lo que Steam y PCGamingWiki devuelven para un título",
                   it="mostra cosa restituiscono Steam e PCGamingWiki per un titolo",
                   fr="affiche ce que Steam et PCGamingWiki renvoient pour un titre"),
    "h_max": dict(en="fetch at most N new games per run", de="höchstens N neue Spiele pro Lauf abfragen",
                  es="consultar como máximo N juegos nuevos por ejecución", it="richiedere al massimo N nuovi giochi per esecuzione",
                  fr="interroger au plus N nouveaux jeux par exécution"),
    "h_threads": dict(en="parallel threads (default 4)", de="parallele Threads (Standard 4)", es="hilos paralelos (por defecto 4)",
                      it="thread paralleli (predefinito 4)", fr="threads parallèles (4 par défaut)"),
    "h_dry": dict(en="write nothing, only show", de="nichts schreiben, nur anzeigen", es="no escribir nada, solo mostrar",
                  it="non scrivere nulla, solo mostrare", fr="ne rien écrire, seulement afficher"),
    "h_new": dict(en="ignore the cache and fetch everything again", de="Cache ignorieren, alles neu abfragen",
                  es="ignorar la caché y consultar todo de nuevo", it="ignorare la cache e richiedere tutto di nuovo",
                  fr="ignorer le cache et tout interroger de nouveau"),
    "h_retry": dict(en="search games that were not found again", de="nicht gefundene Spiele erneut suchen",
                    es="volver a buscar los juegos no encontrados", it="cercare di nuovo i giochi non trovati",
                    fr="rechercher de nouveau les jeux introuvables"),
    "h_refresh": dict(en="fetch cache entries older than DAYS again (e.g. 30)", de="Cache-Einträge älter als TAGE neu abfragen (z. B. 30)",
                      es="volver a consultar entradas con más de DÍAS días (p. ej. 30)",
                      it="richiedere di nuovo le voci più vecchie di GIORNI (es. 30)",
                      fr="interroger de nouveau les entrées de plus de JOURS jours (p. ex. 30)"),
    "h_flatpak": dict(en="use the Flatpak version of Heroic (SteamOS)", de="Flatpak-Heroic verwenden (SteamOS)",
                      es="usar la versión Flatpak de Heroic (SteamOS)", it="usare la versione Flatpak di Heroic (SteamOS)",
                      fr="utiliser la version Flatpak de Heroic (SteamOS)"),
    "h_native": dict(en="use the native Heroic installation (~/.config)", de="natives Heroic verwenden (~/.config)",
                     es="usar la instalación nativa de Heroic (~/.config)", it="usare l'installazione nativa di Heroic (~/.config)",
                     fr="utiliser l'installation native de Heroic (~/.config)"),
    "h_without": dict(en="skip groups: controller, mode, genre, machine, deck, steamos, metacritic, reviews",
                      de="Gruppen weglassen: controller, mode, genre, machine, deck, steamos, metacritic, reviews",
                      es="omitir grupos: controller, mode, genre, machine, deck, steamos, metacritic, reviews",
                      it="omettere gruppi: controller, mode, genre, machine, deck, steamos, metacritic, reviews",
                      fr="ignorer des groupes : controller, mode, genre, machine, deck, steamos, metacritic, reviews"),
    "h_lang": dict(en="language of categories and output (en, de, es, it, fr)",
                   de="Sprache der Kategorien und Ausgaben (en, de, es, it, fr)",
                   es="idioma de las categorías y la salida (en, de, es, it, fr)",
                   it="lingua delle categorie e dei messaggi (en, de, es, it, fr)",
                   fr="langue des catégories et des messages (en, de, es, it, fr)"),
}
MSG.update({
    "h_backfill": dict(en="fetch missing Metacritic scores for games already in the cache (one request per game)",
                       de="fehlende Metacritic-Werte für Spiele im Cache nachladen (eine Abfrage pro Spiel)",
                       es="obtener las puntuaciones de Metacritic que faltan de los juegos en la caché (una consulta por juego)",
                       it="recuperare i punteggi Metacritic mancanti dei giochi nella cache (una richiesta per gioco)",
                       fr="récupérer les notes Metacritic manquantes des jeux en cache (une requête par jeu)"),
    "h_top": dict(en="list the N best-rated games (by Metacritic, then Steam reviews)",
                  de="die N am besten bewerteten Spiele auflisten (nach Metacritic, dann Steam-Bewertung)",
                  es="listar los N juegos mejor valorados (por Metacritic y luego reseñas de Steam)",
                  it="elencare gli N giochi meglio valutati (per Metacritic, poi recensioni Steam)",
                  fr="lister les N jeux les mieux notés (par Metacritic, puis évaluations Steam)"),
    "h_rule": dict(en='only with --top: filter by a rule, e.g. "mode.coop & controller.full"',
                   de='nur mit --top: nach einer Regel filtern, z. B. "mode.coop & controller.full"',
                   es='solo con --top: filtrar por una regla, p. ej. "mode.coop & controller.full"',
                   it='solo con --top: filtrare con una regola, ad es. "mode.coop & controller.full"',
                   fr='uniquement avec --top : filtrer par une règle, p. ex. "mode.coop & controller.full"'),
    "reviews_fetch": dict(en="Steam reviews: {n} games in {r} requests …", de="Steam-Bewertungen: {n} Spiele in {r} Abfragen …",
                          es="Reseñas de Steam: {n} juegos en {r} consultas …", it="Recensioni Steam: {n} giochi in {r} richieste …",
                          fr="Évaluations Steam : {n} jeux en {r} requêtes …"),
    "top_head": dict(en="Title", de="Titel", es="Título", it="Titolo", fr="Titre"),
    "top_none": dict(en="No ratings in the cache yet. Run the script first (older caches: --backfill-ratings).",
                     de="Noch keine Bewertungen im Cache. Erst das Skript ausführen (ältere Caches: --backfill-ratings).",
                     es="Aún no hay valoraciones en la caché. Ejecuta primero el script (cachés antiguas: --backfill-ratings).",
                     it="Ancora nessuna valutazione nella cache. Esegui prima lo script (cache vecchie: --backfill-ratings).",
                     fr="Pas encore de notes dans le cache. Lancez d'abord le script (anciens caches : --backfill-ratings)."),
    "migrated": dict(en="Moved data from an older version: {what}", de="Daten einer älteren Version übernommen: {what}",
                     es="Datos de una versión anterior trasladados: {what}", it="Dati di una versione precedente spostati: {what}",
                     fr="Données d'une version précédente déplacées : {what}"),
    "h_init": dict(en="create categories.ini with all categories and the default combinations",
                   de="categories.ini mit allen Kategorien und den Standard-Kombis erzeugen",
                   es="crear categories.ini con todas las categorías y las combinaciones predeterminadas",
                   it="creare categories.ini con tutte le categorie e le combinazioni predefinite",
                   fr="créer categories.ini avec toutes les catégories et les combinaisons par défaut"),
    "h_force": dict(en="overwrite an existing categories.ini (with --init-config)",
                    de="vorhandene categories.ini überschreiben (mit --init-config)",
                    es="sobrescribir un categories.ini existente (con --init-config)",
                    it="sovrascrivere un categories.ini esistente (con --init-config)",
                    fr="écraser un categories.ini existant (avec --init-config)"),
    "h_config": dict(en="use another settings file instead of ~/.config/heroic-autotag/categories.ini",
                     de="andere Einstellungsdatei statt ~/.config/heroic-autotag/categories.ini verwenden",
                     es="usar otro archivo de configuración en lugar de ~/.config/heroic-autotag/categories.ini",
                     it="usare un altro file di impostazioni invece di ~/.config/heroic-autotag/categories.ini",
                     fr="utiliser un autre fichier de réglages au lieu de ~/.config/heroic-autotag/categories.ini"),
    "ini_exists": dict(en="{path} already exists. Use --force to overwrite it.",
                       de="{path} gibt es schon. Mit --force wird sie überschrieben.",
                       es="{path} ya existe. Usa --force para sobrescribirlo.",
                       it="{path} esiste già. Usa --force per sovrascriverlo.",
                       fr="{path} existe déjà. Utilisez --force pour l'écraser."),
    "ini_created": dict(en="Created: {path}\nEdit it, then run the script as usual.",
                        de="Erstellt: {path}\nAnpassen und dann das Skript wie gewohnt starten.",
                        es="Creado: {path}\nEdítalo y luego ejecuta el script como de costumbre.",
                        it="Creato: {path}\nModificalo, poi esegui lo script come al solito.",
                        fr="Créé : {path}\nModifiez-le, puis lancez le script comme d'habitude."),
    "ini_loaded": dict(en="Settings: {path}", de="Einstellungen: {path}", es="Configuración: {path}",
                       it="Impostazioni: {path}", fr="Réglages : {path}"),
    "ini_error": dict(en="Error in {path}: {err}", de="Fehler in {path}: {err}", es="Error en {path}: {err}",
                      it="Errore in {path}: {err}", fr="Erreur dans {path} : {err}"),
    "rule_unknown": dict(en="[{sec}] unknown category key '{k}' in rule",
                         de="[{sec}] unbekannter Kategorie-Schlüssel '{k}' in der Regel",
                         es="[{sec}] clave de categoría desconocida '{k}' en la regla",
                         it="[{sec}] chiave di categoria sconosciuta '{k}' nella regola",
                         fr="[{sec}] clé de catégorie inconnue '{k}' dans la règle"),
    "rule_syntax": dict(en="[{sec}] the rule cannot be read: {rule}",
                        de="[{sec}] die Regel ist fehlerhaft: {rule}",
                        es="[{sec}] la regla no se puede leer: {rule}",
                        it="[{sec}] la regola non è leggibile: {rule}",
                        fr="[{sec}] la règle est illisible : {rule}"),
    "combos": dict(en="\nCombinations:", de="\nKombis:", es="\nCombinaciones:", it="\nCombinazioni:", fr="\nCombinaisons :"),
    "ini_head": dict(
        en="; Settings for heroic_autotag.py\n; true = create the category, false = do not create it.\n; Recreate this file with:  python3 heroic_autotag.py --init-config --force\n",
        de="; Einstellungen für heroic_autotag.py\n; true = Kategorie anlegen, false = nicht anlegen.\n; Datei neu erzeugen mit:  python3 heroic_autotag.py --init-config --force\n",
        es="; Configuración de heroic_autotag.py\n; true = crear la categoría, false = no crearla.\n; Vuelve a crear este archivo con:  python3 heroic_autotag.py --init-config --force\n",
        it="; Impostazioni di heroic_autotag.py\n; true = crea la categoria, false = non crearla.\n; Ricrea questo file con:  python3 heroic_autotag.py --init-config --force\n",
        fr="; Réglages de heroic_autotag.py\n; true = créer la catégorie, false = ne pas la créer.\n; Recréez ce fichier avec :  python3 heroic_autotag.py --init-config --force\n"),
    "ini_general": dict(
        en="; language: auto (system language) or en, de, es, it, fr\n; genre_min_games: genres with fewer games are not created\n; combo_prefix: placed in front of combinations so they appear at the top ({{n}} = number)\n",
        de="; language: auto (Systemsprache) oder en, de, es, it, fr\n; genre_min_games: Genres mit weniger Spielen werden nicht angelegt\n; combo_prefix: steht vor den Kombis, damit sie ganz oben stehen ({{n}} = Nummer)\n",
        es="; language: auto (idioma del sistema) o en, de, es, it, fr\n; genre_min_games: no se crean géneros con menos juegos\n; combo_prefix: va delante de las combinaciones para que aparezcan arriba ({{n}} = número)\n",
        it="; language: auto (lingua di sistema) oppure en, de, es, it, fr\n; genre_min_games: i generi con meno giochi non vengono creati\n; combo_prefix: precede le combinazioni così appaiono in cima ({{n}} = numero)\n",
        fr="; language : auto (langue du système) ou en, de, es, it, fr\n; genre_min_games : les genres avec moins de jeux ne sont pas créés\n; combo_prefix : placé devant les combinaisons pour qu'elles apparaissent en haut ({{n}} = numéro)\n"),
    "ini_group": dict(en="; enabled = false switches off the whole group", de="; enabled = false schaltet die ganze Gruppe ab",
                      es="; enabled = false desactiva todo el grupo", it="; enabled = false disattiva l'intero gruppo",
                      fr="; enabled = false désactive tout le groupe"),
    "ini_combo": dict(
        en="; Combinations: a game is included when the rule is true. They also work if the categories\n; used in the rule are switched off above.\n; Rule: keys like controller.full, mode.coop, genre.rpg, machine.verified, metacritic.90\n;   &  or  and  = AND     |  or  or  = OR     !  or  not  = NOT     ( ) = grouping\n; name.xx = name per language (en, de, es, it, fr). Add more with [combo:4], [combo:5], ...\n",
        de="; Kombis: Ein Spiel kommt hinein, wenn die Regel zutrifft. Sie funktionieren auch dann,\n; wenn die verwendeten Kategorien oben abgeschaltet sind.\n; Regel: Schlüssel wie controller.full, mode.coop, genre.rpg, machine.verified, metacritic.90\n;   &  oder  and  = UND     |  oder  or  = ODER     !  oder  not  = NICHT     ( ) = Klammern\n; name.xx = Name pro Sprache (en, de, es, it, fr). Weitere mit [combo:4], [combo:5], ...\n",
        es="; Combinaciones: un juego se incluye cuando la regla es verdadera. Funcionan también si las\n; categorías usadas en la regla están desactivadas arriba.\n; Regla: claves como controller.full, mode.coop, genre.rpg, machine.verified, metacritic.90\n;   &  o  and  = Y     |  o  or  = O     !  o  not  = NO     ( ) = agrupar\n; name.xx = nombre por idioma (en, de, es, it, fr). Añade más con [combo:4], [combo:5], ...\n",
        it="; Combinazioni: un gioco viene incluso quando la regola è vera. Funzionano anche se le\n; categorie usate nella regola sono disattivate sopra.\n; Regola: chiavi come controller.full, mode.coop, genre.rpg, machine.verified, metacritic.90\n;   &  o  and  = E     |  o  or  = O     !  o  not  = NON     ( ) = raggruppamento\n; name.xx = nome per lingua (en, de, es, it, fr). Aggiungine altre con [combo:4], [combo:5], ...\n",
        fr="; Combinaisons : un jeu est inclus lorsque la règle est vraie. Elles fonctionnent aussi si les\n; catégories utilisées dans la règle sont désactivées plus haut.\n; Règle : clés comme controller.full, mode.coop, genre.rpg, machine.verified, metacritic.90\n;   &  ou  and  = ET     |  ou  or  = OU     !  ou  not  = NON     ( ) = regroupement\n; name.xx = nom par langue (en, de, es, it, fr). Ajoutez-en avec [combo:4], [combo:5], ...\n"),
})

DEFAULT_COMBOS = [
    ("(controller.full | controller.partial) & (mode.splitscreen | mode.coop) & (machine.verified | machine.playable)",
     dict(en="Controller + co-op + Steam Machine", de="Controller + Koop + Steam Machine",
          es="Mando + cooperativo + Steam Machine", it="Controller + cooperativa + Steam Machine",
          fr="Manette + coop + Steam Machine")),
    ("(controller.full | controller.partial) & (mode.splitscreen | mode.coop) & steamos.compatible",
     dict(en="Controller + co-op + SteamOS", de="Controller + Koop + SteamOS",
          es="Mando + cooperativo + SteamOS", it="Controller + cooperativa + SteamOS",
          fr="Manette + coop + SteamOS")),
    ("(controller.full | controller.partial) & (steamos.compatible | machine.verified | machine.playable)",
     dict(en="Controller + Steam Machine or SteamOS", de="Controller + Steam Machine oder SteamOS",
          es="Mando + Steam Machine o SteamOS", it="Controller + Steam Machine o SteamOS",
          fr="Manette + Steam Machine ou SteamOS")),
]

LANG = "en"

def t(key, **kw):
    return MSG[key][LANG].format(**kw)

def detect_language(argv):
    for i, a in enumerate(argv):
        for opt in ("--language", "--sprache"):
            if a == opt and i + 1 < len(argv):
                return argv[i + 1][:2].lower() if argv[i + 1][:2].lower() in LANGS else "en"
            if a.startswith(opt + "="):
                v = a.split("=", 1)[1][:2].lower()
                return v if v in LANGS else "en"
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(var, "")[:2].lower()
        if v in LANGS:
            return v
    return "en"

# ============================================================== settings (categories.ini)
GROUP_ORDER = ("controller", "mode", "genre", "machine", "deck", "steamos", "metacritic", "reviews")

def default_ini(lang):
    out = [t("ini_head").rstrip("\n"), "", "[general]", t("ini_general").rstrip("\n"),
           "language = auto", "genre_min_games = 2", "combo_prefix = #{n}", ""]
    for g in GROUP_ORDER:
        out += [f"[{g}]", t("ini_group"), "enabled = true"]
        for k in VALUES:
            if k.split(".")[0] == g:
                out += [f"; {cat_name(k, lang)}", f"{k.split('.', 1)[1]} = true"]
        out.append("")
    out.append(t("ini_combo").rstrip("\n"))
    for i, (rule, names) in enumerate(DEFAULT_COMBOS, 1):
        out += ["", f"[combo:{i}]", "enabled = true", f"rule = {rule}"]
        out += [f"name.{l} = {names[l]}" for l in LANGS]
    return "\n".join(out) + "\n"

def tokenize(rule):
    return re.findall(r"\(|\)|&|\||!|[A-Za-z_][A-Za-z0-9_.]*", rule)

def parse_rule(rule, section):
    """Rule -> nested tuples. Grammar: or := and (('|'|or) and)* ; and := not (('&'|and) not)* ;
    not := ('!'|not) not | '(' or ')' | key"""
    toks = tokenize(rule)
    if "".join(toks).replace(" ", "") != re.sub(r"\s+", "", rule):
        raise ValueError(t("rule_syntax", sec=section, rule=rule))
    pos = [0]
    def peek():
        return toks[pos[0]].lower() if pos[0] < len(toks) else None
    def take():
        pos[0] += 1
        return toks[pos[0] - 1]
    def p_or():
        node = p_and()
        while peek() in ("|", "or"):
            take(); node = ("or", node, p_and())
        return node
    def p_and():
        node = p_not()
        while peek() in ("&", "and"):
            take(); node = ("and", node, p_not())
        return node
    def p_not():
        tok = peek()
        if tok in ("!", "not"):
            take(); return ("not", p_not())
        if tok == "(":
            take(); node = p_or()
            if peek() != ")":
                raise ValueError(t("rule_syntax", sec=section, rule=rule))
            take(); return node
        if tok is None or tok in (")", "&", "|", "and", "or"):
            raise ValueError(t("rule_syntax", sec=section, rule=rule))
        key = take().lower()
        if key not in VALUES:
            raise ValueError(t("rule_unknown", sec=section, k=key))
        return ("key", key)
    node = p_or()
    if pos[0] != len(toks):
        raise ValueError(t("rule_syntax", sec=section, rule=rule))
    return node

def eval_rule(node, facts, universe):
    op = node[0]
    if op == "key":
        return facts.get(node[1], set())
    if op == "not":
        return universe - eval_rule(node[1], facts, universe)
    a, b = eval_rule(node[1], facts, universe), eval_rule(node[2], facts, universe)
    return a & b if op == "and" else a | b

class Settings:
    def __init__(self, path):
        self.path = path
        cp = configparser.ConfigParser(interpolation=None, comment_prefixes=(";", "#"),
                                       inline_comment_prefixes=(";",), strict=False)
        try:
            if path.exists():
                cp.read(path, encoding="utf-8")
            else:
                cp.read_string(default_ini(LANG))
            g = cp["general"] if cp.has_section("general") else {}
            self.language = str(g.get("language", "auto")).strip().lower()
            self.genre_min = int(g.get("genre_min_games", GENRE_MIN))
            self.prefix = str(g.get("combo_prefix", "#{n}")).strip()
            self.disabled = set()
            for grp in GROUP_ORDER:
                if not cp.has_section(grp):
                    continue
                if not cp.getboolean(grp, "enabled", fallback=True):
                    self.disabled.update(k for k in VALUES if k.split(".")[0] == grp)
                    continue
                for k in VALUES:
                    if k.split(".")[0] == grp and not cp.getboolean(grp, k.split(".", 1)[1], fallback=True):
                        self.disabled.add(k)
            self.combos = []                      # (number, section, names, rule_tree)
            secs = [x for x in cp.sections() if x.lower().startswith("combo")]
            def num(x):
                m = re.search(r"(\d+)", x)
                return int(m.group(1)) if m else 9999
            for i, sec in enumerate(sorted(secs, key=num), 1):
                if not cp.getboolean(sec, "enabled", fallback=True):
                    continue
                rule = cp.get(sec, "rule", fallback="").strip()
                if not rule:
                    continue
                names = {l: cp.get(sec, f"name.{l}", fallback="").strip() for l in LANGS}
                names["_"] = cp.get(sec, "name", fallback="").strip() or sec
                names["__sec"] = sec
                self.combos.append((i, sec, names, parse_rule(rule, sec)))
        except (configparser.Error, ValueError) as e:
            sys.exit(t("ini_error", path=path, err=e))

    def combo_name(self, number, names, lang):
        base = (names.get(lang) or names.get("en") or
                (names["_"] if names["_"] != sec_name(names) else "") or
                next((names[l] for l in LANGS if names.get(l)), "") or names["_"])
        pre = self.prefix.replace("{n}", str(number))
        return f"{pre} {base}".strip() if pre else base

    def combo_pattern(self):
        if not self.prefix:
            return None
        return re.compile("^" + re.escape(self.prefix).replace(re.escape("{n}"), r"\d+") + r"\s")

def sec_name(names):
    return names.get("__sec")

def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

# ============================================================== Heroic library
def runner_from_path(p):
    s = str(p).lower()
    for key, r in (("legendary", "legendary"), ("gog", "gog"), ("nile", "nile"),
                   ("amazon", "nile"), ("sideload", "sideload")):
        if key in s:
            return r
    return None

def find_games(obj, runner_default, found):
    if isinstance(obj, dict):
        app = obj.get("app_name") or obj.get("appName")
        title = obj.get("title") or obj.get("app_title")
        if isinstance(app, str) and isinstance(title, str) and app and title:
            runner = obj.get("runner") or runner_default
            if runner in RUNNERS and not obj.get("is_dlc") and not obj.get("isDLC"):
                found.setdefault((app, runner), title)
        for v in obj.values():
            find_games(v, runner_default, found)
    elif isinstance(obj, list):
        for v in obj:
            find_games(v, runner_default, found)

def load_library():
    files = []
    for folder in (HEROIC / "store_cache", HEROIC / "gog_store",
                   HEROIC / "store" / "sideload_apps", HEROIC / "sideload_apps",
                   HEROIC / "nile_config" / "nile", HEROIC / "legendaryConfig" / "legendary"):
        if folder.is_dir():
            files += [p for p in folder.glob("*.json") if "installed" not in p.name and "user" not in p.name]
    for meta in (LEGENDARY / "metadata", HEROIC / "legendaryConfig" / "legendary" / "metadata"):
        if meta.is_dir():
            files += list(meta.glob("*.json"))
    found = {}
    for p in files:
        try:
            find_games(json.loads(p.read_text(encoding="utf-8")), runner_from_path(p), found)
        except Exception:
            pass
    return found

# ============================================================== HTTP
def normalize(s):
    s = re.sub(r"[™®©]", "", s.lower())
    s = re.sub(r"\b(game of the year|goty|definitive|deluxe|complete|enhanced|remastered|"
               r"director'?s cut|ultimate|gold|standard|anniversary)( edition)?\b", "", s)
    s = re.sub(r"\bedition\b", "", s)
    return " ".join(re.sub(r"[^a-z0-9äöüßàâçéèêëîïôûùüÿñæœáíóú]+", " ", s).split())

class Rate:
    """Thread-safe minimum interval per endpoint (shared by all threads)."""
    def __init__(self, gap):
        self.gap, self.next, self.lock = gap, 0.0, threading.Lock()
    def wait(self):
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next)
            self.next = start + self.gap
        time.sleep(max(0.0, start - now))
    def pause(self, seconds):
        with self.lock:
            self.next = max(self.next, time.monotonic() + seconds)

# appdetails is the bottleneck (roughly 200 requests / 5 minutes)
RATE = {"search": Rate(0.5), "details": Rate(1.6), "deck": Rate(0.5), "pcgw": Rate(1.0), "browse": Rate(1.0)}
PRINT_LOCK = threading.Lock()

def say(text):
    with PRINT_LOCK:
        print(text, flush=True)

def http_json(url, endpoint, tries=4):
    for i in range(tries):
        RATE[endpoint].wait()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 403):
                s = 60 * (i + 1)
                say(t("throttled", ep=endpoint, code=e.code, s=s))
                RATE[endpoint].pause(s)
                continue
            return ERROR
        except Exception:
            time.sleep(3)
    return ERROR

# ============================================================== title matching
EDITIONS = re.compile(r"\s*[-–:]?\s*\b(game of the year|goty|definitive|deluxe|complete|enhanced|"
                      r"extended|remastered|director'?s cut|ultimate|gold|standard|anniversary|"
                      r"special|collector'?s|digital)\s+edition\b", re.I)

def search_variants(title):
    """Original title, without edition suffix, and without subtitle (after ' - ' or ': ')."""
    s = re.sub(r"[™®©]", "", title).replace("’", "'").replace(" : ", ": ").strip()
    s = re.split(r"\s+\+\s+", s)[0]                 # "Besiege + The Splintered Sea DLC" -> "Besiege"
    clean = " ".join(EDITIONS.sub("", s).split()).strip(" -:")
    variants = [title, s, clean]
    for sep in (" - ", " – ", ": "):
        if sep in clean:
            base = clean.split(sep)[0].strip()
            if len(base) >= 4 and len(normalize(base).split()) >= 2:
                variants.append(base)
    return list(dict.fromkeys(v for v in variants if v))

def match_score(variant, name):
    a, b = normalize(variant), normalize(name)
    if not a or not b:
        return 0.0
    score = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    if len(ta) >= 2 and ta <= tb and len(tb - ta) <= 3:     # e.g. "ACA NEOGEO Alpha Mission II"
        score = max(score, 0.86)
    return score

# ============================================================== Steam
def steam_appid(title):
    variants = search_variants(title)
    best_id, best, failed = None, 0.0, False
    for v in variants:
        for lang, cc in (("english", "US"), ("german", "DE")):
            d = http_json("https://store.steampowered.com/api/storesearch/?term="
                          + urllib.parse.quote(v) + f"&l={lang}&cc={cc}", "search")
            if d == ERROR:
                failed = True
                continue
            for it in (d or {}).get("items", []):
                w = max(match_score(x, it.get("name", "")) for x in variants)
                if w > best:
                    best_id, best = it.get("id"), w
            if best >= 0.95:
                return best_id
        if best >= 0.85:
            return best_id
    if best >= 0.85:
        return best_id
    return ERROR if failed else None

def find_resolved(res, *words):
    for k, v in res.items():
        kl = k.lower()
        if all(w in kl for w in words) and "resolved_category" in kl and isinstance(v, int):
            return v
    return None

def steam_data(appid):
    d = http_json(f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english&cc=US", "details")
    if d == ERROR:
        return ERROR
    e = (d or {}).get(str(appid)) or {}
    if not e.get("success"):
        return None
    data = e.get("data", {})
    info = {
        "source": "steam",
        "appid": appid,
        "categories": sorted({c.get("id") for c in data.get("categories", []) if c.get("id")}),
        "genre_keys": sorted({STEAM_GENRES[str(g.get("id"))] for g in data.get("genres", [])
                              if str(g.get("id")) in STEAM_GENRES}),
        "metacritic": (data.get("metacritic") or {}).get("score") or None,
    }
    r = http_json(f"https://store.steampowered.com/saleaction/ajaxgetdeckappcompatibilityreport?nAppID={appid}", "deck")
    if r == ERROR:
        return ERROR
    res = (r.get("results") or {}) if isinstance(r, dict) else {}
    info["deck"] = res.get("resolved_category") if isinstance(res.get("resolved_category"), int) else None
    info["machine"] = find_resolved(res, "machine")
    info["steamos"] = find_resolved(res, "steamos")
    return info

REVIEW_BATCH = 50

def steam_reviews(appids):
    """Steam user reviews for many apps in one request -> {appid: {score, percent, count} or None}."""
    req = {"ids": [{"appid": a} for a in appids], "context": {"language": "english", "country_code": "US"},
           "data_request": {"include_reviews": True}}
    d = http_json("https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?"
                  + urllib.parse.urlencode({"input_json": json.dumps(req)}), "browse")
    if d == ERROR or not isinstance(d, dict):
        return ERROR
    out = {a: None for a in appids}
    for item in (d.get("response") or {}).get("store_items") or []:
        r = ((item.get("reviews") or {}).get("summary_filtered")) or {}
        if item.get("appid") in out and r.get("review_score"):      # 0 = too few reviews
            out[item["appid"]] = {"score": r["review_score"], "percent": r.get("percent_positive"),
                                  "count": r.get("review_count")}
    return out

def fill_reviews(titles, cache):
    """Adds Steam reviews to cached Steam entries that do not have them yet (batched, cheap)."""
    todo = sorted({ti for ti in titles if isinstance(cache.get(ti), dict) and cache[ti].get("appid")
                   and "reviews" not in cache[ti]}, key=str.lower)
    if not todo:
        return
    batches = [todo[i:i + REVIEW_BATCH] for i in range(0, len(todo), REVIEW_BATCH)]
    print(t("reviews_fetch", n=len(todo), r=len(batches)))
    for batch in batches:
        res = steam_reviews(sorted({cache[ti]["appid"] for ti in batch}))
        if res == ERROR:
            say(t("st_neterr"))
            break
        for ti in batch:
            cache[ti]["reviews"] = res.get(cache[ti]["appid"])
    save_cache(cache)

# ============================================================== PCGamingWiki
PCGW = "https://www.pcgamingwiki.com/w/api.php"

def pcgw_cargo(table, fields, where):
    d = http_json(PCGW + "?" + urllib.parse.urlencode({
        "action": "cargoquery", "format": "json", "tables": table,
        "fields": fields, "where": where, "limit": "1"}), "pcgw")
    if d == ERROR:
        return ERROR
    if not isinstance(d, dict) or "error" in d:
        return None
    rows = d.get("cargoquery") or []
    return rows[0].get("title", {}) if rows else {}

def pcgw_page(title, gog_id=None):
    """Find the PCGamingWiki page: by GOG id first, then via the wiki search."""
    if gog_id and str(gog_id).isdigit():
        r = pcgw_cargo("Infobox_game", "Infobox_game._pageName=Page", f'Infobox_game.GOGcom_ID HOLDS "{gog_id}"')
        if r == ERROR:
            return ERROR
        if r and r.get("Page"):
            return r["Page"]
    variants = search_variants(title)
    for v in variants:
        d = http_json(PCGW + "?" + urllib.parse.urlencode({
            "action": "opensearch", "search": v, "limit": "8", "namespace": "0", "format": "json"}), "pcgw")
        if d == ERROR:
            return ERROR
        names = d[1] if isinstance(d, list) and len(d) > 1 else []
        if names:
            best = max(names, key=lambda n: max(match_score(x, n) for x in variants))
            if max(match_score(x, best) for x in variants) >= 0.85:
                return best
    return None

def pcgw_wikitext(page):
    d = http_json(PCGW + "?" + urllib.parse.urlencode({
        "action": "parse", "page": page, "prop": "wikitext", "redirects": "1",
        "format": "json", "formatversion": "2"}), "pcgw")
    if d == ERROR:
        return ERROR
    if not isinstance(d, dict):
        return None
    w = (d.get("parse") or {}).get("wikitext")
    if isinstance(w, dict):
        w = w.get("*")
    return w if isinstance(w, str) else None

def wt_field(text, name):
    m = re.search(r"\|\s*" + re.escape(name) + r"\s*=\s*([^\n|}]*)", text, re.I)
    return m.group(1).strip() if m else ""

def wt_list(text, kind):
    m = re.search(r"taxonomy/" + kind + r"\s*\|([^}]*)\}\}", text, re.I)
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []

def yes(v):
    return str(v or "").strip().lower() in ("true", "limited")

def wt_metacritic(text):
    m = re.search(r"\{\{\s*Infobox game/row/reception\s*\|\s*Metacritic\s*\|[^|}]*\|\s*(\d{1,3})\s*\}\}", text, re.I)
    return int(m.group(1)) if m and int(m.group(1)) > 0 else None

def pcgw_evaluate(genres_raw, modes, cs, fcs, mp, page, metacritic=None):
    ids, modes = set(), modes.lower()
    if "singleplayer" in modes or "single-player" in modes:
        ids.add(2)
    if "multiplayer" in modes:
        ids.add(1)
    cs, fcs = cs.lower(), fcs.lower()
    if fcs == "true":
        ids.add(CTRL_FULL)
    elif yes(cs) or fcs == "limited":
        ids.add(CTRL_PARTIAL)
    for on, modes_f, coop, pvp, extra in (("L", "LM", 39, 37, 24), ("N", "NM", 48, 47, None), ("O", "OM", 38, 36, None)):
        if yes(mp.get(on)):
            ids.add(1)
            m = str(mp.get(modes_f) or "").lower()
            if "co-op" in m or "coop" in m:
                ids.update({9, coop})
            if "versus" in m:
                ids.update({49, pvp})
            if extra:
                ids.add(extra)
    genres = {PCGW_GENRES[g.lower()] for g in genres_raw if g.lower() in PCGW_GENRES}
    if not ids and not genres:
        return None
    return {"source": "pcgamingwiki", "page": page, "categories": sorted(ids),
            "genre_keys": sorted(genres), "deck": None, "machine": None, "steamos": None,
            "metacritic": metacritic}

def pcgw_data(page):
    text = pcgw_wikitext(page)                    # way 1: read the page's wikitext
    if text == ERROR:
        return ERROR
    if text:
        mp = {"L": wt_field(text, "local play"), "LM": wt_field(text, "local play modes"),
              "N": wt_field(text, "lan play"), "NM": wt_field(text, "lan play modes"),
              "O": wt_field(text, "online play"), "OM": wt_field(text, "online play modes")}
        res = pcgw_evaluate(wt_list(text, "genres"), ", ".join(wt_list(text, "modes")),
                            wt_field(text, "controller support"), wt_field(text, "full controller"), mp, page,
                            wt_metacritic(text))
        if res:
            return res
    p_ = page.replace('"', '\\"')                 # way 2: Cargo database
    info = pcgw_cargo("Infobox_game", "Infobox_game.Genres=Genres,Infobox_game.Modes=Modes",
                      f'Infobox_game._pageName="{p_}"')
    if info is None:
        info = pcgw_cargo("Infobox_game", "Infobox_game.Genres=Genres", f'Infobox_game._pageName="{p_}"')
    inp = pcgw_cargo("Input", "Input.Controller_support=CS,Input.Full_controller_support=FCS", f'Input._pageName="{p_}"')
    mp = pcgw_cargo("Multiplayer", "Multiplayer.Local=L,Multiplayer.Local_modes=LM,Multiplayer.LAN=N,"
                    "Multiplayer.LAN_modes=NM,Multiplayer.Online=O,Multiplayer.Online_modes=OM",
                    f'Multiplayer._pageName="{p_}"')
    if ERROR in (info, inp, mp):
        return ERROR
    info, inp, mp = info or {}, inp or {}, mp or {}
    return pcgw_evaluate(str(info.get("Genres") or "").split(","), str(info.get("Modes") or ""),
                         str(inp.get("CS") or ""), str(inp.get("FCS") or ""), mp, page)

# ============================================================== cache / custom mappings
def load_custom():
    """custom_mapping.txt -> {title: appid(int) or [category keys/raw names]}"""
    result, path = {}, own_file()
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        title, _, value = line.rpartition("=")
        title, value = title.strip(), value.strip()
        if not title or not value:
            continue
        m = re.search(r"(?:app/)?(\d{2,})", value)
        if value.isdigit() or ("store.steampowered.com" in value and m):
            result[title] = int(m.group(1))
        else:
            result[title] = [NAME2KEY.get(c.strip(), "raw:" + c.strip()) for c in value.split(",") if c.strip()]
    return result

def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_cache(c):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")

def source_of(info):
    return info.get("source") or info.get("quelle") or "steam"    # "quelle": older versions

SOURCES = {"steam": "Steam", "pcgamingwiki": "PCGamingWiki"}

# ============================================================== categorisation
def genre_keys(info):
    if "genre_keys" in info:
        return info["genre_keys"]
    return sorted({GENRE_NAMES[g.lower()] for g in info.get("genres", []) if g.lower() in GENRE_NAMES})

def categories_for(info, groups):
    k = set()
    ids = set(info.get("categories") or info.get("kategorien") or [])
    if "controller" in groups:
        if CTRL_FULL in ids:
            k.add("controller.full")
        elif CTRL_PARTIAL in ids:
            k.add("controller.partial")
    if "mode" in groups:
        k.update(name for name, s in MODES.items() if ids & s)
    if "genre" in groups:
        k.update("genre." + g for g in genre_keys(info))
    deck, machine, steamos = info.get("deck"), info.get("machine"), info.get("steamos")
    if "machine" in groups:
        # Valve: Deck Verified automatically counts as Steam Machine Verified
        if machine == 3 or (not machine and deck == 3):
            k.add("machine.verified")
        elif machine == 2:
            k.add("machine.playable")
    if "deck" in groups:
        if deck == 3:
            k.add("deck.verified")
        elif deck == 2:
            k.add("deck.playable")
    if "steamos" in groups and steamos in (2, 3):
        k.add("steamos.compatible")
    if "metacritic" in groups and metacritic_key(info.get("metacritic")):
        k.add(metacritic_key(info.get("metacritic")))
    if "reviews" in groups:
        r = info.get("reviews")
        if isinstance(r, dict) and r.get("score") in REVIEW_KEYS:
            k.add(REVIEW_KEYS[r["score"]])
    return k

# ============================================================== Heroic config
def pick_installation(wish):
    candidates = []
    for name, (h, l) in (("native", NATIVE), ("flatpak", FLATPAK)):
        cfg = h / "store" / "config.json"
        if cfg.exists() and wish in (None, name):
            candidates.append((cfg.stat().st_mtime, h, l, name))
    if not candidates:
        return None
    _, h, l, name = max(candidates)
    return h, l, name

def heroic_running():
    for p in Path("/proc").iterdir():
        if p.name.isdigit() and int(p.name) != os.getpid():
            try:
                if (p / "comm").read_text().strip().lower().startswith("heroic"):
                    return True
                cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "ignore")
                if f"run {FLATPAK_ID}" in cmd:
                    return True
            except Exception:
                pass
    return False

def categories_dict(cfg):
    if isinstance(cfg.get("games.customCategories"), dict):
        return cfg["games.customCategories"]
    games = cfg.setdefault("games", {})
    if not isinstance(games, dict):
        sys.exit(t("bad_config"))
    return games.setdefault("customCategories", {})

def set_categories_dict(cfg, new):
    if isinstance(cfg.get("games.customCategories"), dict):
        cfg["games.customCategories"] = new
    else:
        cfg.setdefault("games", {})["customCategories"] = new

def ids_with_runner(cats):
    every = [x for v in cats.values() if isinstance(v, list) for x in v if isinstance(x, str)]
    return True if not every else any(x.endswith(tuple("_" + r for r in RUNNERS)) for x in every)

# ============================================================== collect / write
def one_game(title, custom=None, gog_id=None):
    preset = (custom or {}).get(title)
    appid = preset if isinstance(preset, int) else steam_appid(title)
    if appid == ERROR:
        return ERROR
    if appid:
        info = steam_data(appid)
        if info is not None:
            return info
    page = pcgw_page(title, gog_id)               # fallback: PCGamingWiki
    if page == ERROR:
        return ERROR
    return pcgw_data(page) if page else None

def collect(games, cache, threads, maximum, custom, backfill=False):
    gog = {ti: app for (app, r), ti in games.items() if r == "gog"}
    def needs_fetch(ti):
        v = custom.get(ti)
        if isinstance(v, list):
            return False
        if isinstance(v, int):
            return not (isinstance(cache.get(ti), dict) and cache[ti].get("appid") == v)
        if backfill and isinstance(cache.get(ti), dict) and "metacritic" not in cache[ti]:
            return True                           # entry from a version without ratings
        return ti not in cache
    todo = sorted({ti for ti in games.values() if needs_fetch(ti)}, key=str.lower)
    if maximum:
        todo = todo[:maximum]
    if not todo:
        print(t("all_cached"))
        return
    print(t("fetching", n=len(todo), t=threads, m=round(len(todo) * RATE["details"].gap / 60)))
    print(t("ctrl_c"))
    lock, done = threading.Lock(), 0
    with ThreadPoolExecutor(max_workers=threads) as ex:
        jobs = {ex.submit(one_game, ti, custom, gog.get(ti)): ti for ti in todo}
        try:
            for f in as_completed(jobs):
                title = jobs[f]
                try:
                    info = f.result()
                except Exception:
                    info = ERROR
                with lock:
                    done += 1
                    if info != ERROR:
                        if isinstance(info, dict):
                            info["_time"] = int(time.time())
                        cache[title] = info
                    if done % 20 == 0:
                        save_cache(cache)
                if info == ERROR:
                    status = t("st_neterr")
                elif info is None:
                    status = t("st_notfound")
                else:
                    src = SOURCES.get(source_of(info), source_of(info))
                    if isinstance(custom.get(title), int):
                        src += ", " + t("own_id")
                    status = t("st_ok", src=src)
                say(f"[{done:>4}/{len(todo)}] {title[:55]:<55} {status}")
        except KeyboardInterrupt:
            say(t("aborting"))
            ex.shutdown(wait=False, cancel_futures=True)
            save_cache(cache)
            raise
    save_cache(cache)

def write(games, cache, skip, dry_run, custom, settings):
    facts, unknown, pending, no_data = {}, [], 0, set()
    every = set(games)
    for (app, runner), title in games.items():
        if isinstance(custom.get(title), list):
            for k in custom[title]:
                facts.setdefault(k, set()).add((app, runner))
            continue
        if title not in cache:
            no_data.add((app, runner)); pending += 1
            continue
        info = cache[title]
        if not isinstance(info, dict):
            unknown.append(title); no_data.add((app, runner))
            continue
        for k in categories_for(info, GROUP_ORDER):
            facts.setdefault(k, set()).add((app, runner))

    # Heroic config: categories you gave by hand to unknown / not yet fetched games are kept
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cats = categories_dict(cfg)
    with_runner = ids_with_runner(cats)
    gid = lambda app, r: f"{app}_{r}" if with_runner else app
    back = {gid(a, r): (a, r) for a, r in every}
    no_ids = {gid(a, r) for a, r in no_data}
    state = load_state()
    pattern = settings.combo_pattern()
    old_combos = set(state.get("combos", []))
    def is_combo(name):
        return name in old_combos or bool(pattern and pattern.match(name))
    for name, ids in cats.items():
        if is_script_category(name) and not is_combo(name) and name not in LEGACY and isinstance(ids, list):
            key = NAME2KEY.get(name, "raw:" + name)
            facts.setdefault(key, set()).update(back[x] for x in ids if x in no_ids and x in back)

    # categories to create (switched-off ones are left out, combos still see them)
    assign = {}
    for k, v in facts.items():
        if k.startswith("raw:"):
            assign[k] = v
        elif k not in settings.disabled and k.split(".")[0] not in skip:
            if not k.startswith("genre.") or len(v) >= settings.genre_min:
                assign[k] = v
    combos = []
    for number, sec, names, tree in settings.combos:
        members = eval_rule(tree, facts, every)
        combos.append((settings.combo_name(number, names, LANG), members))

    if combos:
        print(t("combos"))
        for name, members in combos:
            print(f"  {name:<45} {t('n_games', n=len(members))}")
    names = {k: cat_name(k, LANG) for k in assign}
    print(t("categories"))
    for k in sorted(assign, key=lambda x: names[x].lower()):
        print(f"  {names[k]:<45} {t('n_games', n=len(assign[k]))}")
    counter = {}
    for ti in set(games.values()):
        if isinstance(custom.get(ti), list):
            q = t("src_own")
        elif isinstance(cache.get(ti), dict):
            q = SOURCES.get(source_of(cache[ti]), source_of(cache[ti]))
        else:
            continue
        counter[q] = counter.get(q, 0) + 1
    for q, n in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"  {t('source', q=q):<45} {n:>4}")
    print(f"  {t('nowhere'):<45} {len(unknown):>4}")
    if pending:
        print(f"  {t('pending'):<45} {pending:>4}  {t('pending_hint')}")
    if dry_run:
        print(t("dry_run"))
        return
    if heroic_running():
        sys.exit(t("heroic_running_write"))

    # combos first, then your own categories (unchanged order), then the script's categories
    new = {}
    for name, members in combos:
        if members:
            new[name] = sorted(gid(a, r) for a, r in members)
    for name, ids in cats.items():
        if name in new or is_combo(name) or is_script_category(name):
            continue
        new[name] = ids
    for k in sorted(assign, key=lambda x: names[x].lower()):
        name = names[k]
        ids = {gid(a, r) for a, r in assign[k]}
        if is_script_category(name):
            new[name] = sorted(ids)
        else:                                     # your own category without prefix: only add
            new[name] = sorted(set(new.get(name) or []) | ids)
    set_categories_dict(cfg, new)
    backup = CONFIG.with_name(f"config.json.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(CONFIG, backup)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent="\t"), encoding="utf-8")
    state["combos"] = [name for name, members in combos if members]
    save_state(state)
    print(t("done", path=backup))
    if unknown:
        print(t("unknown_hint", n=len(unknown)))

def top_list(games, cache, custom, n, rule):
    titles = {ti for ti in games.values() if isinstance(cache.get(ti), dict)}
    if rule:
        facts = {}
        for ti in titles:
            own = custom.get(ti) if isinstance(custom.get(ti), list) else []
            for k in categories_for(cache[ti], GROUP_ORDER) | set(own):
                facts.setdefault(k, set()).add(ti)
        try:
            tree = parse_rule(rule, "--rule")
        except ValueError as e:
            sys.exit(str(e))
        titles = eval_rule(tree, facts, titles)
    def rv(ti):
        r = cache[ti].get("reviews")
        return r if isinstance(r, dict) else {}
    rated = [ti for ti in titles if cache[ti].get("metacritic") or rv(ti).get("percent")]
    if not rated:
        print(t("top_none"))
        return
    rated.sort(key=lambda ti: (-(cache[ti].get("metacritic") or 0), -(rv(ti).get("percent") or 0),
                               -(rv(ti).get("count") or 0), ti.lower()))
    print(f"\n{'#':>4}  {'Metacritic':>10}  {'Steam':>16}  {t('top_head')}")
    for i, ti in enumerate(rated[:n], 1):
        mc = cache[ti].get("metacritic") or "–"
        r = rv(ti)
        st = f"{r['percent']}% ({r.get('count') or 0:,})" if r.get("percent") is not None else "–"
        print(f"{i:>4}  {mc:>10}  {st:>16}  {ti}")

# ============================================================== main
def main():
    global LANG, HEROIC, LEGENDARY, CONFIG
    LANG = detect_language(sys.argv[1:])
    ap = argparse.ArgumentParser(description=t("h_desc") + f" (v{VERSION})")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--collect", "--sammeln", action="store_true", help=t("h_collect"))
    mode.add_argument("--write", "--schreiben", action="store_true", help=t("h_write"))
    mode.add_argument("--list-unknown", "--liste-unbekannt", action="store_true", help=t("h_list"))
    mode.add_argument("--template", "--vorlage", action="store_true", help=t("h_template"))
    mode.add_argument("--test", metavar="TITLE", help=t("h_test"))
    mode.add_argument("--init-config", "--config-erstellen", action="store_true", help=t("h_init"))
    mode.add_argument("--top", type=int, metavar="N", help=t("h_top"))
    ap.add_argument("--rule", metavar="RULE", help=t("h_rule"))
    ap.add_argument("--backfill-ratings", action="store_true", help=t("h_backfill"))
    ap.add_argument("--force", action="store_true", help=t("h_force"))
    ap.add_argument("--config", metavar="FILE", help=t("h_config"))
    ap.add_argument("--max", type=int, default=0, help=t("h_max"))
    ap.add_argument("--threads", type=int, default=4, help=t("h_threads"))
    ap.add_argument("--dry-run", action="store_true", help=t("h_dry"))
    ap.add_argument("--new", "--neu", action="store_true", help=t("h_new"))
    ap.add_argument("--retry-unknown", "--nochmal-unbekannt", action="store_true", help=t("h_retry"))
    ap.add_argument("--refresh", "--auffrischen", type=int, metavar="DAYS", help=t("h_refresh"))
    inst = ap.add_mutually_exclusive_group()
    inst.add_argument("--flatpak", action="store_true", help=t("h_flatpak"))
    inst.add_argument("--native", "--nativ", action="store_true", help=t("h_native"))
    ap.add_argument("--without", "--ohne", nargs="+", default=[], choices=sorted(GROUP_ALIASES),
                    metavar="GROUP", help=t("h_without"))
    ap.add_argument("--language", "--sprache", default=None, choices=LANGS, help=t("h_lang"))
    a = ap.parse_args()
    if a.language:
        LANG = a.language
    for what in migrate_old_files():
        print(t("migrated", what=what))
    settings_path = Path(a.config).expanduser() if a.config else SETTINGS_FILE
    if a.init_config:
        if settings_path.exists() and not a.force:
            sys.exit(t("ini_exists", path=settings_path))
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(default_ini(LANG), encoding="utf-8")
        print(t("ini_created", path=settings_path))
        return
    settings = Settings(settings_path)
    if not a.language and settings.language in LANGS:
        LANG = settings.language
    if settings_path.exists():
        print(t("ini_loaded", path=settings_path))
    skip = {GROUP_ALIASES[g] for g in a.without}
    groups = [g for g in GROUP_ORDER if g not in skip]

    choice = pick_installation("flatpak" if a.flatpak else "native" if a.native else None)
    if not choice:
        sys.exit(t("no_heroic"))
    HEROIC, LEGENDARY, kind = choice
    CONFIG = HEROIC / "store" / "config.json"
    print(t("found_heroic", kind=t("kind_" + kind), path=HEROIC))
    games = load_library()
    if not games:
        sys.exit(t("no_games"))
    cache = {} if a.new else load_cache()
    if a.retry_unknown:
        cache = {k: v for k, v in cache.items() if isinstance(v, dict)}
    if a.refresh:
        limit = time.time() - a.refresh * 86400
        before = len(cache)
        cache = {k: v for k, v in cache.items()
                 if not isinstance(v, dict) or v.get("_time", v.get("_zeit", 0)) >= limit}
        print(t("refresh", n=before - len(cache), d=a.refresh))
    print(t("games_cached", n=len(games), c=sum(ti in cache for ti in set(games.values()))))

    if a.test:
        print(t("t_variants"), search_variants(a.test))
        appid = steam_appid(a.test)
        print(t("t_appid"), appid)
        result = None
        if appid and appid != ERROR:
            result = steam_data(appid)
            if isinstance(result, dict):
                rv = steam_reviews([appid])
                result["reviews"] = rv.get(appid) if isinstance(rv, dict) else None
            print(t("t_steam"), json.dumps(result, ensure_ascii=False))
        if not isinstance(result, dict):
            gog_id = next((app for (app, r), ti in games.items() if ti == a.test and r == "gog"), None)
            page = pcgw_page(a.test, gog_id)
            print(t("t_page"), page)
            if page and page != ERROR:
                text = pcgw_wikitext(page)
                if isinstance(text, str):
                    print(t("t_wikitext", n=len(text)))
                    print(t("t_genres", g=wt_list(text, "genres"), m=wt_list(text, "modes")))
                    for f_ in ("controller support", "full controller", "local play", "local play modes",
                               "lan play", "online play", "online play modes"):
                        print(f"  {f_}: {wt_field(text, f_)!r}")
                else:
                    print(t("t_nowikitext"), text)
                result = pcgw_data(page)
                print(t("t_pcgw"), json.dumps(result, ensure_ascii=False))
        if isinstance(result, dict):
            print(t("t_cats"), ", ".join(sorted(cat_name(k, LANG) for k in categories_for(result, groups))))
        return

    custom = load_custom()
    if custom:
        print(t("own_loaded", n=len(custom), path=own_file()))
    unknown = sorted({ti for ti in games.values() if ti in cache and not isinstance(cache[ti], dict)
                      and ti not in custom}, key=str.lower)
    if a.top:
        top_list(games, cache, custom, a.top, a.rule)
        return
    if a.list_unknown:
        for ti in unknown:
            print("  -", ti)
        return
    if a.template:
        path = own_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        new = [ti for ti in unknown if f"# {ti} =" not in existing and f"{ti} =" not in existing]
        with path.open("a", encoding="utf-8") as f:
            f.write(("" if existing else t("template_head")) + "".join(f"# {ti} = \n" for ti in new))
        print(t("template_done", n=len(new), path=path))
        return
    if not a.write:
        collect(games, cache, max(1, a.threads), a.max, custom, a.backfill_ratings)
        fill_reviews(set(games.values()), cache)
    if not a.collect:
        write(games, cache, skip, a.dry_run, custom, settings)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(t("aborted"))
