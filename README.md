# PS5 image converter for macOS Intel

A Tk/CustomTkinter desktop application targeting macOS Sequoia (15) Intel x86_64.
**Compatibility tested:** macOS Sequoia on Intel x86_64, with both `.exfat` and
`.ffpfsc` outputs successfully used on a real PS5 as detailed below.

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

Download `PS5-FFPFS-CLI-macOS-Intel.zip` from the
[stable releases](https://github.com/DeJoTaDeEmE/ps5-ffpfs-cli/releases/latest), extract it,
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

## Tested Compatibility / Compatibilidad comprobada

### Español

El propietario del repositorio confirmó las siguientes pruebas con imágenes
creadas en **macOS Sequoia Intel x86_64** y utilizadas en una consola real:

| Configuración | Detalle |
| --- | --- |
| Consola | PlayStation 5 |
| Firmware | **13.40** |
| Herramientas | kstuff + ShadowMountPlus |
| Juego | Ninja Gaiden: Ragebound (PPSA28002) |
| Versión del juego | 01.006 |
| Sistema utilizado para crear las imágenes | macOS Sequoia Intel x86_64 |

**Resultados verificados en consola real:**

- ✅ **exFAT (`.exfat`):** detectado, montado, ejecutado y funcionando.
- ✅ **FFPFSC comprimido (`.ffpfsc`):** detectado, montado, ejecutado y funcionando.

Estas pruebas confirman el funcionamiento de ambos formatos en **PS5 con firmware
13.40 y esta configuración concreta**. **No garantizan compatibilidad con todos
los juegos y firmwares**, ni con todas las versiones de kstuff o ShadowMountPlus.
No se proporcionaron las versiones exactas de kstuff y ShadowMountPlus en el
informe. ShadowMountPlus sigue describiendo el soporte PFS como experimental.

### English

The repository owner confirmed the following tests using images created on
**macOS Sequoia Intel x86_64** and used on a real console:

| Configuration | Details |
| --- | --- |
| Console | PlayStation 5 |
| Firmware | **13.40** |
| Tools | kstuff + ShadowMountPlus |
| Game | Ninja Gaiden: Ragebound (PPSA28002) |
| Game version | 01.006 |
| System used to create the images | macOS Sequoia Intel x86_64 |

**Results verified on a real console:**

- ✅ **exFAT (`.exfat`):** detected, mounted, launched and working.
- ✅ **Compressed FFPFSC (`.ffpfsc`):** detected, mounted, launched and working.

These tests confirm that both formats work on **PS5 firmware 13.40 with this
specific configuration**. They **do not guarantee compatibility with all games
and firmware versions**, or with all versions of kstuff or ShadowMountPlus.
Exact kstuff and ShadowMountPlus versions were not supplied with the report.
ShadowMountPlus still documents PFS support as experimental.

The stable release adds a custom **exFAT + PFS** macOS icon while preserving the
hardware-tested conversion engine. The icon includes standard and Retina sizes
from 16 to 1024 pixels in `assets/PS5-FFPFS-CLI.icns`; the generic Python icon is
replaced in the application bundle. No Apple Silicon build is claimed.

Automated tests remain enabled: a reproducible synthetic fixture validates image
structure, compression, extraction, SHA-256 identity and rejection of double
wrapping. It is not a playable game and is separate from the owner's real PS5
report. `ps5_hardware_tested: false` in a generated image's validation report means
that **that individual image** has not undergone an automated hardware test; it
does not negate the documented successful test of PPSA28002.

References: [PSBrew/MkPFS](https://github.com/PSBrew/MkPFS) and
[drakmor/ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus).
See [VALIDATION.md](VALIDATION.md) for the audit, reproduction and test evidence.

## Credits and licenses / Créditos y licencias

**Compilación de prueba 1.0.1 RC1 / Test build:** el icono EXFAT/PFS y las protecciones
de cierre incluyen registros persistentes en `~/Library/Logs/PS5-EXFAT-PFS-Builder/`.
UnRAR se excluye temporalmente del ejecutable: extrae los RAR por separado y selecciona
la carpeta del juego. Carpetas, ZIP, `.exfat` y `.ffpfsc` mantienen el motor probado.
Consulta [TEST_BUILD.md](TEST_BUILD.md) para las pruebas y limitaciones.

The protected Intel test build temporarily excludes UnRAR. Extract RAR archives
separately; game-folder conversion to both formats retains the tested serializer.
Persistent diagnostics and close protection are described in [TEST_BUILD.md](TEST_BUILD.md).

This is a maintained fork of [bizkut/ps5-ffpfs-cli](https://github.com/bizkut/ps5-ffpfs-cli).
The original project declares MIT for its wrapper; see [LICENSE](LICENSE).
MkPFS is GPL-3.0; the combined binary is not covered by a blanket MIT grant.
All authors, runtime/build projects and component-specific terms are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), with full texts in [licenses/](licenses/).
ShadowMountPlus and kstuff are credited as separate console tools, not bundled payloads.

Este proyecto deriva de **bizkut/ps5-ffpfs-cli**. Se conserva la declaración MIT
del envoltorio original y se reconocen por separado la GPL de MkPFS y las licencias
de cada dependencia. Los créditos y los avisos completos están enlazados arriba.
La revisión ha identificado una cuestión pendiente entre UnRAR y la GPL de MkPFS:
añadir créditos no sustituye resolverla antes de la siguiente publicación estable.
