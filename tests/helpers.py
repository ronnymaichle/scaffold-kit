"""Test helpers: import path for the quality scripts and temporary projects."""
from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
QUALITY = KIT / "scripts" / "quality"
if str(QUALITY) not in sys.path:
    sys.path.insert(0, str(QUALITY))

HAS_GIT = shutil.which("git") is not None


class TempProject:
    """A throwaway project folder; use as a context manager."""

    def __init__(self, files=None, git=False):
        self.files = files or {}
        self.git = git
        self.root = None
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, content in self.files.items():
            self.write(rel, content)
        if self.git:
            self.run_git("init", "-q", "-b", "main")
            self.run_git("config", "user.email", "test@example.com")
            self.run_git("config", "user.name", "Test")
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
        return path

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def remove(self, rel):
        (self.root / rel).unlink()

    def run_git(self, *args):
        return subprocess.run(["git", "-C", str(self.root)] + list(args), check=True, capture_output=True)


def run_main(main, argv):
    """Run a script's main() and return (exit_code, printed_output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = main(argv)
        except SystemExit as exc:  # argparse errors
            code = exc.code if isinstance(exc.code, int) else 2
    return code, buf.getvalue()
