"""Linear arithmetic over the reals, with a full expansion.

The ``real_linarith`` macro proves a goal ``a ≤ b``, ``a < b``, ``a ≥ b``,
``a > b``, ``a = b`` or ``false`` from hypotheses of the same shapes
(passed as previous facts), whenever the goal follows by linear
reasoning.  Terms that are not linear (``x * y``, ``max x y``, function
applications, ...) are treated as opaque atoms.

Unlike stock HolPy's ``real_norm``, ``real_compare`` and ``simplex_macro``
(level 0, no expansion), this macro is level 1 and its expansion uses only
primitive rules, ``theorem`` and other expandable macros.  The search for
a proof happens in Python; what reaches the kernel is a Farkas
certificate replayed with ordered-field lemmas:

1. each fact becomes ``0 ≤ e`` or ``0 < e`` (``e = rhs - lhs``), and the
   negation of the goal is assumed and treated the same way;
2. Fourier–Motzkin elimination finds non-negative integers ``k_i`` such
   that ``Σ k_i e_i`` is a constant ``c`` with ``c < 0``, or ``c = 0`` and
   some strict fact used;
3. the facts are scaled and added (``real_le_lmul``, ``real_lt_mul``,
   ``real_le_add2`` and friends), the sum is normalised to ``c`` by the
   expandable conversion :func:`lin_norm`, and ``0 ≤ c`` is refuted.

``nat_linarith`` does the same for ``nat`` by moving every fact to
``real`` through ``of_nat`` (see :func:`nat_fact_to_real`).

Numeral arithmetic is done in binary on ``nat`` with the expandable
``add_conv``/``mult_conv`` of :mod:`holpy.data.nat`, so no step evaluates
numbers outside the kernel.

Fractions are handled as HolPy writes them, ``u / q`` with ``q`` a
positive integer numeral (``Real(Fraction(1, 2))`` is ``1 / 2``): each fact
is first multiplied by a common denominator (:func:`push_denom`, using
``real_div_lmul``), so the certificate and the normal form only ever see
integers.  Division by anything else is an opaque atom.

The expansion cites these ``real`` theorems that the bundled library
states without proof, so a transport certificate must list them:
``real_mult_comm``, ``real_mul_lid``, ``real_add_ldistrib``,
``real_poly_neg1``, ``real_poly_neg2``, ``real_of_nat_add``,
``real_of_nat_mul``, ``real_of_nat_lt``, ``real_of_nat_le`` (nat only),
``real_mul_lid``, ``real_lt_neq``, ``real_not_leq``, ``real_not_lt``,
``real_not_geq``, ``real_not_gt``, and from ``nat`` (through
``nat_const_less``) ``less_lesseqI``.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd
from typing import Callable, Dict, List, Optional, Tuple

from holpy.data import nat
from holpy.kernel import term_ord
from holpy.kernel.macro import Macro
from holpy.kernel.proofterm import ProofTerm, refl
from holpy.kernel.term import Binary, Const, Nat, Not, Real, Term
from holpy.kernel.theory import register_macro
from holpy.kernel.thm import Thm
from holpy.kernel.type import NatType, RealType, TFun
from holpy.logic.conv import Conv, arg1_conv, arg_conv, binop_conv, rewr_conv
from holpy.logic.logic import apply_theorem

# Fourier–Motzkin is exponential in the worst case; give up beyond this.
MAX_ROWS = 4000


class LinarithException(Exception):
    """Raised when ``real_linarith`` cannot prove its goal."""


# ---------------------------------------------------------------------------
# Integer numerals: 0, 1, of_nat <binary>, and -n for a positive numeral n.

def dest_num(t: Term) -> Optional[int]:
    """Return the value of a canonical real integer numeral, or None."""
    if t.get_type() != RealType:
        return None
    if t.is_zero():
        return 0
    if t.is_one():
        return 1
    if t.is_comb("of_nat", 1) and t.arg.is_binary() and not t.arg.is_zero() \
            and not t.arg.is_one():
        return t.arg.dest_binary()
    if t.is_uminus():
        n = dest_num(t.arg)
        if n is not None and n > 0:
            return -n
    return None


def is_num(t: Term) -> bool:
    return dest_num(t) is not None


class FunConv(Conv):
    """A conversion given by a function from terms to equality proofs."""

    def __init__(self, f: Callable[[Term], ProofTerm]) -> None:
        self.f = f

    def get_proof_term(self, t: Term) -> ProofTerm:
        return self.f(t)


class EqConv(Conv):
    """Rewrite exactly ``lhs`` to ``rhs`` with a given proof of ``lhs = rhs``."""

    def __init__(self, pt: ProofTerm) -> None:
        self.pt = pt

    def get_proof_term(self, t: Term) -> ProofTerm:
        assert t == self.pt.lhs, "EqConv: %s does not match %s" % (t, self.pt.lhs)
        return self.pt


def _to_of_nat(t: Term) -> ProofTerm:
    """``n = of_nat <binary>`` for a non-negative numeral ``n``."""
    if t.is_zero():
        return refl(t).on_rhs(rewr_conv("real_zero_def"))
    if t.is_one():
        return refl(t).on_rhs(rewr_conv("real_one_def"))
    return refl(t)


def _from_of_nat(t: Term) -> ProofTerm:
    """Inverse of :func:`_to_of_nat`."""
    if t.arg.is_zero():
        return refl(t).on_rhs(rewr_conv("real_zero_def", sym=True))
    if t.arg.is_one():
        return refl(t).on_rhs(rewr_conv("real_one_def", sym=True))
    return refl(t)


def _nat_binop(t: Term, th_name: str, cv: Conv) -> ProofTerm:
    """``a op b = c`` for non-negative numerals, computed on binary nat."""
    return refl(t).on_rhs(binop_conv(FunConv(_to_of_nat)), rewr_conv(th_name),
                          arg_conv(cv), FunConv(_from_of_nat))


def _neg_pos(t: Term) -> ProofTerm:
    """``-x`` for numeral x, as a numeral: ``-0 = 0``, ``--n = n``."""
    n = dest_num(t.arg)
    if n == 0:
        return refl(t).on_rhs(rewr_conv("real_neg_0"))
    if n < 0:
        return refl(t).on_rhs(rewr_conv("real_neg_neg"))
    return refl(t)


def num_add(t: Term) -> ProofTerm:
    """``a + b = c`` for integer numerals a, b."""
    a, b = dest_num(t.arg1), dest_num(t.arg)
    assert a is not None and b is not None, "num_add: %s" % t
    if a >= 0 and b >= 0:
        return _nat_binop(t, "real_of_nat_add", nat.add_conv())
    if a < 0 and b < 0:
        return refl(t).on_rhs(rewr_conv("real_neg_add", sym=True),
                              arg_conv(FunConv(num_add)))
    if a >= 0:  # a + -m  becomes  -m + a
        return refl(t).on_rhs(rewr_conv("real_add_comm"), FunConv(num_add))
    # -m + b with m > 0, b >= 0
    m = -a
    if b >= m:
        # b = m + d, and -m + (m + d) = d
        split = num_add(Real(m) + Real(b - m)).symmetric()
        return refl(t).on_rhs(arg_conv(EqConv(split)), rewr_conv("real_add_assoc"),
                              arg1_conv(rewr_conv("real_add_linv")), rewr_conv("real_add_lid"))
    # m = b + d, and -(b + d) + b = -d
    split = num_add(Real(b) + Real(m - b)).symmetric()
    return refl(t).on_rhs(arg1_conv(arg_conv(EqConv(split))),
                          arg1_conv(rewr_conv("real_neg_add")),
                          rewr_conv("real_add_comm"), rewr_conv("real_add_assoc"),
                          arg1_conv(rewr_conv("real_add_rinv")), rewr_conv("real_add_lid"),
                          FunConv(_neg_pos))


def num_mul(t: Term) -> ProofTerm:
    """``a * b = c`` for integer numerals a, b."""
    a, b = dest_num(t.arg1), dest_num(t.arg)
    assert a is not None and b is not None, "num_mul: %s" % t
    if a >= 0 and b >= 0:
        return _nat_binop(t, "real_of_nat_mul", nat.mult_conv())
    if a < 0:
        return refl(t).on_rhs(rewr_conv("real_mul_lneg"), arg_conv(FunConv(num_mul)),
                              FunConv(_neg_pos))
    return refl(t).on_rhs(rewr_conv("real_mul_rneg"), arg_conv(FunConv(num_mul)),
                          FunConv(_neg_pos))


def num_pos(n: int) -> ProofTerm:
    """``0 < n`` for a positive integer n."""
    assert n > 0
    nat_pt = ProofTerm("nat_const_less", Nat(0) < Nat(n), [])
    # Nat(n) is of_nat <binary> on nat; strip it to the raw binary.
    nat_pt = nat_pt.on_prop(arg_conv(nat.rewr_of_nat_conv()))
    zero = Real(0)
    iff = ProofTerm.theorem("real_of_nat_lt").substitution(m=nat_pt.prop.arg1, n=nat_pt.prop.arg)
    pt = iff.symmetric().equal_elim(nat_pt)
    # of_nat 0 < of_nat <n>  becomes  0 < n
    pt = pt.on_prop(arg1_conv(FunConv(_from_of_nat)), arg_conv(FunConv(_from_of_nat)))
    assert pt.prop == (zero < Real(n)), pt.prop
    return pt


# ---------------------------------------------------------------------------
# Linear normal form.
#
# A normal form is 0, or a left-nested sum m1 + ... + mk of monomials with
# strictly increasing keys.  A monomial is a non-zero numeral (key None,
# always first) or c * a with c a non-zero numeral and a an atom.

def mono_key(m: Term) -> Optional[Term]:
    if is_num(m):
        return None
    assert m.is_times() and is_num(m.arg1), "mono_key: %s" % m
    return m.arg


def cmp_key(k1: Optional[Term], k2: Optional[Term]) -> int:
    if k1 is None or k2 is None:
        return (k1 is not None) - (k2 is not None)
    return term_ord.fast_compare(k1, k2)


def _is_zero(t: Term) -> bool:
    return dest_num(t) == 0


def _combine(t: Term) -> ProofTerm:
    """``m1 + m2`` with equal keys, as one monomial or 0."""
    if mono_key(t.arg1) is None:
        return num_add(t)
    pt = refl(t).on_rhs(rewr_conv("real_add_rdistrib", sym=True), arg1_conv(FunConv(num_add)))
    if _is_zero(pt.rhs.arg1):
        pt = pt.on_rhs(rewr_conv("real_mul_lzero"))
    return pt


def _swap_add_r(t: Term) -> ProofTerm:
    """``(a + b) + c = (a + c) + b``."""
    return refl(t).on_rhs(rewr_conv("real_add_assoc", sym=True),
                          arg_conv(rewr_conv("real_add_comm")), rewr_conv("real_add_assoc"))


def _insert(t: Term) -> ProofTerm:
    """``r + m`` with r in normal form and m a monomial, in normal form."""
    r, m = t.arg1, t.arg
    if _is_zero(r):
        return refl(t).on_rhs(rewr_conv("real_add_lid"))
    if _is_zero(m):
        return refl(t).on_rhs(rewr_conv("real_add_rid"))
    if r.is_plus():
        c = cmp_key(mono_key(r.arg), mono_key(m))
        if c < 0:
            return refl(t)
        if c == 0:
            pt = refl(t).on_rhs(rewr_conv("real_add_assoc", sym=True), arg_conv(FunConv(_combine)))
            if _is_zero(pt.rhs.arg):
                pt = pt.on_rhs(rewr_conv("real_add_rid"))
            return pt
        pt = refl(t).on_rhs(FunConv(_swap_add_r), arg1_conv(FunConv(_insert)))
        if _is_zero(pt.rhs.arg1):
            pt = pt.on_rhs(rewr_conv("real_add_lid"))
        return pt
    c = cmp_key(mono_key(r), mono_key(m))
    if c < 0:
        return refl(t)
    if c == 0:
        return _combine(t)
    return refl(t).on_rhs(rewr_conv("real_add_comm"))


def _merge(t: Term) -> ProofTerm:
    """``p + q`` with p, q in normal form, in normal form."""
    p, q = t.arg1, t.arg
    if _is_zero(q):
        return refl(t).on_rhs(rewr_conv("real_add_rid"))
    if _is_zero(p):
        return refl(t).on_rhs(rewr_conv("real_add_lid"))
    if q.is_plus():
        return refl(t).on_rhs(rewr_conv("real_add_assoc"), arg1_conv(FunConv(_merge)),
                              FunConv(_insert))
    return _insert(t)


def _scale(t: Term) -> ProofTerm:
    """``c * p`` with c a numeral and p in normal form, in normal form."""
    c, p = t.arg1, t.arg
    if _is_zero(c):
        return refl(t).on_rhs(rewr_conv("real_mul_lzero"))
    if is_num(p):
        return num_mul(t)
    if p.is_plus():
        return refl(t).on_rhs(rewr_conv("real_add_ldistrib"),
                              arg1_conv(FunConv(_scale)), arg_conv(FunConv(_scale)))
    return refl(t).on_rhs(rewr_conv("real_mult_assoc"), arg1_conv(FunConv(num_mul)))


def _atom(t: Term) -> ProofTerm:
    return refl(t).on_rhs(rewr_conv("real_mul_lid", sym=True))


def lin_norm(t: Term) -> ProofTerm:
    """Proof of ``t = nf`` with nf the linear normal form of the real term t."""
    if is_num(t):
        return refl(t)
    if t.is_plus():
        return refl(t).on_rhs(binop_conv(FunConv(lin_norm)), FunConv(_merge))
    if t.is_minus():
        return refl(t).on_rhs(rewr_conv("real_poly_neg2"), FunConv(lin_norm))
    if t.is_uminus():
        if is_num(t.arg):
            return _neg_pos(t)
        return refl(t).on_rhs(rewr_conv("real_poly_neg1"), FunConv(lin_norm))
    if t.is_times():
        pt = refl(t).on_rhs(binop_conv(FunConv(lin_norm)))
        a, b = pt.rhs.args
        if is_num(a):
            return pt.on_rhs(FunConv(_scale))
        if is_num(b):
            return pt.on_rhs(rewr_conv("real_mult_comm"), FunConv(_scale))
        # A non-linear product is an atom.
        return pt.on_rhs(FunConv(_atom))
    return _atom(t)


def _lcm(a: int, b: int) -> int:
    return a * b // gcd(a, b)


def denom(t: Term) -> int:
    """A common denominator of the numeral divisions in the linear part of t."""
    if is_num(t):
        return 1
    if t.is_plus() or t.is_minus():
        return _lcm(denom(t.arg1), denom(t.arg))
    if t.is_uminus():
        return denom(t.arg)
    if t.is_times():
        if is_num(t.arg1):
            return denom(t.arg)
        if is_num(t.arg):
            return denom(t.arg1)
        return 1
    if t.is_divides():
        q = dest_num(t.arg)
        if q is not None and q > 0:
            return q * denom(t.arg1)
    return 1


def num_nonzero(q: int) -> ProofTerm:
    """``¬(q = 0)`` for a positive integer q."""
    return apply_theorem("ineq_sym", apply_theorem("real_lt_neq", num_pos(q)))


def push_denom(t: Term) -> ProofTerm:
    """``D * e = e'`` where D is a non-zero integer numeral that clears every
    numeral division in the linear part of e, and e' has none left there.
    """
    d, e = dest_num(t.arg1), t.arg
    assert d is not None and d != 0, "push_denom: %s" % t
    if denom(e) == 1:
        return refl(t)
    if e.is_plus():
        return refl(t).on_rhs(rewr_conv("real_add_ldistrib"),
                              binop_conv(FunConv(push_denom)))
    if e.is_minus():
        return refl(t).on_rhs(arg_conv(rewr_conv("real_poly_neg2")), FunConv(push_denom))
    if e.is_uminus():
        return refl(t).on_rhs(arg_conv(rewr_conv("real_poly_neg1")), FunConv(push_denom))
    if e.is_times():
        pt = refl(t)
        if not is_num(e.arg1):
            pt = pt.on_rhs(arg_conv(rewr_conv("real_mult_comm")))
        return pt.on_rhs(rewr_conv("real_mult_assoc"), arg1_conv(FunConv(num_mul)),
                         FunConv(push_denom))
    # e = u / q with q a positive numeral, and q divides d.
    u, q = e.arg1, dest_num(e.arg)
    k = d // q
    assert k * q == d, "push_denom: %d does not clear %s" % (d, e)
    split = num_mul(Real(k) * Real(q)).symmetric()
    cancel = ProofTerm.theorem("real_div_lmul").substitution(x=u, y=Real(q)).implies_elim(
        num_nonzero(q))
    pt = refl(t).on_rhs(arg1_conv(EqConv(split)), rewr_conv("real_mult_assoc", sym=True),
                        arg_conv(EqConv(cancel)))
    if k == 1:
        return pt.on_rhs(rewr_conv("real_mul_lid"))
    return pt.on_rhs(FunConv(push_denom))


def norm_fact(pt: ProofTerm) -> ProofTerm:
    """From ``0 ≤/< e`` prove ``0 ≤/< nf``: clear denominators, then normalise."""
    d = denom(pt.prop.arg)
    if d > 1:
        pt = _scale_fact(d, pt).on_prop(arg_conv(FunConv(push_denom)))
    return pt.on_prop(arg_conv(FunConv(lin_norm)))


def lin_coeffs(nf: Term) -> Tuple[Dict[Term, Fraction], Fraction]:
    """Read the atom coefficients and the constant of a normal form."""
    coeffs: Dict[Term, Fraction] = {}
    const = Fraction(0)
    monos = []
    while nf.is_plus():
        monos.append(nf.arg)
        nf = nf.arg1
    monos.append(nf)
    for m in monos:
        if is_num(m):
            const += dest_num(m)
        else:
            coeffs[m.arg] = Fraction(dest_num(m.arg1))
    return coeffs, const


# ---------------------------------------------------------------------------
# Facts as 0 ≤ e / 0 < e.

def _comparison(t: Term) -> bool:
    return (t.is_less_eq() or t.is_less() or t.is_greater_eq() or t.is_greater()) \
        and t.arg.get_type() == RealType


def to_sign_facts(pt: ProofTerm) -> List[ProofTerm]:
    """Turn a fact into proofs of ``0 ≤ e`` / ``0 < e``.

    An equality ``a = b`` gives both ``0 ≤ b - a`` and ``0 ≤ a - b``; a
    negated comparison is first turned into a comparison.
    """
    p = pt.prop
    if p.is_not():
        q = p.arg
        if q.is_equals():
            raise LinarithException("real_linarith: cannot use a disequality %s" % p)
        name = {"less_eq": "real_not_leq", "less": "real_not_lt",
                "greater_eq": "real_not_geq", "greater": "real_not_gt"}[q.head.name]
        return to_sign_facts(pt.on_prop(rewr_conv(name)))
    if p.is_equals() and p.lhs.get_type() == RealType:
        a, b = p.args
        le1 = ProofTerm.theorem("real_le_refl").substitution(x=a).on_prop(arg_conv(EqConv(pt)))
        le2 = ProofTerm.theorem("real_le_refl").substitution(x=b).on_prop(
            arg_conv(EqConv(pt.symmetric())))
        return to_sign_facts(le1) + to_sign_facts(le2)
    if not _comparison(p):
        raise LinarithException("real_linarith: not a real comparison: %s" % p)
    if p.is_greater_eq():
        pt = pt.on_prop(rewr_conv("real_geq_to_leq"))
    elif p.is_greater():
        pt = pt.on_prop(rewr_conv("real_ge_to_le"))
    if pt.prop.is_less_eq():
        return [pt.on_prop(rewr_conv("real_sub_le", sym=True))]
    return [pt.on_prop(rewr_conv("real_sub_lt", sym=True))]


# ---------------------------------------------------------------------------
# Certificate search.

Row = Tuple[Dict[Term, Fraction], Fraction, bool, Dict[int, Fraction]]


def _contradiction(row: Row) -> bool:
    coeffs, const, strict, _ = row
    return not coeffs and (const < 0 or (const == 0 and strict))


def find_certificate(facts: List[Tuple[Dict[Term, Fraction], Fraction, bool]]) -> List[int]:
    """Fourier–Motzkin search for a Farkas certificate.

    Parameters
    ----------
    facts : list
        ``(coeffs, const, strict)`` meaning ``0 ≤ const + Σ coeffs·atoms``
        (``<`` when strict).

    Returns
    -------
    List[int]
        Non-negative integer multipliers, one per fact.

    Raises
    ------
    LinarithException
        If the facts are consistent or the search grows too large.
    """
    rows: List[Row] = [(dict(c), k, s, {i: Fraction(1)}) for i, (c, k, s) in enumerate(facts)]
    while True:
        for row in rows:
            if _contradiction(row):
                mult = row[3]
                den = 1
                for v in mult.values():
                    den = den * v.denominator // gcd(den, v.denominator)
                ints = [int(mult.get(i, 0) * den) for i in range(len(facts))]
                g = 0
                for v in ints:
                    g = gcd(g, v)
                return [v // g for v in ints]
        atoms = {a for row in rows for a in row[0]}
        if not atoms:
            raise LinarithException("real_linarith: no linear contradiction found")

        def cost(a):
            pos = sum(1 for r in rows if r[0].get(a, 0) > 0)
            neg = sum(1 for r in rows if r[0].get(a, 0) < 0)
            return (pos * neg - pos - neg, str(a))

        x = min(atoms, key=cost)
        pos = [r for r in rows if r[0].get(x, 0) > 0]
        neg = [r for r in rows if r[0].get(x, 0) < 0]
        new_rows = [r for r in rows if x not in r[0]]
        for p in pos:
            for n in neg:
                lp, ln = -n[0][x], p[0][x]  # both positive
                coeffs = {}
                for a in set(p[0]) | set(n[0]):
                    v = lp * p[0].get(a, 0) + ln * n[0].get(a, 0)
                    if v != 0:
                        coeffs[a] = v
                mult = {i: lp * p[3].get(i, 0) + ln * n[3].get(i, 0)
                        for i in set(p[3]) | set(n[3])}
                new_rows.append((coeffs, lp * p[1] + ln * n[1], p[2] or n[2], mult))
        if len(new_rows) > MAX_ROWS:
            raise LinarithException("real_linarith: search too large")
        rows = new_rows


# ---------------------------------------------------------------------------
# Evaluation without building a proof.
#
# eval only needs to know that a certificate exists.  It reads the linear
# structure directly and treats every other subterm as an atom, compared
# syntactically.  That is sound, and never stronger than the expansion,
# whose normal form identifies at least the terms this identifies.

def py_lin(t: Term) -> Tuple[Dict[Term, Fraction], Fraction]:
    """Linear form of a real term as (atom coefficients, constant)."""
    n = dest_num(t)
    if n is not None:
        return {}, Fraction(n)

    def comb(f1, k1, f2, k2):
        (c1, a1), (c2, a2) = f1, f2
        c = {}
        for a in set(c1) | set(c2):
            v = k1 * c1.get(a, 0) + k2 * c2.get(a, 0)
            if v != 0:
                c[a] = v
        return c, k1 * a1 + k2 * a2

    zero = ({}, Fraction(0))
    if t.is_plus():
        return comb(py_lin(t.arg1), 1, py_lin(t.arg), 1)
    if t.is_minus():
        return comb(py_lin(t.arg1), 1, py_lin(t.arg), -1)
    if t.is_uminus():
        return comb(zero, 0, py_lin(t.arg), -1)
    if t.is_times():
        if is_num(t.arg1):
            return comb(zero, 0, py_lin(t.arg), dest_num(t.arg1))
        if is_num(t.arg):
            return comb(zero, 0, py_lin(t.arg1), dest_num(t.arg))
    if t.is_divides():
        q = dest_num(t.arg)
        if q is not None and q != 0:
            return comb(zero, 0, py_lin(t.arg1), Fraction(1, q))
    return {t: Fraction(1)}, Fraction(0)


def py_sign_facts(p: Term) -> List[Tuple[Dict[Term, Fraction], Fraction, bool]]:
    """Mirror of :func:`to_sign_facts` on statements."""
    if p.is_not():
        q = p.arg
        if q.is_less_eq():
            return py_sign_facts(q.arg < q.arg1)
        if q.is_less():
            return py_sign_facts(q.arg <= q.arg1)
        if q.is_greater_eq():
            return py_sign_facts(q.arg1 < q.arg)
        if q.is_greater():
            return py_sign_facts(q.arg1 <= q.arg)
        raise LinarithException("real_linarith: cannot use %s" % p)
    if p.is_equals() and p.lhs.get_type() == RealType:
        return py_sign_facts(p.lhs <= p.rhs) + py_sign_facts(p.rhs <= p.lhs)
    if not _comparison(p):
        raise LinarithException("real_linarith: not a real comparison: %s" % p)
    if p.is_greater_eq() or p.is_greater():
        a, b = p.arg, p.arg1  # a ≤ b, a < b
    else:
        a, b = p.arg1, p.arg
    c1, k1 = py_lin(b)
    c2, k2 = py_lin(a)
    coeffs = {x: c1.get(x, 0) - c2.get(x, 0) for x in set(c1) | set(c2)}
    coeffs = {x: v for x, v in coeffs.items() if v != 0}
    return [(coeffs, k1 - k2, p.is_less() or p.is_greater())]


def can_refute(props: List[Term]) -> bool:
    try:
        find_certificate([f for p in props for f in py_sign_facts(p)])
    except LinarithException:
        return False
    return True


# ---------------------------------------------------------------------------
# Proof replay.

def _scale_fact(k: int, pt: ProofTerm) -> ProofTerm:
    """From ``0 ≤ e`` (``0 < e``) prove ``0 ≤ k * e`` (``0 < k * e``)."""
    if k == 1:
        return pt
    kt = Real(k)
    if pt.prop.is_less_eq():
        k_nonneg = ProofTerm.theorem("real_pos").substitution(n=Binary(k))
        res = apply_theorem("real_le_lmul", k_nonneg, pt)
        return res.on_prop(arg1_conv(rewr_conv("real_mul_rzero")))
    res = apply_theorem("real_lt_mul", num_pos(k), pt)
    assert res.prop.arg1.is_zero() and res.prop.arg == kt * pt.prop.arg
    return res


_ADD_RULES = {(False, False): "real_le_add2", (True, True): "real_lt_add2",
              (False, True): "real_let_add2", (True, False): "real_lte_add2"}


def _add_facts(pt1: ProofTerm, pt2: ProofTerm) -> ProofTerm:
    """From ``0 ≤/< a`` and ``0 ≤/< b`` prove ``0 ≤/< a + b``."""
    rule = _ADD_RULES[(pt1.prop.is_less(), pt2.prop.is_less())]
    return apply_theorem(rule, pt1, pt2).on_prop(arg1_conv(rewr_conv("real_add_lid")))


def _refute_const(pt: ProofTerm) -> ProofTerm:
    """From ``0 ≤ c`` with c < 0, or ``0 < c`` with c ≤ 0, prove false."""
    c = dest_num(pt.prop.arg)
    if c == 0:
        assert pt.prop.is_less()
        le = ProofTerm.theorem("real_le_refl").substitution(x=Real(0))
        conj = apply_theorem("conjI", pt, le)
    else:
        assert c < 0
        if pt.prop.is_less():
            pt = apply_theorem("real_lt_imp_le", pt)
        # 0 ≤ -n  becomes  n ≤ 0
        pt = pt.on_prop(rewr_conv("real_le_rneg"), arg1_conv(rewr_conv("real_add_lid")))
        conj = apply_theorem("conjI", num_pos(-c), pt)
    return apply_theorem("negE", ProofTerm.theorem("real_lte_antisym").substitution(
        x=conj.prop.arg1.arg1, y=conj.prop.arg1.arg), conj)


def prove_false(pts: List[ProofTerm]) -> ProofTerm:
    """Derive false from real comparison facts by linear reasoning."""
    sign_facts = [f for pt in pts for f in to_sign_facts(pt)]
    if not sign_facts:
        raise LinarithException("real_linarith: no facts")
    sign_facts = [norm_fact(f) for f in sign_facts]
    data = []
    for f in sign_facts:
        coeffs, const = lin_coeffs(f.prop.arg)
        data.append((coeffs, const, f.prop.is_less()))
    ks = find_certificate(data)

    acc = None
    for k, f in zip(ks, sign_facts):
        if k == 0:
            continue
        scaled = _scale_fact(k, f)
        acc = scaled if acc is None else _add_facts(acc, scaled)
    acc = acc.on_prop(arg_conv(FunConv(lin_norm)))
    if not is_num(acc.prop.arg):
        raise LinarithException("real_linarith: certificate did not cancel: %s" % acc.prop)
    return _refute_const(acc)


def _by_contradiction(goal: Term, pts: List[ProofTerm]) -> ProofTerm:
    """Prove a comparison goal by refuting its negation."""
    neg = Not(goal)
    false_pt = prove_false(list(pts) + [ProofTerm.assume(neg)])
    # (¬G ⟶ G) ⟶ G, with ¬G ⟶ G from ¬G ⟶ false.
    goal_pt = apply_theorem("falseE", false_pt, concl=goal)
    return apply_theorem("contradiction", goal_pt.implies_intr(neg))


def check_goal(goal: Term) -> None:
    """Raise unless goal is false, a real comparison, or a real equality."""
    if goal.is_const("false") or _comparison(goal):
        return
    if goal.is_equals() and goal.lhs.get_type() == RealType:
        return
    raise LinarithException("real_linarith: unsupported goal %s" % goal)


@register_macro("real_linarith")
class RealLinarithMacro(Macro):
    """``real_linarith goal``: prove goal from the previous facts by linear arithmetic."""

    def __init__(self) -> None:
        self.level = 1
        self.sig = Term
        self.limit = None

    def eval(self, goal: Term, prevs) -> Thm:
        check_goal(goal)
        props = [prev.prop for prev in prevs]
        if goal.is_const("false"):
            goals = [props]
        elif goal.is_equals():
            goals = [props + [Not(goal.lhs <= goal.rhs)], props + [Not(goal.rhs <= goal.lhs)]]
        else:
            goals = [props + [Not(goal)]]
        if not all(can_refute(g) for g in goals):
            raise LinarithException("real_linarith: no linear proof of %s" % goal)
        return Thm(goal, *(prev.hyps for prev in prevs))

    def get_proof_term(self, goal: Term, pts) -> ProofTerm:
        pts = list(pts)
        check_goal(goal)
        if goal.is_const("false"):
            return prove_false(pts)
        if goal.is_equals():
            a, b = goal.args
            both = apply_theorem("conjI", _by_contradiction(a <= b, pts),
                                 _by_contradiction(b <= a, pts))
            return ProofTerm.theorem("real_le_antisym").substitution(x=a, y=b).equal_elim(both)
        return _by_contradiction(goal, pts)


# ---------------------------------------------------------------------------
# Linear arithmetic over nat, by transfer to real.
#
# Each nat fact is moved to real through of_nat (real_of_nat_le and friends),
# with a non-negativity fact 0 ≤ of_nat x for every atom x.  Strict facts are
# first made integral, a < b becoming a + 1 ≤ b, which covers the usual
# off-by-one reasoning; the search itself is over the rationals, so it is
# not complete for nat.  The theory must import real.

OfNat = Const("of_nat", TFun(NatType, RealType))


def nat_to_real(t: Term, atoms: List[Term]) -> ProofTerm:
    """``of_nat x = r`` pushing of_nat through +, *, Suc and numerals.

    Every remaining ``of_nat a`` is recorded in ``atoms``.
    """
    x = t.arg
    if x.is_zero():
        return refl(t).on_rhs(rewr_conv("real_zero_def", sym=True))
    if x.is_one():
        return refl(t).on_rhs(rewr_conv("real_one_def", sym=True))
    if x.is_comb("of_nat", 1) and x.arg.is_binary():
        return refl(t).on_rhs(rewr_conv("real_of_nat_id"))
    if x.is_comb("Suc", 1):
        return refl(t).on_rhs(arg_conv(rewr_conv("add_1_right", sym=True)),
                              FunConv(lambda u: nat_to_real(u, atoms)))
    rec = FunConv(lambda u: nat_to_real(u, atoms))
    if x.is_plus():
        return refl(t).on_rhs(rewr_conv("real_of_nat_add", sym=True), binop_conv(rec))
    if x.is_times():
        return refl(t).on_rhs(rewr_conv("real_of_nat_mul", sym=True), binop_conv(rec))
    if t not in atoms:
        atoms.append(t)
    return refl(t)


def nat_fact_to_real(pt: ProofTerm, atoms: List[Term]) -> ProofTerm:
    """Turn a nat comparison or equality into a real one over of_nat terms."""
    p = pt.prop
    if p.is_not():
        q = p.arg
        if q.is_greater_eq() or q.is_greater():
            pt = pt.on_prop(arg_conv(rewr_conv("greater_eq_def" if q.is_greater_eq()
                                               else "greater_def")))
            q = pt.prop.arg
        if q.is_less_eq():
            return nat_fact_to_real(pt.on_prop(rewr_conv("not_le")), atoms)
        if q.is_less():
            return nat_fact_to_real(pt.on_prop(rewr_conv("not_lt")), atoms)
        raise LinarithException("nat_linarith: cannot use %s" % p)
    if p.is_greater_eq():
        return nat_fact_to_real(pt.on_prop(rewr_conv("greater_eq_def")), atoms)
    if p.is_greater():
        return nat_fact_to_real(pt.on_prop(rewr_conv("greater_def")), atoms)
    rec = FunConv(lambda u: nat_to_real(u, atoms))
    if p.is_less():
        # a < b  becomes  a + 1 ≤ b
        pt = pt.on_prop(rewr_conv("lesseq_Suc_less", sym=True),
                        arg1_conv(rewr_conv("add_1_right", sym=True)))
        p = pt.prop
    if p.is_less_eq():
        pt = pt.on_prop(rewr_conv("real_of_nat_le", sym=True))
        return pt.on_prop(binop_conv(rec))
    if p.is_equals():
        pt = ProofTerm.reflexive(OfNat).combination(pt)
        return pt.on_prop(binop_conv(rec))
    raise LinarithException("nat_linarith: not a nat comparison: %s" % p)


def _nat_comparison(t: Term) -> bool:
    return (t.is_less_eq() or t.is_less() or t.is_greater_eq() or t.is_greater()
            or t.is_equals()) and t.arg.get_type() == NatType


def nat_prove_false(pts: List[ProofTerm]) -> ProofTerm:
    atoms: List[Term] = []
    facts = [nat_fact_to_real(pt, atoms) for pt in pts]
    for a in atoms:
        facts.append(ProofTerm.theorem("real_pos").substitution(n=a.arg))
    return prove_false(facts)


@register_macro("nat_linarith")
class NatLinarithMacro(Macro):
    """``nat_linarith goal``: linear arithmetic on nat, through real."""

    def __init__(self) -> None:
        self.level = 1
        self.sig = Term
        self.limit = None

    def get_proof_term(self, goal: Term, pts) -> ProofTerm:
        pts = list(pts)
        for pt in pts:
            p = pt.prop.arg if pt.prop.is_not() else pt.prop
            if not _nat_comparison(p):
                raise LinarithException("nat_linarith: not a nat comparison: %s" % pt.prop)
        if goal.is_const("false"):
            return nat_prove_false(pts)
        if not _nat_comparison(goal):
            raise LinarithException("nat_linarith: unsupported goal %s" % goal)

        def by_contradiction(g):
            neg = Not(g)
            false_pt = nat_prove_false(pts + [ProofTerm.assume(neg)])
            g_pt = apply_theorem("falseE", false_pt, concl=g)
            return apply_theorem("contradiction", g_pt.implies_intr(neg))

        if goal.is_equals():
            a, b = goal.args
            both = apply_theorem("conjI", by_contradiction(a <= b), by_contradiction(b <= a))
            return ProofTerm.theorem("le_antisym").substitution(m=a, n=b).equal_elim(both)
        return by_contradiction(goal)
