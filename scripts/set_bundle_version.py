"""Update macOS bundle metadata only; keep the conversion engine untouched."""
from pathlib import Path
import plistlib

APP = Path(__file__).resolve().parents[1] / "dist/PS5-FFPFS-CLI.app"
VERSION = "1.0.1"

if __name__ == "__main__":
    path = APP / "Contents/Info.plist"
    info = plistlib.loads(path.read_bytes())
    info.update({"CFBundleVersion": VERSION, "CFBundleShortVersionString": VERSION,
                 "LSMinimumSystemVersion": "15.0", "NSHighResolutionCapable": True})
    path.write_bytes(plistlib.dumps(info))
    print(f"Bundle version {VERSION}; minimum macOS 15.0; Retina enabled")
