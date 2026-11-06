#!/usr/bin/env python
"""Benchmark the kernel proof-checking phase for stored library proofs.

The script loads each requested theory, parses every stored proof without
checking it, and then measures only repeated calls to
``theory.thy.check_proof`` with :func:`time.process_time` (user CPU time).
Loading, parsing, and reporting are outside the timed region.

Usage, from the repository root::

    python scripts/bench_kernel.py [THEORY ...] [--repeat N] [--json FILE]

The default theories are ``nat``, ``sums`` and ``logic``.
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

# Running ``python scripts/bench_kernel.py`` puts ``scripts/`` on sys.path,
# not the repository root, so make the checkout importable without relying on
# the caller's PYTHONPATH.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from holpy.kernel import report as proof_report  # noqa: E402
from holpy.kernel import theory  # noqa: E402
from holpy.kernel.proof import Proof  # noqa: E402
from holpy.kernel.term import Var  # noqa: E402
from holpy.logic import basic, context  # noqa: E402
from holpy.server.method import ProofState  # noqa: E402
from holpy.syntax import parser  # noqa: E402

logger = logging.getLogger("bench_kernel")

DEFAULT_THEORIES = ("nat", "sums", "logic")


@dataclass(frozen=True)
class TheoryTiming:
    """CPU timings for one theory.

    Parameters
    ----------
    theory : str
        Theory name.
    proofs : int
        Number of stored proofs checked.
    failures : int
        Number of proofs whose check raised during the first repetition.
    cpu_runs : tuple of float
        User CPU seconds for each repetition.
    """

    theory: str
    proofs: int
    failures: int
    cpu_runs: tuple[float, ...]

    @property
    def cpu_total(self) -> float:
        """Return the user CPU time summed over all repetitions."""
        return round(sum(self.cpu_runs), 3)

    @property
    def cpu_mean(self) -> float:
        """Return the mean user CPU time per repetition."""
        return round(self.cpu_total / len(self.cpu_runs), 3)


def _parse_proof_lines(proof: list[dict[str, Any]]) -> ProofState:
    """Parse stored proof lines without checking the proof.

    This mirrors :func:`holpy.server.server.parse_proof`, except that it omits
    the final ``state.check_proof()`` call: checking is the phase being timed.

    Parameters
    ----------
    proof : list of dict
        Stored proof lines in JSON form.

    Returns
    -------
    holpy.server.method.ProofState
        State containing the parsed proof and the theorem variables.
    """
    state = ProofState()
    for name, T in context.ctxt.vars.items():
        state.vars.append(Var(name, T))
    state.prf = Proof()
    for line in proof:
        if line["rule"] == "variable":
            name, type_text = line["args"].split(",", 1)
            context.ctxt.vars[name] = parser.parse_type(type_text.strip())
        state.prf.insert_item(parser.parse_proof_rule(line))
    return state


def _collect_proofs(theory_name: str) -> list[tuple[str, Proof]]:
    """Load a theory and parse all its stored theorem proofs.

    Parameters
    ----------
    theory_name : str
        Name of the theory to load.

    Returns
    -------
    list of (str, Proof)
        Theorem names and their parsed proofs, in JSON item order.
    """
    basic.load_theory(theory_name)
    cache = basic.load_theory_cache(theory_name)
    proofs: list[tuple[str, Proof]] = []
    for item in cache["content"]:
        if item.ty != "thm" or item.error is not None or item.proof is None:
            continue
        context.set_context(None, vars=item.vars)
        state = _parse_proof_lines(item.proof)
        proofs.append((item.name, state.prf))
    return proofs


def benchmark_theory(
    theory_name: str,
    repeat: int,
    check_level: int = 0,
) -> TheoryTiming:
    """Time the stored proof checks for one theory.

    Parameters
    ----------
    theory_name : str
        Theory to benchmark.
    repeat : int
        Number of times to check all stored proofs.
    check_level : int, optional
        Trust level passed to the kernel's proof checker.

    Returns
    -------
    TheoryTiming
        Proof count, first-run failure count, and CPU time for each repetition.
    """
    proofs = _collect_proofs(theory_name)
    runs: list[float] = []
    first_failures = 0

    for run_index in range(repeat):
        failures = 0
        start = time.process_time()
        for name, proof in proofs:
            try:
                theory.thy.check_proof(
                    proof,
                    rpt=proof_report.ProofReport(),
                    no_gaps=False,
                    check_level=check_level,
                )
            except Exception as exc:  # A failed certificate is data, not a crash.
                failures += 1
                if run_index == 0:
                    logger.debug(
                        "Theorem %s.%s failed: %s", theory_name, name, exc
                    )
        runs.append(round(time.process_time() - start, 3))
        if run_index == 0:
            first_failures = failures
        elif failures != first_failures:
            logger.warning(
                "%s: failure count changed from %d to %d in run %d",
                theory_name,
                first_failures,
                failures,
                run_index + 1,
            )

    return TheoryTiming(
        theory=theory_name,
        proofs=len(proofs),
        failures=first_failures,
        cpu_runs=tuple(runs),
    )


def run_benchmark(
    theory_names: Sequence[str],
    repeat: int,
    check_level: int = 0,
    z3_timeout: int = 0,
) -> list[TheoryTiming]:
    """Benchmark a sequence of theories.

    Parameters
    ----------
    theory_names : sequence of str
        Theories to benchmark, in output order.
    repeat : int
        Number of times to check all stored proofs per theory.
    check_level : int, optional
        Trust level passed to the kernel's proof checker.
    z3_timeout : int, optional
        Per-call Z3 time limit in seconds; ``0`` means no limit.

    Returns
    -------
    list of TheoryTiming
        One result per requested theory.
    """
    if z3_timeout > 0:
        import z3

        z3.set_param("timeout", z3_timeout * 1000)

    return [
        benchmark_theory(name, repeat=repeat, check_level=check_level)
        for name in theory_names
    ]


def _z3_version() -> str:
    """Return the version string of the installed Z3."""
    import z3

    return z3.get_version_string()


def _holpy_commit() -> str:
    """Return the git commit of this holpy checkout, or ``unknown``."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _result_data(
    results: Sequence[TheoryTiming],
    repeat: int,
) -> dict[str, Any]:
    """Build the JSON-serializable benchmark result.

    Parameters
    ----------
    results : sequence of TheoryTiming
        Per-theory results.
    repeat : int
        Number of repetitions.

    Returns
    -------
    dict
        Results with the same numbers as the printed table.
    """
    theories = {
        result.theory: {
            "proofs": result.proofs,
            "failures": result.failures,
            "cpu_runs": list(result.cpu_runs),
            "cpu_total_seconds": result.cpu_total,
            "cpu_mean_seconds": result.cpu_mean,
        }
        for result in results
    }
    total_runs = tuple(
        round(sum(result.cpu_runs[index] for result in results), 3)
        for index in range(repeat)
    )
    total = round(sum(total_runs), 3)
    return {
        "python": platform.python_version(),
        "z3": _z3_version(),
        "holpy_commit": _holpy_commit(),
        "repeat": repeat,
        "theories": theories,
        "total": {
            "proofs": sum(result.proofs for result in results),
            "failures": sum(result.failures for result in results),
            "cpu_runs": list(total_runs),
            "cpu_total_seconds": total,
            "cpu_mean_seconds": round(total / repeat, 3),
        },
    }


