# Credits and third-party licensing / Créditos y licencias

## Application and tested PS5 environment

- **bizkut / ps5-ffpfs-cli** — original CLI, GUI and Python UnRAR wrapper.
  [Original repository](https://github.com/bizkut/ps5-ffpfs-cli). Its README
  declares MIT; this declaration and attribution are restored in `LICENSE`.
- **DeJoTaDeEmE** — fork maintenance, macOS Intel packaging and confirmation of
  real PS5 tests with PPSA28002 version 01.006 on firmware 13.40.
- **PSBrew / MkPFS** — PFS/PFSC and exFAT creation, inspection and extraction;
  [source](https://github.com/PSBrew/MkPFS), audited revision
  `1d5df56ae29390900e888fa12e5f9856aa797adc`, GPL-3.0. Full license:
  `licenses/MkPFS-GPL-3.0.txt`. The frozen application's distribution must comply
  with GPLv3 for the combined work; MIT does not override MkPFS's license.
- **drakmor / ShadowMountPlus** — PS5 detection/mounting target and format
  reference; [source](https://github.com/drakmor/ShadowMountPlus), GPL-3.0.
  Its payload is **not included** in the macOS app. Reference license:
  `licenses/ShadowMountPlus-GPL-3.0.txt`.
- **kstuff authors and maintainers** — separate PS5 payload used in the owner's
  test. It is not included in the macOS app. The owner did not supply the precise
  fork/version; this document does not claim to identify that tested binary's
  license or redistribute it.
- **OpenAI imagegen** — approved EXFAT / PFS icon artwork; source image and prompt
  are in `assets/`. The original Python logo is not used as the application icon.

## Python and native dependencies

Each component retains its own license and copyright. The build inventory and
full upstream texts are collected into the app's `Contents/Resources/Licenses/`
and included in the downloadable source/evidence package; a single blanket MIT
label is insufficient for the frozen bundle.

| Project / contributors | Purpose | License / notice source |
| --- | --- | --- |
| Python Software Foundation and CPython contributors | Python interpreter and standard library | PSF/Python license stack; `licenses/CPython-3.11.9-LICENSE.txt` |
| Tcl/Tk Core Teams, UC Regents, Sun/Scriptics/Ajuba and contributors | Native Tk desktop UI | Tcl/Tk permissive license terms; `licenses/Tcl-8.6.13-license.terms`, `licenses/Tk-8.6.13-license.terms` |
| Tom Schimansky / CustomTkinter | Desktop widgets and theme | CC0-1.0; installed package's license and any font-specific notices |
| Google / Christian Robertson / Roboto | Bundled font files | Apache-2.0 for the bundled historical Roboto fonts; actual font name-table notices retained |
| Armin Rigo, Anthony Green and libffi contributors / libffi | Native FFI implementation, where redistributed | MIT; `licenses/libffi-MIT.txt` |
| Hatch / Hatchling contributors | MkPFS isolated wheel build backend | MIT; build-only, upstream source recipe in MkPFS pyproject.toml |
| GitHub Actions contributors | Hosted build/checkout/Python setup service | External build tooling, not application code; each action retains its upstream terms |
| Alberto Sottile / darkdetect | OS appearance detection | BSD-3-Clause |
| Jeffrey A. Clark, Fredrik Lundh / Secret Labs and Pillow contributors | Image processing | MIT-CMU / historical PIL terms; bundled codec/font notices are retained |
| Python Cryptographic Authority and contributors / cryptography | MkPFS crypto bindings | Apache-2.0 OR BSD-3-Clause; OpenSSL/Rust notices remain separate |
| OpenSSL Project and contributors | Native cryptographic backend | Apache-2.0 for current OpenSSL; record the actual bundled version |
| Leiden University Medical Center / python-zlib-ng | Compression binding | PSF-2.0; embedded zlib-ng uses its own zlib license |
| zlib-ng contributors, Jean-loup Gailly and Mark Adler / zlib | Native compression | zlib license; embedded upstream texts retained |
| Leiden University Medical Center / python-isal | Compression binding | PSF-2.0 |
| Intel and ISA-L contributors | Native accelerated compression | BSD-3-Clause |
| Armin Rigo, Maciej Fijalkowski / CFFI | Native FFI | Actual installed package terms; current metadata declares MIT-0 |
| Eli Bendersky / pycparser | C parser | BSD-3-Clause |
| Kenneth Reitz and certifi contributors / Mozilla CA store | Certificate trust bundle | MPL-2.0; source is included if redistributed |
| Donald Stufft, PyPA and packaging contributors | Package/version helpers | Apache-2.0 OR BSD-2-Clause |
| PyInstaller contributors | Frozen executable / bootloader | GPL-2.0-or-later with bootloader distribution exception; full exception retained |
| pyinstaller-hooks-contrib contributors | Build hooks | GPL-2.0 with exception / Apache-2.0 as declared by individual files |
| Ronald Oussoren / altgraph and macholib | Build graph and Mach-O tooling | MIT |
| Python Packaging Authority / setuptools | Build support, optional runtime support and vendored helpers | MIT; vendored modules retain their own license notices |
| Daniel Holth / wheel | Build tool | MIT |

`package-inventory.json` records exact installed versions, authors, project URLs,
license declarations, and paths/hashes of retained notices. Build-only software
is identified by the inventory rather than claimed to be shipped indiscriminately.
Native vendor and Rust crate notices must not be silently discarded.

## UnRAR source and pending binary-distribution decision

**Alexander Roshal / RARLAB UnRAR** is not MIT or GPL. The vendored version header
identifies 7.21 (27 April 2026). The extraction-only source has a restriction on
recreating RAR-compatible compression, and requires preserving its notice.
The full official text is restored in `unrar/LICENSE.txt` and
`licenses/UnRAR-LICENSE.txt`; relevant redistribution text is also retained in
source comments. [Official source download](https://www.rarlab.com/rar_add.htm).

The combination of this restricted module with GPL-licensed MkPFS needs a
licensing resolution before a new stable binary is published. No applicable
exception has been found in the audited MkPFS revision. Options are excluding
UnRAR from the binary (users extract RAR first), or obtaining/confirming a suitable
exception from the relevant rights holders. Adding credit alone does not resolve
that issue. [GNU guidance](https://www.gnu.org/licenses/gpl-faq.en.html#GPLIncompatibleLibs).

## Código fuente / Source availability

Project-specific code is available in this public GitHub repository. Stable
binary releases should additionally include the exact tagged project source,
the pinned MkPFS source and notices, required redistributed component source,
build scripts, dependency versions and hashes alongside the application ZIP.
This preserves license notices, permits reproducible inspection, and does not
include any original game files or PS5 payload binaries.
