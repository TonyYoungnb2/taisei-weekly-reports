#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给采集到的项目补经纬度（国土地理院 住所検索 API），并把同址项目散开。

为什么需要散开：维基/官方清单只到「区市」或「町丁目」粒度，同一个区里的多个项目
会拿到完全相同的坐标，地图上叠成一个点。这里对同址项目做「蜘蛛化」——以该点为中心
按固定半径均分到圆周上（半径 ~0.0035°，约 350m），保证每个项目都能被单独点到。
坐标仍以来源地址为基准，只是做了可视化的去重叠。

用法:
  python scripts/geocode_projects.py _collected_kanagawa.json [_collected_chiba.json ...]
"""
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE, 'data', '_geocode_cache.json')
UA = 'taisei-weekly-reports/1.0 (geocode; contact: taisei-r.com)'


def load_cache():
    if os.path.isfile(CACHE_FILE):
        try:
            return json.load(io.open(CACHE_FILE, encoding='utf-8'))
        except Exception:
            pass
    return {}


def geocode(addr, cache):
    if not addr:
        return None, None
    if addr in cache:
        return cache[addr]
    try:
        q = urllib.parse.quote(addr)
        url = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q=' + q
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode('utf-8'))
        if data:
            c = data[0]['geometry']['coordinates']
            res = [round(float(c[1]), 6), round(float(c[0]), 6)]
        else:
            res = [None, None]
    except Exception:
        res = [None, None]
    cache[addr] = res
    time.sleep(0.25)
    return res


def spiderfy(items, radius=0.0035):
    """同址项目均分到圆周，避免地图上完全重叠。"""
    groups = {}
    for it in items:
        if it.get('latitude') is not None:
            groups.setdefault(it.get('address') or '', []).append(it)
    moved = 0
    for addr, group in groups.items():
        n = len(group)
        if n < 2:
            continue
        lat0 = group[0]['latitude']
        lng0 = group[0]['longitude']
        for i, it in enumerate(group):
            ang = 2 * math.pi * i / n
            it['latitude'] = round(lat0 + radius * math.sin(ang), 6)
            it['longitude'] = round(lng0 + radius * math.cos(ang) / max(0.6, math.cos(math.radians(lat0))), 6)
            moved += 1
    return moved


def main(paths):
    cache = load_cache()
    for p in paths:
        items = json.load(io.open(p, encoding='utf-8'))
        for it in items:
            if it.get('latitude') is not None:
                continue
            lat, lng = geocode(it.get('address', ''), cache)
            it['latitude'], it['longitude'] = lat, lng
        moved = spiderfy(items)
        io.open(p, 'w', encoding='utf-8').write(json.dumps(items, ensure_ascii=False, indent=1))
        got = sum(1 for x in items if x.get('latitude') is not None)
        print('%-34s %3d 件 / 有坐标 %3d / 散开 %3d' % (os.path.basename(p), len(items), got, moved))
    io.open(CACHE_FILE, 'w', encoding='utf-8').write(json.dumps(cache, ensure_ascii=False, indent=0))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python scripts/geocode_projects.py a.json [b.json ...]')
        sys.exit(1)
    main(sys.argv[1:])
