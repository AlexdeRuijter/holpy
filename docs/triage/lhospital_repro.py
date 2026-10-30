#!/usr/bin/env python
"""Standalone reproduction of the Z3 query from realderivative.lhospital."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from holpy.logic import basic, context
from holpy.server import items, server
from holpy.prover import z3wrapper
from holpy.logic import logic

basic.load_theory("realderivative")

with open("holpy/library/realderivative.json") as f:
    data = json.load(f)

for raw in data["content"]:
    if isinstance(raw, dict) and raw.get("name") == "lhospital":
        thm = items.Theorem()
        thm.parse(raw)
        context.set_context(None, vars=thm.vars)
        state = server.parse_proof(copy.deepcopy(thm.proof))
        state.check_proof(compute_only=True)

        def traverse(prf, depth=0):
            for item in prf.items:
                if item.rule == "z3":
                    prev_ths = [state.get_proof_item(p).th for p in item.prevs]
                    assms = [prev.prop for prev in prev_ths]
                    goal = item.th.prop
                    query = logic.Implies(*(assms + [goal]))
                    print("=" * 60)
                    print(f"Z3 step id={item.id}")
                    print(f"Premises ({len(assms)}):")
                    for a in assms:
                        print("  ", a)
                    print(f"Goal: {goal}")
                    print(f"Query: {query}")
                    # Try remedies on the hard steps with a 60 s limit
                    import z3
                    z3.set_param("timeout", 60000)
                    remedies = {}
                    try:
                        from holpy.prover.z3wrapper import norm_term
                        simple_goal = norm_term(goal)
                        remedies["norm_term"] = z3wrapper.solve(logic.Implies(*(assms + [simple_goal])))
                    except Exception as e:
                        remedies["norm_term"] = f"error: {e}"
                    print("Remedies (norm_term):", remedies.get("norm_term"))
                    result = z3wrapper.solve(query)
                    print(f"Result (unsat={result}): {result}")
                if item.subproof:
                    traverse(item.subproof, depth + 1)

        traverse(state.prf)
        break
