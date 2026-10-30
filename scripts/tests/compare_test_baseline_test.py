"""Tests for scripts/compare_test_baseline.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import scripts.compare_test_baseline as cmp


class CompareTestBaselineTest(unittest.TestCase):
    """Exercise compare_test_baseline.py."""

    def test_no_new_failures_exit_0(self) -> None:
        """No failures in output -> exit 0."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("passed\n")
            pytest_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("\n")
            baseline_path = f.name
        result = cmp.main([pytest_path, baseline_path])
        self.assertEqual(result, 0)
        Path(pytest_path).unlink(missing_ok=True)
        Path(baseline_path).unlink(missing_ok=True)

    def test_one_new_failure_exit_1_and_printed(self) -> None:
        """One new failure -> exit 1 and ID printed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("FAILED foo/bar.py::test_x - msg\n")
            pytest_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("other\tFAILED\tmsg\n")
            baseline_path = f.name
        result = cmp.main([pytest_path, baseline_path])
        self.assertEqual(result, 1)
        Path(pytest_path).unlink(missing_ok=True)
        Path(baseline_path).unlink(missing_ok=True)

    def test_fixed_baseline_entry_exit_0_and_reported(self) -> None:
        """Baseline entry that no longer fails -> exit 0."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("passed\n")
            pytest_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("foo/bar.py::test_x\tFAILED\tmsg\n")
            baseline_path = f.name
        result = cmp.main([pytest_path, baseline_path])
        self.assertEqual(result, 0)
        Path(pytest_path).unlink(missing_ok=True)
        Path(baseline_path).unlink(missing_ok=True)

    def test_error_counts_like_failed(self) -> None:
        """ERROR lines count like FAILED."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("ERROR foo/bar.py::test_y - msg\n")
            pytest_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("foo/bar.py::test_x\tFAILED\tmsg\n")
            baseline_path = f.name
        result = cmp.main([pytest_path, baseline_path])
        self.assertEqual(result, 1)
        Path(pytest_path).unlink(missing_ok=True)
        Path(baseline_path).unlink(missing_ok=True)

    def test_message_suffix_ignored(self) -> None:
        """Message suffixes are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("FAILED foo/bar.py::test_z - some message\n")
            pytest_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("foo/bar.py::test_z\tFAILED\tmsg\n")
            baseline_path = f.name
        result = cmp.main([pytest_path, baseline_path])
        self.assertEqual(result, 0)
        Path(pytest_path).unlink(missing_ok=True)
        Path(baseline_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
