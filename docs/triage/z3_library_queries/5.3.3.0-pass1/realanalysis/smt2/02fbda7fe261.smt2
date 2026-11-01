; benchmark generated from python API
(set-info :status unknown)
(declare-fun t (Real) Bool)
(declare-fun s (Real) Bool)
(assert
 (forall ((x Real) )(let (($x51 (t x)))
 (let (($x65 (s x)))
 (=> $x65 $x51))))
 )
(assert
 (exists ((B Real) )(forall ((x1 Real) )(let (($x22 (<= (ite (>= x1 0.0) x1 (- x1)) B)))
 (let (($x51 (t x1)))
 (=> $x51 $x22))))
 )
 )
(assert
 (let (($x7 (exists ((B1 Real) )(forall ((x2 Real) )(let (($x22 (<= (ite (>= x2 0.0) x2 (- x2)) B1)))
(let (($x65 (s x2)))
(=> $x65 $x22))))
)
))
(not $x7)))
(check-sat)
