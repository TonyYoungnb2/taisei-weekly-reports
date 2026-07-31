#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_projects.py — 项目库非交互采集脚本（供 cron 调用，零 input()）。

设计：
  * cron 任务用 web_search 抓取本周真实东京开发/在建项目，整理成 JSON 数组，
    通过 --data 文件或直接喂入 stdin（JSON），本脚本做相似度去重后合并入 data/projects.json。
  * 相似度复用 project_tools._sim 逻辑（阈值 0.45）；命中现有项目则更新其
    last_updated / 补充 aliases；未命中则新建（id 自动顺延 P00x）。
  * 所有经纬度/地址为人工补录项，脚本不编造；cron 若抓到坐标可一并传入。

用法:
  python collect_projects.py --data _collected.json
  echo '[{"name":"...","developer":"...","category":"综合开发","status":"开发中",
          "prefecture":"東京都","city":"港区","district":"六本木","address":"...",
          "latitude":35.66,"longitude":139.73,"aliases":["别名1","别名2"]}]' | python collect_projects.py
"""
import io, os, re, sys, json
from difflib import SequenceMatcher

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, 'data', 'projects.json')

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


def _norm(s):
    s = s or ''
    s = re.sub(r'[\s\-－‐・、。.,/()（）]', '', s)
    return s.lower()


def _sim(a, b):
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def load_projects():
    if not os.path.isfile(PROJ):
        return {'version': 1, 'updated_at': '', 'projects': []}
    return json.load(io.open(PROJ, encoding='utf-8'))


def save_projects(d):
    from datetime import date
    d['updated_at'] = date.today().strftime('%Y-%m-%d')
    io.open(PROJ, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2))


def match_existing(d, item):
    """返回 (project, score) 最佳匹配，score>=0.45 视为命中。"""
    best, best_score = None, 0.0
    for p in d['projects']:
        cands = [p['name']] + p.get('aliases', [])
        score = max(_sim(item.get('name', ''), c) for c in cands)
        if score > best_score:
            best, best_score = p, score
    return best, best_score


def merge_item(d, item):
    p, score = match_existing(d, item)
    if p is not None and score >= 0.45:
        # 命中：补充 aliases + 更新 last_updated + 覆盖可更新的字段
        today = d['updated_at'] or ''
        new_aliases = list(p.get('aliases', []))
        for a in item.get('aliases', []):
            if a and a not in new_aliases:
                new_aliases.append(a)
        p['aliases'] = new_aliases
        p['last_updated'] = today
        # 若原 developer 为空而新传入有值，补上
        if (not p.get('developer') or p.get('developer') == '（開発者未記載）') and item.get('developer'):
            p['developer'] = item['developer']
        # 若原地址为空而新传入有值，补上
        for fld in ('address', 'latitude', 'longitude', 'status', 'city', 'district', 'prefecture'):
            if not p.get(fld) and item.get(fld) is not None:
                p[fld] = item[fld]
        return 'UPDATED', p['id'], score
    else:
        # 未命中：新建
        seq = len(d['projects']) + 1
        pid = 'P%03d' % seq
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        rec = {
            'id': pid,
            'name': item.get('name', '未命名项目'),
            'aliases': item.get('aliases', [item.get('name', '')]),
            'developer': item.get('developer', '（開発者未記載）'),
            'category': item.get('category', '其他'),
            'status': item.get('status', '规划'),
            'prefecture': item.get('prefecture', ''),
            'city': item.get('city', ''),
            'district': item.get('district', ''),
            'address': item.get('address', ''),
            'latitude': item.get('latitude'),
            'longitude': item.get('longitude'),
            'first_seen': today,
            'last_updated': today,
            'news_count': 0,
            'verified': bool(item.get('verified', False)),
        }
        d['projects'].append(rec)
        return 'NEW', pid, score


def main():
    data = None
    if '--data' in sys.argv:
        idx = sys.argv.index('--data') + 1
        if idx < len(sys.argv):
            data = json.load(io.open(sys.argv[idx], encoding='utf-8'))
    if data is None and not sys.stdin.isatty():
        try:
            raw = sys.stdin.read().strip()
            if raw:
                data = json.loads(raw)
        except Exception as e:
            print('[FAIL] stdin JSON 解析失败: %s' % e)
            return
    if not data:
        print('[FAIL] 未提供数据。用法: python collect_projects.py --data file.json 或 echo [...] | python collect_projects.py')
        return
    if not isinstance(data, list):
        data = [data]

    d = load_projects()
    n_new = n_upd = 0
    for item in data:
        act, pid, score = merge_item(d, item)
        if act == 'NEW':
            n_new += 1
            print('  [NEW] %s = %s (sim=%.0f%%)' % (pid, item.get('name', ''), score * 100))
        else:
            n_upd += 1
            print('  [UPD] %s = %s (sim=%.0f%%)' % (pid, item.get('name', ''), score * 100))

    save_projects(d)
    print('[OK] 合并完成: 新建 %d / 更新 %d / 现有总计 %d' % (n_new, n_upd, len(d['projects'])))


if __name__ == '__main__':
    main()
