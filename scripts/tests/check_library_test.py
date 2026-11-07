"""Tests for scripts/check_library.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import scripts.check_library as check_library
from holpy.logic import context
from holpy.server import server

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_library.py"
LIBRARY_DIR = REPO_ROOT / "holpy" / "library"
HEADER = "theory\tname\tstatus\terror_type\tstatement\tsteps\tmacros_eval\ttime\n"


class CheckLibraryTest(unittest.TestCase):
    """Exercise the library checker through its command-line interface."""

    def run_script(
        self,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run the checker in a subprocess with the checkout importable."""
        full_env = os.environ.copy()
        full_env["PYTHONPATH"] = str(REPO_ROOT)
        if env:
            full_env.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            env=full_env,
            capture_output=True,
            text=True,
            check=False,
        )

    def read_rows(self, path: Path) -> list[dict[str, str]]:
        """Read a TSV written by the checker into a list of row dictionaries."""
        lines = path.read_text(encoding="utf-8").splitlines()
        header = lines[0].split("\t")
        return [dict(zip(header, line.split("\t"))) for line in lines[1:]]

    def test_logic_has_42_ok_3_gaps_and_no_failures(self) -> None:
        """Checking logic gives 42 ok, 3 gaps, no fail."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "logic.tsv"
            result = self.run_script(
                "logic",
                "--out",
                str(out),
                env={"HOLPY_LIBRARY_DIR": str(LIBRARY_DIR)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = self.read_rows(out)
            self.assertEqual(sum(row["status"] == "ok" for row in rows), 42)
            self.assertEqual(sum(row["status"] == "gaps" for row in rows), 3)
            gaps = sorted([row["name"] for row in rows if row["status"] == "gaps"])
            self.assertEqual(gaps, ["de_morgan_thm1", "imply_neg", "not_imp"])
            self.assertEqual(
                [row["name"] for row in rows if row["status"] == "fail"],
                [],
            )
            self.assertTrue(all(row["theory"] == "logic" for row in rows))

    def test_corrupted_th_marks_only_that_theorem_failed_with_41_ok_3_gaps(self) -> None:
        """A bad th fails exactly its theorem; others are 41 ok, 3 gaps."""
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / "library"
            library.mkdir()
            for name in ("logic", "logic_base"):
                shutil.copy2(LIBRARY_DIR / f"{name}.json", library / f"{name}.json")

            logic_path = library / "logic.json"
            data: dict[str, Any] = json.loads(logic_path.read_text(encoding="utf-8"))
            corrupted = "conj_comm"
            for raw in data["content"]:
                if raw.get("ty") == "thm" and raw.get("name") == corrupted:
                    raw["proof"][-1]["th"] = "⊢ A"
                    break
            else:
                self.fail(f"{corrupted} not found in logic.json")
            logic_path.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )

            out = Path(tmp) / "corrupted.tsv"
            result = self.run_script(
                "logic",
                "--out",
                str(out),
                env={"HOLPY_LIBRARY_DIR": str(library)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = self.read_rows(out)
            failed = [row["name"] for row in rows if row["status"] == "fail"]
            self.assertEqual(failed, [corrupted])
            self.assertEqual(sum(row["status"] == "ok" for row in rows), 41)
            self.assertEqual(sum(row["status"] == "gaps" for row in rows), 3)

    def test_compare_self_and_changed_status(self) -> None:
        """Compare exits 0 for identical files and 1 for an ok-to-fail change."""
        fields = (
            HEADER
            + "logic\tconj_comm\tok\t\tA ∧ B ⟷ B ∧ A\t31\t\t0.01\n"
        )
        changed = fields.replace(
            "logic\tconj_comm\tok\t", "logic\tconj_comm\tfail\tCheckProofException"
        )

        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "old.tsv"
            same = Path(tmp) / "same.tsv"
            new = Path(tmp) / "new.tsv"
            old.write_text(fields, encoding="utf-8")
            same.write_text(fields, encoding="utf-8")
            new.write_text(changed, encoding="utf-8")

            identical = self.run_script("--compare", str(old), str(same))
            self.assertEqual(identical.returncode, 0, identical.stdout + identical.stderr)
            self.assertIn("No differences", identical.stdout)

            worse = self.run_script("--compare", str(old), str(new))
            output = worse.stdout + worse.stderr
            self.assertEqual(worse.returncode, 1, output)
            self.assertIn("logic.conj_comm", output)

            allow = Path(tmp) / "allow.txt"
            allow.write_text("# brittle\nlogic.conj_comm  # reason\n", encoding="utf-8")
            tolerated = self.run_script(
                "--compare", str(old), str(new), "--allow-degraded", str(allow)
            )
            self.assertEqual(tolerated.returncode, 0, tolerated.stdout + tolerated.stderr)
            self.assertIn("allowed", tolerated.stdout + tolerated.stderr)


class ParseProofCheckTest(unittest.TestCase):
    """parse_proof can skip its check, and still checks by default."""

    def proof_data(self) -> list[dict[str, Any]]:
        """Return a small stored proof that parses without a theory search."""
        return [
            {'id': 0, 'rule': 'assume', 'args': 'A & B', 'prevs': [], 'th': ''},
            {
                'id': 1,
                'rule': 'sorry',
                'args': '',
                'prevs': [],
                'th': 'A & B |- B & A',
            },
            {
                'id': 2,
                'rule': 'implies_intr',
                'args': 'A & B',
                'prevs': [1],
                'th': '',
            },
        ]

    def test_check_false_does_not_call_check_proof(self) -> None:
        """check=False returns the parsed state without checking it."""
        context.set_context('logic_base', vars={'A': 'bool', 'B': 'bool'})
        with mock.patch.object(
            server.ProofState, "check_proof", autospec=True
        ) as check:
            state = server.parse_proof(self.proof_data(), check=False)
        check.assert_not_called()
        self.assertEqual(len(state.vars), 2)
        self.assertEqual(len(state.prf.items), 3)

    def test_default_still_calls_check_proof(self) -> None:
        """Without check=False, parse_proof checks the parsed proof."""
        context.set_context('logic_base', vars={'A': 'bool', 'B': 'bool'})
        with mock.patch.object(
            server.ProofState, "check_proof", autospec=True
        ) as check:
            state = server.parse_proof(self.proof_data())
        check.assert_called_once()
        self.assertIs(check.call_args.args[0], state)


class JobsDefaultTest(unittest.TestCase):
    """The checker uses the available cores by default."""

    def test_jobs_defaults_to_cpu_count_minus_one(self) -> None:
        """--jobs defaults to max(1, cpu_count - 1)."""
        parser = check_library.build_parser()
        expected = max(1, (os.cpu_count() or 2) - 1)
        self.assertEqual(parser.get_default("jobs"), expected)

    def test_jobs_default_tracks_the_cpu_count(self) -> None:
        """An eight-core machine gets seven workers, not the old default one."""
        with mock.patch(
            "scripts.check_library.os.cpu_count", return_value=8
        ):
            parser = check_library.build_parser()
        self.assertEqual(parser.get_default("jobs"), 7)


class Z3TimeoutOptionTest(unittest.TestCase):
    """The checker bounds Z3 calls so that one undecided query cannot hang a run."""

    def test_option_is_documented_with_a_finite_default(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--z3-timeout", result.stdout)
        self.assertIn("default: 60", result.stdout)


if __name__ == "__main__":
    unittest.main()
