#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["brotli"]
# ///
import base64
import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import brotli

CONVERT = Path(__file__).resolve().parent.parent / "convert.py"
spec = importlib.util.spec_from_file_location("convert", CONVERT)
convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(convert)


def string(text):
    data = text.encode("utf-8")
    length = len(data)
    prefix = bytearray()
    while True:
        byte = length & 0x7F
        length >>= 7
        prefix.append(byte | (0x80 if length else 0))
        if not length:
            return bytes(prefix) + data


def save(version=26, is_demo=False, name="Garu Garu", body=b"\x07" * 5000):
    header = struct.pack("<i", version) + uuid.UUID("12345678-1234-5678-1234-567812345678").bytes_le + string(name) + string("Standard") + struct.pack("<q", 0)
    header += b"".join(string(text) for text in (["Woodcutting", "res://wc.png", "Oak Tree", "res://oak.png"] if version >= 9 else ["legacy"]))
    header += struct.pack("<iqq", 1234, 5_000_000, 4_512)
    if version >= 24:
        header += bytes([1 if is_demo else 0])
    return header + body


def run(*args):
    return subprocess.run([sys.executable, str(CONVERT), *map(str, args)], capture_output=True, text=True)


class ConvertTest(unittest.TestCase):
    def test_only_the_demo_flag_changes(self):
        original = save()
        header, converted = convert.convert(original)
        self.assertEqual((header.character, header.gamemode, header.total_level, header.gp, header.slayer_coins), ("Garu Garu", "Standard", 1234, 5_000_000, 4_512))
        self.assertFalse(header.is_demo)
        self.assertEqual(len(converted), len(original))
        self.assertEqual([index for index in range(len(original)) if original[index] != converted[index]], [header.demo_flag_at])
        self.assertEqual(converted[header.demo_flag_at], 1)
        self.assertTrue(convert.Header(converted).is_demo)

    def test_long_names_use_multi_byte_lengths(self):
        header, converted = convert.convert(save(name="G" * 300))
        self.assertEqual(header.character, "G" * 300)
        self.assertTrue(convert.Header(converted).is_demo)

    def test_reads_files_and_save_strings(self):
        packed = brotli.compress(save())
        self.assertEqual(convert.load(packed), (save(), False))
        self.assertEqual(convert.load(base64.b64encode(packed) + b"\n"), (save(), True))
        with self.assertRaises(convert.SaveError):
            convert.load(b"not a save")

    def test_saves_from_before_the_demo_flag_are_refused(self):
        with self.assertRaisesRegex(convert.SaveError, "before Alpha 0.11.0"):
            convert.convert(save(version=23))

    def test_a_cut_off_header_is_reported(self):
        with self.assertRaisesRegex(convert.SaveError, "ends partway"):
            convert.convert(save()[:30])

    def test_command_line_writes_a_save_file_and_a_save_string(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "playtest.txt"
            source.write_text(base64.b64encode(brotli.compress(save())).decode())
            result = run(source)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Garu Garu (Standard), total level 1234", result.stdout)
            written = brotli.decompress((Path(folder) / "playtest-demo.sav").read_bytes())
            self.assertTrue(convert.Header(written).is_demo)
            self.assertEqual(brotli.decompress(base64.b64decode((Path(folder) / "playtest-demo.txt").read_text())), written)

    def test_install_puts_the_save_in_the_demo_folder_and_respects_its_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            convert.DEMO_SAVES = Path(folder) / "saves"
            packed = Path(folder) / "converted.sav"
            packed.write_bytes(b"save")
            header = convert.Header(save())
            target = convert.install(packed, header, force=False)
            self.assertEqual(target.name, "save_12345678-1234-5678-1234-567812345678.sav")
            with self.assertRaisesRegex(convert.SaveError, "already exists"):
                convert.install(packed, header, force=False)
            self.assertEqual(convert.install(packed, header, force=True), target)
            for index in range(4):
                (convert.DEMO_SAVES / f"save_{index}.sav").write_bytes(b"other")
            other = convert.Header(save())
            other.uuid = uuid.uuid4()
            with self.assertRaisesRegex(convert.SaveError, "limit"):
                convert.install(packed, other, force=False)


if __name__ == "__main__":
    unittest.main()
