#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$root/dist"
out="$root/dist/Emoji Picker.alfredworkflow"
rm -f "$out"
(
  cd "$root/workflow"
  zip -X -r "$out" info.plist emoji.py record.py pin.py emojis.json render_icons.swift
)
echo "$out"
