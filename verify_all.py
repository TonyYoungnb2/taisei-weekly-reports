#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_all.py — 全站确定性校验（替代截图人工）。
覆盖：周报页(report) / 地图页(map) / 平台主界面(projects)。
用法: python verify_all.py [report日期 YYYY-MM-DD]
返回: exit 0=全 PASS, 1=有 FAIL。
"""
import io, os, re, sys, json

BASE = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = os.path.join(BASE, 'data', 'news')
results = []


def chk(name, ok, detail=''):
    results.append((name, ok, detail))


def gsi_only(html):
    ext = set(re.findall(r'https?://([^/\s\'"]+)', html))
    ext.discard('cyberjapandata.gsi.go.jp')
    return ext


def verify_report(date=None):
    if date is None:
        # 最新一期
        import glob
        dates = sorted(glob.glob(os.path.join(BASE, 'reports', '*', 'report.html')))
        if not dates:
            chk('report: 存在', False, '无 reports/*/report.html')
            return
        path = dates[-1]
    else:
        path = os.path.join(BASE, 'reports', date, 'report.html')
    if not os.path.isfile(path):
        chk('report: 文件存在 %s' % path, False)
        return
    h = io.open(path, encoding='utf-8').read()
    chk('report: 占位符无残留', 'HTML2CANVAS_INLINE' not in h and 'TITLE_PH' not in h and 'BODY_PH' not in h)
    chk('report: script 配对', h.count('<script') == h.count('</script>'))
    chk('report: html2canvas 内联', 'html2canvas 内联（绕过 CDN 被墙）' in h)
    for i in ['headerDateRange', 'statsBar', 'hotlist', 'share-card-container', 'shareCardImg', 'langSwitch']:
        chk('report: DOM id #%s' % i, ('id="%s"' % i) in h)
    # 双语 span 对称
    cn = h.count('class="lang-cn"') + h.count('lang-cn"')
    jp = h.count('class="lang-jp"') + h.count('lang-jp"')
    chk('report: 双语 span 对称', cn > 0 and cn == jp, 'cn=%d jp=%d' % (cn, jp))
    # 手机 grid 不得裸多列 1fr
    bad_grid = re.search(r'grid-template-columns:\s*repeat\(\d+,\s*1fr\)', h) is not None
    chk('report: 手机 grid 未回退', not bad_grid)
    # 内联 lang 规则
    chk('report: 内联 lang 规则', 'html.lang-jp .lang-jp' in h)


def verify_map():
    path = os.path.join(BASE, 'map.html')
    if not os.path.isfile(path):
        chk('map: 文件存在', False); return
    h = io.open(path, encoding='utf-8').read()
    chk('map: Leaflet 本地引用', 'vendor/leaflet/leaflet.js' in h and 'vendor/leaflet/leaflet.css' in h)
    chk('map: 无 CDN 外链', not any(c in h for c in ['jsdelivr', 'unpkg', 'cdnjs', 'cdn.']))
    chk('map: GSI 瓦片', 'cyberjapandata.gsi.go.jp/xyz/std' in h)
    m = re.search(r'var PROJECTS = (\[.*?\]);', h, re.S)
    n = 0
    if m:
        try: n = len(json.loads(m.group(1)))
        except Exception: pass
    chk('map: 内联 PROJECTS>0', n > 0, 'got %d' % n)
    chk('map: 外部域仅 GSI', len(gsi_only(h)) == 0, 'others: ' + ','.join(gsi_only(h)))
    chk('map: vendor 文件存在', os.path.isfile(os.path.join(BASE, 'vendor', 'leaflet', 'leaflet.js')) and
        os.path.isfile(os.path.join(BASE, 'vendor', 'leaflet', 'leaflet.css')))
    # 标记随缩放放大（修复“放大后点变小”）：必须存在 dotRadius + setRadius + zoomend 重算
    chk('map: 点随缩放放大(dotRadius)', 'function dotRadius' in h)
    chk('map: 缩放时重算半径(zoomend rescale)', "map.on('zoomend', rescale)" in h or 'map.on("zoomend", rescale)' in h)
    chk('map: 光晕提升辨识度(halo)', 'proj-halo' in h)
    chk('map: 载入fitBounds框选全部', 'map.fitBounds(BOUNDS' in h)
    chk('map: __BOUNDS__ 已替换', '__BOUNDS__' not in h)
    chk('map: __DATA__ 已替换', '__DATA__' not in h)


def verify_projects():
    path = os.path.join(BASE, 'projects.html')
    if not os.path.isfile(path):
        chk('projects: 文件存在', False); return
    h = io.open(path, encoding='utf-8').read()
    chk('projects: Leaflet 本地引用', 'vendor/leaflet/leaflet.js' in h and 'vendor/leaflet/leaflet.css' in h)
    chk('projects: 资源无 CDN 外链', not any(c in r for r in
        re.findall(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', h) +
        re.findall(r'L\.tileLayer\(\s*[\'"]([^\'"]+)[\'"]', h) for c in ['jsdelivr', 'unpkg', 'cdnjs', 'cdn.']))
    chk('projects: GSI 瓦片', 'cyberjapandata.gsi.go.jp/xyz/std' in h)
    m1 = re.search(r'var PROJECTS = (\[.*?\]);', h, re.S)
    m2 = re.search(r'var NEWS = (\[.*?\]);', h, re.S)
    np_ = len(json.loads(m1.group(1))) if m1 else 0
    nw = len(json.loads(m2.group(1))) if m2 else 0
    chk('projects: 内联 PROJECTS>0', np_ > 0, 'got %d' % np_)
    chk('projects: 内联 NEWS>0', nw > 0, 'got %d' % nw)
    for i in ['listBody', 'search', 'map', 'detail', 'btnList', 'btnMap', 'groupSel']:
        chk('projects: DOM id #%s' % i, ('id="%s"' % i) in h)
    chk('projects: setView/list/map 切换', 'function setView' in h and "onclick=\"setView('map')\"" in h)
    base_grid = re.search(r'\.grid\s*\{[^}]*grid-template-columns:\s*([^;]+);', h)
    chk('projects: 手机默认 .grid minmax(0,1fr)', bool(base_grid) and 'minmax(0, 1fr)' in base_grid.group(1))
    bad = []
    for m in re.finditer(r'minmax\(\d+px,\s*1fr\)', h):
        prec = [x for x in re.finditer(r'@media\s*\(([^)]+)\)', h) if x.start() < m.start()]
        ctx = prec[-1].group(1) if prec else 'BASE'
        if 'min-width' not in ctx: bad.append(ctx)
    chk('projects: minmax(Npx,1fr) 仅桌面', len(bad) == 0, ','.join(bad))
    for fn in ['function buildChips', 'function filtered', 'function render', 'function openDetail', 'function renderMap']:
        chk('projects: %s' % fn, fn in h)
    chk('projects: vendor 文件存在', os.path.isfile(os.path.join(BASE, 'vendor', 'leaflet', 'leaflet.js')) and
        os.path.isfile(os.path.join(BASE, 'vendor', 'leaflet', 'leaflet.css')))


def main():
    print('=== 周报页 ===')
    verify_report(None if len(sys.argv) < 2 else sys.argv[1])
    print('=== 地图页 ===')
    verify_map()
    print('=== 平台主界面 ===')
    verify_projects()
    # 输出
    fails = 0
    for name, ok, detail in results:
        mark = 'PASS' if ok else 'FAIL'
        if not ok: fails += 1
        extra = ('  (%s)' % detail) if detail else ''
        safe = ('[%s] %s%s' % (mark, name, extra)).encode('ascii', 'replace').decode('ascii')
        print(safe)
    print('---')
    print('TOTAL: %d  PASS, %d FAIL' % (len(results) - fails, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
