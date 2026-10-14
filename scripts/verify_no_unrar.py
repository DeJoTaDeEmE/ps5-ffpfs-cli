"""Verify exclusion from PYZ, executable archive and bundle filesystem."""
from pathlib import Path
import json
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]
app = ROOT / "dist/PS5-FFPFS-CLI.app"
archive = CArchiveReader(str(app / "Contents/MacOS/PS5-FFPFS-CLI"))
names = list(archive.toc)
for name in list(names):
    if name.lower().endswith(".pyz"):
        names.extend(archive.open_embedded_archive(name).toc)
bad = [name for name in names if "unrar" in name.lower()]
bad.extend(str(p.relative_to(app)) for p in app.rglob("*")
           if "unrar" in p.name.lower() and p.is_file()
           and not p.name.endswith("LICENSE.txt"))
assert not bad, f"UnRAR unexpectedly bundled: {bad}"
report = {"unrar_bundled": False, "archive_entries_checked": len(names)}
(ROOT / "validation/unrar-exclusion.json").write_text(json.dumps(report, indent=2) + "\n")
print(report)
