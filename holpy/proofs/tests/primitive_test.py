from __future__ import annotations

import contextlib
import copy
import json
import os
import unittest
from typing import Iterator

from holpy.kernel import theory
from holpy.logic import basic, context
from holpy.proofs import (
    Level,
    ProofContext,
    condense,
    condense_theory,
    expand,
    expand_theory,
    level_of,
    oracles,
)
from holpy.proofs.levels import ORACLES, _has_th, _is_expandable_macro
from holpy.server import items, server

# The printed expansion of these theorems does not parse back with today's
# printer: type variables in ``theorem`` statements and fresh bound variables
# are printed without enough type information.  WS1-B must not work around
# this by weakening the printer settings, so the level properties run on the
# rest and this list is asserted exactly.
_LOGIC_ROUNDTRIP_FAILURES = {
    "ex_conj_distrib",
    "right_or_exists_thm",
    "left_imp_exists_thm",
    "left_imp_forall_thm",
    "left_exists_imp_thm",
    "right_exists_imp_thm",
    "drinker",
    "test",
    "quant_intro_forall",
    "quant_intro_exists",
    "skolem_thm",
    "skolem_thm_gen",
    "eq_imp_false",
    "eq_mean_true",
}

# The successful nat proofs, chosen to cover every macro used in nat that can
# currently be printed back.  add_0_right is the fixed twentieth sample and is
# a known round-trip failure; it makes the regression visible in the test.
_NAT_SAMPLE = [
    "one_Suc",
    "bit0_Suc",
    "nat_const_ineq_test1",
    "le_suc",
    "lt_suc",
    "le_mult_rcancel",
    "lt_mult_rcancel",
    "not_even",
    "not_odd",
    "even_or_odd",
    "even_and_odd",
    "odd_mult",
    "odd_double",
    "fact_le",
    "mod_uniq",
    "div_uniq",
    "even_mod_even",
    "odd_mod_even",
    "mod_mult_mod2",
    "add_0_right",
]
_NAT_SAMPLE_FAILURES = {"add_0_right"}


def _outcome(proof: list[dict], ctx: ProofContext) -> tuple:
    """Return ``("ok", theorem)`` or ``("fail", exception type)``."""
    previous_thy = theory.thy
    if ctx.thy is not None:
        theory.thy = ctx.thy
    try:
        with context.fresh_context(vars=ctx.vars or {}):
            state = server.parse_proof(copy.deepcopy(proof))
        return ("ok", state.prf.items[-1].th)
    except Exception as exc:
        return ("fail", type(exc))
    finally:
        theory.thy = previous_thy


@contextlib.contextmanager
def _without_non_oracle_macros() -> Iterator[None]:
    """Temporarily remove macros that must be expanded at PRIMITIVE."""
    saved = dict(theory.global_macros)
    try:
        for name in list(theory.global_macros):
            if name not in ORACLES:
                del theory.global_macros[name]
        yield
    finally:
        theory.global_macros.clear()
        theory.global_macros.update(saved)


class PrimitiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = {}
        for name in ("logic", "nat"):
            with open(f"holpy/library/{name}.json", encoding="utf-8") as f:
                cls.data[name] = json.load(f)

    def _theorems(self, theory_name: str, names: set[str] | None = None) -> Iterator:
        """Yield parsed theorem items of *theory_name* in order."""
        basic.load_theory(theory_name, limit="start")
        for raw in self.data[theory_name]["content"]:
            item = items.parse_item(raw)
            if (
                item.ty == "thm"
                and item.proof is not None
                and (names is None or item.name in names)
            ):
                yield item
            if item.error is None:
                theory.thy.unchecked_extend(item.get_extension())

    def _assert_primitive_properties(
        self,
        label: str,
        proof: list[dict],
        ctx: ProofContext,
        base_outcome: tuple,
    ) -> None:
        """Run P1-P6 for one proof that can be printed back at PRIMITIVE."""
        snapshot = copy.deepcopy(proof)
        current = level_of(proof, ctx=ctx)
        expanded = expand(proof, Level.PRIMITIVE, ctx=ctx)
        self.assertEqual(proof, snapshot, f"{label}: expand modified its input")

        # The output is primitive and every line carries a statement.
        self.assertFalse(
            any(_is_expandable_macro(str(line.get("rule", ""))) for line in expanded),
            f"{label}: an expandable macro line remains",
        )
        self.assertTrue(
            all(_has_th(line) for line in expanded),
            f"{label}: a PRIMITIVE line has no th",
        )
        self.assertEqual(level_of(expanded, ctx=ctx), Level.PRIMITIVE)

        # P1: expansion is idempotent.
        self.assertEqual(
            expand(expanded, Level.PRIMITIVE, ctx=ctx),
            expanded,
            f"{label}: expand not idempotent at PRIMITIVE",
        )

        # P2: an already primitive proof is left alone.
        if current >= Level.PRIMITIVE:
            self.assertEqual(expand(proof, Level.PRIMITIVE, ctx=ctx), proof)

        # P3: condensing the expansion restores the original macro proof.
        macro = condense(proof, Level.MACRO, ctx=ctx)
        self.assertEqual(
            condense(expanded, Level.MACRO, ctx=ctx),
            macro,
            f"{label}: condense(expand(p)) differs from condense(p)",
        )
        annotated = condense(expanded, Level.ANNOTATED, ctx=ctx)
        self.assertEqual(
            condense(annotated, Level.ANNOTATED, ctx=ctx),
            annotated,
            f"{label}: condense not idempotent at ANNOTATED",
        )
        self.assertEqual(
            condense(annotated, Level.MACRO, ctx=ctx),
            macro,
            f"{label}: condense to MACRO did not collapse the expansion",
        )

        # P4 and P6: the expanded proof checks the same theorem with macros
        # present and with every non-oracle macro unregistered.
        self.assertEqual(
            _outcome(expanded, ctx),
            base_outcome,
            f"{label}: check result changed at PRIMITIVE",
        )
        with _without_non_oracle_macros():
            self.assertEqual(
                _outcome(expanded, ctx),
                base_outcome,
                f"{label}: PRIMITIVE proof needs a non-oracle macro",
            )

    def test_logic_all_theorems(self) -> None:
        """Run P1-P6 on every logic proof whose expansion prints back."""
        failures = set()
        checked = 0
        for item in self._theorems("logic"):
            ctx = ProofContext(vars=item.vars, thy=theory.thy)
            expanded = expand(item.proof, Level.PRIMITIVE, ctx=ctx)
            outcome = _outcome(expanded, ctx)
            if outcome[0] != "ok":
                failures.add(item.name)
                continue
            base = _outcome(item.proof, ctx)
            self._assert_primitive_properties(
                f"logic.{item.name}", item.proof, ctx, base
            )
            checked += 1
        self.assertEqual(failures, _LOGIC_ROUNDTRIP_FAILURES)
        self.assertGreater(checked, 0)

    def test_nat_fixed_sample(self) -> None:
        """Run P1-P6 on the fixed nat sample, including known failures."""
        names = set(_NAT_SAMPLE)
        found = set()
        checked = 0
        for item in self._theorems("nat", names):
            ctx = ProofContext(vars=item.vars, thy=theory.thy)
            expanded = expand(item.proof, Level.PRIMITIVE, ctx=ctx)
            outcome = _outcome(expanded, ctx)
            if outcome[0] != "ok":
                found.add(item.name)
                continue
            base = _outcome(item.proof, ctx)
            self._assert_primitive_properties(
                f"nat.{item.name}", item.proof, ctx, base
            )
            checked += 1
        self.assertEqual(found, _NAT_SAMPLE_FAILURES)
        self.assertEqual(checked, len(_NAT_SAMPLE) - len(_NAT_SAMPLE_FAILURES))

    @unittest.skipUnless(
        os.environ.get("HOLPY_LEVELS_FULL") == "1",
        "set HOLPY_LEVELS_FULL=1 for the full nat expansion run",
    )
    def test_nat_full_expansion(self) -> None:
        """Expand every nat proof and run the properties on those that parse."""
        checked = 0
        failed = []
        for item in self._theorems("nat"):
            ctx = ProofContext(vars=item.vars, thy=theory.thy)
            try:
                expanded = expand(item.proof, Level.PRIMITIVE, ctx=ctx)
            except Exception:
                # nat_MAX and div_le already fail checking in the library
                # (a line cites itself), before any expansion can happen.
                failed.append(item.name)
                continue
            outcome = _outcome(expanded, ctx)
            if outcome[0] != "ok":
                failed.append(item.name)
                continue
            base = _outcome(item.proof, ctx)
            self._assert_primitive_properties(
                f"nat.{item.name}", item.proof, ctx, base
            )
            checked += 1
        self.assertGreater(checked, 0)
        self.assertEqual(checked + len(failed), 218)

    def test_z3_line_survives_and_is_reported(self) -> None:
        names = {"not_all"}
        item = next(iter(self._theorems("logic", names)))
        ctx = ProofContext(vars=item.vars, thy=theory.thy)
        original_z3 = [
            line for line in item.proof if line.get("rule") == "z3"
        ]
        self.assertTrue(original_z3)
        expanded = expand(item.proof, Level.PRIMITIVE, ctx=ctx)
        expanded_z3 = [
            line for line in expanded if line.get("rule") == "z3"
        ]
        self.assertEqual(expanded_z3, original_z3)
        self.assertEqual(
            oracles(expanded),
            [(str(line["id"]), "z3") for line in original_z3],
        )
        self.assertEqual(_outcome(expanded, ctx)[0], "ok")

    def test_theory_functions_support_primitive(self) -> None:
        data = copy.deepcopy(self.data["logic"])
        snapshot = copy.deepcopy(data)
        expanded = expand_theory(data, Level.PRIMITIVE)
        self.assertEqual(data, snapshot, "expand_theory modified its input")
        self.assertEqual(expanded["proof_level"], "primitive")
        expanded_items = {
            item["name"]: item
            for item in expanded["content"]
            if item.get("ty") == "thm" and item.get("proof")
        }
        original_items = {
            item["name"]: item
            for item in data["content"]
            if item.get("ty") == "thm" and item.get("proof")
        }
        for name in ("not_all", "conj_comm"):
            self.assertEqual(
                expanded_items[name]["proof"],
                expand(
                    original_items[name]["proof"],
                    Level.PRIMITIVE,
                    ctx=self._ctx_for("logic", name),
                ),
            )

        # Condensing at PRIMITIVE only removes what the target does not need,
        # so an already primitive proof is unchanged.
        primitive = {
            "name": "primitive_empty",
            "imports": ["logic"],
            "content": [],
            "proof_level": "primitive",
        }
        self.assertEqual(
            condense_theory(primitive, Level.PRIMITIVE)["proof_level"],
            "primitive",
        )
        self.assertEqual(
            condense_theory(primitive, Level.PRIMITIVE)["content"], []
        )

    def _ctx_for(self, theory_name: str, theorem_name: str) -> ProofContext:
        for item in self._theorems(theory_name, {theorem_name}):
            return ProofContext(vars=item.vars, thy=theory.thy)
        raise AssertionError(f"theorem not found: {theorem_name}")


if __name__ == "__main__":
    unittest.main()
