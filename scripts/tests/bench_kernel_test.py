"""Tests for scripts/bench_kernel.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "bench_kernel.py"


class BenchKernelTest(unittest.TestCase):
    """Exercise the check-phase benchmark through its command-line interface."""

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the benchmark in a subprocess with the checkout importable."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_logic_repeat_one_prints_table_and_json(self) -> None:
        """Logic with one repetition prints the environment and result table."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bench.json"
            result = self.run_script(
                "logic", "--repeat", "1", "--json", str(out)
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            output = result.stdout
            self.assertIn("Python:", output)
            self.assertIn("z3:", output)
            self.assertIn("holpy commit:", output)
            self.assertIn("theory", output)
            self.assertIn("total", output)

            rows = [
                line.split()
                for line in output.splitlines()
                if line.strip()
            ]
            logic_rows = [row for row in rows if row and row[0] == "logic"]
            total_rows = [row for row in rows if row and row[0] == "total"]
            self.assertEqual(len(logic_rows), 1, output)
            self.assertEqual(len(total_rows), 1, output)
            self.assertEqual(len(logic_rows[0]), 5, logic_rows[0])
            self.assertEqual(len(total_rows[0]), 5, total_rows[0])

            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["repeat"], 1)
            self.assertIn("logic", data["theories"])
            self.assertGreater(data["theories"]["logic"]["proofs"], 0)
            self.assertEqual(
                data["total"]["proofs"],
                data["theories"]["logic"]["proofs"],
            )

            logic = data["theories"]["logic"]
            self.assertEqual(int(logic_rows[0][1]), logic["proofs"])
            self.assertEqual(int(logic_rows[0][2]), logic["failures"])
            self.assertAlmostEqual(
                float(logic_rows[0][3]), logic["cpu_total_seconds"], places=3
            )
            self.assertAlmostEqual(
                float(logic_rows[0][4]), logic["cpu_mean_seconds"], places=3
            )
            self.assertEqual(
                data["total"]["cpu_total_seconds"],
                logic["cpu_total_seconds"],
            )


if __name__ == "__main__":
    unittest.main()
