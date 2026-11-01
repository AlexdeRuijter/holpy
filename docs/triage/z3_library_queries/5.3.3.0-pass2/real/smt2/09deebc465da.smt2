; benchmark generated from python API
(set-info :status unknown)
(declare-fun d () Real)
(assert
 (> d 0.0))
(assert
 (let (($x16 (exists ((e Real) )(and (> e 0.0) (< e d)))
))
(not $x16)))
(check-sat)
