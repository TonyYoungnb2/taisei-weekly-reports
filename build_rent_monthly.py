#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_rent_monthly.py — 抓取東京カンテイ「分譲マンション賃料月別推移」（每月15日前后发布）
生成 data/rent/monthly.json：23区 / 首都圏 / 都県 的月度賃料指数（円/㎡）。

为什么用这个源：
  - e-Stat 住宅・土地統計調査 是 5 年一次（2023 最新），不能月更；
  - 之前用的 housingassist Tokyo Rent Index 页面自己标「Last updated June 26, 2026」，
    实际已停更（2026-10 抓到的数值与 2026-06 完全一致）；
  - 東京カンテイ 每月 15 日前后发布上月数据，正文明确给出 23区/都県 的数值与环比。

用法: python build_rent_monthly.py [--months 9]
"""
import io, os, re, sys, json, subprocess, time

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'data', 'rent', 'monthly.json')
CAT = 'https://www.kantei.ne.jp/report/category/rent/'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

PREF = ['東京都', '神奈川県', '埼玉県', '千葉県']
PAT_W23 = re.compile(r'東京\s*23\s*区は\s*([＋+\-－−]?\d+\.\d)\s*[％%]\s*の\s*([\d,]+)\s*円/㎡')
# 两种句式都要吃：
#   「東京都では＋0.8％の5,025円/㎡」
#   「神奈川県（＋0.9％、2,935円/㎡）」
PAT_PREF_ANY = re.compile(
    r'(東京都|神奈川県|埼玉県|千葉県)\s*(?:では)?\s*[（(]?\s*'
    r'([＋+\-－−]?\d+\.\d)\s*[％%]\s*(?:の|[、,])\s*([\d,]+)\s*円/㎡')
PAT_KANTO = re.compile(r'首都圏\s*\d+月\s*前月比\s*([＋+\-－−]?\d+\.\d)\s*[％%]\s*の\s*([\d,]+)\s*円/㎡')
PAT_MONTH = re.compile(r'(20\d{2})年\s*(\d{1,2})月')


def fetch(url):
    r = subprocess.run(['curl.exe', '-s', '-L', '--max-time', '40', '-A', UA, url],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout or ''


def body(h):
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', h)
    return re.sub(r'\s+', ' ', t)


def fnum(s):
    return float(s.replace('＋', '+').replace('－', '-').replace('−', '-'))


def parse_report(html):
    t = body(html)
    # 统计月份：取正文开头第一个「YYYY年M月」（标题即「2026年9月　東京23区は…」）
    m = PAT_MONTH.search(t[:400])
    if not m:
        return None, {}
    month = '%s-%02d' % (m.group(1), int(m.group(2)))
    rec = {}
    if (x := PAT_W23.search(t)):
        rec['23区'] = {'v': int(x.group(2).replace(',', '')), 'mom': fnum(x.group(1))}
    if (x := PAT_KANTO.search(t)):
        rec['首都圏'] = {'v': int(x.group(2).replace(',', '')), 'mom': fnum(x.group(1))}
    for x in PAT_PREF_ANY.finditer(t):
        name = x.group(1)
        if name not in rec:   # 同一期里首次出现的为准（后文多为重复引用）
            rec[name] = {'v': int(x.group(3).replace(',', '')), 'mom': fnum(x.group(2))}
    return month, rec


def main():
    limit = 9
    if '--months' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--months') + 1])

    cat = fetch(CAT)
    urls = []
    for u in re.findall(r'href="(https://www\.kantei\.ne\.jp/report/rent/\d+/)"', cat):
        if u not in urls:
            urls.append(u)
    urls = urls[:limit]
    if not urls:
        raise SystemExit('[ERR] 分类页没有取到月报链接')
    print('reports found:', len(urls))

    months = {}
    # 保留已有历史（重跑时累积）
    if os.path.isfile(OUT):
        try:
            old = json.load(io.open(OUT, encoding='utf-8'))
            months = old.get('months', {})
        except Exception:
            months = {}

    for i, u in enumerate(urls):
        h = fetch(u)
        mo, rec = parse_report(h)
        if not mo or not rec:
            print('  [SKIP]', u)
            continue
        rec['url'] = u
        months[mo] = rec
        print('  %s  %s' % (mo, ' '.join('%s=%d(%+.1f%%)' % (k, v['v'], v['mom'])
                                        for k, v in rec.items() if k != 'url')))
        time.sleep(0.25)

    # 序列
    series = {}
    for scope in ['23区', '首都圏', '東京都', '神奈川県', '埼玉県', '千葉県']:
        pts = [{'m': mo, 'v': months[mo][scope]['v']}
               for mo in sorted(months) if scope in months[mo]]
        if pts:
            series[scope] = pts

    latest_m = max(months) if months else None
    latest = {k: v for k, v in (months.get(latest_m, {}) or {}).items() if k != 'url'}

    out = {
        'meta': {
            'source': '東京カンテイ「分譲マンション賃料月別推移」',
            'unit': '円/㎡（月額）',
            'scope': '東京23区・首都圏・都県',
            'cadence': '毎月15日頃に前月分を発表',
            'month': latest_m,
            'url': months.get(latest_m, {}).get('url', ''),
            'note': '分譲マンション（平均専有面積 約60㎡・平均築年 約21年）の月額賃料を㎡単価で表示。'
                    'e-Stat の「月額賃料 中央値（全規模）」とは指標が異なるため、参考指標として併記。',
        },
        'latest': latest,
        'series': series,
        'months': months,
    }
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    print('[OK] %s  %s  %d months  %d scopes' % (OUT, latest_m, len(months), len(series)))
    for s, pts in series.items():
        print('   %-6s %d pts  %s → %s' % (s, len(pts), pts[0]['v'], pts[-1]['v']))


if __name__ == '__main__':
    main()
