"""Z3 (z3-solver 5.3.3): with proof generation on, a query that is `unsat`
immediately in a fresh process returns `unknown` after another (unrelated,
also `unsat`) query was solved earlier in the same process.

    python repro.py warm   # solve Q1 first, then Q2   -> Q2: unknown
    python repro.py cold   # solve only Q2             -> Q2: unsat
    python repro.py warm-noproof   # as warm, without proof=True -> Q2: unsat
"""
import sys, time, z3

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

def solve(text):
    s = z3.Solver()
    s.set("timeout", 5000)
    s.from_string(text)
    t = time.time()
    return s.check(), time.time() - t

mode = sys.argv[1]
if mode != "warm-noproof":
    z3.set_param(proof=True)
if mode.startswith("warm"):
    r, _ = solve(Q1)
    print("Q1:", r)
r, dt = solve(Q2)
print("Q2: %s (%.2fs)" % (r, dt))
