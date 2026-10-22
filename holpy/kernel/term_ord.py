# Author: Bohua Zhan

"""Deterministic ordering on HOL types and terms.

The order is total on well-formed objects and is used for canonicalizing sets
of terms (for example when collecting variables or comparing substitutions).
It is structural rather than semantic: alpha-equivalent terms compare equal
only through the normal term equality used by the ``Term`` class.
"""

from __future__ import annotations

from functools import cmp_to_key
from typing import TYPE_CHECKING, Any, Callable, Iterable, TypeVar

if TYPE_CHECKING:  # Avoid importing the kernel datatypes at module load time.
    from holpy.kernel.term import Term
    from holpy.kernel.type import Type

T = TypeVar("T")


def compare_atom(n1: Any, n2: Any) -> int:
    """Compare two atomic values with ``<``/``>``, returning -1, 0, or 1."""
    if n1 < n2:
        return -1
    elif n1 > n2:
        return 1
    else:
        return 0


def compare_pair(
    p1: tuple[Any, Any],
    p2: tuple[Any, Any],
    cp1: Callable[[Any, Any], int],
    cp2: Callable[[Any, Any], int],
) -> int:
    """Compare two pairs lexicographically using the supplied comparators.

    Parameters
    ----------
    p1, p2 : tuple
        The two pairs to compare.
    cp1, cp2 : callable
        Comparison functions for the first and second components.

    Returns
    -------
    int
        -1, 0, or 1.
    """
    res1 = cp1(p1[0], p2[0])
    if res1 != 0:
        return res1
    else:
        return cp2(p1[1], p2[1])


def compare_list(l1: list[T], l2: list[T], cp: Callable[[T, T], int]) -> int:
    """Compare two lists lexicographically, then by length.

    Parameters
    ----------
    l1, l2 : list
        The two lists to compare.
    cp : callable
        Comparison function for list elements.

    Returns
    -------
    int
        -1, 0, or 1.
    """
    for i in range(min(len(l1), len(l2))):
        res = cp(l1[i], l2[i])
        if res != 0:
            return res

    return compare_atom(len(l1), len(l2))


def fast_compare_typ(T1: Type, T2: Type) -> int:
    """Compare two types by size, constructor kind, name, and arguments.

    This is the structural order used by :func:`sorted_typs`.
    """
    if T1.size() != T2.size():
        return compare_atom(T1.size(), T2.size())
    if T1.ty != T2.ty:
        return compare_atom(T1.ty, T2.ty)
    elif T1.is_stvar() or T1.is_tvar():
        return compare_atom(T1.name, T2.name)
    elif T1.is_tconst():
        return compare_pair((T1.name, T1.args), (T2.name, T2.args),
                            compare_atom, lambda l1, l2: compare_list(l1, l2, fast_compare_typ))
    else:
        raise TypeError


def fast_compare(t1: Term, t2: Term) -> int:
    """Compare two terms structurally.

    The comparison is total for well-formed terms and uses de Bruijn indices
    for bound variables, so it is stable under the kernel's representation of
    abstraction.
    """
    if t1.size() != t2.size():
        return compare_atom(t1.size(), t2.size())
    if t1.ty != t2.ty:
        return compare_atom(t1.ty, t2.ty)
    elif t1.is_svar() or t1.is_var() or t1.is_const():
        return compare_pair((t1.name, t1.T), (t2.name, t2.T), compare_atom, fast_compare_typ)
    elif t1.is_comb():
        return compare_pair((t1.fun, t1.arg), (t2.fun, t2.arg), fast_compare, fast_compare)
    elif t1.is_abs():
        return compare_pair((t1.var_T, t1.body), (t2.var_T, t2.body), fast_compare_typ, fast_compare)
    elif t1.is_bound():
        return compare_atom(t1.n, t2.n)
    else:
        raise TypeError


def fast_compare_list(t1: list[Term], t2: list[Term]) -> int:
    """Compare two lists of terms, first element-wise and then by length."""
    if len(t1) != len(t2):
        return compare_atom(len(t1), len(t2))
    for i in range(len(t1)):
        if t1[i] != t2[i]:
            return fast_compare(t1[i], t2[i])
    return 0


def sorted_typs(ts: Iterable[Type]) -> list[Type]:
    """Return the distinct types in ``ts`` sorted by :func:`fast_compare_typ`."""
    return sorted(set(ts), key=cmp_to_key(fast_compare_typ))


def sorted_terms(ts: Iterable[Term]) -> list[Term]:
    """Return the distinct terms in ``ts`` sorted by :func:`fast_compare`."""
    return sorted(set(ts), key=cmp_to_key(fast_compare))
