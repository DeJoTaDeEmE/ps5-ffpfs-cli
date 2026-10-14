# exFAT + PFS application icon

`icon-source.png` is the transparent master artwork. `PS5-FFPFS-CLI.icns` contains
all ten standard/Retina representations: 16, 16@2x, 32, 32@2x, 128, 128@2x,
256, 256@2x, 512 and 512@2x (1024 pixels).

Generate the icon on macOS with `python scripts/build_icon.py`. Actions regenerates
it, passes `--icon assets/PS5-FFPFS-CLI.icns` to PyInstaller, then validates the
bundle's Info.plist reference, actual bytes, and all decoded representations with
`python scripts/verify_bundle_icon.py`. Application compilation stays on Actions.

Artwork generated using the built-in imagegen tool. Final prompt:

> Use case: logo-brand. Asset: one finished macOS app icon for a native Intel desktop converter of exFAT game folders and compressed PFS containers. Concept: exFAT + PFS, two interlocking precision-engineered storage layers forming one unmistakable geometric container emblem. A polished dark graphite rounded-square macOS tile with subtle beveled edge, one luminous cyan inner storage layer and one cobalt outer enclosing layer; the visual should communicate a filesystem nested once inside another. Refined restrained 3D depth, crisp large simple shapes, premium professional macOS utility design, legible at 16 pixels. Centered square 1024x1024 composition with generous transparent padding outside the rounded-square tile. One icon only, front view, no mockup, no scene. No text, no letters, no Python logo, no PlayStation or Apple logos, no controller, no watermark. Truly transparent canvas outside the icon.
