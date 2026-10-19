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


NEW_ID = uuid.UUID("abcdefab-cdef-abcd-efab-cdefabcdefab")


def unfinished(data):
    compressor = brotli.Compressor()
    return compressor.process(data) + compressor.flush()


class ConvertTest(unittest.TestCase):
    def test_only_the_id_and_the_demo_flag_change(self):
        original = save()
        header, converted = convert.convert(original, NEW_ID)
        self.assertEqual((header.character, header.gamemode, header.total_level, header.gp, header.slayer_coins), ("Garu Garu", "Standard", 1234, 5_000_000, 4_512))
        self.assertFalse(header.is_demo)
        self.assertEqual(len(converted), len(original))
        changed = [index for index in range(len(original)) if original[index] != converted[index]]
        self.assertTrue(set(changed) <= set(range(4, 20)) | {header.demo_flag_at})
        after = convert.Header(converted)
        self.assertTrue(after.is_demo)
        self.assertEqual(after.uuid, NEW_ID, 'a new id, so the copy sits beside the original instead of replacing it')
        self.assertEqual((after.character, after.total_level), (header.character, header.total_level))

    def test_long_names_use_multi_byte_lengths(self):
        header, converted = convert.convert(save(name="G" * 300), NEW_ID)
        self.assertEqual(header.character, "G" * 300)
        self.assertTrue(convert.Header(converted).is_demo)

    def test_reads_files_and_save_strings_including_the_unfinished_streams_the_game_writes(self):
        for packed in (brotli.compress(save()), unfinished(save())):
            self.assertEqual(convert.load(packed), (save(), False))
            self.assertEqual(convert.load(base64.b64encode(packed) + b"\n"), (save(), True))
        with self.assertRaises(convert.SaveError):
            convert.load(b"not a save")

    def test_saves_from_before_the_demo_flag_are_refused(self):
        with self.assertRaisesRegex(convert.SaveError, "before Alpha 0.11.0"):
            convert.convert(save(version=23), NEW_ID)

    def test_a_cut_off_header_is_reported(self):
        with self.assertRaisesRegex(convert.SaveError, "ends partway"):
            convert.convert(save()[:30], NEW_ID)

    def test_command_line_writes_a_save_string_to_the_out_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "playtest.txt"
            source.write_text(base64.b64encode(unfinished(save())).decode())
            out = Path(folder) / "out"
            out.mkdir()
            result = run(source, "--out", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Garu Garu (Standard), total level 1234", result.stdout)
            written = brotli.decompress(base64.b64decode((out / "playtest-demo.txt").read_text()))
            self.assertTrue(convert.Header(written).is_demo)
            self.assertEqual(sorted(path.name for path in out.iterdir()), ["playtest-demo.txt"])


if __name__ == "__main__":
    unittest.main()
