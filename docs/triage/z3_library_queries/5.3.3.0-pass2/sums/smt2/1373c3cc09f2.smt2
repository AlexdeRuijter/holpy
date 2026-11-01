; benchmark generated from python API
(set-info :status unknown)
(declare-sort a 0)
(declare-fun s (a) Bool)
(declare-fun x () a)
(assert
 (s x))
(assert
 (not true))
(check-sat)
