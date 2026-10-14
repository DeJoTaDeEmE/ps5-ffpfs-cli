"""GUI path editing and preflight checks, independent of image serialization."""
from pathlib import Path
import tkinter as tk


def clean_path(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    if any(char in text for char in ("\0", "\r", "\n")):
        raise ValueError("Paste a single path without embedded line breaks or NUL characters.")
    return text


def validate_path(text, label, *, directory=False):
    text = clean_path(text)
    if not text:
        return ""
    path = Path(text).expanduser()
    # A real directory may legitimately contain repeated names. Do not rewrite it.
    if not path.is_dir() and text.startswith("/"):
        parts = [part for part in text.split("/") if part]
        prefix = "/" + "/".join(parts[:2])
        second = text.find(prefix, len(prefix))
        end = second + len(prefix)
        repeated_prefix = len(parts) >= 4 and second >= 0 and (end == len(text) or text[end] == "/")
        repeated_volume_root = text.startswith("/Volumes/") and text.count("/Volumes/") > 1
        if repeated_prefix or repeated_volume_root:
            raise ValueError(f"{label} appears to contain concatenated paths. Paste one complete path or use Browse.")
    if directory and not path.is_dir():
        raise ValueError(f"{label} must be an existing directory. Choose it with Browse.")
    return str(path)


def browse_initial_directory(text):
    try:
        candidate = Path(validate_path(text, "Path") or Path.home()).expanduser()
    except (ValueError, RuntimeError, OSError):
        return str(Path.home())
    while not candidate.is_dir():
        if candidate.parent == candidate:
            return str(Path.home())
        candidate = candidate.parent
    return str(candidate)


def bind_path_entry(entry, label, report_error):
    entry.configure(exportselection=False)

    def select_all(event):
        entry.select_range(0, "end")
        entry.icursor("end")
        return "break"

    def paste(event):
        if entry.cget("state") in {"disabled", "readonly"}:
            return "break"
        try:
            clipboard = event.widget.clipboard_get()
        except tk.TclError:
            return "break"
        if not clipboard:
            return "break"
        try:
            candidate = clean_path(clipboard)
            if candidate.startswith(("/", "~/")):
                candidate = validate_path(candidate, label)
                entry.delete(0, "end")
                entry.insert(0, candidate)
            else:
                # Preserve normal selected-fragment replacement for manual editing.
                if entry.select_present():
                    first, last = entry.index("sel.first"), entry.index("sel.last")
                    entry.delete(first, last)
                    entry.icursor(first)
                entry.insert("insert", clipboard)
        except (ValueError, RuntimeError, OSError) as exc:
            report_error(str(exc))
        return "break"

    for sequence in ("<Command-a>", "<Command-A>", "<Control-a>", "<<SelectAll>>"):
        entry.bind(sequence, select_all, add=True)
    for sequence in ("<Command-v>", "<Command-V>", "<Control-v>", "<<Paste>>"):
        entry.bind(sequence, paste, add=True)
