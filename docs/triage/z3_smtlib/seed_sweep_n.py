import sys, z3
f=sys.argv[1]; n=int(sys.argv[2]); res=""
for seed in range(n):
    s=z3.Solver(); s.set("timeout",10000); s.set("random_seed",seed)
    s.from_file(f); r=str(s.check()); res+= "U" if r=="unsat" else "k"
print(z3.get_version_string().ljust(8), res, res.count("k"),"unknown of",n)
