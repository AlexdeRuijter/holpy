"""holpy: higher-order logic theorem prover and proof assistant."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version

from holpy._paths import add_theory_path, find_theory, theory_path

try:
    __version__ = version("holpy")
except PackageNotFoundError:  # running from a source checkout
    __version__ = "0.1.0"

__all__ = [
    "data",
    "geometry",
    "imperative",
    "integral",
    "kernel",
    "logic",
    "macros",
    "paraverifier",
    "prover",
    "server",
    "syntax",
    "util",
    "add_theory_path",
    "find_theory",
    "theory_path",
]


def __getattr__(name: str):
    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
