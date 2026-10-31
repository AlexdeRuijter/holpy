"""Print a seed matrix for the Z3 proof-mode regression.

The script is deliberately pure Z3: it imports neither holpy nor any other
project module.  The two queries are copied verbatim from
``z3_proof_regression_repro.py``.

For every (row, proof mode, seed) combination a fresh Python process is
started.  That is slower than solving in one process, but it is the only way
to keep an earlier solve from changing the result, which is exactly the
effect being measured.

Examples::

    python docs/triage/z3_proof_seed_matrix.py
    python docs/triage/z3_proof_seed_matrix.py --seeds 0-7
    python docs/triage/z3_proof_seed_matrix.py --worker warm-q1 setparam 3 --stats
    python docs/triage/z3_proof_seed_matrix.py --worker warm-q1 setparam 3 \
        --option smt.mbqi=false --engine smt
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

import z3

Q1 = """
(declare-fun p () Int) (declare-fun q () Int) (declare-fun m () Int) (declare-fun n () Int)
(assert (not (= (< (ite (<= n q) n q) (ite (>= m p) m p))
                (or (< n p) (< q m) (< n m) (< q p)))))
(assert (>= n 0)) (assert (>= q 0)) (assert (>= m 0)) (assert (>= p 0))
"""

Q2 = """
(declare-fun p () Int) (declare-fun n () Int) (declare-fun x () Int) (declare-fun m () Int) (declare-fun x1 () Int)
(assert (let ((a!1 (exists ((x1 Int)) (and (= x (+ x1 p)) (<= m x1) (<= x1 n)))))
  (not (= a!1 (and (<= (+ m p) x) (<= x (+ n p)))))))
