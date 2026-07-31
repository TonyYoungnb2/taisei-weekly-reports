#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_report.py — 周报页生成后确定性校验（不触碰发布）。
对某一期 report.html 跑断言，取代「截图+图像模型肉眼看」这种不可靠验证。
用法:
  python verify_report.py                 # 校验最新一期
  python verify_report.py 2026-07-31     # 校验指定一期
exit code: 0 = 全部通过, 1 = 有失败项
"""
import io, os, re, sys, glob

BASE = os.path.dirname(os.path.abspath(__file__))

# ---- 断言锚点（与 generate_weekly.py 产出强绑定，改模板需同步） ----
KEY_IDS = ['headerDateRange', 'statsBar', 'hotlist',
           'share-card-container', 'shareCardImg', 'langSwitch']
# 内联语言规则（防白屏），生成页实测带空格
LANG_RULES = ['html.lang-jp .lang-jp { display: inline; }',
              'html.lang-cn .lang-jp { display: none; }']


def find_latest():
    roots = sorted(glob.glob(os.path.join(BASE, 'reports', '*')),
                   key=os.path.getmtime, reverse=True)
    for r in roots:
        if os.path.isfile(os.path.join(r, 'report.html')):
            return os.path.basename(r)
    return None


def verify(date_folder):
    path = os.path.join(BASE, 'reports', date_folder, 'report.html')
    if not os.path.isfile(path):
        print('[FAIL] cannot find report: ' + path)
        return False
    html = io.open(path, encoding='utf-8').read()
    results = []

    def check(name, ok, detail=''):
        results.append((name, ok, detail))

    # 1) html2canvas 占位符已完全替换（无残留）
    ph = html.count('HTML2CANVAS_INLINE')
    check('placeholder-cleared', ph == 0, 'residual %d' % ph)

    # 2) 内联库 <script>/</script> 配对
    so, sc = html.count('<script'), html.count('</script>')
    check('script-tags-paired', so == sc and so >= 1, '%d open / %d close' % (so, sc))

    # 3) html2canvas 真实内联（库体已注入，非仅外部引用）
    inlined = ('html2canvas' in html) and ('COMPANY_NAME_JP' in html)
    check('html2canvas-inlined', inlined, 'lib body marker found' if inlined else 'lib NOT injected')

    # 4) 关键 DOM id 齐全
    miss = [i for i in KEY_IDS if ('id="%s"' % i) not in html]
    check('key-dom-ids', not miss, ('missing: ' + ','.join(miss)) if miss else 'all present')

    # 5) 双语 span 对称（lang-cn / lang-jp 数量差小）
    cn = html.count('class="lang-cn"') + html.count("class='lang-cn'")
    jp = html.count('class="lang-jp"') + html.count("class='lang-jp'")
    check('bilingual-spans-balanced', abs(cn - jp) <= max(2, int(0.15 * max(cn, jp))),
          'cn=%d jp=%d diff=%d' % (cn, jp, abs(cn - jp)))

    # 6) 反回退：手机媒体查询块内，多列 grid 不得用裸 1fr（会撑破容器）
    #    单列 1fr（无逗号、非 repeat 多列）是安全的（占满整行），放行
    m = re.search(r'@media[^\n]*max-width:\s*640px(.*?)\n  \}', html, re.S)
    mobile_block = m.group(1) if m else ''
    grids = re.findall(r'grid-template-columns:\s*([^;}]*)', mobile_block)
    bad = []
    for g in grids:
        g = g.strip()
        is_multi = (',' in g) or g.startswith('repeat(')
        if is_multi and '1fr' in g and 'minmax(0' not in g:
            bad.append(g)  # 多列裸 1fr 会撑破容器
    check('mobile-grid-no-regress', not bad,
          ('unsafe multi-col grids in mobile block: ' + ' | '.join(bad)) if bad else 'mobile grid safe')

    # 7) 反回退：内联语言切换规则存在（防白屏）
    miss2 = [r for r in LANG_RULES if r not in html]
    check('inline-lang-rules', not miss2, ('missing: ' + ','.join(miss2)) if miss2 else 'all present')

    # ---- 输出（纯 ASCII，避免 GBK 终端崩） ----
    ok_all = True
    print('=' * 56)
    print('VERIFY: reports/%s/report.html  (%d bytes)' % (date_folder, len(html)))
    print('=' * 56)
    for name, ok, detail in results:
        tag = 'PASS' if ok else 'FAIL'
        line = '  [%s] %s' % (tag, name)
        if detail:
            line += '  (' + detail + ')'
        print(line)
        if not ok:
            ok_all = False
    print('-' * 56)
    print('  RESULT: ' + ('ALL PASS [OK]' if ok_all else 'HAS FAILURE [BLOCK RELEASE]'))
    print('=' * 56)
    return ok_all


def main():
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = find_latest()
        if not folder:
            print('[FAIL] no report found')
            sys.exit(1)
        print('[info] auto-selected latest: ' + folder)
    ok = verify(folder)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
