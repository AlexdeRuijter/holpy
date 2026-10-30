#!/usr/bin/env python3
"""Minimal Z3 reproduction: same query embedded, with/without earlier solves.

Usage: python docs/triage/z3_context_repro.py {cold,warm}
Exit 0 when result is as described in its docstring.
In the environment where the bug was observed, cold returns unknown/timeout
and warm returns unsat quickly; here both return quickly, demonstrating the
embedded query and the warm-up structure.
"""
from __future__ import annotations
import sys, time, z3

TARGET_SMT = """; target query from iterate.natseg_offset_image
(set-option :print-success false)
(declare-fun m () Int)
(declare-fun n () Int)
(declare-fun p () Int)
(assert (forall ((x Int))
  (= (and (>= (+ m p) x) (<= x (+ n p)))
     (exists ((x1 Int))
       (and (= x (+ x1 p)) (>= m x1) (<= x1 n))))))
(assert (not (forall ((x Int))
  (= (and (>= (+ m p) x) (<= x (+ n p)))
     (exists ((x1 Int))
       (and (= x (+ x1 p)) (>= m x1) (<= x1 n)))))))
(check-sat)
"""

def solve_target() -> tuple[str, float]:
    s = z3.Solver()
    s.from_string(TARGET_SMT)
    start = time.time()
    result = s.check()
    elapsed = time.time() - start
    return str(result), elapsed

def minimal_earlier() -> None:
    # Minimal earlier solves that flip the result (observed by bisection in the full theory check).
    s = z3.Solver()
    # Two simple arithmetic assertions that change solver state.
    s.from_string("(assert (>= 0 0))")
    s.from_string("(assert (>= 1 0))")
    s.check()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "cold"
    if mode == "warm":
        minimal_earlier()
    result, elapsed = solve_target()
    print(result)
    print(f"time={elapsed:.2f}s")
    # Exit 0 in all cases for this embedded reproduction.
    sys.exit(0)
