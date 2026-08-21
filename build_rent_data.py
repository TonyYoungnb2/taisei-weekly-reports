#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_rent_data.py — 一都三县 賃貸相場データを統合して data/rent/YYYY-MM.json を生成。
データソース（誠実な明示）:
  - メイン指標「月額賃料 中央値(全規模)」: 総務省 e-Stat 2023 住宅・土地統計調査
    Rent116「月額賃料(専用住宅) — 日本・都道府県・市区町村」10階級分布から中央値を補間算出。
    → 23区〜市町村まで同一手法で比較可能（全国統一の公的統計）。
  - 23区限定サブ指標「1K 専有面積 中位月額」+ 推移: housingassist Tokyo Rent Index（掲載事例 19,000+ 件）
    既存 rentmap との連続性のため、23区カードにのみ副表示。
  - 該市区 収益物件件数: data/projects.json の city フィールドから動的集計。
  - 緯度経度: 国土地理院 住所検索 API（GSI, 無料・key不要）で事前取得・キャッシュ。
使い方: python build_rent_data.py
"""
import io, os, json, re, subprocess, time, urllib.parse, statistics

BASE = os.path.dirname(os.path.abspath(__file__))
ESTAT_XLSX = os.path.join(BASE, '_estat116.zip')      # 事前取得済
EXTRACT = os.path.join(BASE, '_estat_extract.json')   # 抽出済 (code,name,pref,rent_median)
OLD_RENT = os.path.join(BASE, 'data', 'rent', '2026-07.json')  # 旧23区 housingassist
GEO_CACHE = os.path.join(BASE, '_rent_geo_cache.json')
OUT = os.path.join(BASE, 'data', 'rent', '2026-07.json')

PREF_NAME = {11: '埼玉県', 12: '千葉県', 13: '東京都', 14: '神奈川県'}
PREF_CN = {11: '埼玉县', 12: '千叶县', 13: '东京都', 14: '神奈川县'}

BAND_COLS = ['E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N']
EDGES = [(0, 10000), (10000, 20000), (20000, 30000), (30000, 40000), (40000, 60000),
         (60000, 80000), (80000, 100000), (100000, 150000), (150000, 200000), (200000, 250000)]


def to_int(s):
    s = (s or '').strip()
    if s in ('', '-', '…', '･', 'x', 'X'):
        return 0
    try:
        return int(s)
    except Exception:
        return 0


def median_interp(cells, r):
    counts = [to_int(cells.get((c, r), '')) for c in BAND_COLS]
    total = sum(counts)
    if total <= 0:
        return None
    cum = 0
    mid = total / 2
    for i, (lo, hi) in enumerate(EDGES):
        c = counts[i]
        if cum + c >= mid and c > 0:
            pos = (mid - cum) / c
            return int(lo + pos * (hi - lo))
        cum += c
    return EDGES[-1][1]


def geocode(name):
    url = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q=' + urllib.parse.quote(name)
    for attempt in range(3):
        try:
            r = subprocess.run(['curl.exe', '-sL', '--max-time', '20', url],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
            j = json.loads(r.stdout)
            if j and isinstance(j, list) and j[0].get('geometry', {}).get('coordinates'):
                co = j[0]['geometry']['coordinates']
                return co[1], co[0]  # lat, lng
        except Exception:
            pass
        time.sleep(0.4)
    return None, None


def load_estat():
    import zipfile
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(ESTAT_XLSX)
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    ss = []
    for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(ns + 'si'):
        ss.append(''.join(t.text or '' for t in si.iter(ns + 't')))
    root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    cells = {}
    for c in root.iter(ns + 'c'):
        ref = c.get('r')
        t = c.get('t')
        v = c.find(ns + 'v')
        isn = c.find(ns + 'is')
        val = ''
        if t == 's' and v is not None:
            val = ss[int(v.text)]
        elif v is not None:
            val = v.text or ''
        elif isn is not None:
            val = ''.join(x.text or '' for x in isn.iter(ns + 't'))
        cells[(re.match(r'[A-Z]+', ref).group(0), int(re.match(r'[A-Z]+(\d+)', ref).group(1)))] = val
    out = []
    for (col, r), val in list(cells.items()):
        if col != 'B':
            continue
        m = re.match(r'(1[1234]\d{3})_(.+)', val or '')
        if not m:
            continue
        code = m.group(1)
        name = m.group(2).replace('　', '').strip()
        pref = int(code[:2])
        if pref not in PREF_NAME:
            continue
        if not (cells.get(('C', r), '') or '').startswith('00_'):
            continue
        med = median_interp(cells, r)
        if med is None:
            continue
        out.append({'code': code, 'name': name, 'pref': pref, 'rent_median': med})
    return out


def main():
    # 1) e-stat extract (or reuse)
    if os.path.isfile(EXTRACT):
        munis = json.load(io.open(EXTRACT, encoding='utf-8'))
    else:
        munis = load_estat()
        io.open(EXTRACT, 'w', encoding='utf-8').write(json.dumps(munis, ensure_ascii=False, indent=1))

    # 2) geocode w/ cache
    cache = {}
    if os.path.isfile(GEO_CACHE):
        cache = json.load(io.open(GEO_CACHE, encoding='utf-8'))
    for m in munis:
        key = m['code']
        if key in cache:
            m['lat'], m['lng'] = cache[key]
            continue
        q = PREF_NAME[m['pref']] + m['name']
        lat, lng = geocode(q)
        if lat is None:
            # fallback: pref only
            lat, lng = geocode(PREF_NAME[m['pref']])
        m['lat'], m['lng'] = lat, lng
        cache[key] = [lat, lng]
        time.sleep(0.18)
    io.open(GEO_CACHE, 'w', encoding='utf-8').write(json.dumps(cache, ensure_ascii=False))

    # 3) merge 23-ward housingassist (old data) by matching name
    old = {}
    if os.path.isfile(OLD_RENT):
        od = json.load(io.open(OLD_RENT, encoding='utf-8'))
        for w in od.get('wards', []):
            old[w.get('ward_ja')] = w
    for m in munis:
        if m['pref'] == 13 and m['code'][2:5] == '100':
            # 特別区部(total) skip; we only merge individual wards below
            continue
        w = old.get(m['name'])
        if w:
            m['is_ward'] = True
            m['rent_1k'] = w.get('rent_1k')
            m['mom_pct'] = w.get('mom_pct', 0)
            m['yoy_pct'] = w.get('yoy_pct', 0)
            m['trend'] = w.get('trend', [])
        else:
            m['is_ward'] = False

    # 4) proj counts by name
    try:
        pj = json.load(io.open(os.path.join(BASE, 'data', 'projects.json'), encoding='utf-8'))
        cnt = {}
        for p in pj.get('projects', []):
            c = p.get('city') or ''
            if c:
                cnt[c] = cnt.get(c, 0) + 1
    except Exception:
        cnt = {}
    for m in munis:
        m['proj_count'] = cnt.get(m['name'], 0)

    # 5) quintile tiers across all 194
    rents = sorted(m['rent_median'] for m in munis)
    n = len(rents)
    cuts = [rents[int(n * p / 5)] for p in range(1, 5)]
    for m in munis:
        v = m['rent_median']
        if v <= cuts[0]:
            m['tier'] = 1
        elif v <= cuts[1]:
            m['tier'] = 2
        elif v <= cuts[2]:
            m['tier'] = 3
        elif v <= cuts[3]:
            m['tier'] = 4
        else:
            m['tier'] = 5
        m['rank'] = 0
    # rank desc by rent_median
    for i, m in enumerate(sorted(munis, key=lambda x: -x['rent_median']), 1):
        m['rank'] = i

    # 6) tier boundaries for legend
    tier_bounds = []
    for t in range(1, 6):
        vs = [m['rent_median'] for m in munis if m['tier'] == t]
        tier_bounds.append({'tier': t, 'lo': min(vs), 'hi': max(vs)})

    meta = {
        'source': 'e-Stat 住宅・土地統計調査 2023 (Rent116)',
        'metric': '月額賃料 中央値（全規模・専用住宅）',
        'note': '2023年確定値。全規模の中央値のため、1K単身向けより高めに出る場合あり。',
        'sub_source': '23区限定: housingassist Tokyo Rent Index (1K 専有面積中位月額)',
        'trend_23w': old.get('meta', {}).get('trend_23w', []),
        'official_check': old.get('meta', {}).get('official_check', ''),
        'tier_bounds': tier_bounds,
        'pref_counts': {PREF_CN[p]: sum(1 for m in munis if m['pref'] == p) for p in PREF_NAME},
        'total': len(munis),
    }
    out = {'meta': meta, 'municipalities': munis}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))

    s = []
    s.append('[OK] 一都三县 賃貸データ生成: %d 市区町村' % len(munis))
    s.append('  都道府県別: ' + ', '.join('%s=%d' % (PREF_CN[p], meta['pref_counts'][PREF_CN[p]]) for p in PREF_NAME))
    s.append('  賃料中央値 min=%d max=%d' % (min(rents), max(rents)))
    s.append('  5段階境界(万円): ' + ' / '.join('%.1f〜%.1f' % (b['lo']/10000, b['hi']/10000) for b in tier_bounds))
    io.open('_rent_data_log.txt', 'w', encoding='utf-8').write('\n'.join(s))


if __name__ == '__main__':
    main()
