# 🏷️ heroic-autotag

<p align="center">
  <img alt="Python 3.8+" src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white">
  <img alt="Heroic 2.11+" src="https://img.shields.io/badge/Heroic-2.11%2B-1d9bf0">
  <img alt="Linux · SteamOS" src="https://img.shields.io/badge/Linux%20%C2%B7%20SteamOS-supported-1793D1?logo=linux&logoColor=white">
  <img alt="Dependencies: none" src="https://img.shields.io/badge/dependencies-none-brightgreen">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow">
</p>

🇬🇧 **English** · 🇩🇪 [Deutsch](README.de.md)

Automatically sorts your [Heroic Games Launcher](https://heroicgameslauncher.com) library into categories: controller support, game modes (co-op, split screen, …), genres, ratings (Metacritic, Steam reviews) and Steam Machine / Steam Deck / SteamOS compatibility.

📄 one Python file · 📦 standard library only · 🔑 no account, no API key · 🐧 native and Flatpak (SteamOS, Steam Machine, Steam Deck) · 🌍 five languages

> [!TIP]
> **All options with examples:** `python3 heroic_autotag.py --help` · **Something not working?** → [Troubleshooting](#-troubleshooting)

### What your games get

| Game | 🎮 Controller | 👥 Modes | 🏷️ Genres | ⭐ Ratings | 🕹️ Steam Deck |
|---|---|---|---|---|---|
| Disco Elysium – The Final Cut | full | Single-player | RPG | Metacritic 90+ · Very Positive | verified |
| LEGO Star Wars: Classic Obi-Wan | full | Co-op, Couch co-op, Split screen, Remote Play Together | Action, Adventure | Metacritic 70–79 · Very Positive | verified |
| Overcooked: Gourmet Edition | full | Co-op, Couch co-op, Split screen, PvP | Action, Casual, Simulation | Metacritic 80–89 | – |
| Akalabeth: World of Doom¹ | – | Single-player | RPG | – | – |

<sub>¹ not on Steam, data from PCGamingWiki. Real results from a library of ~1,100 games.</sub>

On top of that come **combinations** such as *#1 Controller + co-op + Steam Machine*, which appear at the top of Heroic's category list.

## 📸 Screenshot

<p align="center">
  <img src="docs/screenshot-de-rennspiele.png" alt="Heroic library filtered by the category Genre: Racing (German)" width="800">
  <br><sub>Heroic's category filter with the categories created by heroic-autotag, here <i>Genre: Racing</i> (German language)</sub>
</p>

## ✨ Features

- **Categories:** controller support, game modes, genres, Steam Machine / Steam Deck / SteamOS compatibility
- **Ratings:** Metacritic score ranges and Steam review labels as categories, plus a ranked list of your best-rated games (`--top`)
- **Combinations (AND):** e.g. *controller AND co-op AND Steam Machine*, shown at the top of the list
- **Settings file:** switch every category on or off and define your own combinations in `categories.ini`
- **Five languages** for categories and all output: English, German, Spanish, Italian, French
- **Two data sources:** Steam first, PCGamingWiki for games that are not on Steam
- **Large libraries:** parallel requests, a cache, resumable at any time with Ctrl+C
- **Safe:** backs up Heroic's `config.json` before every write, never touches your own categories
- **Game Mode launcher** for running it with a controller on a Steam Machine or Steam Deck

## 📋 Requirements

- Heroic Games Launcher 2.11 or newer (custom categories), native or Flatpak
- Python 3.8 or newer (preinstalled on most Linux distributions and on SteamOS)
- Internet access

## 📦 Installation

```bash
git clone https://github.com/Slashdacoda/heroic-autotag.git
cd heroic-autotag
```

Or download `heroic_autotag.py` (and `steam-gamemode.sh` for Game Mode) on its own.

## 🚀 Quick start

1. Close Heroic completely (including the tray icon).
2. Run:
   ```bash
   python3 heroic_autotag.py
   ```
3. Start Heroic, open the category filter in the library and pick a category.

> [!TIP]
> `python3 heroic_autotag.py --help` lists every option with a short description and example calls, in your language.

A run looks like this (shortened, here with 80 new games):

```console
$ python3 heroic_autotag.py
Heroic (native): /home/user/.config/heroic
1168 games in Heroic, 1088 of them already in the cache.
Fetching 80 games (4 threads), roughly 2 minutes.
You can stop at any time with Ctrl+C, progress is kept.

[   1/80] Brothers: A Tale of Two Sons                            ok (Steam)
[   2/80] Moving Out                                              ok (Steam)
[   3/80] Akalabeth: World of Doom                                ok (PCGamingWiki)
[   4/80] Supraland                                               ok (Steam)
[   5/80] Vagrus - The Riven Realms: Prologue                     not found
  …
[  79/80] Crossed Swords                                          ok (PCGamingWiki)
[  80/80] Blazing Sails                                           ok (Steam)
Fetching Steam reviews for 72 games …

Combinations:
  #1 Controller + co-op + Steam Machine          192 games
  #2 Controller + co-op + SteamOS                193 games
  #3 Controller + Steam Machine or SteamOS       677 games

Categories:
  Controller: full                               687 games
  Controller: partial                            153 games
  Genre: Action                                  552 games
  Genre: RPG                                     284 games
  Metacritic: 80–89                              202 games
  Metacritic: 90+                                 17 games
  Mode: Couch co-op                              118 games
  Mode: Split screen                             182 games
  Steam Deck: verified                           422 games
  Steam Machine: verified                        515 games
  Steam reviews: Overwhelmingly Positive          63 games
  SteamOS: compatible                            815 games
  …
  (source: Steam)                               1008
  (source: PCGamingWiki)                          73
  (not found anywhere)                            54

Done! Backup: /home/user/.config/heroic/store/config.json.bak-20261112-031502
54 games not found anywhere – list them with  --list-unknown
```

The first run takes about 1.5–2 seconds per game, because Steam limits how fast it may be queried. After that, everything comes from the cache and a run takes seconds.

**Tip for large libraries:** let the slow part run while Heroic stays open, then write in seconds:

```bash
python3 heroic_autotag.py --collect     # Heroic may stay open
python3 heroic_autotag.py --write       # close Heroic first
```

## ⚙️ Usage

All options with a short description and examples, in your language:

```bash
python3 heroic_autotag.py --help
```

**What to do** (without one of these: collect data and write categories)

| Option | What it does |
|---|---|
| `--collect` | only fetch data into the cache (Heroic may stay open) |
| `--write` | only write categories from the cache (Heroic must be closed) |
| `--test N\|TITLE …` | test games online without writing anything (see [Testing](#-testing)) |
| `--top N` | list the N best-rated games (Metacritic, then Steam reviews) |
| `--list-unknown` | list games that were not found anywhere |
| `--template` | add unknown games to the custom mapping file as a template |
| `--init-config` | create `categories.ini` with all categories and the default combinations |
| `-h`, `--help` | show all options and examples |

**Fetching**

| Option | What it does |
|---|---|
| `--max N` | fetch at most N new games per run |
| `--threads N` | parallel threads (default 4) |
| `--new` | ignore the cache and fetch everything again |
| `--retry-unknown` | search games that were not found again |
| `--refresh DAYS` | fetch cache entries older than DAYS again (ratings change over time) |

**Categories and output**

| Option | What it does |
|---|---|
| `--dry-run` | show the result, write nothing |
| `--rule "…"` | with `--top`: only games matching a rule, e.g. `"mode.coop & controller.full"` |
| `-v`, `--verbose` | with `--test`: also show the raw data from Steam / PCGamingWiki |
| `--without GROUP …` | skip groups: `controller`, `mode`, `genre`, `machine`, `deck`, `steamos`, `metacritic`, `reviews` |
| `--language en\|de\|es\|it\|fr` | language of categories and output |

**Heroic and settings**

| Option | What it does |
|---|---|
| `--flatpak` / `--native` | force a Heroic installation (normally detected automatically) |
| `--config FILE` | use another settings file |
| `--force` | overwrite an existing `categories.ini` (with `--init-config`) |

## 💡 Examples

```bash
# normal run: collect data and write categories (close Heroic first)
python3 heroic_autotag.py

# see what would happen, write nothing
python3 heroic_autotag.py --dry-run

# large library: fetch while Heroic stays open, then write in seconds
python3 heroic_autotag.py --collect
python3 heroic_autotag.py --write

# fetch only 50 new games this time
python3 heroic_autotag.py --collect --max 50

# the 20 best-rated games, all or only co-op games with full controller support
python3 heroic_autotag.py --top 20
python3 heroic_autotag.py --top 20 --rule "mode.coop & controller.full"

# no Steam Deck and genre categories, French names
python3 heroic_autotag.py --without deck genre --language fr

# fetch cache entries again that are older than 30 days (ratings change over time)
python3 heroic_autotag.py --refresh 30
```

## 🧪 Testing

`--test` looks games up online and shows what the script would make of them. It **writes nothing**: neither Heroic's configuration nor the cache. Heroic may stay open.

You can pass a **number**, a **name**, or both:

```bash
python3 heroic_autotag.py --test 5                    # 5 random games from your library
python3 heroic_autotag.py --test "Celeste"            # one game by name
python3 heroic_autotag.py --test witcher              # part of a name is enough if it is unique in your library
python3 heroic_autotag.py --test 3 "Celeste" "Hades"  # 3 random games plus two by name
python3 heroic_autotag.py --test "Celeste" -v         # with the raw data from Steam / PCGamingWiki
```

Names are matched against your Heroic library (case does not matter). If a name matches several games, the script lists them and tests the name as typed; names that are not in your library are tested as typed as well.

For every game you see the search variants, the Steam AppID or PCGamingWiki page, the ratings, the resulting categories and whether they match the cache:

```
=== LEGO® Star Wars™: Classic Obi-Wan   (Heroic: legendary)
  Search variants: ['LEGO® Star Wars™: Classic Obi-Wan', 'LEGO Star Wars: Classic Obi-Wan', 'LEGO Star Wars']
  Steam AppID: 920210
  Found: Steam
  Ratings: Metacritic 78 | Steam Very Positive (90%, 38,502)
  Resulting categories: Controller: full, Genre: Action, Genre: Adventure, Metacritic: 70–79, Mode: Co-op, …
  Cache: same categories

5 games tested: 4 found, 1 not found, 0 network errors. Nothing was written.
```

If a game is found wrongly or not at all, fix it in the [custom mapping file](#-games-that-are-not-found).

To try a full run on part of your library first, combine `--max` and `--dry-run`:

```bash
python3 heroic_autotag.py --max 20 --dry-run
```

This fetches up to 20 new games into the cache and shows the resulting categories without writing to Heroic.

## 🌍 Languages

Supported languages for categories and all output:

| | Code | Language |
|---|---|---|
| 🇬🇧 | `en` | English (fallback) |
| 🇩🇪 | `de` | German |
| 🇪🇸 | `es` | Spanish |
| 🇮🇹 | `it` | Italian |
| 🇫🇷 | `fr` | French |

By default the language is taken from your system language; anything other than the five supported languages falls back to English. Override it with `--language`:

```bash
python3 heroic_autotag.py --language fr
```

When you switch languages, the categories in the previous language are removed and recreated in the new one, so nothing is duplicated.

## 🏷️ Categories

| Group | Categories (English) |
|---|---|
| Controller | full, partial |
| Mode | Single-player, Multiplayer, Co-op, Online co-op, Couch co-op, Split screen, PvP, Remote Play Together |
| Genre | Action, Adventure, RPG, Strategy, Simulation, Racing, Sports, Casual, Indie, Free to Play, Massively Multiplayer, Early Access |
| Steam Machine | verified, playable |
| Steam Deck | verified, playable |
| SteamOS | compatible |
| Metacritic | 90+, 80–89, 70–79, under 70 |
| Steam reviews | Overwhelmingly Positive, Very Positive, Positive, Mostly Positive, Mixed, Negative |

A category is only created if at least one game matches; genres need at least two games.

**Steam Machine:** Valve counts games that are Steam Deck Verified as Steam Machine Verified as well. The script follows this rule when Steam has no separate Steam Machine rating for a game.

**Note:** category names starting with these prefixes (in any of the five languages) and with the combination prefix (`#1 …`) are managed by the script and rebuilt on every run. Give your own categories different names.

## ⭐ Ratings

Heroic can only sort by title, so the ratings are offered in two ways:

**As categories** for filtering. Metacritic uses ranges instead of thresholds: Heroic combines selected categories with OR, so selecting *90+* and *80–89* gives you every game rated 80 or better.

<table>
  <tr>
    <td><img src="docs/screenshot-de-metacritic.png" alt="Heroic filtered by the category Metacritic: 80–89"></td>
    <td><img src="docs/screenshot-de-steam-rating.png" alt="Heroic filtered by the category Steam reviews: Overwhelmingly Positive"></td>
  </tr>
  <tr>
    <td align="center"><sub>Metacritic: 80–89</sub></td>
    <td align="center"><sub>Steam reviews: Overwhelmingly Positive</sub></td>
  </tr>
</table>

**As a ranked list** in the terminal, optionally filtered with a rule (same keys as the combinations below):

```bash
python3 heroic_autotag.py --top 20
python3 heroic_autotag.py --top 20 --rule "mode.coop & controller.full"
```

```
   #  Metacritic             Steam  Title
   1          93     96% (843,102)  The Witcher 3: Wild Hunt
   2          89     95% (221,111)  It Takes Two
   3          88     97% (134,389)  Celeste
```

**Where the data comes from:**
- **Metacritic:** from the Steam store page data, or from PCGamingWiki for games that are not on Steam. No extra requests for new games.
- **Steam reviews:** fetched in batches of 50 games per request, so even large libraries take only seconds.

## 🧩 Settings file and combinations

Heroic combines several selected categories with OR, so the list grows the more you select. Combinations solve this: the script computes AND rules itself and creates one category per rule.

Create the settings file once:

```bash
python3 heroic_autotag.py --init-config
```

This writes `~/.config/heroic-autotag/categories.ini` with comments in your language. Without this file, the same defaults apply.

```ini
[general]
language = auto
genre_min_games = 2
combo_prefix = #{n}

[deck]
enabled = false          ; switch off the whole group

[mode]
single = false           ; switch off one category

[combo:1]
enabled = true
rule = (controller.full | controller.partial) & (mode.splitscreen | mode.coop) & (machine.verified | machine.playable)
name.en = Controller + co-op + Steam Machine
name.de = Controller + Koop + Steam Machine
```

**Default combinations:**

| # | Rule |
|---|---|
| 1 | controller (full or partial) AND (split screen or co-op) AND Steam Machine (verified or playable) |
| 2 | controller (full or partial) AND (split screen or co-op) AND SteamOS compatible |
| 3 | controller (full or partial) AND (SteamOS compatible or Steam Machine verified/playable) |

<p align="center">
  <img src="docs/screenshot-de-combination.png" alt="Heroic filtered by the default combination #3" width="800">
  <br><sub>The combinations appear at the top of the list, here <i>#3 Controller + Steam Machine or SteamOS</i> (German language)</sub>
</p>

**Rules** use the keys from the sections, written as `group.key` (e.g. `controller.full`, `mode.coop`, `genre.rpg`, `machine.verified`, `steamos.compatible`, `metacritic.90`, `reviews.very_positive`):

| Operator | Meaning |
|---|---|
| `&` or `and` | AND |
| `\|` or `or` | OR |
| `!` or `not` | NOT |
| `( )` | grouping |

Add your own combinations as `[combo:4]`, `[combo:5]`, and so on. `name.xx` sets the name per language; a single `name = …` works for all languages.

**At the top:** combinations get the prefix `#1`, `#2`, … Punctuation sorts before letters, and the script also writes combinations first into Heroic's configuration, so they appear at the top of the category list. Change the prefix with `combo_prefix` (`{n}` is the number).

Switching a category off only hides it. Combinations still use it, so you can, for example, switch off the whole Steam Deck group and still use `deck.verified` in a rule.

## 🔍 Games that are not found

1. Try again with improved search and PCGamingWiki:
   ```bash
   python3 heroic_autotag.py --retry-unknown
   ```
2. For what is left, create a template:
   ```bash
   python3 heroic_autotag.py --template
   ```
   This writes `~/.config/heroic-autotag/custom_mapping.txt`. Remove the `#` in front of a line and add either a Steam AppID / Steam link, or categories directly:
   ```
   Some Game = https://store.steampowered.com/app/123456/
   Other Game = Controller: full, Genre: RPG
   ```

Alternatively, simply assign categories to such games in Heroic itself. The script keeps them.

## 🎮 Steam Machine / Steam Deck (Game Mode)

The Heroic Flatpak is detected automatically. To run the script from Game Mode with a controller:

1. Switch to Desktop Mode and clone or download the repository, e.g. to `~/heroic-autotag`.
2. Make the launcher executable:
   ```bash
   chmod +x ~/heroic-autotag/steam-gamemode.sh
   ```
3. In Steam: **Games → Add a Non-Steam Game to My Library → Browse**, set the file type to *All files* and select `steam-gamemode.sh`.
4. Optional: in the shortcut's properties, rename it (e.g. "Heroic Autotag") and add launch options such as `--language de`.
5. Back in Game Mode, start the shortcut. A full-screen terminal shows the progress and closes itself 20 seconds after it finishes. The output is also saved to `~/.cache/heroic-autotag/last-run.log`.

Heroic must not be running at the same time. The first run on a large library takes a while; you can copy the cache file from another PC to skip it (see below).

## 🔄 Updating

- **New games:** open Heroic once so it refreshes its library, close it, then run the script again. Only new games are fetched.
- **Changed ratings:** `--refresh 30` fetches entries older than 30 days again.

## 📁 Files

| File | Purpose |
|---|---|
| `~/.config/heroic/store/config.json` | Heroic's configuration (native) |
| `~/.var/app/com.heroicgameslauncher.hgl/config/heroic/store/config.json` | Heroic's configuration (Flatpak) |
| `config.json.bak-DATE-TIME` | backup created before every write, next to `config.json` |
| `~/.cache/heroic-autotag/cache.json` | cache, keyed by game title, can be copied to other devices |
| `~/.config/heroic-autotag/categories.ini` | settings: categories on/off, combinations |
| `~/.config/heroic-autotag/custom_mapping.txt` | your custom mappings |
| `~/.cache/heroic-autotag/state.json` | remembers the combination names, so renamed combinations are cleaned up |

**Undo:** close Heroic and copy a backup over `config.json`.

## 🔧 Troubleshooting

First steps for almost every problem:

```bash
python3 heroic_autotag.py --help               # all options
python3 heroic_autotag.py --dry-run            # what would be written, without writing
python3 heroic_autotag.py --test "Title" -v    # what Steam / PCGamingWiki return for one game
```

<details>
<summary><b>"No Heroic installation found"</b></summary>

The script looks for `~/.config/heroic` (native) and `~/.var/app/com.heroicgameslauncher.hgl` (Flatpak). Start Heroic once, log in to your stores and let the library load. If both installations exist, the most recently used one is taken; force one with `--native` or `--flatpak`.
</details>

<details>
<summary><b>"No games found"</b></summary>

Heroic has not saved its library yet. Open Heroic, wait until all stores are loaded, close it and run the script again.
</details>

<details>
<summary><b>"Heroic is still running"</b></summary>

Heroic overwrites its configuration when it closes, so the script only writes while Heroic is closed. Quit Heroic completely, including the tray icon. For the Flatpak version:

```bash
flatpak kill com.heroicgameslauncher.hgl
```

You don't have to wait for the slow part: `--collect` works while Heroic is open, `--write` afterwards takes only seconds.
</details>

<details>
<summary><b>The categories don't show up in Heroic</b></summary>

- Did the run end with "Done! Backup: …"? With `--dry-run` or `--collect` nothing is written.
- Restart Heroic; it reads the categories only at startup.
- Heroic's **Console Mode** doesn't show custom categories at the moment. Use the normal interface.
- A category is only created if at least one game matches (genres: at least two, see `genre_min_games`).
</details>

<details>
<summary><b>A game is in the wrong categories or not found</b></summary>

1. Check what the script finds: `python3 heroic_autotag.py --test "Title" -v`
2. If the wrong Steam game was matched or none at all, add the right one to the [custom mapping file](#-games-that-are-not-found), e.g. `Title = https://store.steampowered.com/app/123456/`
3. Run the script again. Games that were not found before can be searched again with `--retry-unknown`.
</details>

<details>
<summary><b>"Steam/PCGW is throttling … all threads wait"</b> or network errors</summary>

Steam limits how many requests are allowed. The script waits automatically and continues; nothing is lost. If it happens often, use fewer threads: `--threads 2`. Games with a network error are fetched again on the next run.
</details>

<details>
<summary><b>Ratings are missing for some games</b></summary>

- **Metacritic** only exists for games that Steam or PCGamingWiki list with a score, mostly larger titles.
- **Steam reviews** need a Steam match and a minimum number of reviews; games found only on PCGamingWiki get none.
- Ratings change over time: `--refresh 30` fetches entries older than 30 days again.
</details>

<details>
<summary><b>"Error in categories.ini"</b></summary>

The message names the section and the problem, e.g. an unknown key in a rule (`[combo:4] unknown category key 'mode.koop'`). The keys are listed in the file itself. To start over with the defaults:

```bash
python3 heroic_autotag.py --init-config --force
```
</details>

<details>
<summary><b>Wrong language</b></summary>

The language follows your system language. Set it with `--language de` or permanently with `language = de` in `categories.ini`. When you switch, the categories in the old language are replaced.
</details>

<details>
<summary><b>My own category was changed</b></summary>

Names starting with a script prefix (`Controller: `, `Mode: `, `Genre: `, `Metacritic: `, … in any of the five languages) or with the combination prefix (`#1 …`) belong to the script and are rebuilt on every run. Rename your own category, e.g. `My co-op games`, then restore it from a backup (see below).
</details>

<details>
<summary><b>Undo or start from scratch</b></summary>

- **Undo a run:** close Heroic and copy a backup `config.json.bak-DATE-TIME` over `config.json` (both in Heroic's `store` folder, see [Files](#-files)).
- **Fetch everything again:** `python3 heroic_autotag.py --new`
</details>

<details>
<summary><b>Game Mode: the window closes too fast</b></summary>

The output of the last run is saved in `~/.cache/heroic-autotag/last-run.log`. The window stays open for 20 seconds; change that with the launch option `WAIT=60 %command%` in the shortcut's properties.
</details>

## ⚠️ Limitations

- **Heroic's Console Mode** currently only filters by store and does not show custom categories. The categories are visible in the normal Heroic interface.
- **Steam collections** in SteamOS Game Mode are separate from Heroic's categories and are not changed.
- **SteamOS compatibility** is read from an undocumented Steam field and may stay empty.
- Games from **PCGamingWiki** get no Steam Machine / Steam Deck / SteamOS ratings and no Steam reviews, since only Steam provides them.
- **Metacritic** scores exist only for games that Steam or PCGamingWiki list with a score, mostly larger titles.
- Heroic itself cannot **sort** by rating; use the categories to filter or `--top` for a ranked list.
- Steam's store endpoints are not an official API and may change.

## 🌐 Data sources

- Steam store (public store endpoints)
- [PCGamingWiki](https://www.pcgamingwiki.com)

This project is not affiliated with Valve, Heroic Games Launcher, Epic Games, GOG, Amazon or PCGamingWiki.

## 📄 License

[MIT](LICENSE): you may use, change, fork and share this project freely, as long as the copyright notice stays in it.
