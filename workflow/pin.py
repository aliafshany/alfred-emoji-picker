#!/usr/bin/python3
"""Pin, unpin, or move up a pinned emoji. Pinned emoji sit at the top of the empty picker, in pin order.
pinop=toggle (⌥↩): pin or unpin.  pinop=up (⌃↩): move a pinned emoji up one place, or pin it."""
import json
import os
import sys

BUNDLE = "com.aliafshany.emoji-picker"
base = sys.argv[1] if len(sys.argv) > 1 else ""
op = os.environ.get("pinop", "toggle")
directory = os.environ.get("alfred_workflow_data") or os.path.expanduser(
    "~/Library/Application Support/Alfred/Workflow Data/" + BUNDLE)
path = os.path.join(directory, "pins.json")

try:
    with open(path, encoding="utf-8") as handle:
        pins = json.load(handle)
    if not isinstance(pins, list):
        pins = []
except (OSError, ValueError):
    pins = []

if base:
    if base not in pins:
        pins.append(base)
    elif op == "up":
        i = pins.index(base)
        if i > 0:
            pins[i - 1], pins[i] = pins[i], pins[i - 1]
    else:
        pins.remove(base)
    os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(pins, handle, ensure_ascii=False)
    os.replace(temporary, path)
