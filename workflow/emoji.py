#!/usr/bin/python3
"""Alfred Script Filter: emoji search with a Tab basket and local frecency."""
import json
import math
import os
import re
import sys
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "emojis.json"), encoding="utf-8") as handle:
    DATA = json.load(handle)
EMOJIS = DATA["emojis"]


def build_index(entries):
    """First entry for a base wins, so the emoji-presentation form (FE0F) beats its text twin.
    uid is unique per entry: a later twin gets a codepoint suffix."""
    by_base = {}
    seen = set()
    for entry in entries:
        by_base.setdefault(entry["b"], entry)
        uid = entry["b"]
        if uid in seen:
            uid = entry["b"] + "|" + "-".join("%x" % ord(ch) for ch in entry["e"])
        seen.add(uid)
        entry["_uid"] = uid
    return by_base


BY_BASE = build_index(EMOJIS)
MAX_RESULTS = 60
BUNDLE = "com.aliafshany.emoji-picker"
SKIN = re.compile("[\U0001F3FB-\U0001F3FF\uFE0F]")
TONE_INDEX = {
    "light": 0,
    "medium-light": 1,
    "medium": 2,
    "medium-dark": 3,
    "dark": 4,
}


def data_dir():
    return os.environ.get("alfred_workflow_data") or os.path.expanduser(
        "~/Library/Application Support/Alfred/Workflow Data/" + BUNDLE)


def usage_path():
    return os.path.join(data_dir(), "usage.json")


