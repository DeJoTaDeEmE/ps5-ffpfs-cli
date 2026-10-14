#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import multiprocessing
import os
import re
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] == "--mkpfs-internal":
        from mkpfs.cli import cli_mkpfs_main
        sys.exit(cli_mkpfs_main(sys.argv[2:]))

from converter import convert, prepare_source


def safe_title_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Unsafe title ID in param.json or source name")
    return value

def get_title_id_from_name(name: str) -> str:
    # Look for standard PS4/PS5 title ID formats like PPSA12345 or CUSA12345
    match = re.search(r'\b([A-Z]{4}\d{5})\b', name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    # Otherwise fallback to clean name
    fallback = name
    for suffix in [".exfat", "-app0", "-app", "-patch0", "-patch"]:
        if fallback.lower().endswith(suffix):
            fallback = fallback[:-len(suffix)]
    return fallback

def get_title_id(item_path: Path) -> str:
    if item_path.is_dir():
        param_path = item_path / "sce_sys" / "param.json"
        try:
            if param_path.is_file():
                with open(param_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "titleId" in data:
                        return safe_title_id(data["titleId"])
                    if "title_id" in data:
                        return safe_title_id(data["title_id"])
        except Exception as e:
            print(f"[WARN] Could not parse param.json for title ID: {e}")

    return safe_title_id(get_title_id_from_name(item_path.name))

def find_game_items(path: Path, batch: bool = False) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() == '.exfat':
            return [path]
        else:
            print(f"[ERROR] Unsupported file type: {path.name}. Only .exfat files are supported.")
            sys.exit(1)

    print(f"[INFO] Scanning for game folder(s) and .exfat file(s) in {path}...")
    valid_items = []

    # 1. Scan for .exfat files
    for dirpath, _, filenames in os.walk(path):
        curr_dir = Path(dirpath)
        for f in filenames:
            if f.lower().endswith('.exfat'):
                valid_items.append(curr_dir / f)

    # 2. Scan for game folders
    for dirpath, _, _ in os.walk(path):
        curr_dir = Path(dirpath)
        eboot_path = curr_dir / "eboot.bin"
        param_path = curr_dir / "sce_sys" / "param.json"

        if eboot_path.is_file() and param_path.is_file():
            valid_items.append(curr_dir)

    # Deduplicate (a path could appear in both exfat and folder scans)
    seen = set()
    deduped = []
    for item in valid_items:
        resolved = item.resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(item)
    valid_items = deduped

    if len(valid_items) == 0:
        print(f"[ERROR] Could not find any valid game folders or .exfat files in {path}.")
        sys.exit(1)

    if not batch and len(valid_items) > 1:
        print(f"[ERROR] Multiple game folders/files found in {path}:")
        for item in valid_items:
            print(f"  - {item}")
        print("Please specify a more specific folder/file or use --batch to process all.")
        sys.exit(1)

    if not batch:
        print(f"[OK] Found game source at {valid_items[0]}")
    else:
        print(f"[OK] Found {len(valid_items)} game item(s) for batch processing.")

    return valid_items


def convert_sources(source, output, output_format="ffpfsc", *, batch=False,
                    verify=True, temp_dir=None, password=None, overwrite=False,
                    run=None, cancelled=lambda: False, confirm=None):
    if run is None:
        def run(command):
            return subprocess.run(command, check=False).returncode == 0
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    from converter import guard_output
    guard_output(source, output)
    if temp_dir:
        guard_output(source, Path(temp_dir))
    with prepare_source(source, password, temp_dir) as prepared:
        items = find_game_items(prepared, batch)
        if batch:
            output.mkdir(parents=True, exist_ok=True)
        destinations = []
        for item in items:
            target = output / f"{get_title_id(item)}.{output_format}" if output.is_dir() else output.with_suffix("." + output_format)
            if target in destinations:
                raise ValueError(f"Duplicate output title ID: {target.name}")
            destinations.append(target)
        for item, target in zip(items, destinations):
            if cancelled():
                raise RuntimeError("Cancelled")
            allow_overwrite = overwrite
            if target.exists() and not allow_overwrite:
                if confirm is None or not confirm(target):
                    raise FileExistsError(f"Output exists: {target}. Choose another destination or --overwrite")
                allow_overwrite = True
            convert(item, target, output_format, run, verify=verify, temp_dir=temp_dir,
                    overwrite=allow_overwrite, cancelled=cancelled)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build raw exFAT or a single compressed PFS containing exFAT for ShadowMountPlus")
    parser.add_argument("game_folder", nargs="?")
    parser.add_argument("output", nargs="?", default=".")
    parser.add_argument("--format", choices=["exfat", "ffpfsc"], default="ffpfsc")
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--verify", dest="verify", action="store_true", default=True,
                        help="Extract and compare SHA-256 (default)")
    parser.add_argument("--no-verify", dest="verify", action="store_false",
                        help="Skip full extraction/hashes; structure is always checked")
    parser.add_argument("-f", "--force", "--overwrite", dest="overwrite", action="store_true")
    parser.add_argument("--password")
    parser.add_argument("--temp-dir")
    args = parser.parse_args(argv)
    if args.gui:
        from gui import launch
        return launch(args)
    if not args.game_folder:
        parser.error("a source folder/image is required")
    try:
        convert_sources(args.game_folder, args.output, args.format, batch=args.batch,
                        verify=args.verify, temp_dir=args.temp_dir, password=args.password,
                        overwrite=args.overwrite)
    except (Exception, KeyboardInterrupt) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
