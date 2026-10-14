"""Ensure the built app references our complete custom icon, not Python's icon."""
import hashlib
import plistlib
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "dist/PS5-FFPFS-CLI.app"
EXPECTED = {"icon_16x16.png": 16, "icon_16x16@2x.png": 32,
            "icon_32x32.png": 32, "icon_32x32@2x.png": 64,
            "icon_128x128.png": 128, "icon_128x128@2x.png": 256,
            "icon_256x256.png": 256, "icon_256x256@2x.png": 512,
            "icon_512x512.png": 512, "icon_512x512@2x.png": 1024}


def main():
    info = plistlib.loads((APP / "Contents/Info.plist").read_bytes())
    name = info["CFBundleIconFile"]
    if not name.endswith(".icns"):
        name += ".icns"
    icon = APP / "Contents/Resources" / name
    source = REPO / "assets/PS5-FFPFS-CLI.icns"
    assert icon.read_bytes() == source.read_bytes(), "Bundle contains a different icon"
    assert icon.read_bytes()[:4] == b"icns"
    with tempfile.TemporaryDirectory(prefix="ps5-icon-check-") as tmp:
        decoded = Path(tmp) / "validated.iconset"
        subprocess.run(["iconutil", "-c", "iconset", str(icon), "-o", str(decoded)], check=True)
        for filename, size in EXPECTED.items():
            with Image.open(decoded / filename) as image:
                assert image.size == (size, size), (filename, image.size)
                assert image.mode == "RGBA", (filename, image.mode)
    digest = hashlib.sha256(icon.read_bytes()).hexdigest()
    report = f"Bundle icon: {name}\nSHA-256: {digest}\nAll 10 standard/Retina representations: passed\n"
    (REPO / "validation/icon.txt").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
