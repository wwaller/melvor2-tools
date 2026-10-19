#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["brotli"]
# ///
"""Make a Melvor Idle 2 playtest save loadable in the Melvor Idle 2 Demo."""
import argparse
import base64
import binascii
import shutil
import struct
import sys
import uuid
from pathlib import Path

import brotli

DEMO_SAVES = Path.home() / "Library/Application Support/Games By Malcs/Melvor Idle 2/saves"
MAX_SAVES = 5
LOCALIZATION = 9
FIRST_WITH_DEMO_FLAG = 24
DEMO_VERSION = 26
VERSION_NAMES = {9: "Localization", 24: "Alpha 0.11.0", 25: "Alpha 0.11.1", 26: "Alpha 0.11.1.1"}


class SaveError(Exception):
    pass


def load(raw):
    try:
        return brotli.decompress(raw), False
    except brotli.error:
        pass
    try:
        return brotli.decompress(base64.b64decode(raw.strip(), validate=True)), True
    except (binascii.Error, ValueError, brotli.error):
        raise SaveError("this is neither a Melvor Idle 2 save file nor a save string") from None


class Header:
    def __init__(self, data):
        self.data = data
        self.position = 0
        self.version = self.int32()
        self.uuid = uuid.UUID(bytes_le=self.take(16))
        self.character = self.string()
        self.gamemode = self.string()
        self.take(8)
        for _ in range(4 if self.version >= LOCALIZATION else 1):
            self.string()
        self.total_level = self.int32()
        self.gp, self.slayer_coins = struct.unpack("<qq", self.take(16))
        self.demo_flag_at = self.position if self.version >= FIRST_WITH_DEMO_FLAG else None
        self.is_demo = self.data[self.position] == 1 if self.demo_flag_at is not None else False

    def take(self, count):
        if self.position + count > len(self.data):
            raise SaveError("the save ends partway through its header")
        chunk = self.data[self.position:self.position + count]
        self.position += count
        return chunk

    def int32(self):
        return struct.unpack("<i", self.take(4))[0]

    def string(self):
        length = shift = 0
        while True:
            byte = self.take(1)[0]
            length |= (byte & 0x7F) << shift
            shift += 7
            if byte < 0x80:
                break
        return self.take(length).decode("utf-8")


def convert(data):
    header = Header(data)
    if header.demo_flag_at is None:
        raise SaveError(f"this save is from before Alpha 0.11.0 (save version {header.version}); load it in the playtest once so it is saved in the current format, then export it again")
    if header.version > DEMO_VERSION:
        print(f"warning: this save is newer than the Demo (save version {header.version}, the Demo reads up to {DEMO_VERSION}), so the Demo may fail to load it", file=sys.stderr)
    converted = bytearray(data)
    converted[header.demo_flag_at] = 1
    return header, bytes(converted)


def install(save, header, force):
    DEMO_SAVES.mkdir(parents=True, exist_ok=True)
    target = DEMO_SAVES / f"save_{header.uuid}.sav"
    if target.exists() and not force:
        raise SaveError(f"{target} already exists; pass --force to replace it")
    if not target.exists() and len(list(DEMO_SAVES.glob("save_*.sav"))) >= MAX_SAVES:
        raise SaveError(f"the Demo already has {MAX_SAVES} saves, its limit; delete one in the game first")
    shutil.copyfile(save, target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("save", type=Path, help="a playtest save file, or a text file holding a save string")
    parser.add_argument("--install", action="store_true", help="also copy the converted save into the Demo's saves folder")
    parser.add_argument("--force", action="store_true", help="with --install, replace a Demo save with the same id")
    args = parser.parse_args()
    try:
        data, was_string = load(args.save.read_bytes())
        header, converted = convert(data)
        packed = brotli.compress(converted, quality=11)
        stem = args.save.with_suffix("")
        save_file = stem.with_name(f"{stem.name}-demo.sav")
        string_file = stem.with_name(f"{stem.name}-demo.txt")
        save_file.write_bytes(packed)
        string_file.write_text(base64.b64encode(packed).decode("ascii"))
        source = "save string" if was_string else "save file"
        name = VERSION_NAMES.get(header.version, f"save version {header.version}")
        print(f"{header.character} ({header.gamemode}), total level {header.total_level}, {header.gp:,} GP ({name} {source})")
        if header.is_demo:
            print("it was already a Demo save; written out unchanged")
        print(f"save file:   {save_file}")
        print(f"save string: {string_file}  (paste into the Demo's Import Save)")
        if args.install:
            print(f"installed:   {install(save_file, header, args.force)}")
    except (OSError, SaveError) as error:
        sys.exit(f"error: {error}")


if __name__ == "__main__":
    main()
