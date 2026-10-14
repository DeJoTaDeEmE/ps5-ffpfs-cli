"""Pure path validation regressions; no GUI or real-game operations."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from path_fields import clean_path, validate_path, browse_initial_directory


class PathTests(unittest.TestCase):
    def test_reported_duplicate_volume(self):
        path = "/Volumes/TAHOENTOSH - Data/PS5_OUTPUT"
        with self.assertRaisesRegex(ValueError, "concatenated"):
            validate_path(path * 2, "Output destination")

    def test_different_volume_concatenation(self):
        with self.assertRaisesRegex(ValueError, "concatenated"):
            validate_path("/Volumes/First/out/Volumes/Second/temp", "Temp dir")

    def test_repeated_home_root(self):
        with self.assertRaisesRegex(ValueError, "concatenated"):
            validate_path("/Users/example/output/Users/example/temp", "Output destination")

    def test_two_component_duplicate(self):
        with self.assertRaisesRegex(ValueError, "concatenated"):
            validate_path("/unmounted_example/output/unmounted_example/output", "Output destination")

    def test_prefix_with_different_name_not_rejected(self):
        path = "/unmounted_example/a/unmounted_example/abc"
        self.assertEqual(validate_path(path, "Output destination"), path)

    def test_spaces_unicode_and_quotes(self):
        self.assertEqual(validate_path('"/Volumes/Data/Salida ñ"', "Output destination"), "/Volumes/Data/Salida ñ")

    def test_multiple_paths_and_nul_rejected(self):
        for path in ("/one\n/two", "/one\r/two", "/one\0/two"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                clean_path(path)

    def test_existing_repeated_directory_is_valid(self):
        with tempfile.TemporaryDirectory(prefix="ps5-path-unit-") as tmp:
            path = Path(tmp) / "data/data"
            path.mkdir(parents=True)
            self.assertEqual(validate_path(str(path), "Temp dir", directory=True), str(path))

    def test_temp_must_exist(self):
        with tempfile.TemporaryDirectory(prefix="ps5-path-unit-") as tmp:
            with self.assertRaisesRegex(ValueError, "existing directory"):
                validate_path(str(Path(tmp) / "missing"), "Temp dir", directory=True)
            self.assertEqual(validate_path("", "Temp dir", directory=True), "")

    def test_browse_finds_existing_parent(self):
        with tempfile.TemporaryDirectory(prefix="ps5-path-unit-") as tmp:
            self.assertEqual(browse_initial_directory(str(Path(tmp) / "new/image.ffpfsc")), tmp)

    def test_browse_bad_path_falls_back_home(self):
        self.assertEqual(browse_initial_directory("/Volumes/Data/out/Volumes/Data/out"), str(Path.home()))


if __name__ == "__main__":
    unittest.main()
