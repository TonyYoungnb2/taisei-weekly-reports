import zipfile, io, re, json
from collections import Counter
import xml.etree.ElementTree as ET

z = zipfile.ZipFile('_estat116.zip')
ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ss = []
for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(ns+'si'):
    ss.append(''.join(t.text or '' for t in si.iter(ns+'t')))
root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
def colref(r): return re.match(r'[A-Z]+', r).group(0)
def rownum(r): return int(re.match(r'[A-Z]+(\d+)', r).group(1))
cells = {}
for c in root.iter(ns+'c'):
    ref=c.get('r'); t=c.get('t'); v=c.find(ns+'v'); isn=c.find(ns+'is')
    val=''
    if t=='s' and v is not None: val=ss[int(v.text)]
    elif v is not None: val=v.text or ''
    elif isn is not None: val=''.join(x.text or '' for x in isn.iter(ns+'t'))
    cells[(colref(ref), rownum(ref))]=val

# rent bands = cols E..N (10 bands). D is total households (skip).
# band edges [lo, hi) in JPY:
EDGES = [(0,10000),(10000,20000),(20000,30000),(30000,40000),(40000,60000),
         (60000,80000),(80000,100000),(100000,150000),(150000,200000),(200000,250000)]
BAND_COLS = ['E','F','G','H','I','J','K','L','M','N']  # 10 bands
def to_int(s):
    s=(s or '').strip()
    if s in ('', '-', '…', '･', 'x', 'X'): return 0
    try: return int(s)
    except: return 0
def median_interp(r):
    counts=[to_int(cells.get((c,r),'')) for c in BAND_COLS]
    total=sum(counts)
    if total<=0: return None
    cum=0; mid=total/2
    for i,(lo,hi) in enumerate(EDGES):
        c=counts[i]
        if cum+c >= mid and c>0:
            # interpolate within band
            pos=(mid-cum)/c
            return int(lo + pos*(hi-lo))
        cum+=c
    return EDGES[-1][1]

out=[]
for (col,r),val in list(cells.items()):
    if col!='B': continue
    m=re.match(r'(1[1234]\d{3})_(.+)', val or '')
    if not m: continue
    code=m.group(1); name=m.group(2).replace('\u3000','').strip()
    pref=int(code[:2])
    if pref not in (11,12,13,14): continue
    if not (cells.get(('C',r),'') or '').startswith('00_'): continue
    med=median_interp(r)
    if med is None: continue
    out.append({'code':code,'name':name,'pref':pref,'rent_median':med})

io.open('_estat_extract.json','w',encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
io.open('_estat_stat.txt','w',encoding='utf-8').write('total 1都3県 municipalities: %d\n'%len(out))
cnt=Counter(o['pref'] for o in out)
label={11:'埼玉県',12:'千葉県',13:'東京都',14:'神奈川県'}
io.open('_estat_stat.txt','a',encoding='utf-8').write('by pref: %s\n'%{label[k]:v for k,v in cnt.items()})
rents=sorted(o['rent_median'] for o in out)
io.open('_estat_stat.txt','a',encoding='utf-8').write('min=%d max=%d median=%d\n'%(rents[0],rents[-1],rents[len(rents)//2]))
import statistics
io.open('_estat_stat.txt','a',encoding='utf-8').write('mean=%.0f\n'%statistics.mean(rents))
# show distribution of top/bottom
io.open('_estat_stat.txt','a',encoding='utf-8').write('\nTOP 8 (expensive):\n')
for o in sorted(out,key=lambda x:-x['rent_median'])[:8]:
    io.open('_estat_stat.txt','a',encoding='utf-8').write('  %s %s %d万\n'%(o['code'],o['name'],o['rent_median']//10000))
io.open('_estat_stat.txt','a',encoding='utf-8').write('\nBOTTOM 8 (cheap):\n')
for o in sorted(out,key=lambda x:x['rent_median'])[:8]:
    io.open('_estat_stat.txt','a',encoding='utf-8').write('  %s %s %d万\n'%(o['code'],o['name'],o['rent_median']//10000))
