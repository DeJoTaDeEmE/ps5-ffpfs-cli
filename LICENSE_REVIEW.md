# Licensing release review

This is a technical inventory of the source, notices and distribution conditions,
not a claim that third-party authors have granted any new exception.

## Findings

1. The original [bizkut README](https://github.com/bizkut/ps5-ffpfs-cli#license)
   explicitly declares MIT for the application wrapper. The fork's README rewrite
   had omitted that section. `LICENSE` and `THIRD_PARTY_NOTICES.md` restore the
   declaration, attribution and full MIT terms without relicensing third parties.
2. The audited MkPFS source is GPL-3.0. The frozen app imports its image readers and
   ships its code. Its binary distribution must comply with GPLv3 for the combined
   work; calling all bundled software "MIT" would be incorrect. Corresponding
   source and GPL text must be provided with the binary.
3. RARLAB UnRAR's official 7.21 source license permits extraction and redistribution
   but restricts recreating RAR-compatible compression. This notice was missing
   from the vendored tree. The full text is now in `unrar/LICENSE.txt`,
   `licenses/UnRAR-LICENSE.txt`, and its required paragraph is in wrapper comments.
4. No exception for combining UnRAR with MkPFS was found in the audited MkPFS
   revision. This issue is **not resolved merely by adding attribution**.
   [GNU's compatibility guidance](https://www.gnu.org/licenses/gpl-faq.en.html#GPLIncompatibleLibs)
   explains that only the relevant rights holders can grant such an exception.
5. CPython, Tcl/Tk, UI, image, crypto, compression, FFI and build dependencies have
   distinct terms. Exact installed package notices and corresponding sources must
   be collected on Actions; Rust crates, OpenSSL, native codecs, Roboto and vendored
   helper notices must be preserved, not silently relabeled MIT.

## Prepared materials

- Full MIT/GPL/UnRAR/CPython/Tcl/Tk/Apache/libffi reference texts and project credits.
- `scripts/prepare_release_materials.py`: collects installed notices, metadata,
  checked PyPI source archives, the exact MkPFS source, locked Rust crate sources
  and licenses, actual OpenSSL source/version, and bundled font notices. It creates
  `PS5-FFPFS-CLI-Source.tar.gz`. It does not compile application code.
- The source repository contains the conversion engine, build recipe, dependency
  pins, reproducible tests, icon source, and complete `.icns`.

The collector has been syntax-checked but has **not yet run against the final
Actions environment**. Any missing notice or source/checksum failure must block
publication until repaired. Final packaging should copy its `Licenses/` tree to
`Contents/Resources/Licenses/` and publish the exact source archive alongside ZIP,
SHA-256 and test evidence.

## Decision required before stable binary publication

The recommended profile excludes UnRAR from the frozen app. Folder, ZIP, `.exfat`
and `.ffpfsc` conversion retain the same engine; RAR users extract first. The
engine's files need not change. Alternatively, keep UnRAR but defer publication
until a compatible exception or another licensing resolution is confirmed.

The owner's choice is pending. No new stable binary has been published or claimed
license-complete. Existing release assets have not been changed or deleted.
