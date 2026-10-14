# Approved EXFAT / PFS icon review

The owner approved the revised blue/black icon with the exact uppercase words
**EXFAT** and **PFS**. Source: `assets/icon-source.png`. Complete macOS encoding:
`assets/PS5-FFPFS-CLI.icns`, built with `scripts/build_icon.py`.

## Checks performed

- All ten standard/Retina icon representations, 16 to 1024 pixels, were generated.
- The approval preview was inspected at 128, 64 and 32 pixels.
- Native macOS Sequoia Intel review used a **private copy of the already compiled
  Actions application**, with only icon and review bundle identity changed and an
  ad-hoc signature renewed. No application engine was compiled locally or changed.
- Dock: actual native icon capture showed the approved EXFAT/PFS artwork, not Python.
- Finder: the approved artwork was visible in icon view, including the small 32px
  representation; a 64px icon-view capture was also inspected.
- Launchpad: registration was attempted for a temporary independent review app;
  searches/overlay interaction did not produce a reliable capture of its entry.
  **Launchpad visual verification remains pending and is not claimed as passed.**
- Temporary review installations were removed after checks. Original installed
  applications and game files were not replaced or deleted.

## Release gate

The next bundle explicitly sets version 1.0.1, minimum macOS 15.0 and Retina
capability before signing; the changed version helps native icon cache updates.
This is metadata only. Final Actions packaging must pass the custom `.icns` reference/byte/representation
checks, all current conversion tests, Intel/Mach-O deployment checks and signing.
After that build, verify the final application entry in Launchpad. A valid `.icns`
or successful compile alone must not be presented as proof of its cached appearance
in every macOS surface. The conversion engine, GUI/CLI and current test files are
unchanged from the hardware-tested baseline `03122c76973965aaa8f72470937795ac20cd412a`.
