"""Actions only: signal our own test app; never discover/control installed apps."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

binary = str(Path(sys.argv[1]).resolve())
root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="ps5-lifecycle-ci-") as tmp:
    directory = Path(tmp)
    process = subprocess.Popen([binary, "--lifecycle-test", tmp])
    try:
        deadline = time.monotonic() + 30
        while not (directory / "ready.json").exists():
            assert process.poll() is None, f"Test app exited early: {process.returncode}"
            if time.monotonic() > deadline:
                raise TimeoutError("Lifecycle test app did not become ready")
            time.sleep(0.1)
        ready = json.loads((directory / "ready.json").read_text())
        # Signal the actual launched executable PID, covering frozen entry behavior.
        os.kill(process.pid, signal.SIGTERM)
        assert process.wait(timeout=35) == 0, "Bundled GUI did not survive SIGTERM during work"
        report = json.loads((directory / "result.json").read_text())
        for key in ("signal_blocked", "window_close_blocked", "mac_quit_blocked", "declined_cancel_preserves_work"):
            assert report[key] is True, (key, report)
        log_path = Path(report.pop("log_path"))
        log = log_path.read_text()
        events = [json.loads(line) for line in log.splitlines()]
        assert any(e["event"] == "signal_exit_request" and e["blocked"] for e in events)
        assert events[-1]["event"] == "application_exit"
        report.update(launched_pid=process.pid, unrar_bundled=False)
        (root / "validation/bundled-lifecycle.json").write_text(json.dumps(report, indent=2) + "\n")
        (root / "validation/bundled-lifecycle.jsonl").write_text(log)
        print(json.dumps(report, indent=2))
    finally:
        # Only the exact helper created above, never an app found by name/bundle ID.
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
