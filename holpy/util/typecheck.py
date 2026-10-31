"""Runtime type checking for the untyped kernel APIs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

check: bool = True


def checkinstance(*args: Any) -> None:
    """Check a sequence of ``(value, type)`` pairs at runtime.

    The first argument is the caller name used in error messages. The
    remaining arguments are consumed in pairs ``value, type``; a type may be
    a list ``[T]`` to require an iterable whose elements all have type ``T``.

    Parameters
    ----------
    *args
        Caller name followed by alternating values and expected types.

    Raises
    ------
    TypeError
        If a value does not have the expected type.

    Note
    ----
    The module flag ``check = False`` disables all checking.
    """
    if not check:
        return

    fname = args[0]

    def check_type(v, T):
        if type(T) == list:
            if not isinstance(v, Iterable):
                raise TypeError('%s expects %s but got %s' % (fname, 'list', str(type(v))))
            for item in v:
                check_type(item, T[0])
        elif not isinstance(v, T):
                raise TypeError('%s expects %s but got %s' % (fname, T, str(type(v))))

    for i in range(len(args) // 2):
        check_type(args[2*i+1], args[2*i+2])
