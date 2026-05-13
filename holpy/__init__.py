from importlib import import_module as _import_module
import sys as _sys

__all__ = [
    "app",
    "data",
    "geometry",
    "imperative",
    "integral",
    "kernel",
    "logic",
    "paraverifier",
    "prover",
    "server",
    "syntax",
    "util",
]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = _import_module(name)
    globals()[name] = module
    _sys.modules[f"{__name__}.{name}"] = module
    return module
