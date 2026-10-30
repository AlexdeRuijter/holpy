#!/usr/bin/env python
"""Compare pytest output against a test baseline."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Sequence

logger = logging.getLogger("compare_test_baseline")

FAILED_PATTERN = re.compile(r"^(FAILED|ERROR)\s+(.+?)(?:\s+-.*)?$")


def parse_pytest_ids(text: str) -> set[str]:
    """Parse test IDs from pytest `-rfE` short summary lines.

    Parameters
    ----------
    text : str
        Pytest output text.

    Returns
    -------
    set[str]
        The set of failing or error test IDs.
    """
    ids: set[str] = set()
    for line in text.splitlines():
        match = FAILED_PATTERN.match(line.strip())
        if match:
            ids.add(match.group(2).strip())
    return ids


def read_baseline(path: Path) -> set[str]:
    """Read the baseline file.

    The file is tab-separated; the first column is the test ID.

    Parameters
    ----------
    path : pathlib.Path
        Path to the baseline file.

    Returns
    -------
    set[str]
        Baseline IDs.
    """
    baseline: set[str] = set()
    if not path.exists():
        return baseline
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if parts:
            baseline.add(parts[0].strip())
    return baseline


def main(argv: Sequence[str] | None = None) -> int:
    """Run the comparison.

    Parameters
    ----------
    argv : sequence of str, optional
        Command-line arguments.

    Returns
    -------
    int
        1 if there are new failures, else 0.
    """
    parser = argparse.ArgumentParser(
        description="Compare pytest output against a test baseline."
    )
    parser.add_argument("pytest_output", type=Path, help="pytest output file")
    parser.add_argument(
        "baseline", type=Path, help="baseline TSV file"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    current = parse_pytest_ids(args.pytest_output.read_text(encoding="utf-8"))
    baseline = read_baseline(args.baseline)

    new_failures = current - baseline
    fixed = baseline - current

    for fail_id in sorted(new_failures):
        logger.info("NEW failure: %s", fail_id)
    for fixed_id in sorted(fixed):
        logger.info("fixed, remove from the baseline: %s", fixed_id)

    return 1 if new_failures else 0


if __name__ == "__main__":
    sys.exit(main())
