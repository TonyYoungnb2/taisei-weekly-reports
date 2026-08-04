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


# 通用后缀/套话：几乎所有再开发项目都带这些词，若不剥离会让
# 「八重洲二丁目中地区第一種市街地再開発事業」与「築地二丁目地区第一種市街地再開発事業」
# 相似度虚高到 0.84，导致把不相干项目误合并。比对前一律剔除。
# 注意：不剥离「丁目」——丁目号是区分项目的关键信息
# （八重洲一丁目東B ≠ 八重洲二丁目中）。
_BOILERPLATE = [
    '第一種市街地再開発事業', '第二種市街地再開発事業', '市街地再開発事業',
    '市街地再開発準備組合', '市街地再開発組合', '再開発準備組合', '再開発事業',
    'まちづくり事業', '土地区画整理事業', '新築工事', '建替計画', '建て替え計画',
    '開発計画', '再開発', '再开发', '計画', '事業', '仮称', '地区',
]

# 丁目号：漢数字/阿拉伯数字都归一化成阿拉伯数字，用于“同区不同丁目”冲突检测
HAN2NUM = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
           '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}
_CHOME_RE = re.compile(r'([0-9０-９一二三四五六七八九十]+)丁目')


def _chome(s):
    out = set()
    for m in _CHOME_RE.finditer(s or ''):
        t = m.group(1)
        out.add(HAN2NUM.get(t, t.translate(str.maketrans('０１２３４５６７８９', '0123456789'))))
    return out


def _norm(s, strip_boilerplate=True):
    s = s or ''
    s = re.sub(r'[\s\-－‐・、。.,/()（）]', '', s)
    if strip_boilerplate:
        for w in _BOILERPLATE:
            s = s.replace(w, '')
    return s.lower()


def _sim(a, b):
    """剥离通用套话后比对。内置两道防误判保险：
       1) 丁目号冲突（一丁目 vs 二丁目）直接降分；
       2) 剥离后过短（<4字，如“八重洲”这类地名）要求完全相等，
          避免共享地名前缀的不同项目被误合并。"""
    ca, cb = _chome(a), _chome(b)
    if ca and cb and not (ca & cb):
        return 0.0

    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        na, nb = _norm(a, False), _norm(b, False)
    if not na or not nb:
        return 0.0

    # 短地名令牌（如“八重洲”“新宿”）不足以证明是同一个项目
    if min(len(na), len(nb)) < 4:
        return 1.0 if na == nb else 0.0

    base = SequenceMatcher(None, na, nb).ratio()
    # 完全包含且长度接近才视为强命中
    if (na in nb or nb in na) and min(len(na), len(nb)) / max(len(na), len(nb)) >= 0.6:
        base = max(base, 0.90)
    return base


def load_projects():
    if not os.path.isfile(PROJ):
        return {'version': 1, 'updated_at': '', 'projects': []}
    return json.load(io.open(PROJ, encoding='utf-8'))


def save_projects(d):
    from datetime import date
    d['updated_at'] = date.today().strftime('%Y-%m-%d')
    io.open(PROJ, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2))


# 分层阈值：高于 AUTO 才自动合并；介于两者之间新建并标记人工复核。
# 静默误合并会污染无关项目且难以发现，比多建一条（可用 merge 命令合）危险得多。
AUTO_MERGE = 0.75
REVIEW_MIN = 0.45


def match_existing(d, item):
    """返回 (project, score) 最佳匹配。"""
    best, best_score = None, 0.0
    for p in d['projects']:
        cands = [p['name']] + p.get('aliases', [])
        score = max(_sim(item.get('name', ''), c) for c in cands)
        if score > best_score:
            best, best_score = p, score
    return best, best_score


def merge_item(d, item):
    p, score = match_existing(d, item)
    if p is not None and score >= AUTO_MERGE:
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
        # 中等相似度：可能重复，标记出来等人工定夺，不静默合并
        if p is not None and score >= REVIEW_MIN:
            rec['needs_review'] = {'maybe_same_as': p['id'],
                                   'candidate_name': p['name'],
                                   'score': round(score, 3)}
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
    n_new = n_upd = n_review = 0
    for item in data:
        act, pid, score = merge_item(d, item)
        if act == 'NEW':
            n_new += 1
            tag = ' [待人工复核]' if score >= REVIEW_MIN else ''
            print('  [NEW] %s = %s (sim=%.0f%%)%s' % (pid, item.get('name', ''), score * 100, tag))
            if tag:
                n_review += 1
        else:
            n_upd += 1
            print('  [UPD] %s = %s (sim=%.0f%%)' % (pid, item.get('name', ''), score * 100))

    save_projects(d)
    print('[OK] 合并完成: 新建 %d / 更新 %d / 待复核 %d / 现有总计 %d'
          % (n_new, n_upd, n_review, len(d['projects'])))


if __name__ == '__main__':
    main()
