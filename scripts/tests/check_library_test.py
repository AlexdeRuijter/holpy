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


if __name__ == "__main__":
    unittest.main()


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
