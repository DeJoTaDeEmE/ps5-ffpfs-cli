"""Collect exact-source archives and license texts on Actions, without building code."""
from pathlib import Path
import hashlib
import importlib.metadata as metadata
import io
import json
import re
import shutil
import subprocess
import tarfile
import tomllib
import struct
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release-materials"
NOTICES = OUT / "Licenses"
SOURCES = OUT / "Source"
MKPFS = "1d5df56ae29390900e888fa12e5f9856aa797adc"


def fetch(url):
    # curl uses the platform certificate store; never disable TLS verification.
    return subprocess.check_output(["curl", "--fail", "--location", "--silent",
                                    "--show-error", "--retry", "3", url])


def is_notice(name):
    base = Path(name).name.lower()
    return base.startswith(("license", "licence", "copying", "copyright", "notice", "authors", "acknowledg"))


def source_notices(blob, filename, directory):
    """Read notices only, do not extract arbitrary paths from external archives."""
    directory.mkdir(parents=True, exist_ok=True)
    entries = []
    if filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            entries = [(name, archive.read(name)) for name in archive.namelist()
                       if not name.endswith("/") and is_notice(name)]
    else:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as archive:
            entries = [(item.name, archive.extractfile(item).read())
                       for item in archive.getmembers() if item.isfile() and is_notice(item.name)]
    for name, content in entries:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        (directory / safe).write_bytes(content)
    return len(entries)


def collect_rust_sources(blob):
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as archive:
        locks = [item for item in archive.getmembers() if item.name.endswith("Cargo.lock")]
        if not locks:
            raise RuntimeError("Cryptography corresponding source lacks Cargo.lock")
        lock = tomllib.loads(archive.extractfile(locks[0]).read().decode())
    inventory = []
    directory = SOURCES / "rust-crates"
    directory.mkdir(exist_ok=True)
    for item in lock["package"]:
        if not str(item.get("source", "")).startswith("registry+"):
            continue
        name, version = item["name"], item["version"]
        url = f"https://static.crates.io/crates/{name}/{name}-{version}.crate"
        data = fetch(url)
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["checksum"]:
            raise RuntimeError(f"Cargo source checksum mismatch: {name}")
        (directory / f"{name}-{version}.crate").write_bytes(data)
        count = source_notices(data, f"{name}-{version}.crate", NOTICES / "rust-crates" / f"{name}-{version}")
        if not count:
            raise RuntimeError(f"Missing Rust crate license: {name}")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            manifests = [entry for entry in archive.getmembers() if entry.name.endswith("/Cargo.toml")]
            package = tomllib.loads(archive.extractfile(manifests[0]).read().decode())["package"]
        inventory.append({"name": name, "version": version, "source_url": url,
                          "sha256": digest, "license": package.get("license"),
                          "authors": package.get("authors", []), "repository": package.get("repository")})
    (NOTICES / "rust-crate-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")


def collect_native_notices():
    from cryptography.hazmat.backends.openssl.backend import backend
    version = backend.openssl_version_text()
    match = re.search(r"OpenSSL (\d+\.\d+\.\d+)", version)
    if not match:
        raise RuntimeError(f"Unrecognized bundled crypto backend: {version}")
    url = f"https://codeload.github.com/openssl/openssl/tar.gz/refs/tags/openssl-{match.group(1)}"
    data = fetch(url)
    (SOURCES / "OpenSSL-source.tar.gz").write_bytes(data)
    source_notices(data, "OpenSSL-source.tar.gz", NOTICES / "OpenSSL")
    (NOTICES / "native-backend.json").write_text(json.dumps({"openssl": version,
        "source_url": url, "sha256": hashlib.sha256(data).hexdigest()}, indent=2) + "\n")
    # Preserve the actual bundled font's copyright/license strings from its name table.
    import customtkinter
    font_root = Path(customtkinter.__file__).parent / "assets/fonts/Roboto"
    rows = []
    for font in sorted(font_root.glob("*.ttf")):
        blob = font.read_bytes()
        table_count = struct.unpack_from(">H", blob, 4)[0]
        for index in range(table_count):
            tag, _crc, offset, _length = struct.unpack_from(">4sIII", blob, 12 + index * 16)
            if tag != b"name":
                continue
            _format, count, strings = struct.unpack_from(">HHH", blob, offset)
            values = set()
            for entry in range(count):
                platform, _encoding, _language, name_id, length, start = struct.unpack_from(">HHHHHH", blob, offset + 6 + entry * 12)
                if name_id not in (0, 13, 14):
                    continue
                raw = blob[offset + strings + start:offset + strings + start + length]
                values.add(raw.decode("utf-16-be" if platform in (0, 3) else "latin1"))
            rows.append(font.name + "\n" + "\n".join(sorted(values)))
    (NOTICES / "Roboto-font-notices.txt").write_text("\n\n".join(rows) + "\n")


