"""Z3 queries of realderivative.lhospital, one probe per call (for z3 version/seed sweeps).

    PYTHONPATH=. python docs/triage/lhospital_probe.py STEP|all SEED [--warm] [--timeout S]

Prints `step result seconds` per Z3 step (through holpy.prover.z3wrapper.solve, proof mode
off).  SEED -1 keeps the default.  Run each seed in a fresh process.
"""
import argparse, json, sys, time
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
THEORY, THEOREM = "realderivative", "lhospital"


def _content() -> list[dict[str, Any]]:
    """Return the raw JSON content list for the theory."""
    path = REPO_ROOT / "holpy" / "library" / f"{THEORY}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)["content"]

def _parse_state(raw: dict[str, Any]) -> Any:
    """Parse a stored proof without checking it.

    ``holpy.server.server.parse_proof`` ends with a full ``check_proof``, which
    would execute the very Z3 query this script wants to time.  The proof items
    already contain their expected statements, so parse them and insert them
    without evaluating any macro.  This is only used to recover the target
    query and the earlier steps of the same proof; the checker mode replays the
    real checker instead.
    """
    from holpy.kernel.proof import Proof
    from holpy.kernel.term import Var
    from holpy.logic import basic, context
    from holpy.server import items
    from holpy.server.method import ProofState
    from holpy.syntax import parser

    basic.load_theory(THEORY)
    thm = items.Theorem()
    thm.parse(raw)
    context.set_context(None, vars=thm.vars)

    state = ProofState()
    for nm, T in context.ctxt.vars.items():
        state.vars.append(Var(nm, T))
    state.prf = Proof()
    for line in raw["proof"]:
        if line["rule"] == "variable":
            nm, str_T = line["args"].split(",", 1)
            context.ctxt.vars[nm] = parser.parse_type(str_T.strip())
        state.prf.insert_item(parser.parse_proof_rule(line))
    return state

def _z3_items(prf: Any) -> Iterator[Any]:
    """Yield the Z3 proof items in proof order, including nested subproofs."""
    for item in prf.items:
        if item.rule == "z3":
            yield item
        if item.subproof is not None:
            yield from _z3_items(item.subproof)

def _query(item: Any, state: Any) -> Any:
    """Build the implication that ``Z3Macro.eval`` passes to ``solve``."""
    from holpy.logic import logic

    assms = [state.prf.find_item(prev).th.prop for prev in item.prevs]
    goal = item.args if item.args is not None else item.th.prop
    return logic.Implies(*(assms + [goal]))

def _queries(raw: dict[str, Any]) -> list[tuple[str, Any]]:
    """Return ``(id, query)`` for every Z3 step in one stored proof."""
    if not raw.get("proof"):
        return []
    state = _parse_state(raw)
    return [(str(item.id), _query(item, state)) for item in _z3_items(state.prf)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step"); ap.add_argument("seed", type=int)
    ap.add_argument("--warm", action="store_true"); ap.add_argument("--timeout", type=float, default=20)
    a = ap.parse_args()
    sys.path.insert(0, str(REPO_ROOT))
    raw = [r for r in _content() if isinstance(r, dict) and r.get("name") == THEOREM][0]
    queries = _queries(raw)
    import z3
    from holpy.prover import z3wrapper
    from holpy.syntax import parser
    z3.set_param("timeout", int(a.timeout * 1000))
    if a.seed >= 0:
        z3.set_param("smt.random_seed", a.seed)
    if a.warm:
        z3wrapper.solve(parser.parse_term("(1::nat) < 2"))
    for i, q in queries:
        if a.step in ("all", i):
            t = time.time()
            r = z3wrapper.solve(q)
            print(i, r, round(time.time() - t, 2), flush=True)


if __name__ == "__main__":
    main()