(assert (>= m 0)) (assert (>= p 0)) (assert (>= x 0)) (assert (>= n 0)) (assert (>= x1 0))
"""

TRUE = "(assert true)"

ROWS = ("cold-q2", "warm-true", "warm-q1")
PROOF_MODES = ("off", "setparam", "context")
ROW_HELP = {
    "cold-q2": "Q2 alone",
    "warm-true": "solve (assert true), then Q2",
    "warm-q1": "solve Q1, then Q2",
}
PROOF_HELP = {
    "off": "proof off (default)",
    "setparam": "proof on via z3.set_param(proof=True)",
    "context": "proof on via z3.Context(proof=True)",
}

TIMEOUT_MS = 3000
CODE = {"sat": "s", "unsat": "u", "unknown": "k"}


def parse_bool(value: str) -> bool:
    """Parse a command-line boolean without accepting arbitrary strings."""
    lowered = value.lower()
    if lowered in {"true", "1", "yes", "on"}:
        return True
    if lowered in {"false", "0", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"not a boolean: {value!r}")


def parse_value(value: str) -> Any:
    """Parse a Z3 option value from KEY=VALUE command-line syntax."""
    text = value
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def parse_options(items: list[str]) -> dict[str, Any]:
    """Turn repeated ``KEY=VALUE`` arguments into a dictionary."""
    options: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"option must be KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        options[key] = parse_value(value)
    return options


def make_context(proof_mode: str, seed: int | None, options: dict[str, Any]) -> z3.Context | None:
    """Create the context for one worker, applying proof and option settings."""
    if proof_mode == "context":
        # The seed is part of the context configuration.  Other options are
        # applied globally below, because some of them (e.g. sat.smt) are read
        # from the global parameter table even by solvers with a local context.
        kwargs: dict[str, Any] = {"proof": True}
        if seed is not None:
            kwargs["smt.random_seed"] = seed
        ctx = z3.Context(**kwargs)
    elif proof_mode == "setparam":
        z3.set_param("proof", True)
        ctx = None
    elif proof_mode == "off":
        z3.set_param("proof", False)
        ctx = None
    else:
        raise ValueError(f"unknown proof mode: {proof_mode}")
    if seed is not None:
        z3.set_param("smt.random_seed", seed)
    # Global parameters are also the settings a caller can change without
    # rebuilding a context, so all option experiments use this route.
    for key, value in options.items():
        z3.set_param(key, value)
    return ctx


def make_solver(
    ctx: z3.Context | None, seed: int | None, engine: str, options: dict[str, Any]
) -> z3.Solver:
    """Build one solver, either plain ``smt`` or a tactic-backed solver."""
    if engine == "smt":
        solver = z3.Solver(ctx=ctx) if ctx is not None else z3.Solver()
    else:
        if engine == "qe-smt":
            tactic = z3.Then("qe", "smt", ctx=ctx)
        elif engine == "qe2-smt":
            tactic = z3.Then("qe2", "smt", ctx=ctx)
        elif engine == "qsat":
            tactic = z3.Tactic("qsat", ctx=ctx)
        elif engine == "qe":
            tactic = z3.Tactic("qe", ctx=ctx)
        else:
            raise ValueError(f"unknown engine: {engine}")
        solver = tactic.solver()
    solver.set("timeout", TIMEOUT_MS)
    if engine != "qe" and seed is not None:
        # The pure qe tactic has no random_seed parameter; every other engine
        # here is smt-backed and accepts it.
        solver.set("random_seed", seed)
    return solver


def solve_text(
    text: str,
    ctx: z3.Context | None,
    seed: int | None,
    engine: str,
    options: dict[str, Any],
) -> tuple[z3.CheckSatResult, str, dict[str, Any]]:
    """Solve one SMT-LIB text and return result, reason and statistics."""
    solver = make_solver(ctx, seed, engine, options)
    solver.from_string(text)
    result = solver.check()
    reason = solver.reason_unknown() if str(result) == "unknown" else ""
    stats = {
        str(key): solver.statistics().get_key_value(str(key))
        for key in solver.statistics().keys()
    }
    return result, reason, stats


def run_worker(args: argparse.Namespace) -> int:
    """Run one matrix cell in this process and print a JSON object."""
    options = parse_options(args.option)
    ctx = make_context(args.proof, args.seed, options)
    if args.row == "warm-true":
        solve_text(TRUE, ctx, args.seed, args.engine, options)
    elif args.row == "warm-q1":
        solve_text(Q1, ctx, args.seed, args.engine, options)
    result, reason, stats = solve_text(Q2, ctx, args.seed, args.engine, options)
    payload = {
        "version": z3.get_version_string(),
        "row": args.row,
        "proof": args.proof,
        "seed": args.seed,
        "engine": args.engine,
        "result": str(result),
        "code": CODE[str(result)],
        "reason": reason,
    }
    if args.stats:
        payload["stats"] = stats
    print(json.dumps(payload, sort_keys=True))
    return 0


def parse_seeds(text: str) -> list[int]:
    """Parse ``0-15`` or a comma-separated seed list."""
    if "-" in text and "," not in text:
        first, last = text.split("-", 1)
        return list(range(int(first), int(last) + 1))
    return [int(item) for item in text.split(",") if item]


def run_cell(
    row: str,
    proof: str,
    seeds: list[int],
    engine: str,
    options: dict[str, Any],
    timeout_s: float,
) -> tuple[str, str]:
    """Run all seeds of one cell, each in a fresh subprocess."""
    codes: list[str] = []
    reasons: list[str] = []
    for seed in seeds:
        command = [
            sys.executable,
            __file__,
            "--worker",
            row,
            proof,
            str(seed),
            "--engine",
            engine,
        ]
        for key, value in options.items():
            command.extend(["--option", f"{key}={value}"])
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if completed.returncode != 0:
            codes.append("!")
            reasons.append(completed.stderr.strip().splitlines()[-1:] or ["worker failed"])
            continue
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        codes.append(payload["code"])
        if payload["code"] == "k":
            reasons.append(f"seed {seed}: {payload['reason'] or '(no reason)'}")
    first_reason = reasons[0] if reasons else "-"
    return "".join(codes), first_reason


def print_table(args: argparse.Namespace) -> int:
    """Print the requested matrix as a Markdown table."""
    seeds = parse_seeds(args.seeds)
    options = parse_options(args.option)
    print(f"z3-solver {z3.get_version_string()} (Python {sys.version.split()[0]})")
    print(f"seeds {seeds[0]}..{seeds[-1]}, timeout {TIMEOUT_MS} ms/query, engine {args.engine}")
    if options:
        print("options: " + ", ".join(f"{key}={value}" for key, value in options.items()))
    print()
    rows = [item for item in args.rows.split(",") if item]
    proofs = [item for item in args.proofs.split(",") if item]
    for item in rows:
        if item not in ROWS:
            raise SystemExit(f"unknown row {item!r}; choose from {ROWS}")
    for item in proofs:
        if item not in PROOF_MODES:
            raise SystemExit(f"unknown proof mode {item!r}; choose from {PROOF_MODES}")
    print("| row | " + " | ".join(PROOF_HELP[mode] for mode in proofs) + " |")
    print("|---|" + "---|" * len(proofs))
    for row in rows:
        cells: list[str] = []
        for proof in proofs:
            codes, reason = run_cell(
                row,
                proof,
                seeds,
                args.engine,
                options,
                timeout_s=len(seeds) * (TIMEOUT_MS / 1000.0 + 2.0),
            )
            cell = f"`{codes}`"
            if reason != "-":
                cell += f" first unknown {reason}"
            cells.append(cell.replace("|", "\\|"))
        print(f"| {ROW_HELP[row]} | " + " | ".join(cells) + " |")
    print()
    print("u=unsat, k=unknown, s=sat, !=worker error; cells are seeds in order.")
    return 0


def make_parser() -> argparse.ArgumentParser:
    """Build the command-line parser shared by table and worker modes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", nargs=3, metavar=("ROW", "PROOF", "SEED"))
    parser.add_argument("--seeds", default="0-15", help="seed list, e.g. 0-15 or 1,3,5")
    parser.add_argument("--rows", default=",".join(ROWS), help="comma-separated rows to print")
    parser.add_argument(
        "--proofs", default=",".join(PROOF_MODES), help="comma-separated proof modes"
    )
    parser.add_argument(
        "--engine", default="smt", choices=["smt", "qe-smt", "qe2-smt", "qsat", "qe"]
    )
    parser.add_argument("--option", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument(
        "--stats", action="store_true", help="worker mode: include solver statistics"
    )
    parser.add_argument(
        "--no-seed", action="store_true", help="worker mode: leave smt.random_seed unset"
    )
    return parser


def main() -> int:
    """Dispatch to worker mode or the full table."""
    parser = make_parser()
    args = parser.parse_args()
    if args.worker is not None:
        args.row, args.proof, seed = args.worker
        args.seed = None if args.no_seed else int(seed)
        if args.row not in ROWS:
            parser.error(f"row must be one of {ROWS}")
        if args.proof not in PROOF_MODES:
            parser.error(f"proof mode must be one of {PROOF_MODES}")
        return run_worker(args)
    return print_table(args)


if __name__ == "__main__":
    raise SystemExit(main())
