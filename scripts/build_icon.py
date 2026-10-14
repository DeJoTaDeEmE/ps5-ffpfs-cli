"""Encode the source artwork as a full macOS iconset; no application compilation."""
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SOURCE = ASSETS / "icon-source.png"
OUTPUT = ASSETS / "PS5-FFPFS-CLI.icns"


def main():
    with Image.open(SOURCE) as source:
        assert source.width == source.height and source.width >= 1024, source.size
        assert source.mode == "RGBA", "Icon must preserve transparency"
        assert source.getextrema()[3][0] == 0, "Icon background must be transparent"
        with tempfile.TemporaryDirectory(prefix="ps5-icon-") as tmp:
            iconset = Path(tmp) / "PS5-FFPFS-CLI.iconset"
            iconset.mkdir()
            for size in (16, 32, 128, 256, 512):
                for scale in (1, 2):
                    pixels = size * scale
                    suffix = "@2x" if scale == 2 else ""
                    source.resize((pixels, pixels), Image.Resampling.LANCZOS).save(
                        iconset / f"icon_{size}x{size}{suffix}.png")
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(OUTPUT)], check=True)
    assert OUTPUT.read_bytes()[:4] == b"icns"
    print(f"Complete icon: {OUTPUT}")


if __name__ == "__main__":
    main()
