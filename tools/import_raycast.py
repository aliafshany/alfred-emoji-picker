#!/usr/bin/python3
"""Turn a Raycast 2 .rayconfig export into a local emoji seed.json.

Requires: pip3 install cryptography

The export is RAYCFG3: the bytes RAYCFG3\\n, a little-endian UInt32 header
length, gzip(header JSON), then AES-256-GCM ciphertext with a 16-byte tag.
The header carries hex encryption.iv and encryption.salt, 16 bytes each.
The key is scrypt(passphrase, salt, N=16384, r=8, p=1, dklen=32). The
plaintext is gzip(payload JSON). Only emoji.emojis is read, and only the
symbol, frecencyDate, and customKeywords fields.
"""
import getpass
import gzip
import json
import os
import re
import struct
import sys

BUNDLE = "com.aliafshany.emoji-picker"
MAGIC = b"RAYCFG3\n"
SKIN = re.compile("[\U0001F3FB-\U0001F3FF\uFE0F]")


def data_dir():
    return os.environ.get("alfred_workflow_data") or os.path.expanduser(
        "~/Library/Application Support/Alfred/Workflow Data/" + BUNDLE)


def norm(symbol):
    return SKIN.sub("", symbol)


def load_crypto():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except ImportError:
        print("cryptography is required. Install it with: pip3 install cryptography", file=sys.stderr)
        raise SystemExit(1)
    return AESGCM, Scrypt


def decrypt_rayconfig(blob, passphrase, AESGCM, Scrypt):
    if not isinstance(blob, (bytes, bytearray)) or not blob.startswith(MAGIC):
        raise ValueError("This is not a Raycast .rayconfig file.")
    if len(blob) < len(MAGIC) + 4:
        raise ValueError("This Raycast export is incomplete.")
    offset = len(MAGIC)
    (header_len,) = struct.unpack_from("<I", blob, offset)
    offset += 4
    if header_len <= 0 or offset + header_len > len(blob):
        raise ValueError("This Raycast export is incomplete.")
    try:
        header = json.loads(gzip.decompress(blob[offset:offset + header_len]))
    except (OSError, ValueError) as exc:
        raise ValueError("Could not read the export header.") from exc
    offset += header_len
    try:
        encryption = header["encryption"]
        iv = bytes.fromhex(encryption["iv"])
        salt = bytes.fromhex(encryption["salt"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("The export header has no encryption iv and salt.") from exc
    if len(iv) != 16 or len(salt) != 16:
        raise ValueError("The export iv and salt must each be 16 bytes.")
    ciphertext = bytes(blob[offset:])
    if len(ciphertext) <= 16:
        raise ValueError("This Raycast export is incomplete.")
    key = Scrypt(salt=salt, length=32, n=16384, r=8, p=1).derive(passphrase.encode("utf-8"))
    try:
        plaintext = AESGCM(key).decrypt(iv, ciphertext, None)
    except Exception as exc:
        raise ValueError("Could not decrypt this file. Check the passphrase.") from exc
    try:
        payload = json.loads(gzip.decompress(plaintext))
    except (OSError, ValueError) as exc:
        raise ValueError("The decrypted export was not readable.") from exc
    return payload


def emoji_rows(payload):
    emoji = payload.get("emoji") if isinstance(payload, dict) else None
    rows = emoji.get("emojis") if isinstance(emoji, dict) else None
    if not isinstance(rows, list):
        raise ValueError("This export has no emoji.emojis list.")
    return rows


def to_seed(rows):
    ranked = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            continue
        stamp = row.get("frecencyDate")
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
            continue
        ranked.append((float(stamp), symbol))
    ranked.sort(key=lambda item: -item[0])
    seed = {}
    for index, (_, symbol) in enumerate(ranked):
        seed.setdefault(norm(symbol), max(10.0, 200.0 - 2.0 * index))
    custom = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = row.get("symbol")
        words = row.get("customKeywords")
        if not isinstance(symbol, str) or not symbol or not isinstance(words, list):
            continue
        clean = [str(word) for word in words if isinstance(word, str) and word]
        if clean:
            custom.setdefault(norm(symbol), clean)
    return {"seed": seed, "custom": custom}


def main(argv):
    if len(argv) != 2:
        print("usage: import_raycast.py <file.rayconfig>", file=sys.stderr)
        return 2
    AESGCM, Scrypt = load_crypto()
    try:
        with open(argv[1], "rb") as handle:
            blob = handle.read()
    except OSError as exc:
        print(f"could not read {argv[1]}: {exc.strerror or exc}", file=sys.stderr)
        return 1
    passphrase = getpass.getpass("Raycast passphrase: ")
    try:
        payload = decrypt_rayconfig(blob, passphrase, AESGCM, Scrypt)
        document = to_seed(emoji_rows(payload))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    directory = data_dir()
    os.makedirs(directory, exist_ok=True)
    destination = os.path.join(directory, "seed.json")
    temporary = destination + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, destination)
    print(f"wrote {len(document['seed'])} scores and {len(document['custom'])} keyword entries to {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
