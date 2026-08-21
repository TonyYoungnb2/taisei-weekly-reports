# -*- coding: utf-8 -*-
"""月次快照: 抓取 housingassist Tokyo Rent Index 的 23 区 1K 中位月额,
存入 data/rent/history/<YYYY-MM>.json。每月一个点(同月重复运行自动跳过),
由 build_rent_data 汇集成每个区的真实月次趋势。

用法:
  python build_rent_snapshot.py            # 当前月份
  python build_rent_snapshot.py 2026-08   # 指定月份
依赖: curl.exe 可出网(Python socket 被沙盒禁用)。
"""
import io, os, re, sys, subprocess, datetime, json

BASE = os.path.dirname(os.path.abspath(__file__))
HIST_DIR = os.path.join(BASE, 'data', 'rent', 'history')
URL = 'https://housingassist.com/rent-index'
SRC = os.path.join(BASE, 'data', 'rent', '_ward_source_2026-07.json')

# English slug (housingassist URL) -> 日文区名
WARD_EN2JA = {
    'adachi': '足立区', 'katsushika': '葛飾区', 'edogawa': '江戸川区', 'nerima': '練馬区',
    'suginami': '杉並区', 'setagaya': '世田谷区', 'itabashi': '板橋区', 'arakawa': '荒川区',
    'ota': '大田区', 'kita': '北区', 'nakano': '中野区', 'sumida': '墨田区',
    'toshima': '豊島区', 'koto': '江東区', 'shinagawa': '品川区', 'taito': '台東区',
    'shinjuku': '新宿区', 'shibuya': '渋谷区', 'bunkyo': '文京区', 'chuo': '中央区',
    'meguro': '目黒区', 'chiyoda': '千代田区', 'minato': '港区',
}


def fetch_html():
    tmp = os.path.join(BASE, '_snap_tmp.html')
    r = subprocess.run(['curl.exe', '-s', '-L', '-A', 'Mozilla/5.0', URL, '-o', tmp],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0 or not os.path.isfile(tmp):
        raise RuntimeError('curl failed rc=%s' % r.returncode)
    h = io.open(tmp, encoding='utf-8', errors='replace').read()
    os.remove(tmp)
    return h


def parse(h):
    wards = []
    seen = set()
    for row in h.split('<tr'):
        m = re.search(r'/wards/([a-z]+)"', row)
        if not m:
            continue
        slug = m.group(1)
        if slug not in WARD_EN2JA:
            continue
        name = WARD_EN2JA[slug]
        if name in seen:
            continue
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
        # td[1]=1K, td[2]=1LDK, td[3]=2LDK, td[4]=0Key%, td[5]=Listings
        if len(tds) < 6:
            continue
        def yen(t):
            v = re.sub(r'[^\d,]', '', t)
            return int(v.replace(',', '')) if v else 0
        rent_1k = yen(tds[1])
        zero_key_pct = yen(tds[4])
        listings = yen(tds[5])
        if rent_1k <= 0:
            continue
        wards.append({'name': name, 'en': slug, 'rent_1k': rent_1k,
                      'zero_key_pct': zero_key_pct, 'listings': listings})
        seen.add(name)
    return wards


def backfill_from_source(month):
    """从既有 23 区源(含 rent_1k)造一个历史点,作为种子。"""
    if not os.path.isfile(SRC):
        return None
    d = json.load(io.open(SRC, encoding='utf-8'))
    wards = []
    for w in d.get('wards', []):
        wards.append({'name': w.get('ward_ja'), 'en': '', 'rent_1k': w.get('rent_1k'),
                      'zero_key_pct': w.get('zero_key_pct'), 'listings': w.get('listings')})
    return {'meta': {'month': month, 'source': 'housingassist Tokyo Rent Index (seed from _ward_source)',
                     'url': URL, 'fetched': 'backfilled-from-source'}, 'wards': wards}


def main(month=None):
    os.makedirs(HIST_DIR, exist_ok=True)
    if month is None:
        month = datetime.date.today().strftime('%Y-%m')
    out = os.path.join(HIST_DIR, month + '.json')
    if os.path.isfile(out):
        print('[SKIP] %s 已存在, 跳过(每月一个点)' % month)
        return

    # 种子月(首个历史点)从既有源回填, 避免空趋势
    if len([f for f in os.listdir(HIST_DIR) if f.endswith('.json')]) == 0 and month > '2026-07':
        seed = backfill_from_source('2026-07')
        if seed:
            io.open(os.path.join(HIST_DIR, '2026-07.json'), 'w', encoding='utf-8').write(
                json.dumps(seed, ensure_ascii=False, indent=1))
            print('[SEED] 回填 2026-07 种子点(来自既有23区源)')

    try:
        h = fetch_html()
        wards = parse(h)
    except Exception as e:
        print('[ERR] 抓取失败: %s' % e)
        return
    if len(wards) < 23:
        print('[WARN] 只解析到 %d 区(期望23), 不写入' % len(wards))
        return
    snap = {'meta': {'month': month, 'source': 'housingassist Tokyo Rent Index',
                     'url': URL, 'fetched': datetime.datetime.now().strftime('%Y-%m-%d')},
            'wards': wards}
    io.open(out, 'w', encoding='utf-8').write(json.dumps(snap, ensure_ascii=False, indent=1))
    print('[OK] %s 快照写入 %d 区 (例: 港区=%d, 足立区=%d)'
          % (month, len(wards),
             [w['rent_1k'] for w in wards if w['name'] == '港区'][0],
             [w['rent_1k'] for w in wards if w['name'] == '足立区'][0]))


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
