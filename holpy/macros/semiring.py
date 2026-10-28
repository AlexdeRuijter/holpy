"""Normalisation in a (commutative, possibly idempotent) semiring whose laws
are given explicitly.

``semiring_norm (names, goal)`` proves ``goal = (lhs = rhs)`` by bringing both
sides to a normal form.  The laws are not built in: they are taken from

* the named theorems in ``names`` (space separated, may be empty), and
* the previous facts, which may be hypotheses such as
  ``∀x y. add x y = add y x``.

So the same macro works for a concrete semiring (max-plus ``ereal``, with
its laws as library theorems) and inside abstract proofs, where the
structure is a predicate on explicit operations and the laws are
assumptions.

Each law is recognised by its shape; the operations are whatever the laws
mention:

========== ===================================================
comm       ``h x y = h y x``
assoc      ``h x (h y z) = h (h x y) z`` (either direction)
idem       ``h x x = x``
unit       ``h e x = x`` or ``h x e = x``
zero       ``g z x = z`` or ``g x z = z``
distrib    ``g x (f y z) = f (g x y) (g x z)`` or the right-hand form
========== ===================================================

With a distributivity law, ``f`` is the addition and ``g`` the
multiplication, and terms are normalised to sorted sums of sorted
products (duplicates removed in the sum when ``f`` is idempotent).
Without one, the macro normalises a single associative-commutative
operation.  Every operation that is normalised needs comm and assoc.

The macro is level 1 and its expansion is a chain of rewrites with the
given laws, so it is mechanically expandable to primitive steps.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from holpy.kernel import term_ord
from holpy.kernel.macro import Macro
from holpy.kernel.proofterm import ProofTerm, refl
from holpy.kernel.term import SVar, Term
from holpy.kernel.theory import register_macro
from holpy.logic.conv import Conv, ConvException, arg1_conv, arg_conv, binop_conv, rewr_conv


class SemiringException(Exception):
    """Raised when ``semiring_norm`` cannot prove its goal."""


def dest_op(t: Term) -> Optional[Tuple[Term, Term, Term]]:
    """``(h, a, b)`` if t is a binary application ``h a b``."""
    if t.is_comb() and t.fun.is_comb():
        return t.fun.fun, t.fun.arg, t.arg
    return None


def is_op(t: Term, h: Term) -> bool:
    d = dest_op(t)
    return d is not None and d[0] == h


def _schematic(pt: ProofTerm) -> ProofTerm:
    """Instantiate a law's outer ∀ with fresh schematic variables."""
    used = {v.name for v in pt.prop.get_svars()}
    while pt.prop.is_forall():
        nm = pt.prop.arg.var_name
        while nm in used:
            nm += "1"
        used.add(nm)
        pt = pt.forall_elim(SVar(nm, pt.prop.arg.var_T))
    return pt


class OpLaws:
    """The laws known for one operation."""

    def __init__(self, op: Term) -> None:
        self.op = op
        self.comm: Optional[ProofTerm] = None
        self.assoc: Optional[ProofTerm] = None  # h x (h y z) = h (h x y) z
        self.idem: Optional[ProofTerm] = None
        self.unit: Optional[Tuple[Term, ProofTerm]] = None  # (e, h e x = x)
        self.zero: Optional[Tuple[Term, ProofTerm]] = None  # (z, h z x = z)

    def ready(self) -> bool:
        return self.comm is not None and self.assoc is not None


