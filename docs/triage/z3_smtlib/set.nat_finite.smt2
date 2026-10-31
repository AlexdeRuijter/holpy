; benchmark generated from python API
(set-info :status unknown)
(declare-fun s1 (Int) Bool)
(declare-fun x () Int)
(declare-fun x1 () Int)
(declare-fun a () Int)
(declare-fun x11 () Int)
(declare-fun a1 () Int)
(assert
 (exists ((a Int) )(forall ((x1 Int) )(let (($x511 (<= x1 a)))
 (let (($x17 (s1 x1)))
 (=> $x17 $x511))))
 )
 )
(assert
 (let (($x358 (exists ((a1 Int) )(forall ((x11 Int) )(let (($x511 (<= x11 a1)))
 (=> (or (= x11 x) (s1 x11)) $x511)))
 )
 ))
 (not $x358)))
(assert
 (>= x1 0))
(assert
 (>= a 0))
(assert
 (>= x11 0))
(assert
 (>= x 0))
(assert
 (>= a1 0))
(check-sat)
