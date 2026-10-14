# macOS Intel protected test build — 1.0.1 RC1

This test build combines the approved EXFAT/PFS icon with persistent diagnostics
and conversion close protection. It targets macOS Sequoia Intel x86_64.

Supported: game folders to raw `.exfat` and compressed `.ffpfsc`, existing exFAT
input, and ZIP extraction. **UnRAR is temporarily excluded from the executable.**
Extract RAR archives separately and select the extracted game folder. Source
still contains the separately licensed UnRAR code/notices for transparency.

Logs: `~/Library/Logs/PS5-EXFAT-PFS-Builder/`, `.jsonl` and `.faults.log`.
Progress/errors, child status and full tracebacks persist outside game temp/output.
Closing the window or choosing Quit during work is refused. Cancel requires
confirmation. Forced kills, power loss and OS failures cannot be guaranteed
preventable; missing completion indicates interruption, not successful output.
Do not assume a partial file can be resumed. Existing temporary cleanup is unchanged.

The serializer, format commands and dependency pins match hardware-tested revision
`03122c76973965aaa8f72470937795ac20cd412a`. GUI lifecycle/input selection and packaging
change; converter.py and cli.py do not. Both formats previously worked on PS5 13.40
with kstuff + ShadowMountPlus, PPSA28002 Ninja Gaiden: Ragebound 01.006. This test
build has not itself been tested on PS5 and no Astro Bot conversion was rerun.

Built only in GitHub Actions. Checks include nine existing synthetic conversion
tests in source and frozen GUI, nine headless protection tests, native frozen
SIGTERM/window close/macOS Quit/declined Cancel tests with a held synthetic worker,
UnRAR exclusion, icon representations, x86_64/minimum deployment and signature.
Lifecycle tests initialize widgets only on the Actions runner; they never control
the owner's desktop. Test evidence and exact corresponding source accompany ZIP.

The app uses an ad-hoc signature; it is not Apple notarized. This is a prerelease
for validation, not a guarantee of stability for every game/size/firmware.
