# Emoji Picker

Alfred workflow to search Unicode emoji and paste or copy the one you want. Each row shows the emoji as a large icon, Tab stacks several emoji without closing Alfred, and the list learns which ones you use.

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
| `emoji` | Open the picker |
| type | Search names and keywords, in English or Persian |
| Return | Paste into the frontmost app |
| Command-Return | Copy only |
| Tab | Add the selected emoji to the basket and keep Alfred open |
| Return on **Paste** | Paste every emoji in the basket |
| Return on the emoji just added with Tab | Paste the basket once, without appending that emoji again |
| Option-Return | Pin the emoji to the top of the empty picker, or unpin it |
| Control-Return | Move a pinned emoji up one place (pins it if it isn't pinned) |
| empty query | Pinned emoji first, then your most-used |

Emoji characters at the start of the query are the basket. Tab appends the highlighted emoji and leaves the window open. A **Paste** row stays on top. Its result id changes with the basket, so the highlight comes back to **Paste** after each Tab.

## How it works

The `emoji` Script Filter reads `emojis.json` and ranks matches against the Unicode name, English and Persian CLDR keywords, and a fixed set of symbols: arrows, punctuation, currency (including ﷼), and the Mac keys ⌘ ⌥ ⇧ ⌃ and their usual aliases (`cmd`, `opt`, `shift`, `ctrl`, and so on).

An exact custom keyword ranks first, then an exact name, then a name prefix, then other keyword hits. Recent and repeated use adds a frecency bonus.

Return runs `record.py`, which stores a count and a timestamp for every emoji in the pasted text in `$alfred_workflow_data/usage.json`, then copies the text to the clipboard. Return pastes it. Command-Return only copies. Both clipboard writes are transient.

`emojis.json` stores up to five skin-tone variants on each emoji that has them (`t`: light, medium-light, medium, medium-dark, dark). The `skin_tone` setting picks one when the list is drawn. The file's `seed` and `custom` objects are empty. Per-user data loads from `$alfred_workflow_data/seed.json` when that file exists:

```json
{"seed": {"👍": 200}, "custom": {"👍": ["ok"]}}
```

Keys are the base emoji, with no skin tone and no variation selector. `seed` maps a base emoji to a number. `custom` maps a base emoji to a list of extra keywords.

Row icons are drawn once with Apple's emoji font. On first use, `emoji.py` compiles `render_icons.swift` with `xcrun swiftc` and renders a 128 px PNG per emoji into Alfred's workflow cache folder. That takes about 10 seconds in the background and about 27 MB, and happens again if you change the skin tone. Without the Xcode Command Line Tools the icons are skipped and each row shows the emoji in its title instead.

Rebuild the data file and the workflow archive with:

```bash
python3 tools/build_data.py
bash tools/package.sh
```

`tools/build_data.py` downloads `emoji-test.txt` and the English and Persian CLDR annotation files, then writes `workflow/emojis.json`. `tools/package.sh` zips the workflow folder into `dist/Emoji Picker.alfredworkflow`.

Pins live in `$alfred_workflow_data/pins.json` as an ordered list of base emoji. Option-Return and Control-Return update it and reopen the picker on the same query.

## Privacy

Search and paste stay on this Mac. Usage and an optional `seed.json` stay in Alfred's workflow data folder.

`tools/build_data.py` downloads Unicode and CLDR files when you rebuild `emojis.json`. The importer reads the export you pass in and writes `seed.json` on this Mac. The shipped workflow contains no usage history and no custom keywords.

## Requirements

- Alfred 5 with the Powerpack
- macOS
- `/usr/bin/python3`
- Xcode Command Line Tools (`xcode-select --install`), optional, for the large emoji icons
- `pip3 install cryptography`, only if you run the Raycast importer

## Data

Emoji characters and the names in `emoji-test.txt` come from the Unicode Consortium. English and Persian keywords come from Unicode CLDR annotations and derived annotations. Both are used under the [Unicode License v3](https://www.unicode.org/license.txt).

## License

MIT. See [LICENSE](LICENSE).
