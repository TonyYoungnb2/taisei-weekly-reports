# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
d = json.load(open(r'..\data\projects.json', encoding='utf-8'))
ids = ['P001','P002','P003','P009','P114','P116','P117','P120','P122','P123','P124','P125',
       'P126','P127','P128','P129','P130','P131','P132','P133','P134']
m = {p['id']: p for p in d['projects']}
lines = []
for i in ids:
    p = m.get(i)
    if not p:
        lines.append(f"{i} MISSING")
        continue
    lines.append(f"{i} | {p.get('name','')} | {p.get('developer','')} | {p.get('status','')} | {p.get('city','')}{p.get('district','')}")
open('_miss_names.txt','w',encoding='utf-8').write('\n'.join(lines))
print('written', len(lines))
