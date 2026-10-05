#!/usr/bin/python3
"""Add slang tags from iAli/emoji-search-workflow into workflow/emojis.json.

Reads arg/match pairs from the slang source. Tags are the comma-separated list
after " : " in match. Variation selectors are stripped before matching arg to
emojis.json "b". New tags are lowercase, deduped, and appended after existing "k".
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMOJI_PATH = os.path.join(ROOT, "workflow", "emojis.json")
PAIR = re.compile(
    r'"match"\s*:\s*"((?:\\.|[^"\\])*)"\s*,\s*"arg"\s*:\s*"((?:\\.|[^"\\])*)"'
)
VS = str.maketrans("", "", "\uFE0E\uFE0F")


def unescape(raw):
    return json.loads('"%s"' % raw)


def strip_vs(text):
    return text.translate(VS)


def tags_from(match):
    if " : " not in match:
        return []
    found, seen = [], set()
    for part in match.split(" : ", 1)[1].split(","):
        tag = part.strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            found.append(tag)
    return found


def slang_by_base(text):
    pairs = PAIR.findall(text)
    wanted, seen = {}, {}
    for raw_match, raw_arg in pairs:
        tags = tags_from(unescape(raw_match))
        if not tags:
            continue
        key = strip_vs(unescape(raw_arg))
        bag = seen.setdefault(key, set())
        row = wanted.setdefault(key, [])
        for tag in tags:
            if tag not in bag:
                bag.add(tag)
                row.append(tag)
    return wanted, len(pairs)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: merge_tags.py <iAli emoji source file> [emojis.json]")
    slang_path = sys.argv[1]
    emoji_path = sys.argv[2] if len(sys.argv) > 2 else EMOJI_PATH
    with open(slang_path, encoding="utf-8") as handle:
        wanted, pairs = slang_by_base(handle.read())
    with open(emoji_path, encoding="utf-8") as handle:
        data = json.load(handle)
    gained = 0
    added = 0
    matched = set()
    for entry in data["emojis"]:
        key = strip_vs(entry.get("b") or "")
        incoming = wanted.get(key)
        if not incoming:
            continue
        matched.add(key)
        have = {tag.lower() for tag in entry.get("k") or [] if isinstance(tag, str)}
        grew = False
        entry.setdefault("k", [])
        for tag in incoming:
            if tag in have:
                continue
            entry["k"].append(tag)
            have.add(tag)
            added += 1
            grew = True
        if grew:
            gained += 1
    temporary = emoji_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
    os.replace(temporary, emoji_path)
    print("slang pairs: %d" % pairs)
    print("slang keys with tags: %d" % len(wanted))
    print("matched bases: %d" % len(matched))
    print("unmatched slang keys: %d" % (len(wanted) - len(matched)))
    print("entries gained tags: %d" % gained)
    print("tags added: %d" % added)


if __name__ == "__main__":
    main()
