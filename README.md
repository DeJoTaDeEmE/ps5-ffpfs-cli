# PS5 image converter for macOS Intel

A Tk/CustomTkinter desktop application targeting macOS Sequoia (15) Intel x86_64.
Builds run in GitHub Actions on `macos-15-intel`, not on your computer.

Choose the output format in the GUI:

- **exfat**: raw, uncompressed exFAT with 64 KiB clusters and game files at its root.
- **ffpfsc**: one unsigned PS5 PFS container with one PFSC-compressed `<titleId>.exfat` file. The inner exFAT contains the game files at its root.

Expected compressed layout:

```text
PPSA00001.ffpfsc (PFS)
└── PPSA00001.exfat (PFSC-compressed payload; actual exFAT signature)
    ├── eboot.bin
    └── sce_sys/param.json
```

The GUI and CLI use the same converter. No `pfs_image.dat` intermediate, no second
PFS wrapper, no raw game files at the outer PFS root. Structural verification is
mandatory. Full extraction and SHA-256 comparison are enabled by default; keep
"Extract and compare SHA-256" selected for validated output. A sibling
`.validation.json` report records the format, checks and per-file hashes.

## Download and run

Download `PS5-FFPFS-CLI-macOS-Intel.zip` from this repository's Releases, extract it,
and open `PS5-FFPFS-CLI.app`. Actions also provides the application ZIP, its SHA-256,
and `validation-evidence.zip`. The application is ad-hoc signed, not notarized;
macOS may require approval in System Settings → Privacy & Security after the
first launch attempt. No Python installation is needed for the bundled app.

Select a game folder containing `eboot.bin` and `sce_sys/param.json`, an existing
64 KiB-cluster `.exfat`, or a ZIP/RAR containing such a folder. Select an output
directory outside the source, choose the format, and click the build button.
Existing output is replaced only after the new staged image passes validation.
Original folders/images are never deleted. Symbolic links are rejected. MkPFS's
automatic AMPR source rewriting is disabled.

Full validation temporarily extracts all game files. Allow space for the staged
image and extracted contents; converting existing exFAT also extracts the source
for comparison. Choose a temporary directory with enough free space. Hashing
large games takes time. Disabling full verification checks structure but does
not prove file contents match. Cancellation preserves the old destination.

## Source usage

Python 3.11; dependencies and upstream revision are pinned in `requirements.txt`.
Installing the optional RAR extension requires a compiler; all application build
and test commands for this delivery run on Actions.

```bash
python -m pip install -r requirements.txt
python -m pip install ./unrar
python cli.py /path/Game /path/output/PPSA00001.ffpfsc --format ffpfsc
python cli.py /path/Game /path/output/PPSA00001.exfat --format exfat
python cli.py /path/Games /path/output --batch
python cli.py --gui
```

`--verify` is the default. `--no-verify` skips extraction/hashes, `--overwrite`
replaces an existing validated output, `--temp-dir` selects validation scratch
space, and `--password` supplies an archive password. `--keep-pfs` was removed
because this conversion creates no nested PFS intermediate.

## Compatibility limits

The synthetic fixture verifies format, compression, extraction and byte identity.
It is not a playable game. **No PS5 hardware launch has been performed.** A green
build or SHA-256 match does not prove that a particular game mounts, installs or
launches on a PS5. ShadowMountPlus documents PFS support as experimental. Validate
on your console with your own game dump and record the SMP version, firmware,
mount log, detection, installation and launch results.

References: [PSBrew/MkPFS](https://github.com/PSBrew/MkPFS) and
[drakmor/ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus).
See [VALIDATION.md](VALIDATION.md) for the audit, reproduction and test evidence.