class Laws:
    """Laws sorted by operation, plus distributivity."""

    def __init__(self) -> None:
        self.ops: Dict[Term, OpLaws] = {}
        self.ldist: Optional[ProofTerm] = None  # g x (f y z) = f (g x y) (g x z)
        self.rdist: Optional[ProofTerm] = None  # g (f y z) x = f (g y x) (g z x)
        self.add: Optional[Term] = None
        self.mul: Optional[Term] = None

    def of(self, h: Term) -> OpLaws:
        if h not in self.ops:
            self.ops[h] = OpLaws(h)
        return self.ops[h]

    def add_law(self, pt: ProofTerm) -> None:
        """Classify one law and record it.  Unrecognised laws are an error."""
        pt = _schematic(pt)
        p = pt.prop
        if not p.is_equals():
            raise SemiringException("semiring_norm: law is not an equation: %s" % p)
        lhs, rhs = p.lhs, p.rhs
        dl, dr = dest_op(lhs), dest_op(rhs)
        sv = lambda t: t.is_svar()  # noqa: E731

        # comm: h x y = h y x
        if dl and dr and dl[0] == dr[0] and sv(dl[1]) and sv(dl[2]) and dl[1] != dl[2] \
                and dr[1] == dl[2] and dr[2] == dl[1]:
            self.of(dl[0]).comm = pt
            return
        # idem: h x x = x
        if dl and sv(dl[1]) and dl[1] == dl[2] and rhs == dl[1]:
            self.of(dl[0]).idem = pt
            return
        # unit: h e x = x, or h x e = x
        if dl and sv(rhs) and not dl[1].get_svars() and dl[2] == rhs:
            self.of(dl[0]).unit = (dl[1], pt)
            return
        if dl and sv(rhs) and not dl[2].get_svars() and dl[1] == rhs:
            self.of(dl[0]).unit = (dl[2], ("right", pt))
            return
        # zero: g z x = z, or g x z = z
        if dl and not rhs.get_svars() and dl[1] == rhs and sv(dl[2]):
            self.of(dl[0]).zero = (rhs, pt)
            return
        if dl and not rhs.get_svars() and dl[2] == rhs and sv(dl[1]):
            self.of(dl[0]).zero = (rhs, ("right", pt))
            return
        # assoc: h x (h y z) = h (h x y) z, or the reverse
        for a, b, flip in ((lhs, rhs, False), (rhs, lhs, True)):
            da, db = dest_op(a), dest_op(b)
            if da and db and da[0] == db[0] and is_op(da[2], da[0]) and is_op(db[1], da[0]):
                x, (_, y, z) = da[1], dest_op(da[2])[0:3]
                _, x2, y2 = dest_op(db[1])
                if x == x2 and y == y2 and z == db[2] and all(map(sv, (x, y, z))):
                    self.of(da[0]).assoc = pt.symmetric() if flip else pt
                    return
        # distrib: g x (f y z) = f (g x y) (g x z), or g (f y z) x = ...
        if dl and dr:
            g, f = dl[0], dr[0]
            if is_op(dl[2], f) and sv(dl[1]):
                self.ldist = pt
                self._set_ring(f, g)
                return
            if is_op(dl[1], f) and sv(dl[2]):
                self.rdist = pt
                self._set_ring(f, g)
                return
        raise SemiringException("semiring_norm: unrecognised law %s" % p)

    def _set_ring(self, f: Term, g: Term) -> None:
        if (self.add, self.mul) not in ((None, None), (f, g)):
            raise SemiringException("semiring_norm: laws distribute different operations")
        self.add, self.mul = f, g


def _rw(pt, sym: bool = False) -> Conv:
    return rewr_conv(pt, sym=sym)


class FunConv(Conv):
    def __init__(self, f) -> None:
        self.f = f

    def get_proof_term(self, t: Term) -> ProofTerm:
        return self.f(t)


def _unit_conv(L: OpLaws, right: bool) -> Conv:
    """Rewrite ``h e x`` (or ``h x e`` when right) to ``x``."""
    e, law = L.unit
    if isinstance(law, tuple):  # stated on the right
        _, pt = law
        return _rw(pt) if right else FunConv(lambda t: refl(t).on_rhs(_rw(L.comm), _rw(pt)))
    return FunConv(lambda t: refl(t).on_rhs(_rw(L.comm), _rw(law))) if right else _rw(law)


def _zero_conv(L: OpLaws, right: bool) -> Conv:
    z, law = L.zero
    if isinstance(law, tuple):
        _, pt = law
        return _rw(pt) if right else FunConv(lambda t: refl(t).on_rhs(_rw(L.comm), _rw(pt)))
    return FunConv(lambda t: refl(t).on_rhs(_rw(L.comm), _rw(law))) if right else _rw(law)


def _cmp(a: Term, b: Term) -> int:
    return term_ord.fast_compare(a, b)


def ac_insert(L: OpLaws, t: Term) -> ProofTerm:
    """``h r m`` with r sorted and m an element: sorted again."""
    h = L.op
    _, r, m = dest_op(t)
    if L.zero is not None:
        z = L.zero[0]
        if r == z:
            return refl(t).on_rhs(_zero_conv(L, right=False))
        if m == z:
            return refl(t).on_rhs(_zero_conv(L, right=True))
    if L.unit is not None:
        e = L.unit[0]
        if m == e:
            return refl(t).on_rhs(_unit_conv(L, right=True))
        if r == e:
            return refl(t).on_rhs(_unit_conv(L, right=False))
    if is_op(r, h):
        _, r1, m1 = dest_op(r)
        c = _cmp(m1, m)
        if c < 0 or (c == 0 and L.idem is None):
            return refl(t)
        if c == 0:
            return refl(t).on_rhs(_rw(L.assoc, sym=True), arg_conv(_rw(L.idem)))
        pt = refl(t).on_rhs(_rw(L.assoc, sym=True), arg_conv(_rw(L.comm)), _rw(L.assoc),
                            arg1_conv(FunConv(lambda u: ac_insert(L, u))))
        if L.zero is not None and pt.rhs.fun.arg == L.zero[0]:
            pt = pt.on_rhs(_zero_conv(L, right=False))
        return pt
    c = _cmp(r, m)
    if c < 0 or (c == 0 and L.idem is None):
        return refl(t)
    if c == 0:
        return refl(t).on_rhs(_rw(L.idem))
    return refl(t).on_rhs(_rw(L.comm))


