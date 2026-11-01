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
 (let ((?x53 (/ (+ (/ sx cx) (/ sy cy)) (- 1.0 (* (/ sx cx) (/ sy cy))))))
(let ((?x66 (* sx sy)))
(let ((?x18 (- (* cx cy) ?x66)))
(let (($x84 (= (/ (+ (* sx cy) (* cx sy)) ?x18) ?x53)))
(not $x84))))))
(check-sat)