def main():
    NOTICES.mkdir(parents=True, exist_ok=True)
    SOURCES.mkdir(parents=True, exist_ok=True)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, NOTICES / name)
    shutil.copytree(ROOT / "licenses", NOTICES / "reference-texts", dirs_exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (SOURCES / "application.tar").write_bytes(subprocess.check_output(
        ["git", "archive", "--format=tar", "--prefix=application/", commit], cwd=ROOT))
    url = f"https://codeload.github.com/PSBrew/MkPFS/tar.gz/{MKPFS}"
    data = fetch(url)
    (SOURCES / "MkPFS-source.tar.gz").write_bytes(data)
    source_notices(data, "MkPFS-source.tar.gz", NOTICES / "MkPFS")
    inventory = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name, version = dist.metadata["Name"], dist.version
        if name.lower() == "unrar":
            # Source is in application.tar; do not imply inclusion in a reviewed binary.
            continue
        directory = NOTICES / "packages" / f"{name}-{version}"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "METADATA.txt").write_text(dist.read_text("METADATA") or dist.read_text("PKG-INFO") or "", encoding="utf-8")
        copied = []
        for relative in dist.files or ():
            if not is_notice(str(relative)):
                continue
            path = Path(dist.locate_file(relative))
            if not path.is_file():
                continue
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(relative))
            target = directory / safe
            shutil.copy2(path, target)
            copied.append({"installed_path": str(relative), "notice": str(target.relative_to(OUT)),
                           "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        record = {"name": name, "version": version, "author": dist.metadata.get("Author"),
                  "author_email": dist.metadata.get("Author-email"),
                  "license_expression": dist.metadata.get("License-Expression"),
                  "license": dist.metadata.get("License"),
                  "urls": dist.metadata.get_all("Project-URL", []), "notices": copied}
        if name.lower() != "mkpfs":
            package = json.loads(fetch(f"https://pypi.org/pypi/{name}/{version}/json"))
            sdists = [file for file in package["urls"] if file["packagetype"] == "sdist"]
            if not sdists:
                raise RuntimeError(f"Missing exact source distribution for {name} {version}")
            item = sdists[0]
            blob = fetch(item["url"])
            digest = hashlib.sha256(blob).hexdigest()
            if digest != item["digests"]["sha256"]:
                raise RuntimeError(f"Source checksum mismatch: {name}")
            (SOURCES / item["filename"]).write_bytes(blob)
            count = source_notices(blob, item["filename"], directory / "source-notices")
            if name.lower() == "cryptography":
                collect_rust_sources(blob)
            record["source"] = {"filename": item["filename"], "url": item["url"], "sha256": digest}
            if not copied and not count:
                raise RuntimeError(f"No license notice found for {name}")
        elif not copied:
            raise RuntimeError("MkPFS license not collected")
        inventory.append(record)
    collect_native_notices()
    (NOTICES / "package-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    (SOURCES / "SOURCE-INFO.json").write_text(json.dumps({"application_commit": commit,
        "mkpfs_commit": MKPFS, "mkpfs_source_url": url,
        "mkpfs_source_sha256": hashlib.sha256(data).hexdigest()}, indent=2) + "\n")
    source_archive = ROOT / "PS5-FFPFS-CLI-Source.tar.gz"
    with tarfile.open(source_archive, "w:gz") as archive:
        archive.add(OUT, arcname="PS5-FFPFS-CLI-Source")
    with source_archive.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    source_archive.with_suffix(source_archive.suffix + ".sha256").write_text(
        f"{digest}  {source_archive.name}\n")
    print(f"Collected {len(inventory)} exact package inventories, notices and source archives")


if __name__ == "__main__":
    main()
