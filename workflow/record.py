#!/usr/bin/python3
"""Record emoji usage for frecency, then echo the emoji for the clipboard output."""
import json
import os
import sys
import time

BUNDLE = "com.aliafshany.emoji-picker"
emoji = sys.argv[1] if len(sys.argv) > 1 else ""
base = os.environ.get("base") or emoji
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
    previous = usage.get(base)
    try:
        count = int(previous[0]) if isinstance(previous, list) and previous else 0
    except (TypeError, ValueError, IndexError):
        count = 0
    usage[base] = [count + 1, time.time()]
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(usage, handle, ensure_ascii=False)
    os.replace(temporary, path)
except OSError:
    pass
sys.stdout.write(emoji)
