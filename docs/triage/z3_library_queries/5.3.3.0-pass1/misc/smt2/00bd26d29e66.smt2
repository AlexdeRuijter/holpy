; benchmark generated from python API
(set-info :status unknown)
(declare-fun a () Real)
(declare-fun b () Real)
(assert
 (let (($x83 (forall ((x Real) )(not (and (< a x) (< x b))))
))
(let (($x91 (= $x83 (<= b a))))
(not $x91))))
(check-sat)
