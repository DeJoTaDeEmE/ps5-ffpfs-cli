# exFAT + PFS application icon

`icon-source.png` is the transparent master artwork. `PS5-FFPFS-CLI.icns` contains
all ten standard/Retina representations: 16, 16@2x, 32, 32@2x, 128, 128@2x,
256, 256@2x, 512 and 512@2x (1024 pixels).

Generate the icon on macOS with `python scripts/build_icon.py`. Actions regenerates
it, passes `--icon assets/PS5-FFPFS-CLI.icns` to PyInstaller, then validates the
bundle's Info.plist reference, actual bytes, and all decoded representations with
`python scripts/verify_bundle_icon.py`. Application compilation stays on Actions.

Artwork generated with the built-in imagegen tool and explicitly approved by the
repository owner. The exact uppercase names **EXFAT** and **PFS** are large,
front-facing and high-contrast for 32/64 pixel Dock and Finder views. Approval
preview was inspected at 128, 64 and 32 pixels. Final prompt:

> Use case: logo-brand. Create a revised professional macOS application icon proposal. The supplied image is a reference for its blue, cyan and black aesthetic only, NOT a shape to preserve. The new icon must prominently and unmistakably show the exact words "EXFAT" (E X F A T) and "PFS" (P F S), both ALL UPPERCASE, perfectly spelled. These two words are the primary design, not small labels. Use two stacked centered lines: EXFAT above, PFS below. Extremely bold clean sans-serif lettering, generous character spacing, broad strokes and very high contrast, occupying most of the usable icon face; the longest line EXFAT spans about 80% of the inner width. Letters must face straight toward the viewer with no perspective, curvature or distortion. Aim for readable words in Dock/Finder at 32 and 64 pixels. Use a refined black/graphite macOS rounded-square tile, restrained cobalt-blue and cyan storage-layer accents, subtle premium bevel and finish. Keep geometric file-container symbolism secondary and simple; remove the large 3D cubes so they cannot compete with the text. Both names must remain large, crisp and fully unobstructed. One finished icon, square canvas, transparent outside the rounded-square tile, standard macOS icon margins. No mockup, no scene, no Python logo, no additional words, no watermark. This is a design preview only, not an app change.
