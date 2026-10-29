"""Filesystem locations for holpy's bundled and user data."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

_logger = logging.getLogger(__name__)

# Directories added at run time, in search order (most recent first by default).
_added_paths: list[Path] = []

# Parsed HOLPY_THEORY_PATH, keyed by its raw value so a changed variable is
# read again.  Relative entries are resolved when the value is first seen.
_env_path_cache: tuple[str, tuple[Path, ...]] | None = None

# Each problem is reported once per process; keeping the sets here also makes
# them easy to reset in tests.
_missing_warned: set[Path] = set()
_shadow_warned: set[str] = set()

# Zero-argument callbacks run after a path change.  The theory loader uses
# this to discard its caches without _paths importing holpy.logic.basic.
_path_listeners: list[Callable[[], None]] = []


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


def _absolute(path: str | os.PathLike[str]) -> Path:
    """Return *path* expanded and absolute, without resolving symlinks."""
    return Path(os.path.abspath(os.path.expanduser(os.fspath(path))))


def _environment_dirs() -> list[Path]:
    """Return the directories in ``HOLPY_THEORY_PATH``.

    Empty entries are ignored.  The result is cached for the raw value of the
    variable, which is what makes relative entries stable across later
    changes of the current directory.
    """
    global _env_path_cache

    raw = os.environ.get("HOLPY_THEORY_PATH")
    if raw is None:
        _env_path_cache = None
        return []
    if _env_path_cache is not None and _env_path_cache[0] == raw:
        return list(_env_path_cache[1])

    entries = tuple(_absolute(entry) for entry in raw.split(os.pathsep) if entry)
    _env_path_cache = (raw, entries)
    return list(entries)


def _existing_dir(directory: Path) -> bool:
    """Return whether *directory* exists, warning once if it does not."""
    if directory.is_dir():
        return True
    if directory not in _missing_warned:
        _missing_warned.add(directory)
        _logger.warning(
            "Skipping theory search directory %s: not a directory", directory
        )
    return False


def theory_path(username: str = "master") -> list[Path]:
    """Return the directories searched for theories of *username*.

    The search order is:

    1. for a user other than ``master``, :func:`user_dir` for that user;
    2. the directories in ``HOLPY_THEORY_PATH``, in order (empty entries are
       ignored, ``~`` is expanded, and relative entries are resolved against
       the current directory when the variable is first read);
    3. directories added by :func:`add_theory_path`, most recently added first
       unless the directory was added with ``prepend=False``;
    4. the bundled library, :func:`library_dir`.

    The first file with a given theory name wins.  A name earlier on the path
    therefore shadows the same name later on the path.  Directories that do not
    exist are skipped, with one warning per directory per process.

    Parameters
    ----------
    username : str, optional
        User whose own theory directory comes first.  The default ``master``
        uses the bundled library as its directory, so it is not repeated at the
        front of the path.

    Returns
    -------
    list[Path]
        Existing theory directories in search order.
    """
    if not username:
        raise ValueError("username must be non-empty")

    result: list[Path] = []
    if username != "master":
        result.append(user_dir(username))
    result.extend(_environment_dirs())
    result.extend(_added_paths)
    result.append(library_dir())
    return [directory for directory in result if _existing_dir(directory)]


def add_theory_path(
    path: str | os.PathLike[str], *, prepend: bool = True
) -> None:
    """Add a directory to the theory search path.

    The new directory is searched before the bundled library, and after the
    directories already in ``HOLPY_THEORY_PATH``.  With ``prepend=True`` (the
    default) it is searched before directories added earlier; with
    ``prepend=False`` it is searched after them.  The first file with a given
    theory name wins, so an added directory shadows the same name in the
    bundled library.

    Adding a directory that was already added has no further effect.  Every
    successful change notifies the callbacks registered in
    ``_path_listeners``, which lets the theory loader clear its caches.

    Parameters
    ----------
    path : str or os.PathLike
        Directory to add.  ``~`` is expanded and a relative path is resolved
        against the current directory when this function is called.
    prepend : bool, optional
        Search the new directory before previous additions (default) or after
        them.

    Returns
    -------
    None
    """
    directory = _absolute(path)
    if directory in _added_paths:
        return
    if prepend:
        _added_paths.insert(0, directory)
    else:
        _added_paths.append(directory)
    for listener in list(_path_listeners):
        listener()


def find_theory(name: str, username: str = "master") -> Path:
    """Find the file for a theory name on the search path.

    The directories are consulted in the order given by :func:`theory_path`.
    The first file named ``<name>.json`` wins; if the same name occurs in a
    later directory, the earlier file shadows it.  One warning naming the
    files is logged per shadowed name per process.

    Parameters
    ----------
    name : str
        Theory name, with or without the ``.json`` suffix.
    username : str, optional
        User whose search path is used.  Defaults to ``master``.

    Returns
    -------
    Path
        Path to the winning theory file.

    Raises
    ------
    FileNotFoundError
        If no directory on the search path contains the theory.
    """
    filename = name if name.endswith(".json") else f"{name}.json"
    matches: list[Path] = []
    for directory in theory_path(username):
        candidate = directory / filename
        if candidate.is_file():
            matches.append(candidate)

    if not matches:
        raise FileNotFoundError(
            f"Theory {name!r} not found on the theory path for user {username!r}"
        )

    if len(matches) > 1 and filename not in _shadow_warned:
        _shadow_warned.add(filename)
        _logger.warning(
            "Theory %s is shadowed: using %s; also found %s",
            name,
            matches[0],
            ", ".join(str(candidate) for candidate in matches[1:]),
        )
    return matches[0]