def ac_merge(L: OpLaws, t: Term) -> ProofTerm:
    """``h p q`` with p, q sorted: sorted."""
    _, p, q = dest_op(t)
    if is_op(q, L.op):
        return refl(t).on_rhs(_rw(L.assoc), arg1_conv(FunConv(lambda u: ac_merge(L, u))),
                              FunConv(lambda u: _after_merge(L, u)))
    return ac_insert(L, t)


def _after_merge(L: OpLaws, t: Term) -> ProofTerm:
    # The inner merge may have collapsed to a unit or zero; insert handles both.
    if is_op(t, L.op):
        return ac_insert(L, t)
    return refl(t)


class Normaliser:
    def __init__(self, laws: Laws) -> None:
        self.laws = laws
        if laws.add is not None:
            self.add = laws.of(laws.add)
            self.mul = laws.of(laws.mul)
            for L in (self.add, self.mul):
                if not L.ready():
                    raise SemiringException("semiring_norm: %s needs comm and assoc" % L.op)
        else:
            ready = [L for L in laws.ops.values() if L.ready()]
            if len(ready) != 1:
                raise SemiringException(
                    "semiring_norm: without distributivity, give comm and assoc for one operation")
            self.add, self.mul = ready[0], None

    def norm(self, t: Term) -> ProofTerm:
        if is_op(t, self.add.op):
            return refl(t).on_rhs(binop_conv(FunConv(self.norm)),
                                  FunConv(lambda u: ac_merge(self.add, u)))
        if self.mul is not None and is_op(t, self.mul.op):
            return refl(t).on_rhs(binop_conv(FunConv(self.norm)), FunConv(self.mult))
        return refl(t)

    def mult(self, t: Term) -> ProofTerm:
        """``g a b`` with a, b normal sums: a normal sum."""
        _, a, b = dest_op(t)
        f = self.add.op
        sub = FunConv(lambda u: self.mult(u) if is_op(u, self.mul.op) else refl(u))
        merge = FunConv(lambda u: ac_merge(self.add, u) if is_op(u, f) else refl(u))
        if is_op(a, f):
            return refl(t).on_rhs(self._rdist(), binop_conv(sub), merge)
        if is_op(b, f):
            return refl(t).on_rhs(self._ldist(), binop_conv(sub), merge)
        return ac_merge(self.mul, t)

    def _ldist(self) -> Conv:
        L = self.laws
        if L.ldist is not None:
            return _rw(L.ldist)
        return FunConv(lambda t: refl(t).on_rhs(_rw(self.mul.comm), _rw(L.rdist)))

    def _rdist(self) -> Conv:
        L = self.laws
        if L.rdist is not None:
            return _rw(L.rdist)
        return FunConv(lambda t: refl(t).on_rhs(_rw(self.mul.comm), _rw(L.ldist)))


def parse_names(names: str) -> List[str]:
    return [n for n in names.split() if n]


def _laws(names: str, pts) -> Laws:
    laws = Laws()
    for nm in parse_names(names):
        laws.add_law(ProofTerm.theorem(nm))
    for pt in pts:
        laws.add_law(pt)
    return laws


def semiring_norm_conv(names: str, pts) -> Conv:
    """A conversion to the normal form, for use in other macros and tactics."""
    return FunConv(Normaliser(_laws(names, pts)).norm)


@register_macro("semiring_norm")
class SemiringNormMacro(Macro):
    """``semiring_norm (names, lhs = rhs)``: normalise both sides with the laws
    named in ``names`` (space separated) and given as previous facts.
    """

    def __init__(self) -> None:
        self.level = 1
        self.sig = Tuple[str, Term]
        self.limit = None

    def get_proof_term(self, args, pts) -> ProofTerm:
        names, goal = args
        if not goal.is_equals():
            raise SemiringException("semiring_norm: goal is not an equation: %s" % goal)
        try:
            norm = Normaliser(_laws(names, pts))
            pt1, pt2 = norm.norm(goal.lhs), norm.norm(goal.rhs)
        except ConvException as e:
            raise SemiringException("semiring_norm: %s" % e.str)
        if pt1.rhs != pt2.rhs:
            raise SemiringException("semiring_norm: normal forms differ:\n  %s\n  %s"
                                    % (pt1.rhs, pt2.rhs))
        return pt1.transitive(pt2.symmetric())
