"""
conftest.py for unit tests — Windows compatibility fixes.
Forces garbage collection after each test to release SQLite file handles,
preventing PermissionError during temp-dir teardown on Windows.
"""
import gc
import os
import sys
import stat
import time
import shutil
import pytest


def _robust_rmtree(path):
    """Remove directory tree, retrying on Windows PermissionError."""

    def handle_error(func, path, exc_info):
        # Try making the file writable, then retry
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except PermissionError:
            time.sleep(0.1)
            try:
                func(path)
            except Exception:
                pass

    gc.collect()
    shutil.rmtree(path, onerror=handle_error)


# Patch shutil.rmtree for the test session so temp-dir teardown is robust
_orig_rmtree = shutil.rmtree


def _patched_rmtree(path, ignore_errors=False, onerror=None, onexc=None, **kwargs):
    if onerror is None and onexc is None and not ignore_errors:
        _robust_rmtree(path)
    else:
        # onexc was added in Python 3.12; do not pass it on older interpreters
        if sys.version_info >= (3, 12):
            _orig_rmtree(path, ignore_errors=ignore_errors, onerror=onerror, onexc=onexc, **kwargs)
        else:
            _orig_rmtree(path, ignore_errors=ignore_errors, onerror=onerror, **kwargs)


shutil.rmtree = _patched_rmtree


@pytest.fixture(autouse=True)
def _force_gc_after_test():
    """Force GC after every unit test to release Windows file handles."""
    yield
    gc.collect()
