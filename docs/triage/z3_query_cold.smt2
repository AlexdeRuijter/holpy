; benchmark generated from python API
(set-info :status unknown)
(declare-sort b 0)
(declare-sort a 0)
(declare-fun P (b) Bool)
(declare-fun x () b)
(declare-fun s (b) Bool)
(declare-fun g (b) a)
(declare-fun f (b) a)
(assert
 (let (($x732 (P x)))
 (let (($x1303 (not $x732)))
 (let (($x280 (s x)))
 (and $x280 $x1303)))))
(assert
 (let ((?x73 (g x)))
(let (($x1251 (= (ite (P x) (f x) ?x73) ?x73)))
(not $x1251))))
(check-sat)
