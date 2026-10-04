#!/usr/bin/python3
"""Record emoji usage for frecency, then echo the text for the clipboard output.
Every emoji in a pasted basket counts, not just the last one."""
import json
import os
import re
import sys
import time

BUNDLE = "com.aliafshany.emoji-picker"
HERE = os.path.dirname(os.path.abspath(__file__))
SKIN = re.compile("[\U0001F3FB-\U0001F3FF️]")


def bases_in(text):
    """Split pasted text into base emoji (no skin tone, no variation selector)."""
    try:
        with open(os.path.join(HERE, "emojis.json"), encoding="utf-8") as handle:
            entries = json.load(handle)["emojis"]
    except (OSError, ValueError, KeyError):
        return [os.environ.get("base") or text]
    glyphs = set()
    for entry in entries:
        for glyph in [entry.get("e"), entry.get("b")] + list(entry.get("t") or []):
            if glyph and not glyph.isascii():
                glyphs.add(glyph)
    longest = max(len(g) for g in glyphs)
    found, i = [], 0
    while i < len(text):
        for size in range(min(longest, len(text) - i), 0, -1):
            if text[i:i + size] in glyphs:
                found.append(SKIN.sub("", text[i:i + size]))
                i += size
                break
        else:
            i += 1
    return found or [os.environ.get("base") or text]


text = sys.argv[1] if len(sys.argv) > 1 else ""
directory = os.environ.get("alfred_workflow_data") or os.path.expanduser(
    "~/Library/Application Support/Alfred/Workflow Data/" + BUNDLE)
path = os.path.join(directory, "usage.json")
try:
    os.makedirs(directory, exist_ok=True)
    try:
        with open(path, encoding="utf-8") as handle:
            usage = json.load(handle)
        if not isinstance(usage, dict):
            usage = {}
    except (OSError, ValueError):
        usage = {}
    now = time.time()
    for base in bases_in(text):
        previous = usage.get(base)
        try:
            count = int(previous[0]) if isinstance(previous, list) and previous else 0
        except (TypeError, ValueError, IndexError):
            count = 0
        usage[base] = [count + 1, now]
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(usage, handle, ensure_ascii=False)
    os.replace(temporary, path)
except OSError:
    pass
sys.stdout.write(text)
