# Author: Bohua Zhan

"""Schematic-variable, variable, and definition context.

A :class:`Context` records the names and types that parsing and proof methods
should treat as in scope. The module-level ``ctxt`` is the active context;
:func:`fresh_context` temporarily replaces it and restores the previous one.
"""

from __future__ import annotations

import contextlib
from typing import Any, Dict, Iterator, List, Optional, Union

from holpy.kernel.term import Var
from holpy.kernel.type import Type
from holpy.logic import basic
from holpy.syntax import parser


class Context:
    """Types of the schematic variables, variables, and definitions in scope.

    String type specifications are parsed with :mod:`holpy.syntax.parser` when
    the context is constructed; already-parsed :class:`Type` values are kept
    as is.
    """

    def __init__(self, *, svars: Optional[Dict[str, Union[str, Type]]] = None,
                 vars: Optional[Dict[str, Union[str, Type]]] = None,
                 defs: Optional[Dict[str, Union[str, Type]]] = None):
        # Mapping of schematic variables
        self.svars: Dict[str, Type] = dict()
        if svars is not None:
            for nm, T in svars.items():
                if isinstance(T, str):
                    T = parser.parse_type(T)
                self.svars[nm] = T

        # Mapping of variables
        self.vars: Dict[str, Type] = dict()
        if vars is not None:
            for nm, T in vars.items():
                if isinstance(T, str):
                    T = parser.parse_type(T)
                self.vars[nm] = T

        # Mapping of definitions
        self.defs: Dict[str, Type] = dict()
        if defs is not None:
            for nm, T in defs.items():
                if isinstance(T, str):
                    T = parser.parse_type(T)
                self.defs[nm] = T

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Context) and \
            self.vars == other.vars and self.svars == other.svars and self.defs == other.defs

    def __str__(self) -> str:
        return 'vars: %s' % str(self.vars)

    def __repr__(self) -> str:
        return str(self)

    def get_vars(self) -> List[Var]:
        """Return the variables in scope as kernel ``Var`` terms."""
        return [Var(nm, T) for nm, T in self.vars.items()]


#: Active parsing and proof-method context.
ctxt = Context()


@contextlib.contextmanager
def fresh_context(*, svars=None, vars=None, defs=None) -> Iterator[None]:
    """Temporarily install a fresh context and restore the previous one."""
    # Record previous context
    global ctxt
    prev_ctxt = ctxt

    # Set fresh context
    ctxt = Context(svars=svars, vars=vars, defs=defs)
    try:
        yield None
    finally:
        # Recover previous context
        ctxt = prev_ctxt


def set_context(thy_name: Optional[str], *, limit: Any = None, username: str = "master",
                svars=None, vars=None, defs=None):
    """Set the current theory and parsing context.

    Parameters
    ----------
    thy_name : str or None
        Theory to load. ``None`` leaves the current theory unchanged.
    limit : Any, optional
        Optional theory item at which loading stops.
    username : str
        User whose theory files are read.
    svars, vars, defs : dict, optional
        Context entries for schematic variables, variables, and definitions.
    """
    # Set theory
    if thy_name is not None:
        basic.load_theory(thy_name, limit=limit, username=username)

    # Set context
    global ctxt
    ctxt = Context(svars=svars, vars=vars, defs=defs)
