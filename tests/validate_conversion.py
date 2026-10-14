"""Reproducible end-to-end tests. Run only on Actions, no game files required."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cli
from converter import assert_same, check_structure, convert, manifest, sha256


def fixture(root):
    root.mkdir()
    (root / "sce_sys").mkdir()
    (root / "sce_sys/param.json").write_text(json.dumps({"titleId": "PPSA00001", "contentId": "TEST-PPSA00001_00-TEST000000000000", "localizedParameters": {"defaultLanguage": "en-US", "en-US": {"titleName": "Synthetic conversion test"}}}), encoding="utf-8")
    (root / "eboot.bin").write_bytes(b"Synthetic fixture; NOT a playable executable\n")
    (root / "data").mkdir()
    (root / "data/empty-directory").mkdir()
    (root / "data/empty.bin").touch()
    (root / "data/over-block.bin").write_bytes(bytes(range(256)) * 1025)
    (root / "data/zeros.bin").write_bytes(b"\0" * 1048576)
    (root / "data/espacio ñ.txt").write_text("Contenido reproducible\n", encoding="utf-8")


class ConversionTests(unittest.TestCase):
    binary = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ps5-repro-")
        self.root = Path(self.tmp.name)
        self.source = self.root / "game"
        fixture(self.source)
        self.before = manifest(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def run_command(self, cmd):
        subprocess.run(cmd, check=True, timeout=180)
        return True

    def build(self, fmt):
        output = self.root / f"PPSA00001.{fmt}"
        if self.binary:
            # Exercises actual widgets -> worker -> shared converter -> frozen MkPFS.
            self.run_command([self.binary, "--gui-test", str(self.source), str(output), fmt])
        else:
            cli.convert_sources(self.source, output, fmt, run=self.run_command)
        report = json.loads(Path(str(output) + ".validation.json").read_text())
        self.assertEqual(report["sha256_comparison"], "passed")
        self.assertEqual(report["manifest"], self.before)
        self.assertEqual(manifest(self.source), self.before)
        self.assertEqual(report["image_sha256"], sha256(output))
        self.assertFalse(report["ps5_hardware_tested"])
        return output

    def test_folder_to_exfat(self):
        output = self.build("exfat")
        self.assertEqual(check_structure(output, "exfat")["pfs_layers"], 0)

    def test_folder_to_single_compressed_exfat(self):
        output = self.build("ffpfsc")
        structure = check_structure(output, "ffpfsc")
        self.assertEqual(structure["outer_files"], ["PPSA00001.exfat"])
        self.assertEqual(structure["pfs_layers"], 1)
        self.assertTrue(structure["pfsc_compressed"])
        outer = self.root / "outer"
        base = [self.binary, "--mkpfs-internal"] if self.binary else [sys.executable, "-m", "mkpfs"]
        self.run_command(base + ["unpack", str(output), str(outer)])
        self.assertEqual([p.name for p in outer.iterdir()], ["PPSA00001.exfat"])
        self.assertEqual(check_structure(outer / "PPSA00001.exfat", "exfat")["pfs_layers"], 0)

    def test_existing_exfat_to_compressed(self):
        source = self.build("exfat")
        output = self.root / "existing.ffpfsc"
        convert(source, output, "ffpfsc", self.run_command)
        self.assertEqual(check_structure(output, "ffpfsc")["pfs_layers"], 1)

    def test_reject_double_wrapper_and_disguised_pfs(self):
        base = [self.binary, "--mkpfs-internal"] if self.binary else [sys.executable, "-m", "mkpfs"]
        # Reproduce the historical bug with the current dependency, not old code.
        nested = self.root / "pfs_image.dat"
        double = self.root / "double.ffpfsc"
        self.run_command(base + ["pack", "folder", "--no-ampr-index", "--no-compress", "--no-adjust-output-file-extension", str(self.source), str(nested)])
        self.run_command(base + ["pack", "file", str(nested), str(double)])
        with self.assertRaises(ValueError):
            check_structure(double, "ffpfsc")
        renamed = self.root / "fake.exfat"
        renamed.write_bytes(nested.read_bytes())
        with self.assertRaises(ValueError):
            check_structure(renamed, "exfat")

    def test_zip_source_and_path_traversal(self):
        import zipfile
        archive = self.root / "game.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for path in self.source.rglob("*"):
                zf.write(path, "Game/" + path.relative_to(self.source).as_posix())
        output = self.root / "archive.exfat"
        cli.convert_sources(archive, output, "exfat", run=self.run_command)
        report = json.loads(Path(str(output) + ".validation.json").read_text())
        self.assertEqual(report["manifest"], self.before)
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../escaped.txt", "unsafe")
        with self.assertRaises(ValueError):
            cli.convert_sources(archive, self.root / "unsafe.exfat", "exfat", run=self.run_command)
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_failure_preserves_existing_output_and_source(self):
        output = self.root / "existing.ffpfsc"
        output.write_bytes(b"prior output")
        with self.assertRaises(RuntimeError):
            convert(self.source, output, "ffpfsc", lambda cmd: False, overwrite=True)
        self.assertEqual(output.read_bytes(), b"prior output")
        self.assertEqual(manifest(self.source), self.before)
        self.assertFalse(list(self.root.glob(".ps5-stage-*")))

    def test_hash_comparison_detects_changed_missing_and_extra_files(self):
        (self.source / "eboot.bin").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            assert_same(self.before, manifest(self.source))
        (self.source / "data/empty.bin").unlink()
        with self.assertRaises(ValueError):
            assert_same(self.before, manifest(self.source))

    def test_reject_output_inside_source_and_symlink(self):
        with self.assertRaises(ValueError):
            convert(self.source, self.source / "bad.ffpfsc", "ffpfsc", self.run_command)
        (self.source / "link").symlink_to(self.source / "eboot.bin")
        with self.assertRaises(ValueError):
            convert(self.source, self.root / "bad.ffpfsc", "ffpfsc", self.run_command)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary")
    args = parser.parse_args()
    ConversionTests.binary = args.binary
    unittest.main(argv=[sys.argv[0]], verbosity=2)
