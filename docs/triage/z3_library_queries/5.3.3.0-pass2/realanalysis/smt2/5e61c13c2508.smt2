; benchmark generated from python API
(set-info :status unknown)
(declare-fun t (Real) Bool)
(declare-fun s (Real) Bool)
(assert
 (forall ((x Real) )(let (($x71 (t x)))
 (let (($x60 (s x)))
 (=> $x60 $x71))))
 )
(assert
 (exists ((B Real) )(forall ((x1 Real) )(let (($x54 (<= (ite (>= x1 0.0) x1 (- x1)) B)))
 (let (($x71 (t x1)))
 (=> $x71 $x54))))
 )
 )
(assert
 (let (($x16 (exists ((B1 Real) )(forall ((x2 Real) )(let (($x54 (<= (ite (>= x2 0.0) x2 (- x2)) B1)))
(let (($x60 (s x2)))
(=> $x60 $x54))))
)
))
(not $x16)))
(check-sat)
