# Author: Bohua Zhan

"""Theory state, proof checking, and the global theory context.

A :class:`Theory` owns the type and term signatures, proved theorems, theorem
attributes, overload registrations, and arbitrary extension data. It is also
the object that checks a linear proof against the primitive derivations.

The module-level ``thy`` value is the current theory. Higher layers install
theories through :func:`fresh_theory` or by extending the current context.
"""

from __future__ import annotations

from copy import copy
from typing import Any, Callable, Iterator, Tuple
import contextlib

from holpy.kernel.type import Type, TVar, TFun, BoolType, TypeMatchException
from holpy.kernel.term import Term, Var, TypeCheckException
from holpy.kernel.thm import Thm, primitive_deriv, InvalidDerivationException
from holpy.kernel.proof import Proof, ProofItem, ProofStateException
from holpy.kernel import extension
from holpy.kernel.report import ExtensionReport, ProofReport


class TheoryException(Exception):
    """General exception for theory operations."""

    def __init__(self, str: str):
        self.str = str


class CheckProofException(Exception):
    """Raised when proof checking fails."""

    def __init__(self, str: str):
        self.str = str


class ParameterQueryException(Exception):
    """Raised when a method needs additional parameters.

    Attributes
    ----------
    params : list of str
        Names of the missing parameters.
    """

    def __init__(self, params: list[str]):
        assert isinstance(params, list) and all(isinstance(param, str) for param in params), \
            "ParameterQueryException: input is not a list of strings"
        self.params = params


