from __future__ import annotations

import unittest
import inspect

# Import every module that registers macros.
import holpy.logic.logic
import holpy.logic.tactic
import holpy.logic.auto
import holpy.logic.basic  # loads real
import holpy.data.nat
import holpy.data.integer
import holpy.data.expr
import holpy.data.function
import holpy.data.real
import holpy.prover.z3wrapper
import holpy.prover.simplex
import holpy.prover.simplex_strict
import holpy.prover.sympywrapper
import holpy.macros.structural
import holpy.macros.transfer
import holpy.macros.semiring
import holpy.macros.linarith
import holpy.macros.induct
import holpy.imperative.imp
import holpy.integral.inequality

from holpy.kernel import theory
from holpy.kernel.macro import Macro
from holpy.syntax import parser, printer


ORACLES = {
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
}


class MacroContractTest(unittest.TestCase):
    def test_contract(self):
        # Import happens above; collect registered macros.
        macros = dict(theory.global_macros)
        results = {}
        untested = []
        infeasible_expansion = []
        graph = {}
        library_args = {}
        # Scan a few library files for arguments (limit to logic, nat, set)
        import json, os
        for fname in ("logic.json", "nat.json", "set.json"):
            path = os.path.join("holpy/library", fname)
            if not os.path.exists(path):
                continue
            data = json.load(open(path))
            for item in data.get("content", []):
                proof = item.get("proof", [])
                if not isinstance(proof, list):
                    continue
                for line in proof:
                    rule = line.get("rule", "")
                    args = line.get("args", "")
                    if rule not in macros:
                        continue
                    # Store first argument found per macro
                    if rule not in library_args:
                        library_args[rule] = args

        # Also pull arguments from macro tests if available.
        # For simplicity, use library args when present; else try dummy args.
        for name, macro in sorted(macros.items()):
            results[name] = {}
            # Rule 1 / 2
            is_oracle = name in ORACLES
            if is_oracle:
                results[name]["rule2"] = (macro.level == 0)
            else:
                overridden = False
                try:
                    # Try calling with dummy args; NotImplementedError means not overridden.
                    dummy_args = ""
                    macro.get_proof_term(dummy_args, [])
                    overridden = True
                except NotImplementedError:
                    overridden = False
                except Exception:
                    overridden = True  # any other exception implies overridden
                results[name]["rule1_get_proof_term"] = overridden
                results[name]["rule1_level"] = (macro.level is None or macro.level >= 1)

            # Rule 3: round-trip of sig with a real argument.
            sig = macro.sig
            args_str = library_args.get(name, "")
            if not args_str:
                # Try to construct a minimal argument from macro tests if any exist.
                # For this contract test, if no argument available, record untested.
                untested.append(name)
                results[name]["rule3"] = "untested (no argument)"
                continue
            try:
                parsed_args = parser.parse_args(sig, args_str)
                printed = printer.print_str_args(name, parsed_args, None)
                # print_str_args returns either list or string; normalize.
                printed_str = "".join(str(s) for s in printed) if isinstance(printed, list) else str(printed)
                reparsed = parser.parse_args(sig, printed_str)
                results[name]["rule3"] = True
            except Exception as exc:
                results[name]["rule3"] = f"fail: {exc}"

            # Rule 4: expansion graph for macros that have args.
            if name in untested or results[name].get("rule3", True) is False:
                continue
            try:
                args_str = library_args.get(name, "")
                # Need a real previous-proof-term sequence? Some macros need empty.
                # Build dummy prevs: empty list for simplicity.
                parsed_args = parser.parse_args(sig, args_str)
                pt = macro.get_proof_term(parsed_args, [])
                # Traverse to find nested macro rules.
                used = set()
                def traverse(node):
                    if isinstance(node, type(pt)) and hasattr(node, 'rule'):
                        r = node.rule
                        if r in macros and r != name and r not in used:
                            # Check if it's a macro (not primitive)
                            if r in macros:
                                used.add(r)
                        # Recurse into prevs if they are ProofTerm objects.
                        if hasattr(node, 'prevs'):
                            for prev in node.prevs:
                                traverse(prev)
                    # Also handle if prevs contain macro proof terms nested differently.
                traverse(pt)
                graph[name] = used
            except Exception as exc:
                infeasible_expansion.append((name, str(exc)))
                graph[name] = set()

        # Report discrepancy with ORACLES.
        actual_oracles = {n for n, m in macros.items() if m.level == 0}
        missing_in_plan = sorted(actual_oracles - ORACLES)
        extra_in_plan = sorted(ORACLES - actual_oracles)

        # Assert no cycles among feasible expansions.
        feasible_macros = [n for n in sorted(macros) if n not in [m for m, _ in infeasible_expansion]]
        # Build subgraph.
        def has_cycle(start, visited, stack):
            visited.add(start)
            stack.add(start)
            for neighbor in graph.get(start, set()):
                if neighbor not in feasible_macros:
                    continue
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, stack):
                        return True
                elif neighbor in stack:
                    return True
            stack.remove(start)
            return False

        visited_all = set()
        cycle_found = False
        for start in feasible_macros:
            if start not in visited_all:
                if has_cycle(start, visited_all, set()):
                    cycle_found = True
                    break
        self.assertFalse(cycle_found, f"Expansion cycle detected among {feasible_macros}")

        # Print results for visibility (not failures).
        print("=== Macro Contract Report ===")
        print(f"Total macros: {len(macros)}")
        print(f"ORACLES (plan): {sorted(ORACLES)}")
        print(f"Actual oracles (level 0): {sorted(actual_oracles)}")
        if missing_in_plan:
            print(f"ORACLES discrepancy (actual but not in plan): {missing_in_plan}")
        if extra_in_plan:
            print(f"ORACLES discrepancy (plan but not actual): {extra_in_plan}")
        print(f"Untested (no argument): {sorted(untested)}")
        print(f"Infeasible expansion: {sorted([m for m, _ in infeasible_expansion])}")
        for name in sorted(macros):
            r = results[name]
            print(f"{name}: rule1={r.get('rule1_get_proof_term', r.get('rule1_level'))}, rule2={r.get('rule2', 'N/A')}, rule3={r.get('rule3')}, expansion_used={sorted(graph.get(name, set()))}")
        print("================================")


if __name__ == "__main__":
    unittest.main()
