# -*- coding: utf-8 -*-
import io, subprocess, re, time
time.sleep(90)  # 等 EdgeOne 重部署
url = 'https://taisei-weekly-reports.edgeone.cool/projects.html?b=wait' + str(int(time.time()))
out = subprocess.run(['curl.exe', '-s', url], capture_output=True, timeout=30)
b = out.stdout.decode('utf-8', errors='replace')
m = re.search(r'@media \(max-width: 640px\) \{(.*?)\}', b, re.S)
block = m.group(1) if m else ''
res = []
res.append('EDGE mobile single-col rule: ' + str('.grid { grid-template-columns: minmax(0, 1fr); }' in block))
res.append('EDGE card padding in 640: ' + str('padding: 12px' in block))
res.append('EDGE len=' + str(len(b)))
io.open('_wv.txt', 'w', encoding='utf-8').write('\n'.join(res))