def load_usage():
    try:
        with open(usage_path(), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_seed():
    """Optional per-user scores and keywords. The shipped data file has neither."""
    path = os.path.join(data_dir(), "seed.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}, {}
    if not isinstance(data, dict):
        return {}, {}
    seed, custom = {}, {}
    raw_seed = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    for key, score in raw_seed.items():
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        seed[SKIN.sub("", str(key))] = float(score)
    raw_custom = data.get("custom") if isinstance(data.get("custom"), dict) else {}
    for key, words in raw_custom.items():
        if not isinstance(words, list):
            continue
        clean = [str(word) for word in words if isinstance(word, str) and word]
        if clean:
            custom[SKIN.sub("", str(key))] = clean
    return seed, custom


SEED, CUSTOM = load_seed()


def frecency(base, usage, now):
    score = SEED.get(base, 0.0)
    record = usage.get(base)
    if isinstance(record, list) and len(record) >= 2:
        try:
            count = float(record[0])
            last = float(record[1])
        except (TypeError, ValueError):
            return score
        age_days = max(0.0, (now - last) / 86400.0)
        score += count * 10.0 * math.exp(-age_days / 30.0) + 50.0 * math.exp(-age_days / 3.0)
    return score


def words_of(e):
    ws = set(e["n"].lower().replace(":", " ").replace("-", " ").split())
    for keyword in e["k"] + CUSTOM.get(e["b"], []) + e["fa"]:
        ws.update(keyword.lower().replace("-", " ").split())
    return ws


def match(e, q, qwords):
    name = e["n"].lower()
    custom = [c.lower() for c in CUSTOM.get(e["b"], [])]
    if q in custom:
        return 120
    if name == q:
        return 110
    if name.startswith(q):
        return 90
    ws = words_of(e)
    if all(any(w.startswith(qw) for w in ws) for qw in qwords):
        namews = name.replace(":", " ").replace("-", " ").split()
        if all(any(w.startswith(qw) for w in namews) for qw in qwords):
            return 70
        if any(k.lower() == q for k in e["k"] + custom + e["fa"]):
            return 65
        return 50
    if len(q) >= 3 and q in name:
        return 30
    return 0


def glyphs(entry):
    found = [entry.get("e") or "", entry.get("b") or ""]
    found.extend(entry.get("t") or [])
    return found


ALL = {glyph for entry in EMOJIS for glyph in glyphs(entry) if glyph and not glyph.isascii()}
LONGEST = max((len(glyph) for glyph in ALL), default=1)
BASKET, REST, LAST = "", "", ""  # emojis queued with Tab, search text after them, last queued


def split_basket(raw):
    """Leading emojis in the query are the basket; the rest is the search."""
    basket, index = [], 0
    while index < len(raw):
        if raw[index] == " ":
            index += 1
            continue
        for size in range(min(LONGEST, len(raw) - index), 0, -1):
            if raw[index:index + size] in ALL:
                basket.append(raw[index:index + size])
                index += size
                break
        else:
            break
    return "".join(basket), raw[index:].strip()


def with_skin(entry):
    choice = (os.environ.get("skin_tone") or "none").strip().lower()
    index = TONE_INDEX.get(choice)
    tones = entry.get("t") or []
    if index is None or index >= len(tones) or not tones[index]:
        return entry
    shown = dict(entry)
    shown["e"] = tones[index]
    return shown


CACHE = os.environ.get("alfred_workflow_cache") or os.path.expanduser(
    f"~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/{BUNDLE}")
ICON_DIR = os.path.join(CACHE, "icons")


def icon_stem(glyph):
    return "-".join("%x" % ord(c) for c in glyph)


def icon_for(glyph):
    path = os.path.join(ICON_DIR, icon_stem(glyph) + ".png")
    return {"icon": {"path": path}} if os.path.exists(path) else {}


def ensure_icons():
    """Render emoji icons once, in the background, for the current skin tone.
    Needs swiftc (Xcode Command Line Tools); without it rows simply keep the emoji in the title."""
    tone = (os.environ.get("skin_tone") or "none").strip().lower()
    done = os.path.join(ICON_DIR, f".done-{tone}")
    lock = os.path.join(CACHE, "icons.lock")
    if os.path.exists(done):
        return
    try:
        if time.time() - os.path.getmtime(lock) < 300:
            return
    except OSError:
        pass
    os.makedirs(ICON_DIR, exist_ok=True)
    listing = os.path.join(CACHE, "icons.list")
    with open(lock, "w"), open(listing, "w", encoding="utf-8") as f:
        for entry in EMOJIS:
            glyph = with_skin(entry)["e"]
            f.write(f"{icon_stem(glyph)}\t{'s' if entry['g'] == 'Symbols' else 'e'}\t{glyph}\n")
    # Rebuild when the binary is missing or older than render_icons.swift.
    script = '[ -x "$1" ] && [ "$1" -nt "$2" ] || xcrun swiftc -O "$2" -o "$1" || exit 0; "$1" "$3" < "$4" && touch "$5"; rm -f "$6"'
    subprocess.Popen(
        ["/bin/sh", "-c", script, "sh", os.path.join(CACHE, "render_icons"),
         os.path.join(HERE, "render_icons.swift"), ICON_DIR, listing, done, lock],
        start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# Shown on an empty query until your own usage takes over.
POPULAR = "😂 ❤️ 🤣 👍 😭 🙏 😘 🥰 😍 😊 🎉 😁 🥺 😅 🔥 🤦 🤷 🙄 😆 🤗 😉 🤔 👏 🙂 😳 🥳 😎 👌 💪 ✨ 👀 😏 😢 💯 🙌 😡 😜 🙈".split()


def load_pins():
    try:
        with open(os.path.join(data_dir(), "pins.json"), encoding="utf-8") as handle:
            pins = json.load(handle)
    except (OSError, ValueError):
        return []
    return [p for p in pins if isinstance(p, str)] if isinstance(pins, list) else []


PINS = load_pins()
RAW = ""  # the full query, so ⌥↩/⌃↩ can reopen the picker where you were


def item(entry):
    entry = with_skin(entry)
    keywords = [k for k in (CUSTOM.get(entry["b"], []) + entry["k"]) if k.lower() != entry["n"].lower()][:6]
    subtitle = ", ".join(keywords) if keywords else entry["g"]
    pinned = entry["b"] in PINS
    if pinned:
        subtitle = "📌 " + subtitle
    # Return pastes exactly the basket when the highlight sits on the emoji just added with Tab.
    # Picking a different emoji and pressing Return appends it.
    out = BASKET if BASKET and LAST in (entry["e"], entry["b"]) else BASKET + entry["e"]
    icon = icon_for(entry["e"])
    return {
        **icon,
        # uid changes with the basket so Alfred re-highlights the Paste row after each Tab
        "uid": (f"{entry.get('_uid', entry['b'])}|{len(BASKET)}" if BASKET
                else entry.get("_uid", entry["b"])),
        "title": entry["n"] if icon else f"{entry['e']}   {entry['n']}",
        "subtitle": subtitle,
        "arg": out,
        "autocomplete": f"{BASKET}{entry['e']} {REST}",
        "variables": {"base": entry["b"]},
        "text": {"copy": entry["e"], "largetype": entry["e"]},
        "mods": {
            "cmd": {
                "arg": out,
                "subtitle": "Copy only (no paste)",
                "variables": {"base": entry["b"]},
            },
            "alt": {
                "arg": entry["b"],
                "subtitle": "Unpin" if pinned else "📌 Pin to the top",
                "variables": {"q": RAW, "pinop": "toggle"},
            },
            "ctrl": {
                "arg": entry["b"],
                "subtitle": "Move up among pinned" if pinned else "📌 Pin to the top",
                "variables": {"q": RAW, "pinop": "up"},
            },
        },
    }


def last_of(basket):
    return next(
        (piece for piece in (basket[-size:] for size in range(min(LONGEST, len(basket)), 0, -1)) if piece in ALL),
        "",
    )


def basket_row():
    last = LAST
    base = SKIN.sub("", last)
    return {
        **icon_for(last),
        "uid": f"__basket__|{len(BASKET)}",
        "title": f"Paste  {BASKET}",
        "subtitle": f"↩ paste all  ·  ⇥ one more {last}  ·  ↓ then ⇥ to add another",
        "arg": BASKET,
        "autocomplete": f"{BASKET}{last} {REST}",
        "variables": {"base": base},
        "text": {"copy": BASKET, "largetype": BASKET},
        "mods": {"cmd": {"arg": BASKET, "subtitle": "Copy all (no paste)", "variables": {"base": base}}},
    }


def main():
    global BASKET, REST, LAST, RAW
    RAW = " ".join(sys.argv[1:]).strip()
    BASKET, REST = split_basket(RAW)
    LAST = last_of(BASKET)
    ensure_icons()
    query = REST.lower()
    usage = load_usage()
    now = time.time()
    if not query:
        pinned = [base for base in PINS if base in BY_BASE]
        ranked = pinned + sorted(
            (base for base in set(SEED) | set(usage) if base in BY_BASE and base not in pinned),
            key=lambda base: -frecency(base, usage, now),
        )
        if len(ranked) < 12:  # new install: pad with popular emoji
            ranked += [b for b in (SKIN.sub("", p) for p in POPULAR) if b in BY_BASE and b not in ranked]
        items = [item(BY_BASE[base]) for base in ranked[:MAX_RESULTS]]
    else:
        qwords = query.split()
        scored = []
        for index, entry in enumerate(EMOJIS):
            score = match(entry, query, qwords)
            if score:
                boost = min(40.0, 8.0 * math.log1p(frecency(entry["b"], usage, now)))
                boost += 30.0 if entry["b"] in PINS else 0.0
                scored.append((score + boost, -index, entry))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        items = [item(entry) for _, _, entry in scored[:MAX_RESULTS]]
    if BASKET:
        items = [basket_row()] + items
    if not items:
        items = [{"title": "No emoji found", "subtitle": query, "valid": False}]
    print(json.dumps({"skipknowledge": True, "items": items}, ensure_ascii=False))


if __name__ == "__main__":
    main()
