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

The collector passed on [Actions run 38621256156](https://github.com/DeJoTaDeEmE/ps5-ffpfs-cli/actions/runs/38621256156)
for source commit `373aef4c5d15d47dbada434f1384fd7e70cab3dd`:
18 installed package inventories, 32 locked Rust crate inventories and the actual
cryptography backend source, OpenSSL 4.0.0 (14 April 2026), were collected. The
source archive SHA-256 was `875d277b666d80dc43b6199dda7fb342a589a79a84659228c7af43d15027f6aa`.
An earlier audit failed on metadata serialization and was repaired by preserving
raw METADATA; the successful run confirms the repaired collector.

This is a **source/notices audit, not a new application build or release**. Final
packaging must rerun the collector at the exact release commit, include its
`Licenses/` tree in `Contents/Resources/Licenses/`, and publish the corresponding
source archive with ZIP, SHA-256 and test evidence. Missing notices, unavailable
source or checksum mismatches remain publication failures.

## Decision required before stable binary publication

The recommended profile excludes UnRAR from the frozen app. Folder, ZIP, `.exfat`
and `.ffpfsc` conversion retain the same engine; RAR users extract first. The
engine's files need not change. Alternatively, keep UnRAR but defer publication
until a compatible exception or another licensing resolution is confirmed.

The owner has now authorized temporarily excluding UnRAR to prioritize an Intel
test executable with the approved icon and PR #3 protections. The workflow omits
its native build, explicitly excludes its modules, and audits frozen archive and
filesystem contents. Source retains separate UnRAR notices without bundling its
executable code. No new stable binary is claimed; the next binary is a prerelease.
Existing release assets have not been changed or deleted.

## UnRAR redistribution recheck (14 October 2026)

The official version-matched source archive was downloaded again with TLS
verification:

```sh
curl --fail --location --silent --show-error \
  https://www.rarlab.com/rar/unrarsrc-7.2.1.tar.gz \
  -o /tmp/ps5-unrar-redistribution-audit.tar.gz
tar -xOf /tmp/ps5-unrar-redistribution-audit.tar.gz unrar/license.txt
```

Its license matches the restored notice: redistribution, including inside other
packages, is permitted; modified source must retain the specified paragraph in
the license/documentation and source comments. Recreating RAR-compatible archiving
or its proprietary compression algorithm is prohibited. The relevant terms are
the UnRAR source license, not the paid WinRAR application's general EULA.
See [RARLAB's official source downloads](https://www.rarlab.com/rar_add.htm).

The current workflow builds `unrar._unrar` from the vendored C++ sources and
collects it into the same frozen application as MkPFS. Treating this as mere
aggregation has not been justified. According to
[GNU's guidance](https://www.gnu.org/licenses/gpl-faq.en.html#MereAggregation),
the communication and actual integration matter; putting a component in a
separate file alone does not establish independence. The compatibility concern
is an assessment of this integration, not a claim that RARLAB prohibits all
redistribution.

Options assessed at the redistribution recheck (the owner subsequently authorized
option 1 for the protected test build):

1. **Publish without bundled UnRAR (recommended):** retain the proven folder,
   ZIP, exFAT and FFPFSC engine; users extract RAR archives before conversion.
   Packaging and documentation must accurately reflect this limitation.
2. **Retain the current integrated UnRAR:** defer the new public binary until
   the relevant rights holders provide an applicable exception or another
   licensing resolution is established. Source publication and credits alone
   do not remove conflicting conditions.
3. **Investigate an independent external extractor:** a separately installed
   command-line tool exchanging ordinary files may allow a different licensing
   analysis. This needs an actual separation review and new extraction tests;
   it is not an automatic workaround and is outside the priority release scope.

No Finder, Dock, Launchpad or System Events automation is part of this review.
The owner's running application and Astro Bot conversion are left untouched.
Launchpad verification is no longer a release task requested by the owner;
the existing Finder and Dock checks are accepted. Stable publication remains
pending explicit stable-release authorization. The test ZIP is separately authorized.
