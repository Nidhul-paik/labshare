"""Copy text to the system clipboard on Windows, Linux and macOS."""

from __future__ import annotations

import shutil
import subprocess
import sys


def _run(cmd, data: bytes) -> bool:
    try:
        subprocess.run(cmd, input=data, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _tkinter_copy(text: str) -> bool:
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


def copy_to_clipboard(text: str) -> bool:
    """Return True on success.  Never raises."""
    data = text.encode("utf-8")
    if sys.platform.startswith("win"):
        if _tkinter_copy(text):
            return True
        # clip.exe understands UTF-16 with a byte-order mark
        return _run(["clip"], b"\xff\xfe" + text.encode("utf-16-le"))
    if sys.platform == "darwin":
        return _run(["pbcopy"], data)
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        if shutil.which(cmd[0]) and _run(cmd, data):
            return True
    return False  # tkinter on Linux loses the clipboard when the program exits
