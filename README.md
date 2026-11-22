# Emoji Picker

Alfred workflow to search Unicode emoji and paste or copy the one you want. It opens a native Alfred UI grid: your pinned and recent emoji on top, then every emoji, with Tab stacking several before you paste. It learns which ones you use.

> **Version 2 needs Alfred 6.** It is built on Alfred UI, which Alfred 5 doesn't have. On Alfred 5, use [v1.1.1](https://github.com/aliafshany/alfred-emoji-picker/releases/tag/v1.1.1).

## Install

Download `Emoji Picker.alfredworkflow` from Releases, or take `dist/Emoji Picker.alfredworkflow` from this repository. Double-click the file and Alfred imports it.

## Setup

The Hotkey trigger ships with no shortcut. Alfred strips hotkeys on import.

1. Open the workflow in Alfred Preferences.
2. Double-click the Hotkey object.
3. Tap Control twice. That assigns a double-tap Control hotkey.

Skin tone is a workflow setting. Open **Configure Workflow…** and set **Skin tone** to None, Light, Medium-Light, Medium, Medium-Dark, or Dark. None keeps the yellow emoji.

To bring over frecency and custom keywords from a Raycast 2 export:

```bash
pip3 install cryptography
python3 tools/import_raycast.py /path/to/export.rayconfig
```

The script asks for the Raycast passphrase and writes `seed.json` into Alfred's workflow data folder for this workflow.

## Usage

| Key | Action |
| --- | --- |
| `emoji` or the double-tap hotkey | Open the grid |
| type | Search names and keywords, in English or Persian |
| arrow keys | Move around the grid; the footer names the selected emoji and its group |
| Return | Paste into the frontmost app (the basket, when it has emoji) |
| Tab | Add the selected emoji to the basket, top right |
| Command-B | Add to the basket, same as Tab |
| Command-Delete | Empty the basket |
| Command-Return | Copy only |
| Command-P | Pin the selected emoji, or unpin it |
| Command-U / Command-D | Move a pinned emoji one place earlier / later |
| empty search | Pinned emoji (amber), then your most-used (grey): two rows; below them every emoji in Unicode order |

Emoji your version of macOS can't draw yet (newer than its emoji font) are left out, so the grid never shows a "?" box. The check runs once per macOS build.

## How it works

The panel lives in `emoji.alfredui`. Its backend, `emoji.alfredui/grid`, runs `emoji.py` for every search. `emoji.py` reads `emojis.json` and ranks matches against the Unicode name, English and Persian CLDR keywords, and a fixed set of symbols: arrows, punctuation, currency (including ﷼), and the Mac keys ⌘ ⌥ ⇧ ⌃ and their usual aliases (`cmd`, `opt`, `shift`, `ctrl`, and so on). With an empty search the backend shows the pins and most-used first, then all of `emojis.json`.

The search box is a one-line text area rather than a text field, because a text field keeps Tab for moving focus. In a text area Tab arrives as a character, which the backend turns into "add to basket"; Return arrives the same way and pastes.

`emoji_support.swift` lists the emoji that Core Text can only draw with the LastResort font (the "?" box). The backend compiles it with `swiftc` into Alfred's workflow cache and caches its answer per macOS build.

An exact custom keyword ranks first, then an exact name, then a name prefix, then other keyword hits. Recent and repeated use adds a frecency bonus.

Return runs `record.py`, which stores a count and a timestamp for every emoji in the pasted text in `$alfred_workflow_data/usage.json`, then copies the text to the clipboard. Return pastes it. Command-Return only copies. Both clipboard writes are transient.

`emojis.json` stores up to five skin-tone variants on each emoji that has them (`t`: light, medium-light, medium, medium-dark, dark). The `skin_tone` setting picks one when the list is drawn. The file's `seed` and `custom` objects are empty. Per-user data loads from `$alfred_workflow_data/seed.json` when that file exists:

```json
{"seed": {"👍": 200}, "custom": {"👍": ["ok"]}}
```

Keys are the base emoji, with no skin tone and no variation selector. `seed` maps a base emoji to a number. `custom` maps a base emoji to a list of extra keywords.

Rebuild the data file and the workflow archive with:

```bash
python3 tools/build_data.py
bash tools/package.sh
```

`tools/build_data.py` downloads `emoji-test.txt` and the English and Persian CLDR annotation files, then writes `workflow/emojis.json`. `tools/package.sh` zips the workflow folder into `dist/Emoji Picker.alfredworkflow`.

Pins live in `$alfred_workflow_data/pins.json` as an ordered list of base emoji. Command-P, Command-U and Command-D update it and redraw the grid with the same emoji selected.

## Privacy

Search and paste stay on this Mac. Usage and an optional `seed.json` stay in Alfred's workflow data folder.

`tools/build_data.py` downloads Unicode and CLDR files when you rebuild `emojis.json`. The importer reads the export you pass in and writes `seed.json` on this Mac. The shipped workflow contains no usage history and no custom keywords.

## Requirements

- Alfred 6 with the Powerpack (Alfred UI)
- macOS
- `/usr/bin/python3`
- Xcode Command Line Tools (`xcode-select --install`), for the check that hides emoji your Mac can't draw; without them every emoji is listed
- `pip3 install cryptography`, only if you run the Raycast importer

## Data

Emoji characters and the names in `emoji-test.txt` come from the Unicode Consortium. English and Persian keywords come from Unicode CLDR annotations and derived annotations. Both are used under the [Unicode License v3](https://www.unicode.org/license.txt).

Extra slang tags (`lmao`, `rofl`, and others) come from [iAli/emoji-search-workflow](https://github.com/iAli/emoji-search-workflow), Copyright (c) 2026 iAli, MIT License. `tools/merge_tags.py` merges them into `emojis.json`.

## License

MIT. See [LICENSE](LICENSE).
