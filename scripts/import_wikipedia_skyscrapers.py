#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从维基百科「XX県の超高層建築物の一覧」抓取大型开发项目（2019〜2030）。

为什么用维基：
  * 该系列页面按「名称 / 高さ / 階数 / 竣工年 / 所在地 / 状態」的表格组织，
    正好对应「大型开发 + 竣工年 + 所在」三个维度；
  * 页面同时有「一覧」（已竣工）和「建設中・計画中」两段，覆盖在规划项目。

口径：
  * 高度 >= 100m（维基该系列页面本身的收录门槛，等于「大型」）
  * 竣工年 2019〜2032（含「2030年度」这种年度表述）
  * 只取一都三県（由 --pref 指定并校验所在地字段）

用法:
  python scripts/import_wikipedia_skyscrapers.py --page 神奈川県の超高層建築物の一覧 --pref 神奈川県 --out _collected_kanagawa.json
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = 'https://ja.wikipedia.org/w/api.php'
UA = 'taisei-weekly-reports/1.0 (data import; contact: taisei-r.com)'

PREF_CITY = {
    '神奈川県': ['横浜市', '川崎市', '相模原市', '横須賀市', '藤沢市', '茅ヶ崎市', '厚木市', '海老名市', '大和市'],
    '埼玉県': ['さいたま市', '川口市', '所沢市', '越谷市', '川越市', '草加市', '春日部市', '上尾市', '熊谷市'],
    '千葉県': ['千葉市', '船橋市', '柏市', '市川市', '松戸市', '浦安市', '流山市', '習志野市'],
}


def fetch_wikitext(page):
    q = urllib.parse.urlencode({
        'action': 'parse', 'page': page, 'prop': 'wikitext',
        'format': 'json', 'formatversion': '2', 'redirects': '1',
    })
    req = urllib.request.Request(API + '?' + q, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.loads(r.read().decode('utf-8'))
    return d['parse']['wikitext']


def clean(s):
    """清掉 wiki 标记，保留纯文本。"""
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'\{\{[^{}]*\}\}', '', s)
    s = re.sub(r'\[\[(?:ファイル|File|Image):[^\]]*\]\]', '', s, flags=re.I)
    s = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)
    s = re.sub(r"'''?", '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&nbsp;', ' ')
    return s.strip()


def split_rows(section):
    """把 wikitabke 拆成行 → 每行是单元格列表。"""
    rows = []
    for chunk in re.split(r'\n\|-', section)[1:]:
        cells = []
        # 单元格可能写成 |a || b || c 或每行一个 |
        for line in chunk.split('\n'):
            line = line.strip()
            if not line or line.startswith('|}'):
                continue
            if line[0] in '|!':
                body = line[1:]
                for c in re.split(r'\|\||!!', body):
                    c = re.sub(r'^[^|]*\|', '', c.strip()) if re.match(r'^[a-zA-Z\- ]+\|', c) else c
                    cells.append(c.strip())
        if cells:
            rows.append(cells)
    return rows


def year_of(s):
    m = re.search(r'(20\d{2})', s or '')
    return int(m.group(1)) if m else None


def height_of(s):
    m = re.search(r'(\d+(?:\.\d+)?)\s*m', (s or '').replace('メートル', 'm'), re.I)
    return float(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', required=True)
    ap.add_argument('--pref', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--since', type=int, default=2019)
    ap.add_argument('--until', type=int, default=2032)
    ap.add_argument('--min-height', type=float, default=100)
    a = ap.parse_args()

    wt = fetch_wikitext(a.page)
    print('[info] wikitext %d chars' % len(wt))

    out, seen = [], set()
    cities = PREF_CITY.get(a.pref, [])

    for sec_name in ('一覧', '建設中・計画中', '未完成の建築物', '建設中の建築物', '計画中の建築物'):
        # 标题层级不定（== / ===），统一匹配任意级别
        m = re.search(r'\n={2,4}\s*' + re.escape(sec_name) + r'\s*={2,4}\n(.*?)(?=\n={2,4}[^=])', wt, re.S)
        if not m:
            print('[warn] section not found:', sec_name)
            continue
        rows = split_rows(m.group(1))
        print('[info] %s: %d rows' % (sec_name, len(rows)))
        for cells in rows:
            txt = [clean(c) for c in cells]
            # 表格首列是排名序号（纯数字），跳过
            while txt and (not txt[0] or re.fullmatch(r'[\d\-–]+', txt[0])):
                txt = txt[1:]
            if not txt:
                continue
            name = txt[0]
            h = None
            yr = None
            loc = ''
            for c in txt[1:]:
                # 严格匹配整格，避免把备注里的年份/数字当成高度或竣工年
                if h is None and re.fullmatch(r'\d+(?:\.\d+)?\s*m', c.strip(), re.I):
                    h = height_of(c)
                elif yr is None and re.fullmatch(r'20\d{2}(?:年|年度)?', c.strip()):
                    yr = year_of(c)
                elif not loc and any(city in c for city in cities):
                    loc = c
            if not name or name.startswith('名称'):
                continue
            if h is None or h < a.min_height:
                continue
            if yr is None or yr < a.since or yr > a.until:
                continue
            city = next((c for c in cities if c in loc), '')
            if not city:
                continue
            key = (name, city, yr)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                'name': name,
                'developer': '（開発者未記載）',
                'category': '综合开发',
                'status': '完工' if sec_name == '一覧' else '开发中',
                'prefecture': a.pref,
                'city': city,
                'district': '',
                'address': a.pref + loc if loc else a.pref + city,
                'height_m': h,
                'completion_year': yr,
                'source_url': 'https://ja.wikipedia.org/wiki/' + urllib.parse.quote(a.page),
                'source_name': 'Wikipedia「%s」' % a.page,
                'verified': False,
            })

    io.open(a.out, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    print('[OK] %d 件 -> %s' % (len(out), a.out))
    for x in out[:8]:
        print('   ', x['city'], x['name'][:34], x['height_m'], x['completion_year'], x['status'])


if __name__ == '__main__':
    sys.exit(main())
