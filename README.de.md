# 🏷️ heroic-autotag

<p align="center">
  <img alt="Python 3.8+" src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white">
  <img alt="Heroic 2.11+" src="https://img.shields.io/badge/Heroic-2.11%2B-1d9bf0">
  <img alt="Linux · SteamOS" src="https://img.shields.io/badge/Linux%20%C2%B7%20SteamOS-supported-1793D1?logo=linux&logoColor=white">
  <img alt="Dependencies: none" src="https://img.shields.io/badge/dependencies-none-brightgreen">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow">
</p>

🇬🇧 [English](README.md) · 🇩🇪 **Deutsch**

Sortiert deine Bibliothek im [Heroic Games Launcher](https://heroicgameslauncher.com) automatisch in Kategorien ein: Controller-Unterstützung, Spielmodi (Koop, Splitscreen, …), Genres, Bewertungen (Metacritic, Steam) sowie Kompatibilität mit Steam Machine, Steam Deck und SteamOS.

Eine einzige Python-Datei, nur Standardbibliothek. Kein Konto, kein API-Schlüssel. Funktioniert mit der nativen Heroic-Installation und mit der Flatpak-Version (SteamOS, Steam Machine, Steam Deck).

```
[  12/50] Celeste                                    ok (Steam)
[  13/50] Akalabeth: World of Doom                   ok (PCGamingWiki)

Kategorien:
  Controller: voll                     117 Spiele
  Modus: Couch-Koop                     15 Spiele
  Steam Machine: verifiziert            87 Spiele
  ...
```

## 📸 Screenshot

<p align="center">
  <img src="docs/screenshot-de-rennspiele.png" alt="Heroic-Bibliothek, gefiltert nach der Kategorie Genre: Rennspiele" width="800">
  <br><sub>Heroics Kategorien-Filter mit den von heroic-autotag angelegten Kategorien, hier <i>Genre: Rennspiele</i></sub>
</p>

## ✨ Funktionen

- **Kategorien:** Controller-Unterstützung, Spielmodi, Genres, Kompatibilität mit Steam Machine, Steam Deck und SteamOS
- **Bewertungen:** Metacritic-Bereiche und Steam-Bewertungen als Kategorien, dazu eine Rangliste deiner am besten bewerteten Spiele (`--top`)
- **Kombis (UND):** z. B. *Controller UND Koop UND Steam Machine*, ganz oben in der Liste
- **Einstellungsdatei:** jede Kategorie ein- oder ausschalten und eigene Kombis festlegen, in `categories.ini`
- **Fünf Sprachen** für Kategorien und alle Ausgaben: Englisch, Deutsch, Spanisch, Italienisch, Französisch
- **Zwei Datenquellen:** zuerst Steam, für Spiele, die es dort nicht gibt, PCGamingWiki
- **Große Bibliotheken:** parallele Abfragen, Cache, jederzeit mit Strg+C unterbrechbar und fortsetzbar
- **Sicher:** sichert Heroics `config.json` vor jedem Schreiben und lässt deine eigenen Kategorien in Ruhe
- **Starter für den Spielmodus**, um das Skript auf Steam Machine oder Steam Deck per Controller auszuführen

## 📋 Voraussetzungen

- Heroic Games Launcher ab Version 2.11 (eigene Kategorien), nativ oder als Flatpak
- Python ab Version 3.8 (auf den meisten Linux-Distributionen und unter SteamOS vorinstalliert)
- Internetverbindung

## 📦 Installation

```bash
git clone https://github.com/Slashdacoda/heroic-autotag.git
cd heroic-autotag
```

Oder lade nur `heroic_autotag.py` herunter (und `steam-gamemode.sh` für den Spielmodus).

## 🚀 Schnellstart

1. Heroic komplett schließen, auch aus dem Tray.
2. Ausführen:
   ```bash
   python3 heroic_autotag.py
   ```
3. Heroic starten, in der Bibliothek den Kategorien-Filter öffnen und eine Kategorie wählen.

Der erste Lauf dauert etwa 1,5–2 Sekunden pro Spiel, weil Steam die Anzahl der Abfragen begrenzt. Danach kommt alles aus dem Cache, und ein Lauf dauert nur noch Sekunden.

**Tipp für große Bibliotheken:** Den langsamen Teil laufen lassen, während Heroic offen bleibt, und danach in Sekunden schreiben:

```bash
python3 heroic_autotag.py --collect     # Heroic darf offen bleiben
python3 heroic_autotag.py --write       # vorher Heroic schließen
```

## ⚙️ Bedienung

| Option | Wirkung |
|---|---|
| *(keine)* | Daten sammeln und Kategorien schreiben |
| `--collect` | nur Daten in den Cache holen (Heroic darf offen bleiben) |
| `--write` | nur Kategorien aus dem Cache schreiben (Heroic muss geschlossen sein) |
| `--dry-run` | Ergebnis anzeigen, nichts schreiben |
| `--max N` | höchstens N neue Spiele pro Lauf abfragen |
| `--threads N` | parallele Threads (Standard 4) |
| `--language en\|de\|es\|it\|fr` | Sprache der Kategorien und Ausgaben |
| `--without GRUPPE …` | Gruppen weglassen: `controller`, `mode`, `genre`, `machine`, `deck`, `steamos`, `metacritic`, `reviews` |
| `--refresh TAGE` | Cache-Einträge älter als TAGE neu abfragen (Bewertungen ändern sich) |
| `--top N` | die N am besten bewerteten Spiele auflisten (Metacritic, dann Steam-Bewertung) |
| `--rule "…"` | mit `--top`: nur Spiele, die eine Regel erfüllen, z. B. `"mode.coop & controller.full"` |
| `--backfill-ratings` | fehlende Metacritic-Werte für Spiele im Cache nachladen |
| `--retry-unknown` | nicht gefundene Spiele erneut suchen |
| `--list-unknown` | nirgends gefundene Spiele auflisten |
| `--template` | nicht gefundene Spiele als Vorlage in die Datei für eigene Zuordnungen eintragen |
| `--test "Titel"` | zeigen, was Steam und PCGamingWiki zu einem Titel liefern |
| `--init-config` | `categories.ini` mit allen Kategorien und den Standard-Kombis erzeugen |
| `--force` | vorhandene `categories.ini` überschreiben (mit `--init-config`) |
| `--config DATEI` | andere Einstellungsdatei verwenden |
| `--flatpak` / `--native` | Heroic-Installation erzwingen (wird normalerweise automatisch erkannt) |
| `--new` | Cache ignorieren und alles neu abfragen |

Die deutschen Optionsnamen früherer Versionen (`--sammeln`, `--schreiben`, `--ohne`, …) funktionieren weiterhin.

## 🌍 Sprachen

Unterstützte Sprachen für Kategorien und alle Ausgaben:

| | Code | Sprache |
|---|---|---|
| 🇬🇧 | `en` | Englisch (Rückfall) |
| 🇩🇪 | `de` | Deutsch |
| 🇪🇸 | `es` | Spanisch |
| 🇮🇹 | `it` | Italienisch |
| 🇫🇷 | `fr` | Französisch |

Standardmäßig wird die Systemsprache verwendet. Alles außer den fünf unterstützten Sprachen fällt auf Englisch zurück. Mit `--language` legst du die Sprache fest:

```bash
python3 heroic_autotag.py --language fr
```

Beim Sprachwechsel werden die Kategorien in der bisherigen Sprache entfernt und in der neuen angelegt, damit nichts doppelt vorhanden ist.

## 🏷️ Kategorien

| Gruppe | Kategorien (Deutsch) |
|---|---|
| Controller | voll, teilweise |
| Modus | Einzelspieler, Mehrspieler, Koop, Online-Koop, Couch-Koop, Splitscreen, PvP, Remote Play Together |
| Genre | Action, Abenteuer, Rollenspiel, Strategie, Simulationen, Rennspiele, Sport, Gelegenheitsspiele, Indie, Kostenlos spielbar, MMO, Early Access |
| Steam Machine | verifiziert, spielbar |
| Steam Deck | verifiziert, spielbar |
| SteamOS | kompatibel |
| Metacritic | 90+, 80–89, 70–79, unter 70 |
| Steam-Bewertungen | Äußerst positiv, Sehr positiv, Positiv, Größtenteils positiv, Ausgeglichen, Negativ |

Eine Kategorie entsteht nur, wenn mindestens ein Spiel passt. Bei Genres müssen es mindestens zwei Spiele sein.

**Steam Machine:** Valve wertet Spiele mit „Steam Deck verifiziert“ automatisch auch als „Steam Machine verifiziert“. Das Skript übernimmt diese Regel, wenn Steam für ein Spiel noch keine eigene Steam-Machine-Bewertung hat.

**Hinweis:** Kategorien, deren Name mit diesen Präfixen (in einer der fünf Sprachen) oder mit dem Kombi-Präfix (`#1 …`) beginnt, verwaltet das Skript und baut sie bei jedem Lauf neu auf. Gib deinen eigenen Kategorien andere Namen.

## ⭐ Bewertungen

Heroic kann nur nach Titel sortieren. Die Bewertungen gibt es deshalb auf zwei Wegen:

**Als Kategorien** zum Filtern. Metacritic verwendet Bereiche statt Schwellen: Heroic verknüpft ausgewählte Kategorien mit ODER. Wählst du *90+* und *80–89*, bekommst du alle Spiele ab 80.

<table>
  <tr>
    <td><img src="docs/screenshot-de-metacritic.png" alt="Heroic, gefiltert nach der Kategorie Metacritic: 80–89"></td>
    <td><img src="docs/screenshot-de-steam-rating.png" alt="Heroic, gefiltert nach der Kategorie Steam-Bewertungen: Äußerst positiv"></td>
  </tr>
  <tr>
    <td align="center"><sub>Metacritic: 80–89</sub></td>
    <td align="center"><sub>Steam-Bewertungen: Äußerst positiv</sub></td>
  </tr>
</table>

**Als Rangliste** im Terminal, auf Wunsch mit einer Regel gefiltert (gleiche Schlüssel wie bei den Kombis unten):

```bash
python3 heroic_autotag.py --top 20
python3 heroic_autotag.py --top 20 --rule "mode.coop & controller.full"
```

```
   #  Metacritic             Steam  Titel
   1          93     96% (843,102)  The Witcher 3: Wild Hunt
   2          89     95% (221,111)  It Takes Two
   3          88     97% (134,389)  Celeste
```

**Woher die Daten kommen:**
- **Metacritic:** aus den Daten der Steam-Store-Seite, für Spiele, die es nicht auf Steam gibt, aus PCGamingWiki. Bei neuen Spielen keine zusätzliche Abfrage.
- **Steam-Bewertungen:** gebündelt, 50 Spiele pro Abfrage. Auch große Bibliotheken dauern nur Sekunden.

**Cache von einer älteren Version?** Steam-Bewertungen werden beim nächsten Lauf automatisch ergänzt. Metacritic-Werte brauchen eine Abfrage pro Spiel und werden deshalb nur auf Wunsch nachgeladen:

```bash
python3 heroic_autotag.py --backfill-ratings
```

## 🧩 Einstellungsdatei und Kombis

Heroic verknüpft mehrere ausgewählte Kategorien mit ODER, die Liste wird also länger, je mehr du auswählst. Kombis lösen das: Das Skript berechnet UND-Regeln selbst und legt pro Regel eine eigene Kategorie an.

Einstellungsdatei einmalig erzeugen:

```bash
python3 heroic_autotag.py --init-config
```

Das schreibt `~/.config/heroic-autotag/categories.ini` mit Kommentaren in deiner Sprache. Ohne diese Datei gelten dieselben Standardwerte.

```ini
[general]
language = auto
genre_min_games = 2
combo_prefix = #{n}

[deck]
enabled = false          ; ganze Gruppe abschalten

[mode]
single = false           ; einzelne Kategorie abschalten

[combo:1]
enabled = true
rule = (controller.full | controller.partial) & (mode.splitscreen | mode.coop) & (machine.verified | machine.playable)
name.en = Controller + co-op + Steam Machine
name.de = Controller + Koop + Steam Machine
```

**Standard-Kombis:**

| # | Regel |
|---|---|
| 1 | Controller (voll oder teilweise) UND (Splitscreen oder Koop) UND Steam Machine (verifiziert oder spielbar) |
| 2 | Controller (voll oder teilweise) UND (Splitscreen oder Koop) UND SteamOS-kompatibel |
| 3 | Controller (voll oder teilweise) UND (SteamOS-kompatibel oder Steam Machine verifiziert/spielbar) |

<p align="center">
  <img src="docs/screenshot-de-combination.png" alt="Heroic, gefiltert nach der Standard-Kombi #3" width="800">
  <br><sub>Die Kombis stehen ganz oben in der Liste, hier <i>#3 Controller + Steam Machine oder SteamOS</i></sub>
</p>

**Regeln** verwenden die Schlüssel aus den Abschnitten in der Form `gruppe.schlüssel` (z. B. `controller.full`, `mode.coop`, `genre.rpg`, `machine.verified`, `steamos.compatible`, `metacritic.90`, `reviews.very_positive`):

| Operator | Bedeutung |
|---|---|
| `&` oder `and` | UND |
| `\|` oder `or` | ODER |
| `!` oder `not` | NICHT |
| `( )` | Klammern |

Eigene Kombis fügst du als `[combo:4]`, `[combo:5]` usw. hinzu. `name.xx` legt den Namen pro Sprache fest, ein einzelnes `name = …` gilt für alle Sprachen.

**Ganz oben:** Kombis bekommen das Präfix `#1`, `#2`, … Satzzeichen werden vor Buchstaben sortiert, und das Skript schreibt die Kombis zusätzlich als Erstes in Heroics Konfiguration. So stehen sie oben in der Kategorienliste. Das Präfix änderst du mit `combo_prefix` (`{n}` ist die Nummer).

Eine abgeschaltete Kategorie wird nur nicht angelegt. Kombis nutzen sie trotzdem: Du kannst zum Beispiel die ganze Gruppe „Steam Deck“ abschalten und `deck.verified` trotzdem in einer Regel verwenden.

## 🔍 Nicht gefundene Spiele

1. Mit verbesserter Suche und PCGamingWiki erneut versuchen:
   ```bash
   python3 heroic_autotag.py --retry-unknown
   ```
2. Für den Rest eine Vorlage anlegen:
   ```bash
   python3 heroic_autotag.py --template
   ```
   Das schreibt `~/.config/heroic-autotag/custom_mapping.txt`. Entferne die Raute `#` vor einer Zeile und trage entweder eine Steam-AppID bzw. einen Steam-Link oder direkt Kategorien ein:
   ```
   Ein Spiel = https://store.steampowered.com/app/123456/
   Anderes Spiel = Controller: voll, Genre: Rollenspiel
   ```

Alternativ kannst du solchen Spielen die Kategorien auch direkt in Heroic geben. Das Skript behält sie bei.

## 🎮 Steam Machine / Steam Deck (Spielmodus)

Die Flatpak-Version von Heroic wird automatisch erkannt. So startest du das Skript aus dem Spielmodus per Controller:

1. In den Desktop-Modus wechseln und das Repository klonen oder herunterladen, zum Beispiel nach `~/heroic-autotag`.
2. Den Starter ausführbar machen:
   ```bash
   chmod +x ~/heroic-autotag/steam-gamemode.sh
   ```
3. In Steam: **Spiele → Ein Nicht-Steam-Spiel zur Bibliothek hinzufügen → Durchsuchen**, als Dateityp *Alle Dateien* wählen und `steam-gamemode.sh` auswählen.
4. Optional: In den Eigenschaften der Verknüpfung einen Namen vergeben (z. B. „Heroic-Kategorien“) und Startoptionen wie `--language de` eintragen.
5. Zurück im Spielmodus die Verknüpfung starten. Ein Terminal im Vollbild zeigt den Fortschritt und schließt sich 20 Sekunden nach dem Ende selbst. Die Ausgabe wird zusätzlich in `~/.cache/heroic-autotag/last-run.log` gespeichert.

Heroic darf dabei nicht gleichzeitig laufen. Der erste Lauf dauert bei einer großen Bibliothek eine Weile. Du kannst ihn überspringen, indem du die Cache-Datei von einem anderen PC kopierst (siehe unten).

## 🔄 Aktualisieren

- **Neue Spiele:** Heroic einmal öffnen, damit es die Bibliothek aktualisiert, schließen und das Skript erneut ausführen. Es werden nur die neuen Spiele abgefragt.
- **Geänderte Bewertungen:** `--refresh 30` fragt Einträge, die älter als 30 Tage sind, neu ab.

## 📁 Dateien

| Datei | Zweck |
|---|---|
| `~/.config/heroic/store/config.json` | Heroics Konfiguration (nativ) |
| `~/.var/app/com.heroicgameslauncher.hgl/config/heroic/store/config.json` | Heroics Konfiguration (Flatpak) |
| `config.json.bak-DATUM-ZEIT` | Sicherung vor jedem Schreiben, neben der `config.json` |
| `~/.cache/heroic-autotag/cache.json` | Cache, nach Spieltitel gespeichert, auf andere Geräte kopierbar |
| `~/.config/heroic-autotag/categories.ini` | Einstellungen: Kategorien an/aus, Kombis |
| `~/.config/heroic-autotag/custom_mapping.txt` | deine eigenen Zuordnungen (ältere Versionen: `eigene_zuordnung.txt`, wird weiter gelesen) |
| `~/.cache/heroic-autotag/state.json` | merkt sich die Namen der Kombis, damit umbenannte Kombis aufgeräumt werden |

**Rückgängig machen:** Heroic schließen und eine Sicherung über die `config.json` kopieren.

**Umstieg von einer älteren Version** (`heroic_kategorien.py`)? Die Ordner `~/.config/heroic-kategorien` und `~/.cache/heroic-kategorien` werden beim ersten Lauf automatisch auf die neuen Namen umgezogen. Cache und Einstellungen bleiben also erhalten.

## ⚠️ Einschränkungen

- **Heroics Konsolenmodus** filtert derzeit nur nach Store und zeigt keine eigenen Kategorien an. In der normalen Heroic-Oberfläche sind die Kategorien sichtbar.
- **Steam-Sammlungen** im Spielmodus von SteamOS sind unabhängig von Heroics Kategorien und werden nicht verändert.
- **SteamOS-Kompatibilität** wird aus einem nicht dokumentierten Steam-Feld gelesen und kann leer bleiben.
- Spiele aus **PCGamingWiki** bekommen keine Bewertung für Steam Machine, Steam Deck oder SteamOS und keine Steam-Bewertung, weil nur Steam diese liefert.
- **Metacritic-Werte** gibt es nur für Spiele, die Steam oder PCGamingWiki mit Wertung führen, vor allem größere Titel.
- Heroic selbst kann nicht nach Bewertung **sortieren**. Zum Filtern dienen die Kategorien, für eine Rangliste `--top`.
- Die Steam-Store-Schnittstellen sind keine offizielle API und können sich ändern.

## 🌐 Datenquellen

- Steam-Store (öffentliche Store-Schnittstellen)
- [PCGamingWiki](https://www.pcgamingwiki.com)

Dieses Projekt steht in keiner Verbindung zu Valve, Heroic Games Launcher, Epic Games, GOG, Amazon oder PCGamingWiki.

## 📄 Lizenz

[MIT](LICENSE): Du darfst das Projekt frei nutzen, verändern, forken und weitergeben, solange der Copyright-Hinweis erhalten bleibt.
