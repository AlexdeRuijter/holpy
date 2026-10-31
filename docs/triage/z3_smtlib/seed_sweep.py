import sys, z3, time
f=sys.argv[1]; res=""
for seed in range(16):
    s=z3.Solver(); s.set("timeout",3000); s.set("random_seed",seed)
    s.from_file(f); r=str(s.check()); res+= "U" if r=="unsat" else "k"
print(z3.get_version_string().ljust(8), res, res.count("k"),"unknown of 16")