class Theory:
    """The current state of a theory.

    The theory stores:

    * ``type_sig``: arity of each type constructor;
    * ``term_sig``: most general type of each term constant;
    * ``theorems``: proved theorems;
    * ``theorems_svar``: cache of theorems with schematic variables;
    * ``attributes``: attributes attached to theorems;
    * ``overload``: registered overloaded constants.

    Extension data lives in ``self.data`` and is keyed by data-type name. The
    theory also checks proofs and applies checked or unchecked extensions.
    """

    def __init__(self):
        self.data: dict[str, Any] = dict()

    def __copy__(self) -> Theory:
        """Return a shallow copy of the theory.

        Each value in ``self.data`` is shallow-copied, so the top-level
        dictionaries are independent while their contents are shared.
        """
        res = Theory()
        res.data = dict()
        for name, val in self.data.items():
            res.data[name] = copy(val)
        return res

    def add_data_type(self, name: str, init: Any = None):
        """Register a new extension-data type.

        Parameters
        ----------
        name : str
            Data-type name.
        init : Any, optional
            Initial value; defaults to an empty dict.
        """
        if name in self.data:
            raise TheoryException("Add data type")

        if init is None:
            init = dict()
        self.data[name] = init

    def add_data(self, name: str, key: str, val: Any):
        """Add ``val`` under ``key`` to a dictionary-valued data type."""
        if name not in self.data:
            raise TheoryException("Add data")

        assert isinstance(self.data[name], dict), "add_data: data must be a dictionary"

        self.data[name][key] = val

    def update_data(self, name: str, f: Callable[[Any], Any]):
        """Replace a data type's value with ``f(current_value)``."""
        if name not in self.data:
            raise TheoryException("Update data")

        self.data[name] = f(self.data[name])

    def get_data(self, name: str) -> Any:
        """Return the value of the given extension-data type."""
        return self.data[name]

    def add_type_sig(self, name: str, n: int):
        """Register a type constructor with arity ``n``."""
        self.add_data("type_sig", name, n)

    def has_type_sig(self, name: str) -> bool:
        """Return whether ``name`` is a registered type constructor."""
        return name in self.get_data("type_sig")

    def get_type_sig(self, name: str) -> int:
        """Return the arity of the type constructor ``name``."""
        data = self.get_data("type_sig")
        if name not in data:
            raise TheoryException("Type " + name + " not found")

        return data[name]

    def add_term_sig(self, name: str, T: Type):
        """Register a constant with most general type ``T``.

        Overloaded constants must be instantiated with concrete type
        constructors; non-overloaded names must not already exist.
        """
        if self.is_overload_const(name):
            # An overloaded constant may be registered repeatedly, but only
            # with instances of its schematic type.
            aT = self.get_term_sig(name, stvar=True)
            try:
                inst = aT.match(T)
            except TypeMatchException:
                raise TheoryException("Constant %s :: %s does not match overloaded type %s" % (name, T, aT))

            for _, v in sorted(inst.items()):
                if not v.is_tconst():
                    raise TheoryException("When overloading %s with %s: cannot instantiate to type variables" % (aT, T))
        else:
            # Make sure this name does not already occur in the theory
            if self.has_term_sig(name):
                raise TheoryException("Constant %s already exists" % name)

            self.add_data("term_sig", name, T)

    def has_term_sig(self, name: str) -> bool:
        """Return whether ``name`` is a registered constant."""
        return name in self.get_data("term_sig")

    def get_term_sig(self, name: str, stvar: bool = False) -> Type:
        """Return the most general type of ``name``.

        If ``stvar`` is true, return a version with schematic variables.
        """
        data = self.get_data("term_sig")
        if name not in data:
            raise TheoryException("Const " + name + " not found")

        if stvar:
            return data[name].convert_stvar()
        else:
            return data[name]

    def add_theorem(self, name: str, th: Thm):
        """Register ``th`` under ``name``."""
        if not isinstance(th, Thm):
            raise TypeError

        self.add_data("theorems", name, th)

    def has_theorem(self, name: str) -> bool:
        """Return whether the theory contains a theorem named ``name``."""
        data = self.get_data("theorems")
        return name in data

    def get_theorem(self, name: str, *, svar: bool = True) -> Thm:
        """Return the theorem named ``name``.

        Parameters
        ----------
        name : str
            Theorem name.
        svar : bool
            If true, return the version with schematic variables; the
            converted theorem is cached in ``theorems_svar``.

        Returns
        -------
        Thm
            The requested theorem.

        Raises
        ------
        TheoryException
            If the theorem does not exist.
        """
        data = self.get_data("theorems")
        if name not in data:
            raise TheoryException("Theorem " + name + " not found")

        if svar:
            data_svar = self.get_data("theorems_svar")
            if name not in data_svar:
                data_svar[name] = Thm.convert_svar(data[name])
            return data_svar[name]
        else:
            return data[name]

    def add_attribute(self, name: str, attribute: str):
        """Attach ``attribute`` to the theorem named ``name``."""
        old_attributes = tuple()
        if name in self.data['attributes']:
            old_attributes = self.data['attributes'][name]
        self.data['attributes'][name] = old_attributes + (attribute,)

    def get_attributes(self, name: str) -> tuple[str, ...]:
        """Return the attributes attached to theorem ``name``."""
        if name in self.data['attributes']:
            return self.data['attributes'][name]
        else:
            return tuple()

    def add_overload_const(self, name: str):
        """Register ``name`` as an overloaded constant."""
        data = self.get_data("overload")
        data[name] = True

    def is_overload_const(self, name: str) -> bool:
        """Return whether ``name`` is an overloaded constant."""
        data = self.get_data("overload")
        return name in data

    def get_overload_const_name(self, name: str, T: Type) -> str:
        """Return the concrete name of an overloaded constant.

        The instantiated type constructors are prefixed to the base name and
        separated by underscores. For example, ``(plus, nat => nat => nat)``
        becomes ``nat_plus`` and ``(power, real => nat => real)`` becomes
        ``real_nat_power``.
        """
        if self.is_overload_const(name):
            aT = self.get_term_sig(name, stvar=True)
            try:
                inst = aT.match(T)
            except TypeMatchException:
                raise TheoryException("Constant %s :: %s does not match overloaded type %s" % (name, T, aT))

            baseT = []
            for _, v in sorted(inst.items()):
                if v.is_tconst():
                    baseT.append(v)

            T_name = "_".join(T.name for T in baseT)
            return T_name + "_" + name
        else:
            return name

    def check_type(self, T: Type) -> None:
        """Check that ``T`` is well formed in this theory.

        All type constructors must exist and be applied to the right number
        of arguments.
        """
        if T.is_stvar() or T.is_tvar():
            return None
        elif T.is_tconst():
            if not self.has_type_sig(T.name):
                raise TheoryException("Unknown type %s" % T.name)
            if self.get_type_sig(T.name) != len(T.args):
                raise TheoryException("Incorrect arity for type %s" % T.name)
            for arg in T.args:
                self.check_type(arg)
        else:
            raise TypeError

    def check_term(self, t: Term) -> None:
        """Check that ``t`` is well formed in this theory.

        Constants must exist and have types compatible with their registered
        signatures.
        """
        if t.is_var():
            return None
        elif t.is_const():
            try:
                self.get_term_sig(t.name, stvar=True).match(t.T)
            except TypeMatchException:
                raise TheoryException("Check term: " + repr(t))
        elif t.is_comb():
            self.check_term(t.fun)
            self.check_term(t.arg)
        elif t.is_abs():
            self.check_term(t.body)
        elif t.is_bound():
            return None
        else:
            raise TypeError

    def _check_proof_item(self, prf: Proof, seq: ProofItem, rpt: ProofReport | None,
                          no_gaps: bool, compute_only: bool, check_level: int) -> None:
        """Check one proof item and update its statement.

        Parameters
        ----------
        prf : Proof
            Proof containing the item.
        seq : ProofItem
            Item to check.
        rpt : ProofReport or None
            Report updated by the check.
        no_gaps : bool
            Reject gaps when true.
        compute_only : bool
            Trust an existing statement; only recurse into subproofs.
        check_level : int
            Trust level for direct macro evaluation.
        """
        if seq.rule == "":
            # Empty line in the proof
            return None

        if seq.rule == "sorry":
            # Gap in the proof
            assert seq.th is not None, "sorry must have explicit statement."
            if no_gaps:
                raise CheckProofException("gaps are not allowed")
            if rpt is not None:
                rpt.add_gap(seq.th)
            return None

        if compute_only and seq.th is not None:
            # In compute_only mode, skip when a theorem exists. However,
            # subproofs still need to be checked.
            if seq.rule == "subproof":
                for s in seq.subproof.items:
                    self._check_proof_item(prf, s, rpt, no_gaps, compute_only, check_level)
            return None

        if seq.rule == "theorem":
            # Copies an existing theorem in the theory into the proof.
            try:
                res_th = self.get_theorem(seq.args)
                if rpt is not None:
                    rpt.apply_theorem(seq.args)
            except TheoryException:
                raise CheckProofException("theorem not found")
        elif seq.rule == "variable":
            # Declares a variable. Skip check.
            nm, T = seq.args
            res_th = Thm.mk_VAR(Var(nm, T))
        elif seq.rule == "subproof":
            for s in seq.subproof.items:
                self._check_proof_item(prf, s, rpt, no_gaps, compute_only, check_level)
            res_th = seq.subproof.items[-1].th
        else:
            # Otherwise, apply one of the proof methods. First, we
            # obtain list of previous sequents used by the proof method:
            prev_ths = []
            assert isinstance(seq.prevs, list), "prevs should be a list"
            for prev in seq.prevs:
                if not seq.id.can_depend_on(prev):
                    raise CheckProofException("id %s cannot depend on %s" % (seq.id, prev))
                try:
                    prev_ths.append(prf.find_item(prev).th)
                except ProofStateException:
                    raise CheckProofException("previous item not found")

            for prev, prev_th in zip(seq.prevs, prev_ths):
                if prev_th is None:
                    raise CheckProofException("previous theorem %s is None" % prev)

            if seq.rule in primitive_deriv:
                # If the method is one of the primitive derivations, obtain and
                # apply that primitive derivation.
                rule_fun, _ = primitive_deriv[seq.rule]
                try:
                    res_th = rule_fun(*prev_ths) if seq.args is None else rule_fun(seq.args, *prev_ths)
                    if rpt is not None:
                        rpt.apply_primitive_deriv()
                except InvalidDerivationException:
                    raise CheckProofException("invalid derivation")
                except TypeError:
                    raise CheckProofException("invalid input to derivation " + seq.rule)

            elif has_macro(seq.rule):
                # Otherwise, the proof method corresponds to a macro. If
                # the level of the macro is less than or equal to the current
                # trust level, simply evaluate the macro to check that results
                # match. Otherwise, expand the macro and check all of the steps.
                macro = get_macro(seq.rule)
                assert macro.level is None or (isinstance(macro.level, int) and macro.level >= 0), \
                    ("check_proof: invalid macro level " + str(macro.level))
                if macro.level is not None and macro.level <= check_level:
                    res_th = macro.eval(seq.args, prev_ths)
                    if rpt is not None:
                        rpt.eval_macro(seq.rule)
                else:
                    seq.subproof = macro.expand(seq.id, seq.args, list(zip(seq.prevs, prev_ths)))
                    if rpt is not None:
                        rpt.expand_macro(seq.rule)
                    for s in seq.subproof.items:
                        self._check_proof_item(prf, s, rpt, no_gaps, compute_only, check_level)
                    res_th = seq.subproof.items[-1].th
                    seq.subproof = None
            else:
                raise CheckProofException("proof method not found: " + seq.rule)

        if seq.th is None:
            # No expected theorem is provided
            seq.th = res_th
        elif not res_th.can_prove(seq.th):
            # Resulting res_th is OK as long as the conclusion is the same,
            # and the assumptions is a subset of that of seq.th.
            raise CheckProofException("output does not match\n" + str(seq.th) + "\n vs.\n" + str(res_th))

        # Check the current statement is correctly typed.
        try:
            seq.th.check_thm_type()
        except TypeCheckException:
            raise CheckProofException("typing error")

        return None

    def check_proof(self, prf: Proof, rpt: ProofReport | None = None, *,
                    no_gaps: bool = False, compute_only: bool = False,
                    check_level: int = 0) -> Thm:
        """Verify a linear proof and return its final theorem.

        Parameters
        ----------
        prf : Proof
            Proof to check.
        rpt : ProofReport, optional
            Report updated during checking.
        no_gaps : bool
            Reject ``sorry`` items when true.
        compute_only : bool
            Trust items that already have a statement instead of re-deriving
            them.
        check_level : int
            Trust level for direct macro evaluation.

        Returns
        -------
        Thm
            The theorem proved by the last item.

        Raises
        ------
        CheckProofException
            If the proof is invalid.
        """
        assert isinstance(prf, Proof), "check_proof"
        for seq in prf.items:
            self._check_proof_item(prf, seq, rpt, no_gaps, compute_only, check_level)

        return prf.items[-1].th

    def get_proof_rule_sig(self, name: str) -> Any:
        """Return the argument signature of a proof rule."""
        if name == "theorem":
            return str
        elif name == "variable":
            return Tuple[str, Type]
        elif name == "sorry" or name == "subproof":
            return None
        elif name in primitive_deriv:
            _, sig = primitive_deriv[name]
            return sig
        else:
            macro = get_macro(name)
            return macro.sig

    def extend_type(self, ext: extension.Extension):
        """Apply a type-constructor extension."""
        assert ext.is_tconst(), "extend_type"

        self.add_type_sig(ext.name, ext.arity)

    def extend_constant(self, ext: extension.Extension):
        """Apply a constant extension."""
        assert ext.is_constant(), "extend_constant"

        self.add_term_sig(ext.name, ext.T)

    def extend_attribute(self, ext: extension.Extension):
        """Apply a theorem-attribute extension."""
        assert ext.is_attribute(), "extend_attribute"

        self.add_attribute(ext.name, ext.attribute)

    def unchecked_extend(self, exts: list[extension.Extension]):
        """Apply extensions without proof checking."""
        for ext in exts:
            if ext.is_tconst():
                self.extend_type(ext)
            elif ext.is_constant():
                self.extend_constant(ext)
            elif ext.is_theorem():
                self.add_theorem(ext.name, ext.th)
            elif ext.is_attribute():
                self.extend_attribute(ext)
            elif ext.is_overload():
                self.add_overload_const(ext.name)
            else:
                raise TypeError

    def checked_extend(self, exts: list[extension.Extension]) -> ExtensionReport:
        """Apply extensions, checking every supplied proof."""
        ext_report = ExtensionReport()

        for ext in exts:
            if ext.is_tconst():
                self.extend_type(ext)
            elif ext.is_constant():
                self.extend_constant(ext)
            elif ext.is_theorem():
                if ext.prf:
                    self.check_proof(ext.prf)
                else:  # No proof - add as axiom
                    ext_report.add_axiom(ext.name, ext.th)

                self.add_theorem(ext.name, ext.th)
            elif ext.is_attribute():
                self.extend_attribute(ext)
            elif ext.is_overload():
                self.add_overload_const(ext.name)
            else:
                raise TypeError

        return ext_report


