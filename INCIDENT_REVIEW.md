# Large-conversion incident review — 14 October 2026

## Evidence before implementation

The owner reported that Builder disappeared while compressing Astro Bot (~140 GB),
with no remaining conversion process, empty output/temp folders and no recent
Builder DiagnosticReports entry. The game and its outputs were not accessed or
modified for this investigation; the reported empty directories were not treated
as proof of an external deletion.

Historical command records show that icon review created independent app copies
with bundle ID `com.dejotadeeme.ps5-ffpfs-cli.icon-review`. A cleanup command at
**21:02:44 Europe/Madrid** selected running apps by that ID and sent SIGTERM,
then unregistered/deleted those review copies. It did not check for active work.
That was unsafe: a review app could have been used for a real conversion.
The command did not record selected PIDs at cleanup time.

Read-only macOS log inspection corroborates two separate process exits:

| Instance | PID | Local exit time | Finding |
| --- | --- | --- | --- |
| Original bundle ID | 22805 | 20:43:53 | Exit recorded; cause not established |
| Review bundle ID | 39724 | 21:02:44 | Matches cleanup command timing |

The review PID was also explicitly recorded in an earlier inventory. Neither
the surviving logs nor the old app recorded which process was converting Astro
Bot. It is therefore incorrect to claim that cleanup could not have interfered,
or to assert that it definitely explains the original instance's earlier exit.
The internal launchd termination tuple is not interpreted as a Python exit code
or an OOM diagnosis. No forensic raw logs/screenshots are published here because
they include private desktop/system context.

Other visual commands opened Launchpad, changed focus, sent text/Escape and
changed Finder view. No broad Builder kill, replacement of an existing app or
Mac restart was found in the collected visual commands. Focus interference cannot
be ruled out. No desktop automation was repeated during this investigation.

## Code findings and small reproductions

- The original GUI close handler set cancellation, terminated its child and
  destroyed the window without confirmation. Executing that exact method via
  AST against fake objects reproduced `terminate` and `destroy`, with no real
  process touched.
- A synthetic ENOSPC exception in the same TemporaryDirectory pattern removed
  a small staged partial while retaining the synthetic original's SHA-256.
  This explains why failures can leave no output; it does not identify this
  incident's cause. Unvalidated output is never published as a finished image.
- Source packing uses streaming exFAT -> PFSC with 64 KiB blocks and a bounded
  `workers * 4` thread window. There is no evidence of loading the full 140 GB
  payload into memory. Offsets still grow with the block count, and exFAT metadata,
  native codecs, GUI text and Python overhead consume memory. No RSS measurement
  from the failed conversion exists; OOM remains unproved.
- Verification extracts the full game and requires substantial free disk space.
  Staging is hidden `.ps5-stage-*` beside the destination. The chosen temp directory
  is used for extraction/verification and does not direct every MkPFS pack artifact.
- Errors previously existed only in the GUI console; child status became a boolean
  and worker exceptions lost their traceback. A normal worker exception leaves the
  app open, so it alone does not explain disappearance of the entire GUI.

## Prepared protection (not installed or published)

Only GUI lifecycle/diagnostics and new support/test files change. `converter.py`,
`cli.py`, dependency pins, MkPFS format commands and the existing nine conversion
tests remain unchanged from the hardware-tested baseline.

- JSONL logs in `~/Library/Logs/PS5-EXFAT-PFS-Builder/`, separate from conversion
  temp/output. Each app session records PID, executable, source/output/temp settings
  without the password, progress, child PID/command/status/signal, traceback,
  confirmation/cancellation, heartbeat and completion. File permissions are 0600.
- Native Python fatal-error output goes to a companion `.faults.log`; Tk callback
  and worker errors are retained, including SystemExit in the worker.
- Window close and macOS Quit are refused while conversion/worker/child is active.
  Cancel requires confirmation. SIGTERM/SIGINT delivered to the Python GUI process
  become recorded requests, refused while active; the handler itself does not
  call Tk or perform file I/O.
- GUI text history is capped at 5,000 lines, while the disk log retains history.
  Nonzero child exit codes are explicit. No image serialization changes.

Limits: SIGKILL, native crashes, power loss, and termination imposed by an external
bootloader/OS cannot be guaranteed preventable. A session with a start but no end
indicates interruption; it is not an automatic resume feature. Logs include paths
and tool output and should be reviewed before sharing. They consume disk space;
no automatic deletion is implemented. RSS heartbeat reports GUI peak and completed
children peak, not the active child's live memory. Existing temp cleanup remains
unchanged; partial-output preservation needs a separate lifecycle design and is
not claimed here.

## Validation

`python tests/test_runtime_protection.py` runs nine headless regressions: blocked
close, live-child close guard, rejected cancel, signal request, persistent progress,
abrupt exit of a dedicated tiny helper, nonzero exit of another tiny helper,
blocked signal polling during active work and retention of worker SystemExit.
It never initializes Tk or converts a game. GitHub Actions additionally retains
the existing nine synthetic conversion tests. No Astro Bot conversion, original
file operation, local app compilation, installation or stable publication is part
of this change. Native bundled Quit/signal behavior still needs a final Actions
binary check after the separate UnRAR licensing decision.
