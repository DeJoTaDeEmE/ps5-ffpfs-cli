"""Shared conversion and validation pipeline for CLI and GUI (MkPFS pinned API)."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

MKPFS_COMMIT = "1d5df56ae29390900e888fa12e5f9856aa797adc"


def mkpfs_command():
    # Never search sibling checkouts, install packages, or pick an unknown PATH tool.
    import mkpfs
    if mkpfs.__version__ != "1.1.0":
        raise RuntimeError("Install the MkPFS revision specified in requirements.txt")
    return [sys.executable, "--mkpfs-internal"] if getattr(sys, "frozen", False) else [sys.executable, "-m", "mkpfs"]


def sha256(path, cancelled=lambda: False):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            if cancelled():
                raise RuntimeError("Cancelled")
            digest.update(chunk)
    return digest.hexdigest()


def manifest(root, cancelled=lambda: False):
    root = Path(root)
    files, directories = {}, []
    for path in sorted(root.rglob("*")):
        if cancelled():
            raise RuntimeError("Cancelled")
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"Symbolic links are not supported: {name}")
        if path.is_file():
            files[name] = {"size": path.stat().st_size, "sha256": sha256(path, cancelled)}
        elif path.is_dir():
            directories.append(name)
        else:
            raise ValueError(f"Unsupported source entry: {name}")
    return {"files": files, "directories": directories}


def assert_same(expected, actual):
    if expected != actual:
        names = set(expected["files"]) | set(actual["files"])
        changed = sorted(n for n in names if expected["files"].get(n) != actual["files"].get(n))
        raise ValueError(f"Extracted contents differ (SHA-256/paths/directories): {changed[:20]}")


def check_structure(image, output_format):
    """Require one compressed PFS file, real exFAT magic, and game root markers."""
    from mkpfs.exfat import ExfatReader
    from mkpfs.pfs import inspect_pfs_image, open_inner_file_view
    inner_name = None
    if output_format == "ffpfsc":
        inspection = inspect_pfs_image(Path(image), verify_payloads=False)
        if inspection.errors:
            raise ValueError("; ".join(inspection.errors))
        if len(inspection.file_inodes) != 1:
            raise ValueError("Container must hold exactly one exFAT file")
        inner_name, inode_number = next(iter(inspection.file_inodes.items()))
        if "/" in inner_name or not inner_name.lower().endswith(".exfat"):
            raise ValueError(f"Unexpected nested image: {inner_name}; double wrapping is forbidden")
        if not inspection.inodes[inode_number].is_compressed:
            raise ValueError("Inner exFAT must use PFSC compression")
        opened = open_inner_file_view(Path(image))
        if opened is None:
            raise ValueError("Cannot open single inner exFAT")
        view, handle, _ = opened
    else:
        handle = Path(image).open("rb")
        view = handle
    try:
        # ExfatReader validates the actual signature, irrespective of the extension.
        reader = ExfatReader(view)
        if reader.geometry.cluster_size != 65536:
            raise ValueError("exFAT requires 64 KiB clusters for this SMP profile")
        entries = reader.root_entries()
        root = {entry.name: entry for entry in entries}
        if "eboot.bin" not in root or root["eboot.bin"].is_dir:
            raise ValueError("eboot.bin must be a file at the exFAT root")
        sce = root.get("sce_sys")
        if sce is None or not sce.is_dir or not any(e.name == "param.json" and not e.is_dir for e in sce.children):
            raise ValueError("sce_sys/param.json must be at the exFAT root")
        return {"outer_files": [inner_name] if inner_name else [], "inner_format": "exFAT",
                "cluster_bytes": reader.geometry.cluster_size, "pfs_layers": 1 if inner_name else 0,
                "pfsc_compressed": output_format == "ffpfsc"}
    finally:
        handle.close()


@contextlib.contextmanager
def prepare_source(path, password=None, temp_dir=None):
    path = Path(path)
    if path.suffix.lower() not in {".zip", ".rar", ".r00"}:
        yield path
        return
    with tempfile.TemporaryDirectory(dir=temp_dir, prefix="ps5-source-") as tmp:
        if path.suffix.lower() == ".zip":
            import zipfile
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    (Path(tmp) / member.filename).resolve().relative_to(Path(tmp).resolve())
                    if (member.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError("ZIP symbolic links are not supported")
                archive.extractall(tmp, pwd=password.encode() if password else None)
        else:
            from unrar.rarfile import RarFile
            with RarFile(path, pwd=password) as archive:
                archive.extractall(tmp)
        yield Path(tmp)


def guard_output(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == source or (source.is_dir() and output.is_relative_to(source)):
        raise ValueError("Output and validation workspace must be outside the source folder/image")


def convert(source, output, output_format, run, *, verify=True, temp_dir=None,
            overwrite=False, cancelled=lambda: False):
    """Stage, validate, then atomically replace the destination. Never modify source."""
    source, output = Path(source).resolve(), Path(output).resolve()
    guard_output(source, output)
    if temp_dir:
        guard_output(source, Path(temp_dir))
    if output_format not in {"exfat", "ffpfsc"}:
        raise ValueError("Unsupported output format")
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    if source.is_dir():
        # Reject links even when full hashing is disabled; MkPFS must not follow them.
        for entry in source.rglob("*"):
            if entry.is_symlink():
                raise ValueError(f"Symbolic link in source: {entry}")
        metadata = json.loads((source / "sce_sys/param.json").read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("param.json must contain a JSON object")
    elif source.suffix.lower() != ".exfat":
        raise ValueError("Expected a game folder or .exfat")
    else:
        check_structure(source, "exfat")
    before = manifest(source, cancelled) if verify and source.is_dir() else None
    source_hash = sha256(source, cancelled) if verify and source.is_file() else None
    base = mkpfs_command()

    def execute(arguments):
        if cancelled():
            raise RuntimeError("Cancelled")
        command = base + list(map(str, arguments))
        print("[COMMAND] " + shlex.join(command), flush=True)
        if not run(command) or cancelled():
            raise RuntimeError("MkPFS failed or conversion cancelled")

    output.parent.mkdir(parents=True, exist_ok=True)
    # Staging beside destination ensures os.replace is on the same filesystem.
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".ps5-stage-") as staging:
        image = Path(staging) / output.name
        if source.is_dir():
            if output_format == "exfat":
                execute(["pack", "exfat", "--cluster-size", "65536", source, image])
            else:
                execute(["pack", "folder", "--no-ampr-index", "--compress", "--version", "PS5",
                         "--inode-bits", "32", source, image])
        elif output_format == "exfat":
            shutil.copyfile(source, image)
        else:
            execute(["pack", "file", "--compress", "--version", "PS5", "--inode-bits", "32", source, image])
        structure = check_structure(image, output_format)
        report = {"mkpfs_commit": MKPFS_COMMIT, "source": str(source), "output": str(output),
                  "structure": structure, "full_verification": verify, "ps5_hardware_tested": False}
        if verify:
            execute(["verify", image])
            with tempfile.TemporaryDirectory(dir=temp_dir, prefix="ps5-verify-") as workspace:
                extracted = Path(workspace) / "game"
                execute(["unpack", image, extracted, "--deep"])
                actual = manifest(extracted, cancelled)
                if source.is_dir():
                    assert_same(before, actual)
                    assert_same(before, manifest(source, cancelled))
                else:
                    original = Path(workspace) / "original"
                    execute(["unpack", source, original])
                    assert_same(manifest(original, cancelled), actual)
                    if sha256(source, cancelled) != source_hash:
                        raise ValueError("Source image changed during conversion")
                report["manifest"] = actual
                report["sha256_comparison"] = "passed"
            report["image_sha256"] = sha256(image, cancelled)
        if cancelled():
            raise RuntimeError("Cancelled")
        report_path = Path(staging) / "report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if output.exists() and not overwrite:
            raise FileExistsError(output)
        os.replace(image, output)
        os.replace(report_path, Path(str(output) + ".validation.json"))
    print(f"[OK] Structure validated: {structure}")
    print(f"[OK] Created {output}; full SHA-256 verification: {verify}")
    return report