def _print_results(data: dict[str, Any]) -> None:
    """Print the environment and benchmark table.

    Parameters
    ----------
    data : dict
        Result dictionary from :func:`_result_data`.
    """
    logger.info("Python: %s", data["python"])
    logger.info("z3: %s", data["z3"])
    logger.info("holpy commit: %s", data["holpy_commit"])
    logger.info("repeat: %d", data["repeat"])
    logger.info("")
    logger.info(
        "%-12s %8s %8s %14s %14s",
        "theory",
        "proofs",
        "failed",
        "CPU total (s)",
        "CPU mean (s)",
    )
    for name, result in data["theories"].items():
        logger.info(
            "%-12s %8d %8d %14.3f %14.3f",
            name,
            result["proofs"],
            result["failures"],
            result["cpu_total_seconds"],
            result["cpu_mean_seconds"],
        )
    total = data["total"]
    logger.info(
        "%-12s %8d %8d %14.3f %14.3f",
        "total",
        total["proofs"],
        total["failures"],
        total["cpu_total_seconds"],
        total["cpu_mean_seconds"],
    )


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer for argparse.

    Parameters
    ----------
    value : str
        Command-line value.

    Returns
    -------
    int
        The parsed integer.

    Raises
    ------
    argparse.ArgumentTypeError
        If the value is not a positive integer.
    """
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser for the benchmark command.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark the kernel proof-checking phase of stored library proofs."
        )
    )
    parser.add_argument(
        "theory",
        nargs="*",
        default=list(DEFAULT_THEORIES),
        help="theory names to benchmark (default: nat sums logic)",
    )
    parser.add_argument(
        "--repeat",
        type=_positive_int,
        default=3,
        metavar="N",
        help="number of times to check all proofs (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        metavar="FILE",
        help="write the same results as JSON to FILE",
    )
    parser.add_argument(
        "--check-level",
        type=int,
        default=0,
        help="trust level passed to the kernel proof checker (default: %(default)s)",
    )
    parser.add_argument(
        "--z3-timeout",
        type=int,
        default=60,
        metavar="SECONDS",
        help="per-call Z3 time limit, 0 for none (default: %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the benchmark.

    Parameters
    ----------
    argv : sequence of str, optional
        Command-line arguments, excluding the program name.

    Returns
    -------
    int
        Process exit status.  Proof-check failures are reported in the table
        and do not make the benchmark fail.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    # The cache is keyed only by the master user, while library locations can
    # change in an embedding process. Start from the current location.
    basic.theory_cache.clear()
    basic.item_index.clear()

    results = run_benchmark(
        args.theory,
        args.repeat,
        args.check_level,
        args.z3_timeout,
    )
    data = _result_data(results, args.repeat)
    _print_results(data)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        logger.info("Wrote %s", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
