; benchmark generated from python API
(set-info :status unknown)
(declare-fun s1 (Int) Bool)
(declare-fun x () Int)
(declare-fun x1 () Int)
(declare-fun a () Int)
(declare-fun x11 () Int)
(declare-fun a1 () Int)
(assert
 (exists ((a Int) )(forall ((x1 Int) )(let (($x415 (<= x1 a)))
 (let (($x135 (s1 x1)))
 (=> $x135 $x415))))
 )
 )
(assert
 (let (($x163 (exists ((a1 Int) )(forall ((x11 Int) )(let (($x415 (<= x11 a1)))
 (=> (or (= x11 x) (s1 x11)) $x415)))
 )
 ))
 (not $x163)))
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
