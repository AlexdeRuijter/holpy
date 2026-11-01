from __future__ import annotations

import contextlib
import copy
import enum
import logging
from dataclasses import dataclass
from typing import Any, Iterator

from holpy.kernel import report as proof_report
from holpy.kernel import theory
from holpy.kernel.proof import ItemID
from holpy.logic import basic, context
from holpy.server import items, server
from holpy.syntax import printer
from holpy.syntax.settings import global_setting

__all__ = [
    "Level",
    "ProofContext",
    "expand",
    "condense",
    "level_of",
    "oracles",
    "expand_theory",
    "condense_theory",
]

logger = logging.getLogger(__name__)

#: Macros that have no expansion and are kept as-is at every proof level.
ORACLES = frozenset({
    "const_inequality",  # level 0 like the others; missing from the plan's list
    "int_const_ineq",
    "int_eval",
    "integer_simplex",
    "nat_eval",
    "real_compare",
    "real_const_eq",
    "real_const_ineq",
    "real_eq_comparison",
    "real_eval",
    "real_norm",
    "simplex_macro",
    "sympy",
    "z3",
})


class Level(enum.IntEnum):
    """Amount of detail stored in a proof.

    Attributes
    ----------
    MACRO : int
        Macro-level lines, with ``th`` only where checking requires it.
    ANNOTATED : int
        Macro-level lines, with ``th`` on every line.
    PRIMITIVE : int
        Fully expanded lines.  This level is implemented by WS1-B.
    """

    MACRO = 1
    ANNOTATED = 2
    PRIMITIVE = 3


@dataclass
class ProofContext:
    """State needed to parse and check one theorem's proof.

    Parameters
    ----------
    vars : dict, optional
        Variable declarations of the theorem item.  Values may be parsed
        types or the type strings stored in JSON.
    thy : holpy.kernel.theory.Theory, optional
        Theory state loaded up to, but not including, the theorem item.
        When omitted, the caller's current global theory is used.
    """

    vars: dict[str, Any] | None = None
    thy: theory.Theory | None = None


