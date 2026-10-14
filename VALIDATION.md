# Audit and reproducible validation

Audited application baseline: `318d0565cf37a31410b0fe22abba51718213e6e8`.
MkPFS: `1d5df56ae29390900e888fa12e5f9856aa797adc` (version 1.1.0).
ShadowMountPlus: `98c524890176c7b474fcb03387bec88c4a559861`.

## Findings and fixes

- CLI had switched to `pack folder`, but GUI retained a two-pass flow. In current
  MkPFS `pack folder` wraps an exFAT by default even with the historical flags.
  Packing that result again introduced `ffpfsc → pfs_image.dat → exfat → game`.
- GUI now calls the shared conversion pipeline used by CLI. Compressed packing
  calls `pack folder --no-ampr-index --compress --version PS5 --inode-bits 32`.
- Raw exFAT calls `pack exfat --cluster-size 65536`; existing exFAT compression
  calls `pack file --compress --version PS5 --inode-bits 32`.
- Unknown sibling checkouts, PATH executables and automatic dependency installs
  were removed. Upstream is pinned to the audited commit. The old Intel workflow
  forced cryptography 45.0.7 despite current MkPFS requiring >=47.0.0; corrected.
- The installed UnRAR extension is copied into its source package on Actions to
  avoid the local package hiding the installed native module; both source and
  bundled imports of UnRAR, crypto and compression libraries are checked.
- The old workflow mislabeled `macos-latest` as universal without a universal
  build. Both workflow entrypoints now use tested `macos-15-intel` x86_64.
  Windows/Linux builds are deferred; they are not targets of this delivery.
- Mandatory checks inspect the PFS tree, require exactly one root `.exfat` file,
  check its compressed inode, parse actual exFAT signature/geometry, require
  64 KiB clusters and root `eboot.bin` plus `sce_sys/param.json`.
- Full checks run `mkpfs verify`, `mkpfs unpack --deep`, compare all relative
  paths, sizes, empty directories and streaming SHA-256 against the source,
  then rehash source to detect changes during packing. Existing exFAT is also
  extracted and compared. A report records image SHA-256 and hardware-test status.
- Output is staged beside destination and replaced after validation. Failure
  and cancellation retain previous output. No source deletion or AMPR regeneration.
- Tk values are captured on the UI thread; overwrite requests use the UI queue.

## Commands and evidence

Local inspection only (no application compilation or dependency builds):

```bash
git clone https://github.com/DeJoTaDeEmE/ps5-ffpfs-cli.git
git clone https://github.com/PSBrew/MkPFS.git /tmp/ps5-audit-mkpfs
git clone https://github.com/drakmor/ShadowMountPlus.git /tmp/ps5-audit-smp
rg -n 'exfat|wrap|no-compress|unpack' /tmp/ps5-audit-mkpfs/mkpfs/cli.py
rg -n 'ffpfsc|exfat|nested' /tmp/ps5-audit-smp/README.md
```

Actions executes (exact subprocess commands appear in uploaded logs):

```bash
python -m pip install -r requirements-build.txt
python -m pip install ./unrar
python -m pip check
python tests/validate_conversion.py
python -m PyInstaller ... gui.py
lipo <each Mach-O file> -verify_arch x86_64
codesign --force --deep --sign - dist/PS5-FFPFS-CLI.app
codesign --verify --deep --strict dist/PS5-FFPFS-CLI.app
python tests/validate_conversion.py --binary "$PWD/dist/PS5-FFPFS-CLI.app/Contents/MacOS/PS5-FFPFS-CLI"
ditto -c -k --sequesterRsrc --keepParent dist/PS5-FFPFS-CLI.app PS5-FFPFS-CLI-macOS-Intel.zip
shasum -a 256 PS5-FFPFS-CLI-macOS-Intel.zip
```

`tests/validate_conversion.py` generates a deterministic synthetic game with
`sce_sys/param.json`, a dummy eboot, a zero-length file, an empty directory,
Unicode/spaced filenames, and data crossing PFSC block boundaries. Both output
formats are fully extracted and hashed. The compressed output is additionally
unpacked without `--deep` and must yield exactly `PPSA00001.exfat`, whose actual
signature is independently parsed. Tests reproduce and reject the old double
wrapper, reject a PFS renamed `.exfat`, check failed overwrite preserves old data,
and reject source-contained destinations and symbolic links.

The bundled suite opens actual GUI widgets, selects each format, starts the GUI
worker and waits for validation. Frozen MkPFS subprocesses are exercised during
packing, verification and extraction. This is stronger than `--help` smoke tests.
The workflow checks all bundled Mach-O files for x86_64 and minimum OS <=15.0.

Logs, dependency versions, application commit and architecture inventory are
published as `validation-evidence.zip`. Only a successful complete job publishes
the application artifact. A failed run uploads diagnostics instead.

## Outstanding hardware validation

No PS5 device is available to Actions. Console detection, mount, installation,
launch, firmware compatibility and real-game performance remain unverified.
Unsigned/ad-hoc macOS signing is not Apple notarization. No Apple Silicon support
is claimed. The references describe PFS as experimental, and older documentation
examples must not be applied without checking current MkPFS default behavior.

## Actions environment correction

Initial run `38607403295` failed in setup-python, before compilation/tests: Python
3.11.14 x64 is absent from the official Actions python-versions manifest. The
workflow now pins 3.11.9, the latest available 3.11 macOS x64 distribution in
that manifest. No older application or MkPFS source was substituted.
