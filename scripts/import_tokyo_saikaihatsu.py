#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从「東京都 市街地再開発事業地区一覧」官方 CSV 导入大型再开发项目。

数据源：東京都都市整備局 市街地再開発事業地区一覧（令和7年10月31日現在・311地区）
  https://www.toshiseibi.metro.tokyo.lg.jp/machizukuri/shigaichi_seibi/sai-kai/saikaihatsu
  CSV: .../documents/d/toshiseibi/csv-bosai-data-kushi-data-chikuichiran

筛选口径（「大型开发」）：
  * 施行区域面積 >= 1.0 ha
  * 工事完了公告が 2019 年以降、または未完工（＝事業中/予定）
  * 2019〜2030 年に竣工見込みのもの（完了年が 2031 以降の既完了は除外しない：事業中扱い）

座標：国土地理院 住所検索 API（https://msearch.gsi.go.jp/address-search/AddressSearch）
  建物名ではなく「東京都+区市+地区名」で引く。取得できなければ lat/lng は null（地図に出ないだけ）。

用法:
  python scripts/import_tokyo_saikaihatsu.py --csv qa/tokyo_saikaihatsu.csv \
      --out _collected_tokyo.json [--no-geocode]
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PAGE = 'https://www.toshiseibi.metro.tokyo.lg.jp/machizukuri/shigaichi_seibi/sai-kai/saikaihatsu'
SOURCE_NAME = '東京都都市整備局 市街地再開発事業地区一覧（令和7年10月31日現在）'

ERA = {'S': 1925, 'H': 1988, 'R': 2018}
SHI_MAP = {
    '組合': '市街地再開発組合',
    '都': '東京都',
    '市': '市区（施行）',
    '機構': 'UR都市機構',
    '会社': '民間事業者（会社施行）',
    '個人': '地権者（個人施行）',
}


def era_year(s):
    s = (s or '').strip()
    m = re.match(r'([SHRS])(\d+)', s)
    if not m:
        return None
    return ERA.get(m.group(1), 0) + int(m.group(2))


def clean_city(s):
    s = (s or '').strip().replace('\n', '/')
    s = re.split(r'[、，,／/・]', s)[0].strip()
    return s


def geocode(addr, cache):
    """国土地理院 住所検索 → (lat, lng) or (None, None)"""
    if not addr:
        return None, None
    if addr in cache:
        return cache[addr]
    try:
        q = urllib.parse.quote(addr)
        url = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q=' + q
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode('utf-8'))
        if data:
            c = data[0]['geometry']['coordinates']
            res = (round(float(c[1]), 6), round(float(c[0]), 6))
        else:
            res = (None, None)
    except Exception:
        res = (None, None)
    cache[addr] = res
    time.sleep(0.25)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--out', default='_collected_tokyo.json')
    ap.add_argument('--min-ha', type=float, default=1.0)
    ap.add_argument('--since', type=int, default=2019)
    ap.add_argument('--no-geocode', action='store_true')
    a = ap.parse_args()

    raw = io.open(a.csv, encoding='utf-8-sig').read()
    rows = list(csv.reader(io.StringIO(raw)))

    out, seen = [], set()
    cache_file = os.path.join(BASE, 'data', '_geocode_cache.json')
    cache = {}
    if os.path.isfile(cache_file):
        try:
            cache = json.load(io.open(cache_file, encoding='utf-8'))
        except Exception:
            cache = {}

    for r in rows[4:]:
        if len(r) < 11:
            continue
        city = clean_city(r[0])
        if not city or city in ('区市名',):
            continue
        name = (r[2] or '').strip()
        if not name:
            continue
        try:
            ha = float((r[5] or '0').strip() or 0)
        except Exception:
            ha = 0.0
        if ha < a.min_ha:
            continue
        plan = era_year(r[7])
        appr = era_year(r[8])
        done = era_year(r[10])
        # 2019 年以前に竣工済みのものは対象外（＝2019〜2030 の開発に限定）
        if done is not None and done < a.since:
            continue
        if done is not None and done > 2030:
            continue

        # 地区名本身可能已含「地区」（如 六本木五丁目西地区），避免出现「地区地区」
        base = name if name.endswith('地区') else name + '地区'
        full_name = base + '市街地再開発事業'
        if full_name in seen:
            continue
        seen.add(full_name)

        area_txt = (r[4] or '').strip().replace('の一部', '').strip()
        addr = '東京都' + area_txt if area_txt else '東京都' + city
        status = '完工' if done else ('开发中' if appr else '规划')

        item = {
            'name': full_name,
            'aliases': [name + '再開発', name + '市街地再開発', '東京都' + city + name],
            'developer': SHI_MAP.get((r[3] or '').strip(), (r[3] or '').strip() or '不明'),
            'category': '综合开发',
            'status': status,
            'prefecture': '東京都',
            'city': city,
            'district': name,
            'address': addr,
            'area_ha': ha,
            'completion_year': done,
            'start_year': appr or plan,
            'source_url': SOURCE_PAGE,
            'source_name': SOURCE_NAME,
            'verified': True,
        }
        if not a.no_geocode:
            lat, lng = geocode(addr if len(addr) > 8 else '東京都' + city + name, cache)
            item['latitude'] = lat
            item['longitude'] = lng
        out.append(item)

    io.open(a.out, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    if not a.no_geocode:
        io.open(cache_file, 'w', encoding='utf-8').write(json.dumps(cache, ensure_ascii=False, indent=0))

    got = sum(1 for x in out if x.get('latitude'))
    print('[OK] %d 件 -> %s（坐标 %d 件，%.0f%%）' % (len(out), a.out, got, got * 100.0 / max(1, len(out))))
    from collections import Counter
    print('   状态:', Counter(x['status'] for x in out).most_common())
    print('   区市:', Counter(x['city'] for x in out).most_common(8))


if __name__ == '__main__':
    sys.exit(main())
