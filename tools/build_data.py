#!/usr/bin/python3
"""Download Unicode emoji data and CLDR keywords, then write workflow/emojis.json.

The file ships with empty seed and custom objects. Personal scores and keywords
belong in the workflow data directory, not in this repository.
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "workflow", "emojis.json")
SKIN = re.compile("[\U0001F3FB-\U0001F3FF\uFE0F]")
EMOJI_TEST = "https://unicode.org/Public/emoji/latest/emoji-test.txt"
CLDR = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json"
ANNOTATION_URLS = {
    "en": (
        CLDR + "/cldr-annotations-derived-full/annotationsDerived/en/annotations.json",
        CLDR + "/cldr-annotations-full/annotations/en/annotations.json",
    ),
    "fa": (
        CLDR + "/cldr-annotations-derived-full/annotationsDerived/fa/annotations.json",
        CLDR + "/cldr-annotations-full/annotations/fa/annotations.json",
    ),
}
TONE_INDEX = {
    "light skin tone": 0,
    "medium-light skin tone": 1,
    "medium skin tone": 2,
    "medium-dark skin tone": 3,
    "dark skin tone": 4,
}
SYMBOLS = (
    "→←↑↓↔↕⇒⇐⇔↩↪⤴⤵⟶⟵•·…–—«»“”‘’„‹›©®™°±×÷≈≠≤≥∞√∑∏∆πµ‰§¶†‡½¼¾⅓⅔⅟"
    "€£¥$¢₺₽₹₩₿﷼✓✔✗✘★☆♠♣♥♦⌘⌥⇧⌃⎋⏎⌫⌦⇥⇪⏏␣♪♫☐☑☒¬∴∵∈∉∩∪⊂⊃∀∃∅∇∂∫"
)
EXTRA = {
    "\uf8ff": ("apple logo", ["apple", "mac", "logo"]),
    "﷼": ("rial sign", ["rial", "iran", "toman", "currency"]),
    "⌘": ("command key", ["cmd", "command", "mac"]),
    "⌥": ("option key", ["opt", "option", "alt"]),
    "⇧": ("shift key", ["shift"]),
    "⌃": ("control key", ["ctrl", "control"]),
    "⎋": ("escape key", ["esc", "escape"]),
    "⏎": ("return key", ["return", "enter"]),
    "⌫": ("delete key", ["delete", "backspace"]),
    "⌦": ("forward delete key", ["delete", "del"]),
    "⇥": ("tab key", ["tab"]),
    "⇪": ("caps lock key", ["caps", "capslock"]),
    "⏏": ("eject key", ["eject"]),
}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "alfred-emoji-picker-build"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except OSError as exc:
        raise SystemExit(f"download failed: {url}\n{exc}") from exc


def annotation_map(payload):
    if "annotationsDerived" in payload:
        block = payload["annotationsDerived"]
    elif "annotations" in payload:
        block = payload["annotations"]
    else:
        raise SystemExit("unrecognized CLDR annotation file")
    if isinstance(block, dict) and "annotations" in block:
        block = block["annotations"]
    if not isinstance(block, dict):
        raise SystemExit("unrecognized CLDR annotation file")
    out = {}
    for key, value in block.items():
        if isinstance(value, dict):
            out[key.replace("\uFE0F", "")] = value
    return out


def load_annotations(lang):
    # Derived keywords first. Full annotations override them for the same emoji.
    merged = {}
    for url in ANNOTATION_URLS[lang]:
        print(f"fetch {url}", file=sys.stderr)
        merged.update(annotation_map(json.loads(fetch(url).decode("utf-8"))))
    return merged


def norm(text):
    return SKIN.sub("", text)


def keywords(record, name):
    found = []
    for word in record.get("default") or []:
        if isinstance(word, str) and word.lower() != name.lower():
            found.append(word)
    return found


def build():
    print(f"fetch {EMOJI_TEST}", file=sys.stderr)
    listing = fetch(EMOJI_TEST).decode("utf-8")
    english, persian = load_annotations("en"), load_annotations("fa")
    order = []
    tones = {}
    group = ""
    line_re = re.compile(r".*# (\S+) E\d+\.\d+ (.+)$")
    for line in listing.splitlines():
        if line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
            continue
        if "; fully-qualified" not in line or group == "Component":
            continue
        matched = line_re.match(line.strip())
        if not matched:
            continue
        char, name = matched.group(1), matched.group(2)
        if "skin tone" in name:
            base_name, tone = name.split(": ", 1)
            index = TONE_INDEX.get(tone)
            if index is not None:
                slot = tones.setdefault(base_name, ["", "", "", "", ""])
                slot[index] = char
            continue
        order.append((char, name, group))

    emojis = []
    for char, name, grp in order:
        key = char.replace("\uFE0F", "")
        en_ann = english.get(key) or {}
        fa_ann = persian.get(key) or {}
        spoken = en_ann.get("tts") or [name]
        title = spoken[0] if spoken else name
        fa_tts = [word for word in (fa_ann.get("tts") or []) if isinstance(word, str)]
        fa_default = [word for word in (fa_ann.get("default") or []) if isinstance(word, str)]
        entry = {
            "e": char,
            "b": norm(char),
            "n": title,
            "k": keywords(en_ann, title),
            "fa": fa_tts + fa_default,
            "g": grp,
        }
        slot = tones.get(name)
        if slot and any(slot):
            entry["t"] = slot
        emojis.append(entry)

    for char in SYMBOLS + "\uf8ff":
        title, words = EXTRA.get(char, (unicodedata.name(char, "symbol").lower(), []))
        emojis.append({"e": char, "b": char, "n": title, "k": list(words) + ["symbol"], "fa": [], "g": "Symbols"})

    payload = {"emojis": emojis, "seed": {}, "custom": {}}
    temporary = OUT + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
    os.replace(temporary, OUT)
    toned = sum(1 for entry in emojis if entry.get("t"))
    print(f"wrote {OUT} emojis={len(emojis)} tones={toned}")


if __name__ == "__main__":
    build()
