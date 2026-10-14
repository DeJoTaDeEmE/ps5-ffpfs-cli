"""Persistent diagnostics; independent of conversion/image serialization."""
from __future__ import annotations
import datetime
import faulthandler
import json
import os
from pathlib import Path
import resource
import sys
import threading
import uuid


class RunLog:
    def __init__(self, directory=None):
        directory = Path(directory) if directory else (
            Path.home() / "Library/Logs/PS5-EXFAT-PFS-Builder" if sys.platform == "darwin"
            else Path.home() / ".local/state/ps5-exfat-pfs-builder")
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = directory / f"{stamp}-{os.getpid()}-{uuid.uuid4().hex[:8]}.jsonl"
        self.stream = self.path.open("x", encoding="utf-8", buffering=1)
        os.chmod(self.path, 0o600)
        self.lock = threading.Lock()
        self.write_error = None
        self.event("application_start", pid=os.getpid(), executable=sys.executable,
                   python=sys.version, platform=sys.platform)

    def event(self, event, **fields):
        row = {"time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "event": event, **fields}
        with self.lock:
            try:
                self.stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                self.stream.flush()
                if event not in {"output", "heartbeat"}:
                    os.fsync(self.stream.fileno())
            except (OSError, ValueError) as exc:
                # Diagnostics must not prevent worker completion or Tk callbacks.
                self.write_error = str(exc)
                return False
        return True

    def heartbeat(self, running, child_pid):
        self.event("heartbeat", running=running, child_pid=child_pid,
                   gui_peak_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   completed_children_peak_rss=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                   rss_units="bytes" if sys.platform == "darwin" else "KiB")

    def enable_faults(self):
        self.fault_stream = self.path.with_suffix(".faults.log").open("a", buffering=1)
        os.chmod(self.path.with_suffix(".faults.log"), 0o600)
        faulthandler.enable(file=self.fault_stream, all_threads=True)

    def close(self):
        self.event("application_exit")
        try:
            self.stream.close()
        except OSError as exc:
            self.write_error = str(exc)
        if hasattr(self, "fault_stream"):
            faulthandler.disable()
            try:
                self.fault_stream.close()
            except OSError as exc:
                self.write_error = str(exc)


class ExitGuard:
    """Signal handler only records a request; Tk processes it on its own thread."""
    def __init__(self):
        self.pending_signal = None

    def receive(self, signum, frame):
        self.pending_signal = signum
