import random, probe_question_selection as Q
CHOSEN=['labels6','nouns_adj','object']
axes=Q.load_axes()
names=sorted(axes)
rng=random.Random(99)  # different seed from qsel -> fresh combos
# 60 new 4-axis combos over ALL values (not the 4/axis sample) for a broad test set
combos=[[ (ax, rng.choice(axes[ax])) for ax in rng.sample(names,4)] for _ in range(60)]
todo=[(("; ".join(v for _,v in c)),q) for c in combos for q in CHOSEN]
todo=[(c,q) for c,q in todo if not Q.is_cached(c,q)]
print(f'new combos=60, gens todo={len(todo)}', flush=True)
for i,(c,q) in enumerate(todo,1):
    Q.gen(c,q)
    if i%15==0 or i==len(todo): print(f'  {i}/{len(todo)}', flush=True)
print('DONE')