#: Global theory used by the proof checker.
thy: Theory = None  # type: ignore[assignment]


def EmptyTheory() -> Theory:
    """Create a theory with the absolute minimum HOL setup."""
    thy = Theory()

    # Fundamental data structures, needed for proof checking.
    thy.add_data_type("type_sig")
    thy.add_data_type("term_sig")
    thy.add_data_type("theorems")
    thy.add_data_type("theorems_svar")  # cache of version of theorem with SVar.
    thy.add_data_type("attributes")
    thy.add_data_type("overload")

    # Fundamental types.
    thy.add_type_sig("bool", 0)
    thy.add_type_sig("fun", 2)

    # Fundamental terms.
    thy.add_term_sig("equals", TFun(TVar("a"), TVar("a"), BoolType))
    thy.add_term_sig("implies", TFun(BoolType, BoolType, BoolType))
    thy.add_term_sig("all", TFun(TFun(TVar("a"), BoolType), BoolType))

    return thy


@contextlib.contextmanager
def fresh_theory() -> Iterator[None]:
    """Temporarily install an empty theory and restore the previous one.

    This is used when loading a theory file: the file is checked in a fresh
    context so it cannot accidentally depend on ambient state.
    """
    global thy
    prev_thy = thy

    thy = EmptyTheory()
    try:
        yield None
    finally:
        thy = prev_thy


