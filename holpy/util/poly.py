"""Polynomials over arbitrary HOL terms."""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from functools import cmp_to_key
from typing import Any

from holpy.kernel.term import Term
from holpy.kernel import term_ord


def compare_fst(p1: tuple[Any, ...], p2: tuple[Any, ...]) -> int:
    """Compare two polynomial keys structurally (only the first factor; sorted up to ties)."""
    if isinstance(p1[0], Term):
        return term_ord.fast_compare(p1[0], p2[0])
    else:
        if len(p1[0]) != len(p2[0]):
            return term_ord.compare_atom(len(p1[0]), len(p2[0]))
        for i in range(len(p1[0])):
            if p1[0][i] != p2[0][i]:
                return compare_fst(p1[0][i], p2[0][i])
            return 0


def collect_pairs(ps: Iterable[tuple[Any, Any]]) -> tuple[tuple[Any, Any], ...]:
    """Collect pairs by first component and add their second components.

    The first components must be hashable. Zero coefficients are dropped and
    the result is sorted by the first component. For example,
    ``[(Var('x', IntType), 1), (Var('y', IntType), 2), (Var('x', IntType), 3)]``
    becomes ``[(Var('x', IntType), 4), (Var('y', IntType), 2)]``.
    """
    res = {}
    for v, c in ps:
        if v in res:
            res[v] += c
        else:
            res[v] = c
    return tuple(sorted([(k, v) for k, v in res.items() if v != 0], key=cmp_to_key(compare_fst)))


class Monomial:
    """A monomial coefficient times a product of powered factors.

    Attributes
    ----------
    coeff : int or Fraction
        Numeric coefficient.
    factors : tuple of (Term, int)
        Sorted, de-duplicated powered factors; each factor is a ``Term``.
    """

    def __init__(self, coeff: int | Fraction, factors: Iterable[tuple[Any, int]]):
        """Construct a monomial from a coefficient and powered factors.

        Examples: ``(2, ())`` is ``2``, ``(2, ((x, 1),))`` is ``2*x``, and
        ``(2, ((x, 2), (y, 1)))`` is ``2*x^2*y``.
        """
        assert isinstance(coeff, int) or isinstance(coeff, Fraction)
        assert all(isinstance(factor, Iterable) and len(factor) == 2 and \
            isinstance(factor[1], int) for factor in factors), \
            "Unexpected argument for factors: %s" % str(factors)
        self.coeff = coeff
        self.factors = collect_pairs(factors)

    def __eq__(self, other: object) -> bool:
        """Return whether two monomials are structurally equal."""
        return isinstance(other, Monomial) and self.coeff == other.coeff and \
            self.factors == other.factors

    def __str__(self) -> str:
        res = ""
        if self.coeff != 1:
            res += str(self.coeff)
        for var, p in self.factors:
            s = str(var)
            if len(s) != 1:
                s = "(" + s + ")"
            if p != 1:
                s = s + "^" + str(p)
            res += s

        if res == "":
            res = "1"
        return res

    def __repr__(self) -> str:
        return "Monomial(%s)" % str(self)

    def __le__(self, other: Monomial) -> bool:
        """Compare monomials by factor list and then coefficient."""
        cp = term_ord.fast_compare_list(self.factors, other.factors)  # type: ignore[arg-type]
        if cp < 0:
            return True
        elif cp > 0:
            return False
        else:
            return term_ord.compare_atom(self.coeff, other.coeff) <= 0

    def __lt__(self, other: Monomial) -> bool:
        """Return whether this monomial sorts before ``other``."""
        return self <= other and self != other

    def __mul__(self, other: Monomial) -> Monomial:
        """Multiply two monomials by multiplying coefficients and concatenating factors."""
        return Monomial(self.coeff * other.coeff, self.factors + other.factors)

    def scale(self, c: int | Fraction) -> Monomial:
        """Return this monomial with its coefficient multiplied by ``c``."""
        if c == 1:
            return self
        else:
            return Monomial(c * self.coeff, self.factors)

    def __neg__(self) -> Monomial:
        """Return the additive inverse of this monomial."""
        return self.scale(-1)

    def is_constant(self) -> bool:
        """Return whether this monomial has no factors."""
        return len(self.factors) == 0

    def get_constant(self) -> int | Fraction:
        """Return the coefficient of a constant monomial."""
        assert self.is_constant()
        return self.coeff


class Polynomial:
    """A sum of monomials with like terms collected.

    Attributes
    ----------
    monomials : tuple of Monomial
        Collected non-zero monomials.
    """

    def __init__(self, monomials: Iterable[Monomial]):
        """Construct a polynomial from an iterable of monomials."""
        monomials = tuple(monomials)
        assert all(isinstance(mono, Monomial) for mono in monomials)
        ts = collect_pairs((mono.factors, mono.coeff) for mono in monomials)
        self.monomials = tuple(Monomial(coeff, factor) for factor, coeff in ts)

    def __eq__(self, other: object) -> bool:
        """Return whether two polynomials are structurally equal."""
        return isinstance(other, Polynomial) and self.monomials == other.monomials

    def __str__(self) -> str:
        if len(self.monomials) == 0:
            return "0"
        else:
            return " + ".join(str(mono) for mono in self.monomials)

    def __repr__(self) -> str:
        return "Polynomial(%s)" % str(self)

    def __add__(self, other: Polynomial) -> Polynomial:
        """Return the sum of two polynomials."""
        return Polynomial(self.monomials + other.monomials)

    def scale(self, c: int | Fraction) -> Polynomial:
        """Return this polynomial multiplied by the scalar ``c``."""
        return Polynomial(mono.scale(c) for mono in self.monomials)

    def __neg__(self) -> Polynomial:
        """Return the additive inverse of this polynomial."""
        return self.scale(-1)

    def __sub__(self, other: Polynomial) -> Polynomial:
        """Return the difference of two polynomials."""
        return self + (-other)

    def __mul__(self, other: Polynomial) -> Polynomial:
        """Return the product of two polynomials."""
        return Polynomial(m1 * m2 for m1 in self.monomials for m2 in other.monomials)

    def __pow__(self, other: int) -> Polynomial:
        """Return this polynomial raised to a non-negative integer power."""
        assert isinstance(other, int) and other >= 0
        if other == 0:
            return Polynomial([Monomial(1, [])])

        res = self
        for i in range(other-1):
            res *= self
        return res

    def is_nonzero_constant(self) -> bool:
        """Return whether this is a single non-zero constant monomial."""
        return len(self.monomials) == 1 and self.monomials[0].is_constant()

    def is_zero_constant(self) -> bool:
        """Return whether this polynomial is the zero constant."""
        return len(self.monomials) == 0

    def is_constant(self) -> bool:
        """Return whether this polynomial is a constant."""
        return self.is_nonzero_constant() or self.is_zero_constant()

    def get_constant(self) -> int | Fraction:
        """Return the value of a constant polynomial."""
        if self.is_zero_constant():
            return 0
        elif self.is_nonzero_constant():
            return self.monomials[0].get_constant()
        else:
            raise AssertionError


def singleton(s: Term) -> Polynomial:
    """Return the polynomial ``1 * s``."""
    return Polynomial([Monomial(1, [(s, 1)])])


def constant(c: int | Fraction) -> Polynomial:
    """Return a polynomial representing the numeric constant ``c``."""
    assert isinstance(c, int) or isinstance(c, Fraction)
    if isinstance(c, Fraction) and c.denominator == 1:
        return Polynomial([Monomial(c.numerator, tuple())])
    else:
        return Polynomial([Monomial(c, tuple())])
