#!/usr/bin/python3
"""Alfred Grid View source: every emoji, pins then frecency then file order."""
import json
import sys
import time

import emoji


def match_text(entry):
    parts = [entry["n"]]
    parts.extend(entry.get("k") or [])
    parts.extend(entry.get("fa") or [])
    parts.extend(emoji.CUSTOM.get(entry["b"], []))
    return " ".join(str(part) for part in parts if part)


def grid_item(entry):
    shown = emoji.with_skin(entry)
    glyph = shown["e"]
    icon = emoji.icon_for(glyph)
    item = {
        "title": entry["n"] if icon else "%s %s" % (glyph, entry["n"]),
        "arg": glyph,
        "match": match_text(entry),
        "variables": {"base": entry["b"]},
    }
    if icon:
        item["icon"] = icon["icon"]
    return item


def ordered_entries():
    """Pins in pin order, then usage/seed by frecency, then the rest in file order."""
    usage = emoji.load_usage()
    now = time.time()
    by_base = {}
    for index, entry in enumerate(emoji.EMOJIS):
        by_base.setdefault(entry["b"], []).append((index, entry))
    seen = set()
    ordered = []

    def take(base):
        for index, entry in by_base.get(base, ()):
            if index in seen:
                continue
            seen.add(index)
            ordered.append(entry)

    pinned = set()
    for base in emoji.PINS:
        if base in by_base and base not in pinned:
            pinned.add(base)
            take(base)

    ranked = [
        base for base in set(emoji.SEED) | set(usage)
        if base in by_base and base not in pinned
    ]
    ranked.sort(key=lambda base: (-emoji.frecency(base, usage, now), by_base[base][0][0]))
    for base in ranked:
        take(base)
    for index, entry in enumerate(emoji.EMOJIS):
        if index not in seen:
            ordered.append(entry)
    return ordered


def main():
    emoji.ensure_icons()
    json.dump({"items": [grid_item(entry) for entry in ordered_entries()]}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
