; benchmark generated from python API
(set-info :status unknown)
(declare-fun p () Int)
(declare-fun n () Int)
(declare-fun x () Int)
(declare-fun m () Int)
(declare-fun x1 () Int)
(assert
 (let (($x45 (exists ((x1 Int) )(and (= x (+ x1 p)) (and (<= m x1) (<= x1 n))))
 ))
 (let (($x118 (= $x45 (and (<= (+ m p) x) (<= x (+ n p))))))
 (not $x118))))
(assert
 (>= m 0))
(assert
 (>= p 0))
(assert
 (>= x 0))
(assert
 (>= n 0))
(assert
 (>= x1 0))
(check-sat)
