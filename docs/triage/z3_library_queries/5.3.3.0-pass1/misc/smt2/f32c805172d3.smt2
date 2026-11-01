; benchmark generated from python API
(set-info :status unknown)
(declare-fun a () Real)
(declare-fun b () Real)
(assert
 (let (($x35 (forall ((x Real) )(not (and (< a x) (< x b))))
))
(let (($x69 (= $x35 (<= b a))))
(not $x69))))
(check-sat)
