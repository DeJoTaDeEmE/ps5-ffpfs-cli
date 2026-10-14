# macOS path-input regression review

Reported example: pasting `/Volumes/TAHOENTOSH - Data/PS5_OUTPUT` into an already
populated Output destination appended a second complete path. Temp dir had the
same editing behavior. RC1 uses standard Entry insertion without custom path-paste
handling; a paste at the caret with no selected text can append the clipboard.

Implementation references: [CustomTkinter 5.2.2 Entry delegation](https://github.com/TomSchimansky/CustomTkinter/blob/v5.2.2/customtkinter/windows/widgets/ctk_entry.py)
and [Tk Entry selection/paste bindings](https://www.tcl-lang.org/man/tcl8.6/TkCmd/entry.htm).
The Actions reproduction uses exact release commit
`6911cd828a8b5f2202d9bdf94124442013f47406` and actual Aqua widgets. Cmd+A behavior
before the fix is recorded without assuming it failed on every Tk installation.

## Changes

- Explicit Cmd+A/SelectAll handling, including the native inner Entry via CTk's
  delegated bind method. A handled paste returns `break` so class bindings cannot
  insert the clipboard a second time.
- An absolute clipboard path replaces the whole field. Ordinary fragments retain
  caret/selection editing behavior. Empty clipboard and disabled entry leave text
  intact. Spaces/Unicode are preserved; outer copied quotes are removed.
- Multiline/NUL input, repeated volume roots and repeated absolute prefixes are
  rejected with feedback before a worker starts. This is a conservative heuristic,
  not a universal parser of accidentally concatenated paths. Existing directories
  with legitimate repeated names are exempt; no silent path repair is attempted.
- Temp dir must be an existing directory when supplied. Output still accepts a
  directory or explicit file path, preserving the converter's existing contract.
- Browse starts from an existing directory/parent even if the entry is malformed
  or contains an output filename. Actual buttons are invoked in widget tests;
  chooser selection/cancellation is controlled, not a manual OS-picker visual test.

## Protection review

RC1 frozen lifecycle guards and persistent logs remain enabled. Logging write
failure no longer raises into worker completion/UI callbacks; new work is refused
if a log probe fails, and ongoing diagnostic degradation is visible. An orphan
child which subsequently finishes is reaped and releases the close guard. Active
child/worker state also blocks a signal-driven exit even if the running flag alone
is false. There is no promise to survive SIGKILL or power loss.

## Evidence

Actions exports `paste-before.json`, `paths-source.json`, `paths-bundled.json`,
`path-validation-tests.log`, `protection-tests.log` and frozen lifecycle evidence.
Both format/extraction/hash suites, icon/architecture/signature and UnRAR exclusion
remain mandatory. Results describe synthetic tests, not another PS5/Astro Bot run.

`converter.py`, `cli.py`, requirements and the nine existing conversion tests are
byte-identical to hardware-tested baseline `03122c76973965aaa8f72470937795ac20cd412a`.
Only GUI editing/preflight/lifecycle, diagnostics, test support, docs and packaging
change. No local application compilation, desktop automation or original-game
operation is used. This build is made and checked in GitHub Actions.
