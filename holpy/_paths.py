"""Filesystem locations for holpy's bundled and user data."""

from __future__ import annotations

import os
import sys
from importlib.resources import files
from pathlib import Path


def library_dir() -> Path:
    """Return the directory containing the bundled theory library.

    ``HOLPY_LIBRARY_DIR`` can point at a writable checkout when developing
    or rewriting the bundled theories.
    """
    override = os.environ.get("HOLPY_LIBRARY_DIR")
    if override:
        return Path(override).expanduser()
    return Path(str(files("holpy.library")))


def user_data_dir() -> Path:
    """Return the root directory for user-created theories."""
    override = os.environ.get("HOLPY_USER_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "holpy"


def user_dir(username: str = "master") -> Path:
    """Return the directory containing a user's theories."""
    if not username:
        raise ValueError("username must be non-empty")
    if username == "master":
        return library_dir()
    return user_data_dir() / "users" / username


def user_file(filename: str, username: str = "master") -> Path:
    """Return the JSON file for a theory name and user."""
    return user_dir(username) / f"{filename}.json"