class _CondensedTheory(dict):
    """Result of :func:`condense_theory`.

    It is an ordinary theory dictionary for serialization and comparison.
    The ``guard`` attribute lists theorem names that were kept at
    ``ANNOTATED`` because condensation would have changed checking.
    """

    guard: list[str]

    def __init__(self, *args: Any, guard: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.guard = list(guard or [])


def _as_level(value: Level | int) -> Level:
    """Return *value* as a :class:`Level`, raising ``ValueError`` otherwise."""
    try:
        return Level(value)
    except ValueError:
        raise ValueError(f"unknown proof level: {value!r}") from None


def _check_level(to: Level) -> None:
    """Reject targets that WS1-A does not implement."""
    if to == Level.PRIMITIVE:
        raise NotImplementedError("PRIMITIVE is implemented by WS1-B")


def _check_steps(steps: str) -> None:
    """Validate the ``steps`` argument of the theory functions."""
    if steps not in ("keep", "drop"):
        raise ValueError("steps must be 'keep' or 'drop'")


def _has_th(line: dict) -> bool:
    """Return whether *line* has a non-empty ``th`` value."""
    return line.get("th", "") != ""


def _last_top_level_index(proof: list[dict]) -> int:
    """Return the index of the last line whose id has no dot."""
    last = len(proof) - 1
    for index, line in enumerate(proof):
        if "." not in str(line.get("id", "")):
            last = index
    return last


@contextlib.contextmanager
def _installed(ctx: ProofContext) -> Iterator[None]:
    """Temporarily install the theory and variables of *ctx*."""
    previous_thy = theory.thy
    if ctx.thy is not None:
        theory.thy = ctx.thy
    try:
        with context.fresh_context(vars=ctx.vars or {}):
            yield
    finally:
        theory.thy = previous_thy


def _check_state(proof: list[dict], ctx: ProofContext) -> Any:
    """Parse and check *proof* in *ctx*, returning the checked proof state."""
    with _installed(ctx):
        return server.parse_proof(copy.deepcopy(proof))


def _check(proof: list[dict], ctx: ProofContext) -> tuple[Any, proof_report.ProofReport]:
    """Parse and check *proof* in *ctx*, returning its theorem and report."""
    if not proof:
        return None, proof_report.ProofReport()
    state = _check_state(proof, ctx)
    return state.prf.items[-1].th, state.rpt


def _printed_th(item: Any) -> str:
    """Print a checked proof item's theorem in library notation."""
    with global_setting(unicode=True, highlight=False, line_length=None):
        return printer.print_thm(item.th)


def _fill_missing_th(proof: list[dict], ctx: ProofContext) -> list[dict]:
    """Return a copy of *proof* with missing ``th`` values checked and filled."""
    result = copy.deepcopy(proof)
    if all(_has_th(line) for line in result):
        return result

    with _installed(ctx):
        state = server.parse_proof(copy.deepcopy(proof))
    for line in result:
        if _has_th(line):
            continue
        item = state.prf.find_item(ItemID(line["id"]))
        if item.th is not None:
            line["th"] = _printed_th(item)
    return result


def expand(
    proof: list[dict],
    to: Level = Level.ANNOTATED,
    *,
    ctx: ProofContext,
) -> list[dict]:
    """Return *proof* expanded to at least level *to*.

    Parameters
    ----------
    proof : list of dict
        Proof lines in JSON form.  The input is not modified.
    to : Level, optional
        Requested level.
    ctx : ProofContext
        Variables and theory state for checking.

    Returns
    -------
    list of dict
        A new proof.  At ``ANNOTATED`` every missing ``th`` is filled by
        checking the proof.  At ``MACRO`` the proof is copied unchanged.

    Raises
    ------
    NotImplementedError
        If *to* is ``PRIMITIVE``.
    """
    level = _as_level(to)
    _check_level(level)
    if level == Level.MACRO:
        return copy.deepcopy(proof)
    return _fill_missing_th(proof, ctx)


def condense(
    proof: list[dict],
    to: Level = Level.MACRO,
    *,
    ctx: ProofContext,
) -> list[dict]:
    """Return *proof* condensed to at most level *to*.

    Parameters
    ----------
    proof : list of dict
        Proof lines in JSON form.  The input is not modified.
    to : Level, optional
        Requested level.
    ctx : ProofContext
        Variables and theory state for checking.

    Returns
    -------
    list of dict
        At ``MACRO``, ``th`` is removed from every line except the last
        top-level line, every ``sorry`` line, and lines whose ``th`` is not
        reproduced by checking the proof without it.  If the proof cannot be
        checked after dropping ``th``, it is returned fully annotated.  At
        ``ANNOTATED`` the proof is copied unchanged.

    Raises
    ------
    NotImplementedError
        If *to* is ``PRIMITIVE``.
    """
    level = _as_level(to)
    _check_level(level)
    if level == Level.ANNOTATED:
        return copy.deepcopy(proof)
    result, _, _ = _condense_macro(proof, ctx)
    return result


def _condense_macro(
    proof: list[dict],
    ctx: ProofContext,
) -> tuple[list[dict], bool, tuple[Any, proof_report.ProofReport] | None]:
    """Condense to MACRO and keep ``th`` where it is not recomputable.

    A line keeps ``th`` when it is the last top-level line, when its rule is
    ``sorry``, or when checking the proof without that ``th`` gives a
    different statement for the line.  The last case makes
    ``expand(condense(p, MACRO), ANNOTATED)`` restore the original strings.

    Returns
    -------
    tuple of (list of dict, bool, outcome or None)
        The condensed proof, whether the proof had to be kept fully annotated
        because dropping ``th`` broke checking, and the final check outcome of
        the condensed proof when available.
    """
    if not proof:
        return [], False, (None, proof_report.ProofReport())

    result = copy.deepcopy(proof)
    last = _last_top_level_index(result)
    keep = {
        index
        for index, line in enumerate(result)
        if index == last or line.get("rule") == "sorry"
    }

    for _ in range(len(result) + 1):
        candidate = copy.deepcopy(proof)
        for index, line in enumerate(candidate):
            if index not in keep:
                line.pop("th", None)
        try:
            state = _check_state(candidate, ctx)
        except Exception:
            return copy.deepcopy(proof), True, None

        added = set()
        for index, line in enumerate(proof):
            if index in keep or not _has_th(line):
                continue
            item = state.prf.find_item(ItemID(line["id"]))
            if item.th is None or _printed_th(item) != line["th"]:
                added.add(index)
        if not added:
            return (
                candidate,
                False,
                (state.prf.items[-1].th, state.rpt),
            )
        keep.update(added)

    return copy.deepcopy(proof), True, None


def level_of(proof: list[dict], *, ctx: ProofContext) -> Level:
    """Return the highest supported level at which *proof* is already stored.

    Parameters
    ----------
    proof : list of dict
        Proof lines in JSON form.
    ctx : ProofContext
        Variables and theory state.  The argument is accepted for the common
        proof-level interface and is not needed for the MACRO/ANNOTATED test.

    Returns
    -------
    Level
        ``ANNOTATED`` when every line has a non-empty ``th``, otherwise
        ``MACRO``.
    """
    del ctx
    if all(_has_th(line) for line in proof):
        return Level.ANNOTATED
    return Level.MACRO


def oracles(proof: list[dict]) -> list[tuple[str, str]]:
    """Return ``(line id, rule)`` for every oracle line in *proof*.

    Nested ``subproof`` lists are searched as well as the flat line list used
    by theory JSON.

    Parameters
    ----------
    proof : list of dict
        Proof lines in JSON form.

    Returns
    -------
    list of tuple of str
        Oracle line ids and rule names, in proof order.
    """
    result: list[tuple[str, str]] = []
    for line in proof:
        rule = line.get("rule", "")
        if rule in ORACLES:
            result.append((str(line.get("id", "")), rule))
        children = line.get("subproof")
        if isinstance(children, list):
            result.extend(oracles(children))
    return result


def _load_base_theory(data: dict) -> None:
    """Load the imports of *data* into the global theory."""
    basic.load_metadata()
    name = data.get("name")
    known = basic.theory_cache.get("master", {})
    if name in known:
        basic.load_theory(name, limit="start")
        return

    theory.thy = theory.EmptyTheory()
    imports = data.get("imports", [])
    if imports:
        for prev_name in basic.get_import_order(imports):
            prev_cache = basic.load_theory_cache(prev_name)
            for item in prev_cache["content"]:
                if item.error is None:
                    theory.thy.unchecked_extend(item.get_extension())


def _drop_steps(data: dict) -> None:
    """Remove every theorem item's ``steps`` key from *data*."""
    for item in data.get("content", []):
        item.pop("steps", None)


def expand_theory(
    data: dict,
    to: Level,
    *,
    steps: str = "keep",
) -> dict:
    """Return a copy of theory *data* with every proof expanded to *to*.

    Parameters
    ----------
    data : dict
        Theory JSON data.  The input is not modified.
    to : Level
        Requested proof level.  ``PRIMITIVE`` is not implemented yet.
    steps : {'keep', 'drop'}, optional
        Whether theorem items keep their ``steps`` key.

    Returns
    -------
    dict
        Expanded theory with top-level ``proof_level`` set to the level name.

    Raises
    ------
    NotImplementedError
        If *to* is ``PRIMITIVE``.
    """
    level = _as_level(to)
    _check_level(level)
    _check_steps(steps)

    result = copy.deepcopy(data)
    result["proof_level"] = level.name.lower()
    previous_thy = theory.thy
    try:
        _load_base_theory(result)
        for raw in result.get("content", []):
            item = items.parse_item(raw)
            if item.ty == "thm" and item.proof is not None:
                ctx = ProofContext(vars=item.vars, thy=theory.thy)
                raw["proof"] = expand(item.proof, level, ctx=ctx)
            if item.error is None:
                theory.thy.unchecked_extend(item.get_extension())
    finally:
        theory.thy = previous_thy

    if steps == "drop":
        _drop_steps(result)
    return result


def _guard_reason(
    annotated: list[dict],
    condensed: list[dict],
    ctx: ProofContext,
    *,
    condensed_outcome: tuple[Any, proof_report.ProofReport] | None = None,
) -> str | None:
    """Return why *condensed* must stay at ``ANNOTATED``, or ``None``."""
    try:
        base_thm, base_report = _check(annotated, ctx)
    except Exception as exc:
        return f"annotated check failed: {type(exc).__name__}: {exc}".splitlines()[0]

    if condensed_outcome is None:
        try:
            new_thm, new_report = _check(condensed, ctx)
        except Exception as exc:
            return f"condensed check failed: {type(exc).__name__}: {exc}".splitlines()[0]
    else:
        new_thm, new_report = condensed_outcome

    if (base_thm is None) != (new_thm is None):
        return "condensed proof gives a different theorem"
    if base_thm is not None and base_thm != new_thm:
        return "condensed proof gives a different theorem"
    if base_report.steps and new_report.steps > 1.5 * base_report.steps:
        return (
            f"condensed check uses {new_report.steps} steps, "
            f"annotated uses {base_report.steps}"
        )
    return None


def condense_theory(
    data: dict,
    to: Level,
    *,
    steps: str = "keep",
) -> dict:
    """Return a copy of theory *data* with every proof condensed to *to*.

    At ``MACRO`` each theorem is re-checked.  A theorem whose condensed proof
    fails, gives a different theorem, or uses more than 1.5 times the kernel
    steps of the annotated proof is kept at ``ANNOTATED`` and its name is
    logged and recorded on the result's ``guard`` attribute.

    Parameters
    ----------
    data : dict
        Theory JSON data.  The input is not modified.
    to : Level
        Requested proof level.  ``PRIMITIVE`` is not implemented yet.
    steps : {'keep', 'drop'}, optional
        Whether theorem items keep their ``steps`` key.

    Returns
    -------
    dict
        Condensed theory with top-level ``proof_level`` set to the level name.
        The concrete return value is a ``dict`` subclass with a ``guard``
        attribute listing theorem names kept at ``ANNOTATED``.

    Raises
    ------
    NotImplementedError
        If *to* is ``PRIMITIVE``.
    """
    level = _as_level(to)
    _check_level(level)
    _check_steps(steps)

    result = copy.deepcopy(data)
    result["proof_level"] = level.name.lower()
    guard: list[str] = []
    previous_thy = theory.thy
    try:
        _load_base_theory(result)
        for raw in result.get("content", []):
            item = items.parse_item(raw)
            if item.ty == "thm" and item.proof is not None:
                ctx = ProofContext(vars=item.vars, thy=theory.thy)
                if level == Level.MACRO:
                    annotated = expand(item.proof, Level.ANNOTATED, ctx=ctx)
                    condensed, forced, condensed_outcome = _condense_macro(
                        annotated, ctx
                    )
                    reason = (
                        "proof cannot be checked without intermediate th"
                        if forced
                        else _guard_reason(
                            annotated,
                            condensed,
                            ctx,
                            condensed_outcome=condensed_outcome,
                        )
                    )
                    if reason is None:
                        raw["proof"] = condensed
                    else:
                        raw["proof"] = annotated
                        guard.append(item.name)
                        logger.warning(
                            "Keeping theorem %s at ANNOTATED: %s", item.name, reason
                        )
                else:
                    raw["proof"] = condense(item.proof, level, ctx=ctx)
            if item.error is None:
                theory.thy.unchecked_extend(item.get_extension())
    finally:
        theory.thy = previous_thy

    if steps == "drop":
        _drop_steps(result)
    return _CondensedTheory(result, guard=guard)
