import os
import subprocess
import sys
import tempfile

class LocalRepository:
    """Manages the lifecycle of a cloned local git repository as a context manager."""

    def __init__(self, url: str, version: str):
        self.url = url
        self.version = version
        self.path = None
        self.cloned_successfully = False
        self.error_message = ""
        self._tmpdir_ctx = None

    def __enter__(self):
        self._tmpdir_ctx = tempfile.TemporaryDirectory()
        self.path = self._tmpdir_ctx.__enter__()
        
        try:
            self._clone()
            self.cloned_successfully = True
        except Exception as e:
            self.error_message = str(e)
            self.cloned_successfully = False
            
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._tmpdir_ctx:
            self._tmpdir_ctx.__exit__(exc_type, exc_val, exc_tb)

    def _clone(self):
        """Clones the repository using a shallow clone."""
        print(f"Cloning {self.url} (branch/version: {self.version}) into temporary directory...", file=sys.stderr)
        res = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", self.version, self.url, self.path],
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            raise RuntimeError(f"Failed to clone repository: {res.stderr.strip()}")