def get_theorem(name: str, *, svar: bool = True) -> Thm:
    """Return a theorem from the current theory."""
    return thy.get_theorem(name, svar=svar)


def print_theorem(*args: str):
    """Print the named theorems from the current theory."""
    for name in args:
        print('%s: %s' % (name, get_theorem(name, svar=False)))


def check_proof(prf: Proof, rpt: ProofReport | None = None, *,
                no_gaps: bool = False, compute_only: bool = False,
                check_level: int = 0) -> Thm:
    """Check a proof against the current theory."""
    return thy.check_proof(
        prf, rpt, no_gaps=no_gaps, compute_only=compute_only, check_level=check_level)


#: Global store of macros. Keys are macro names, values are macro objects.
#: Availability is determined by this registry and the macro's optional
#: ``limit`` theorem; there is no separate macro extension kind.
global_macros: dict[str, Any] = {}


def has_macro(name: str) -> bool:
    """Return whether a macro exists and its optional limit is available."""
    if name in global_macros:
        macro = global_macros[name]
        return macro.limit is None or thy.has_theorem(macro.limit)
    else:
        return False


def get_macro(name: str) -> Any:
    """Return the macro named ``name``.

    Raises
    ------
    AssertionError
        If the macro does not exist or its limit is not available.
    """
    assert has_macro(name), "get_macro: %s is not available." % name
    return global_macros[name]


def register_macro(name: str) -> Callable[[type], type]:
    """Decorator registering a macro class under ``name``."""
    def decorator(macro_cls: type) -> type:
        assert name not in global_macros, 'register_macro: %s already exists' % name
        global_macros[name] = macro_cls()
        return macro_cls
    return decorator
