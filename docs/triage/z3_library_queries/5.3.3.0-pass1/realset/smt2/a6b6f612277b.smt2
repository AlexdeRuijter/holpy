; benchmark generated from python API
(set-info :status unknown)
(declare-fun l () Real)
(declare-fun s (Real) Bool)
(assert
 (forall ((c Real) )(let (($x14 (forall ((x Real) )(let (($x46 (s x)))
 (=> $x46 (<= c x))))
 ))
 (= $x14 (<= c l))))
 )
(assert
 (let (($x51 (forall ((x1 Real) )(let (($x46 (s x1)))
(=> $x46 (<= l x1))))
))
(not $x51)))
(check-sat)
