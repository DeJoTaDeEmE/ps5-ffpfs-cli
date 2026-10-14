#!/usr/bin/env python3
from __future__ import annotations
import multiprocessing
import sys
import os

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] == "--mkpfs-internal":
        from mkpfs.cli import cli_mkpfs_main
        sys.exit(cli_mkpfs_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--dependency-test":
        import importlib.util
        assert importlib.util.find_spec("unrar") is None, "Test bundle must exclude UnRAR"
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import isal, zlib_ng
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--convert-internal":
        from cli import main
        sys.exit(main(sys.argv[2:]))

import io
import contextlib
import re
import queue
import threading
import subprocess
import shutil
import tempfile
import signal
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    raise ImportError("GUI requires 'customtkinter'. Install it via: pip install customtkinter")

import cli
from runtime_log import RunLog, ExitGuard

PROGRESS_LINE_RE: re.Pattern[str] = re.compile(r"\[(?P<bar>[#-]{4,})\]\s*(?P<pct>\d{1,3})%\s*(?P<label>[^\r\n]*)")

def read_stream_by_lines(stream):
    """Yield logical lines from a stream, deduplicating \\r-overwrite progress frames.

    Uses readline() rather than read(1) to avoid per-character overhead.
    Consecutive lines that would overwrite the previous terminal line (i.e.
    lines produced by a \\r-only progress bar) are collapsed so only the most
    recent frame for a given prefix is forwarded to the GUI log queue.
    """
    last_cr_line: str | None = None
    for raw in stream:
        # raw still contains the trailing newline / CR from readline
        stripped = raw.rstrip('\r\n')
        if not stripped:
            continue
        # Detect whether the original line ended with \r only (progress frame)
        ends_cr = raw.endswith('\r') and not raw.endswith('\n')
        if ends_cr:
            # Accumulate, only emit when a non-CR line follows or stream ends
            last_cr_line = stripped
        else:
            if last_cr_line is not None:
                yield last_cr_line
                last_cr_line = None
            yield stripped
    if last_cr_line is not None:
        yield last_cr_line

@contextlib.contextmanager
def managed_temp_dir(user_temp_dir: str | None = None):
    """Create a temporary directory, optionally inside a user-specified directory."""
    if user_temp_dir:
        import tempfile
        path = tempfile.mkdtemp(dir=user_temp_dir)
        try:
            yield Path(path)
        finally:
            import shutil
            shutil.rmtree(path)
    else:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

class GuiLogRedirect(io.TextIOBase):
    """Thread-safe redirector that feeds a Tkinter text widget via a queue."""
    def __init__(self, app: PS5ContainerBuilderApp, tag: str = "info") -> None:
        super().__init__()
        self._app = app
        self._tag = tag

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        self._app.enqueue_log(text, self._tag)
        return len(text)

    def flush(self) -> None:
        pass

class PS5ContainerBuilderApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.log_queue = queue.Queue(maxsize=10000)
        self.progress_queue = queue.Queue(maxsize=10000)
        self.completion_queue = queue.Queue(maxsize=10000)
        self.confirmation_queue = queue.Queue()
        self.worker_thread = None
        self.current_process = None
        self.is_closing = False
        self.is_cancelled = False
        self.is_running = False
        self.run_log = RunLog()
        self.run_log.enable_faults()
        self.exit_guard = ExitGuard()
        self.previous_signals = {}
        for signum in (signal.SIGTERM, signal.SIGINT):
            self.previous_signals[signum] = signal.signal(signum, self.exit_guard.receive)
        self.root.report_callback_exception = self._report_callback_exception

        self.log_after_id = None
        self.progress_after_id = None
        self.completion_after_id = None

        self._setup_window()
        self._build_ui()
        self._start_log_polling()
        self._start_progress_polling()
        self._start_completion_polling()
        self.diagnostics_after_id = self.root.after(5000, self._poll_diagnostics)

    def _setup_window(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.root.title("PS5 PFS Container Builder GUI")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if sys.platform == "darwin":
            self.root.createcommand("tk::mac::Quit", self._on_close)

    def _report_callback_exception(self, exc_type, exc, tb):
        self.run_log.event("tk_exception", traceback="".join(traceback.format_exception(exc_type, exc, tb)))
        self.enqueue_log(f"[ERROR] UI error: {exc}\nSee {self.run_log.path}\n", "error")

    def _poll_diagnostics(self):
        requested = self.exit_guard.pending_signal
        self.exit_guard.pending_signal = None
        if requested is not None:
            self.run_log.event("signal_exit_request", signal=requested, blocked=self.is_running)
            if not self.is_running:
                self._on_close()
                return
            self.enqueue_log("[WARN] Exit signal blocked while conversion is active.\n")
        process = self.current_process
        self.run_log.heartbeat(self.is_running, process.pid if process else None)
        self.diagnostics_after_id = self.root.after(5000, self._poll_diagnostics)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=0)
        self.root.rowconfigure(3, weight=1)

        self._build_header()
        self._build_fields()
        self._build_progress()
        self._build_log_console()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.root)
        header.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")

        title_label = ctk.CTkLabel(
            header,
            text="PS5 PFS Container Builder",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(side="left", padx=15, pady=10)

        subtitle_label = ctk.CTkLabel(
            header,
            text="Create exFAT images or a single compressed PFS wrapper",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#94a3b8"
        )
        subtitle_label.pack(side="left", padx=(10, 15), pady=10)

    def _build_fields(self) -> None:
        fields_frame = ctk.CTkFrame(self.root)
        fields_frame.grid(row=1, column=0, padx=12, pady=6, sticky="ew")
        fields_frame.columnconfigure(1, weight=1)

        # Source Path
        ctk.CTkLabel(fields_frame, text="Source path:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=12, pady=10, sticky="e"
        )
        self.source_var = tk.StringVar()
        self.source_entry = ctk.CTkEntry(
            fields_frame,
            textvariable=self.source_var,
            placeholder_text="Select a game folder or an existing .exfat file"
        )
        self.source_entry.grid(row=0, column=1, padx=6, pady=10, sticky="ew")

        self.source_var.trace_add("write", self._on_source_changed)

        source_buttons = ctk.CTkFrame(fields_frame, fg_color="transparent")
        source_buttons.grid(row=0, column=2, padx=12, pady=10, sticky="w")

        browse_folder_btn = ctk.CTkButton(
            source_buttons,
            text="Browse Folder",
            width=110,
            command=self._browse_folder
        )
        browse_folder_btn.pack(side="left", padx=3)

        browse_file_btn = ctk.CTkButton(
            source_buttons,
            text="Browse File",
            width=110,
            command=self._browse_file
        )
        browse_file_btn.pack(side="left", padx=3)

        # Output Destination
        ctk.CTkLabel(fields_frame, text="Output destination:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, padx=12, pady=10, sticky="e"
        )
        self.output_var = tk.StringVar(value=str(Path(".").resolve()))
        self.output_entry = ctk.CTkEntry(
            fields_frame,
            textvariable=self.output_var,
            placeholder_text="Optional: output directory or specific file path (defaults to current directory)"
        )
        self.output_entry.grid(row=1, column=1, padx=6, pady=10, sticky="ew")

        browse_out_btn = ctk.CTkButton(
            fields_frame,
            text="Browse Destination",
            width=120,
            command=self._browse_destination
        )
        browse_out_btn.grid(row=1, column=2, padx=12, pady=10, sticky="w")

        # Temp dir Row
        ctk.CTkLabel(fields_frame, text="Temp dir:", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, padx=12, pady=10, sticky="e"
        )
        self.temp_dir_var = tk.StringVar()
        self.temp_dir_entry = ctk.CTkEntry(
            fields_frame,
            textvariable=self.temp_dir_var,
            placeholder_text="Optional: directory for temporary PFS images (defaults to system temp)"
        )
        self.temp_dir_entry.grid(row=2, column=1, padx=6, pady=10, sticky="ew")
        browse_temp_btn = ctk.CTkButton(
            fields_frame,
            text="Browse",
            width=110,
            command=self._browse_temp_dir
        )
        browse_temp_btn.grid(row=2, column=2, padx=12, pady=10, sticky="w")

        # Password Field (Hidden by default)
        self.password_label = ctk.CTkLabel(fields_frame, text="Password:", font=ctk.CTkFont(weight="bold"))
        self.password_var = tk.StringVar()
        self.password_entry = ctk.CTkEntry(
            fields_frame,
            textvariable=self.password_var,
            show="*",
            placeholder_text="Archive Password (if any)"
        )

        # Options Row
        self.options_frame = ctk.CTkFrame(fields_frame, fg_color="transparent")
        self.options_frame.grid(row=3, column=1, columnspan=2, padx=6, pady=6, sticky="w")

        self.format_var = tk.StringVar(value="ffpfsc")
        ctk.CTkOptionMenu(self.options_frame, values=["ffpfsc", "exfat"],
                          variable=self.format_var, width=100).pack(side="left", padx=10)

        self.batch_var = tk.BooleanVar(value=False)
        self.batch_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Batch Mode (process all subfolders/exfat files)",
            variable=self.batch_var
        )
        self.batch_checkbox.pack(side="left", padx=10)

        self.verify_var = tk.BooleanVar(value=True)
        self.verify_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Extract and compare SHA-256",
            variable=self.verify_var
        )
        self.verify_checkbox.pack(side="left", padx=10)

    def _build_progress(self) -> None:
        self.progress_frame = ctk.CTkFrame(self.root)
        self.progress_frame.grid(row=2, column=0, padx=12, pady=6, sticky="ew")
        self.progress_frame.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            variable=self.progress_var,
            mode="determinate"
        )
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="w")

        buttons_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        buttons_frame.grid(row=0, column=1, rowspan=2, padx=12, pady=12, sticky="e")

        self.action_btn = ctk.CTkButton(
            buttons_frame,
            text="Pack / Convert",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_action,
            width=150,
            height=35
        )
        self.action_btn.pack(side="left", padx=5)

        self.cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100,
            height=35,
            state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=5)

    def _build_log_console(self) -> None:
        log_frame = ctk.CTkFrame(self.root)
        log_frame.grid(row=3, column=0, padx=12, pady=(6, 12), sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=11)
        )
        self.log_text.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self.log_text.configure(state="disabled")

        # Colors configure
        self.log_text._textbox.tag_config("header", foreground="#38bdf8", font=("Courier", 11, "bold"))
        self.log_text._textbox.tag_config("section", foreground="#c084fc", font=("Courier", 11, "bold"))
        self.log_text._textbox.tag_config("success", foreground="#34d399")
        self.log_text._textbox.tag_config("warning", foreground="#fbbf24")
        self.log_text._textbox.tag_config("error", foreground="#f87171", font=("Courier", 11, "bold"))
        self.log_text._textbox.tag_config("info", foreground="#cbd5e1")

    def _on_source_changed(self, *args) -> None:
        src = self.source_var.get().lower()
        # Supported archive extensions from mkpfs
        if any(src.endswith(ext) for ext in (".zip", ".rar", ".r00", ".001", "part1.rar")):
            self.password_label.grid(row=3, column=0, padx=12, pady=10, sticky="e")
            self.password_entry.grid(row=3, column=1, padx=6, pady=10, sticky="w")
            self.options_frame.grid(row=4, column=1, columnspan=2, padx=6, pady=6, sticky="w")
        else:
            self.password_label.grid_forget()
            self.password_entry.grid_forget()
            self.password_var.set("")
            self.options_frame.grid(row=3, column=1, columnspan=2, padx=6, pady=6, sticky="w")

    def _browse_folder(self) -> None:
        initial = self.source_var.get() or str(Path(".").resolve())
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            self.source_var.set(path)

    def _browse_file(self) -> None:
        initial = self.source_var.get() or str(Path(".").resolve())
        if initial:
            p = Path(initial)
            if p.is_file():
                initial = str(p.parent)
        path = filedialog.askopenfilename(
            initialdir=initial,
            filetypes=[
                ("exFAT files", "*.exfat"),
                ("ZIP files", "*.zip"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.source_var.set(path)

    def _browse_destination(self) -> None:
        initial = self.output_var.get() or str(Path(".").resolve())
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            self.output_var.set(path)

    def _browse_temp_dir(self) -> None:
        initial = self.temp_dir_var.get() or str(Path(".").resolve())
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            self.temp_dir_var.set(path)

    def enqueue_log(self, text: str, tag: str = "info") -> None:
        self.run_log.event("output", tag=tag, text=text)
        for match in PROGRESS_LINE_RE.finditer(text):
            percent = max(0, min(int(match.group("pct")), 100))
            label = match.group("label").strip() or "Processing"
            try:
                self.progress_queue.put_nowait((percent / 100, label))
            except queue.Full:
                pass
        log_text = PROGRESS_LINE_RE.sub("", text.replace("\r", "\n"))
        if log_text.strip():
            try:
                self.log_queue.put_nowait((log_text, tag))
            except queue.Full:
                pass

    def _start_log_polling(self) -> None:
        self._poll_log_queue()

    def _start_progress_polling(self) -> None:
        self._poll_progress_queue()

    def _start_completion_polling(self) -> None:
        self._poll_completion_queue()

    # Maximum log items processed per poll tick.  Keeps the main thread
    # responsive even when the subprocess emits output in large bursts.
    _LOG_DRAIN_LIMIT = 200

    def _poll_log_queue(self) -> None:
        if self.is_closing:
            return
        chunks = []
        try:
            for _ in range(self._LOG_DRAIN_LIMIT):
                chunks.append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        if chunks:
            for text, tag in chunks:
                self._append_log(text, tag)
        # If we hit the drain limit the queue may still have items;
        # reschedule immediately so we don't introduce a 100 ms gap,
        # but still yield control back to the event loop between batches.
        more_pending = len(chunks) == self._LOG_DRAIN_LIMIT
        delay = 0 if more_pending else 100
        self.log_after_id = self.root.after(delay, self._poll_log_queue)

    def _poll_progress_queue(self) -> None:
        if self.is_closing:
            return
        latest = None
        try:
            while True:
                latest = self.progress_queue.get_nowait()
        except queue.Empty:
            pass
        if latest is not None:
            value, label = latest
            self.progress_var.set(value)
            self.progress_label.configure(text=f"{label} ({int(value * 100)}%)")
        self.progress_after_id = self.root.after(100, self._poll_progress_queue)

    def _poll_completion_queue(self) -> None:
        if self.is_closing:
            return
        try:
            path, result, event = self.confirmation_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            result[0] = messagebox.askyesno("Overwrite?", f"Replace validated output {path.name}?")
            event.set()
        completed_info = None
        try:
            while True:
                completed_info = self.completion_queue.get_nowait()
        except queue.Empty:
            pass
        if completed_info is not None:
            name, is_success = completed_info
            self._on_worker_done(name, is_success)
        self.completion_after_id = self.root.after(100, self._poll_completion_queue)

    # Terms that trigger special tag colouring — compiled once for speed.
    _ERROR_TERMS   = ("error:", "failed", "exception", "failed:", "builderror", "unsupported")
    _WARNING_TERMS = ("warning", "warn", "stale")
    _SUCCESS_TERMS = ("successfully", "completed", "passed")
    _SECTION_NAMES = frozenset({
        "PFS Image Builder - Parameters",
        "Build Summary",
        "PFS Check Report",
        "Build Details",
    })

    def _append_log(self, text: str, source_tag: str = "info") -> None:
        self.log_text.configure(state="normal")
        lines = text.split("\n")
        # Accumulate plain "info" lines so they can be inserted in one call,
        # which is far cheaper than one Tkinter insert per line.
        plain_buf: list[str] = []

        def _flush_plain() -> None:
            if plain_buf:
                self.log_text.insert("end", "\n".join(plain_buf) + "\n", "info")
                plain_buf.clear()

        for i, line in enumerate(lines):
            suffix = "\n" if i < len(lines) - 1 else ""
            stripped = line.strip()

            if stripped.startswith("===") or stripped.endswith("==="):
                _flush_plain()
                self.log_text.insert("end", line + suffix, "header")
            elif stripped in self._SECTION_NAMES:
                _flush_plain()
                self.log_text.insert("end", line + suffix, "section")
            elif any(term in line.lower() for term in self._ERROR_TERMS):
                _flush_plain()
                self.log_text.insert("end", line + suffix, "error")
            elif any(term in line.lower() for term in self._WARNING_TERMS):
                _flush_plain()
                self.log_text.insert("end", line + suffix, "warning")
            elif any(term in line.lower() for term in self._SUCCESS_TERMS):
                _flush_plain()
                self.log_text.insert("end", line + suffix, "success")
            elif source_tag == "error":
                _flush_plain()
                self.log_text.insert("end", line + suffix, "error")
            else:
                # Plain info line — buffer it
                plain_buf.append(line)

        _flush_plain()
        # The persistent file retains history; the widget must not grow forever.
        lines_kept = int(self.log_text.index("end-1c").split(".")[0])
        if lines_kept > 5000:
            self.log_text.delete("1.0", f"{lines_kept - 5000}.0")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _on_action(self) -> None:
        if self.is_running or self.current_process is not None:
            return
        selected_source = Path(self.source_var.get().strip())
        if not selected_source.is_dir() and selected_source.suffix.lower() in {".rar", ".r00", ".001"}:
            messagebox.showinfo("Extract RAR first", "This test build excludes UnRAR.\nExtract the archive separately, then select the game folder.")
            return

        self._clear_log()
        self.is_cancelled = False
        self.is_running = True
        self.action_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.progress_label.configure(text="Initializing pack process...")

        # Capture all Tk values on the UI thread before starting the worker.
        self.pack_settings = dict(source=self.source_var.get().strip(), output=self.output_var.get().strip() or ".",
                                  output_format=self.format_var.get(), batch=self.batch_var.get(),
                                  verify=self.verify_var.get(), password=self.password_var.get() or None,
                                  temp_dir=self.temp_dir_var.get().strip() or None)
        self.run_log.event("conversion_start", settings={k: v for k, v in self.pack_settings.items() if k != "password"})
        self.worker_thread = threading.Thread(target=self._run_pack_worker, daemon=True)
        self.worker_thread.start()

    def _run_pack_worker(self) -> None:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = GuiLogRedirect(self, "info")
        sys.stderr = GuiLogRedirect(self, "error")
        is_success = False

        try:
            is_success = self._do_pack_work()
        except BaseException as e:
            self.run_log.event("worker_exception", traceback=traceback.format_exc())
            print(f"[ERROR] Unhandled exception in worker: {e}")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.run_log.event("conversion_end", success=is_success and not self.is_cancelled,
                               cancelled=self.is_cancelled)
            try:
                self.completion_queue.put_nowait(("Pack Process", is_success and not self.is_cancelled))
            except queue.Full:
                pass

    def _do_pack_work(self) -> bool:
        return cli.convert_sources(**self.pack_settings, run=self.run_command_stream,
                                   cancelled=lambda: self.is_cancelled,
                                   confirm=self.ask_overwrite_confirmation)

    def run_command_stream(self, cmd: list[str], cwd: str | None = None) -> bool:
        print(f"[INFO] Running: {' '.join(cmd)}")
        try:
            popen_kwargs = {}
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            env = getattr(self, "_headless_env", None)
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
                cwd=cwd,
                env=env,
                **popen_kwargs,
            )
            self.run_log.event("child_start", pid=self.current_process.pid, command=cmd, cwd=cwd)

            # Use readline()-based iteration; read_stream_by_lines already
            # uses readline() internally and handles \r deduplication.
            for line in read_stream_by_lines(self.current_process.stdout):
                print(line)

            code = self.current_process.wait()
            self.current_process.stdout.close()
            self.run_log.event("child_exit", pid=self.current_process.pid, returncode=code,
                               signal=-code if code < 0 else None)
            if code != 0:
                print(f"[ERROR] MkPFS exited with code {code}; signal {-code if code < 0 else 'none'}")
            self.current_process = None
            return code == 0
        except Exception as e:
            self.run_log.event("subprocess_exception", traceback=traceback.format_exc())
            print(f"[ERROR] Subprocess execution failed: {e}")
            if self.current_process is not None and self.current_process.poll() is not None:
                self.run_log.event("child_exit", pid=self.current_process.pid,
                                   returncode=self.current_process.returncode)
                if self.current_process.stdout:
                    self.current_process.stdout.close()
                self.current_process = None
            return False

    def _on_cancel(self) -> None:
        if not (self.is_running or self.current_process is not None) or not messagebox.askyesno(
                "Cancel conversion?", "Stop the active conversion? Unvalidated temporary output will be removed."):
            return
        self.run_log.event("cancel_confirmed")
        self.is_cancelled = True
        self.progress_label.configure(text="Cancelling...")
        if self.current_process:
            print("\n[WARN] Cancelling... terminating subprocess.\n")
            try:
                self.current_process.terminate()
            except ProcessLookupError:
                pass
        self.cancel_btn.configure(state="disabled")

    def ask_overwrite_confirmation(self, path: Path) -> bool:
        """Thread-safe way to ask for overwrite confirmation via a messagebox."""
        if threading.current_thread() is threading.main_thread():
            return messagebox.askyesno(
                "Overwrite?",
                f"File '{path.name}' already exists.\nDo you want to overwrite it?"
            )

        # We are on a background thread. Schedule on the main thread and wait.
        result = [False]
        event = threading.Event()

        self.confirmation_queue.put((path, result, event))
        while not event.wait(0.1):
            if self.is_cancelled or self.is_closing:
                return False
        return result[0]

    def _on_worker_done(self, name: str, is_success: bool) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_var.set(1.0)
        self.is_running = False
        self.action_btn.configure(state="normal")
        self.cancel_btn.configure(state="normal" if self.current_process is not None else "disabled")
        self.worker_thread = None

        if self.is_cancelled:
            self.progress_label.configure(text="Cancelled")
            messagebox.showinfo("Cancelled", "The operation was successfully cancelled.")
        elif is_success:
            self.progress_label.configure(text="Success")
            messagebox.showinfo("Success", "Operation completed successfully!")
        else:
            self.progress_label.configure(text="Failed")
            messagebox.showerror("Error", "Operation finished with errors.\nCheck the log console for details.")

    def _on_close(self) -> None:
        if self.is_running:
            self.run_log.event("close_blocked")
            messagebox.showinfo("Conversion active", "The application will remain open until conversion finishes.\nUse Cancel and confirm if you want to stop it.")
            return
        if self.current_process is not None or (self.worker_thread and self.worker_thread.is_alive()):
            self.run_log.event("close_blocked", reason="worker still active")
            return
        self.is_closing = True
        for after_id in (self.log_after_id, self.progress_after_id, self.completion_after_id, self.diagnostics_after_id):
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except Exception:
                    pass
        for signum, handler in self.previous_signals.items():
            signal.signal(signum, handler)
        self.run_log.close()
        self.root.destroy()

def gui_test(source, output, output_format):
    """Actions-only integration hook: exercise the real GUI worker without dialogs."""
    messagebox.showinfo = lambda *args, **kwargs: None
    messagebox.showerror = lambda *args, **kwargs: None
    root = ctk.CTk()
    app = PS5ContainerBuilderApp(root)
    app.source_var.set(source)
    app.output_var.set(output)
    app.format_var.set(output_format)
    app.verify_var.set(True)
    root.update()
    app._on_action()
    result = [1]
    def finish():
        if app.is_running:
            root.after(100, finish)
        else:
            result[0] = 0 if Path(output).is_file() and Path(output + ".validation.json").is_file() else 1
            app._on_close()
    root.after(100, finish)
    root.mainloop()
    return result[0]


def launch(args=None):
    root = ctk.CTk()
    app = PS5ContainerBuilderApp(root)
    if args:
        if args.game_folder:
            app.source_var.set(str(Path(args.game_folder).resolve()))
        app.output_var.set(str(Path(args.output).resolve()))
        app.format_var.set(args.format)
        app.batch_var.set(args.batch)
        app.verify_var.set(args.verify)
        if args.temp_dir:
            app.temp_dir_var.set(args.temp_dir)
    root.mainloop()
    return 0


def lifecycle_test(directory):
    """Actions-only native lifecycle test; no image or original game is processed."""
    import json
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: None
    messagebox.askyesno = lambda *a, **k: False
    root = ctk.CTk()
    app = PS5ContainerBuilderApp(root)
    released = threading.Event()
    app._do_pack_work = lambda: released.wait(30)
    app._on_action()
    (directory / "ready.json").write_text(json.dumps({"gui_pid": os.getpid()}))
    checks = {}
    deadline = __import__("time").monotonic() + 25

    def probe():
        if __import__("time").monotonic() > deadline:
            checks["timeout"] = True
            released.set()
            root.after(100, finish)
            return
        recorded_signal = any(json.loads(line).get("event") == "signal_exit_request"
                              for line in app.run_log.path.read_text().splitlines())
        if app.exit_guard.pending_signal is None and not recorded_signal:
            root.after(50, probe)
            return
        app._poll_diagnostics()
        checks["signal_blocked"] = app.is_running and not app.is_cancelled and bool(root.winfo_exists())
        app._on_close()
        checks["window_close_blocked"] = app.is_running and not app.is_cancelled and bool(root.winfo_exists())
        root.tk.call("tk::mac::Quit")
        checks["mac_quit_blocked"] = app.is_running and not app.is_cancelled and bool(root.winfo_exists())
        app._on_cancel()
        checks["declined_cancel_preserves_work"] = not app.is_cancelled
        released.set()
        root.after(100, finish)

    def finish():
        if app.is_running or (app.worker_thread and app.worker_thread.is_alive()):
            root.after(100, finish)
            return
        checks["log_path"] = str(app.run_log.path)
        checks["gui_pid"] = os.getpid()
        (directory / "result.json").write_text(json.dumps(checks, indent=2))
        app._on_close()

    root.after(50, probe)
    root.mainloop()
    return 0 if all(checks.get(k) is True for k in ("signal_blocked", "window_close_blocked", "mac_quit_blocked", "declined_cancel_preserves_work")) else 1


if __name__ == "__main__":
    if multiprocessing.current_process().name == "MainProcess":
        if len(sys.argv) == 3 and sys.argv[1] == "--lifecycle-test":
            sys.exit(lifecycle_test(sys.argv[2]))
        if len(sys.argv) == 5 and sys.argv[1] == "--gui-test":
            sys.exit(gui_test(*sys.argv[2:]))
        sys.exit(launch())
