; benchmark generated from python API
(set-info :status unknown)
(declare-fun cx () Real)
(declare-fun cy () Real)
(declare-fun sy () Real)
(declare-fun sx () Real)
(assert
 (not (= cx 0.0)))
(assert
 (not (= cy 0.0)))
(assert
 (not (= (- (* cx cy) (* sx sy)) 0.0)))
(assert
 (let ((?x145 (/ sy cy)))
(let ((?x144 (/ sx cx)))
(let ((?x146 (+ ?x144 ?x145)))
(let ((?x58 (* sx sy)))
(let ((?x87 (- (* cx cy) ?x58)))
(let (($x136 (= (/ (+ (* sx cy) (* cx sy)) ?x87) (/ ?x146 (- 1.0 (* ?x144 ?x145))))))
(not $x136))))))))
(check-sat)
