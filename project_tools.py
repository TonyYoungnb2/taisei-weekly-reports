#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
project_tools.py — 房地产情报平台 Phase 0 数据运维工具（零 AI、零网络）。
设计原则（用户拍板）：
  * Project 由「新闻驱动」：录入新闻时系统按名称/aliases 做字符串相似度匹配，
    建议挂到已有 project 或新建，由人工确认。不调用任何 AI。
  * news(project_id 可空) 与 projects 两层解耦，从第一天就支持 Merge。
用法:
  python project_tools.py list
  python project_tools.py add-news --title "..." --source "..." --date 2026-08-01 --summary "..."
  python project_tools.py add-project --name "..." --developer "..." --category "住宅"
  python project_tools.py merge --from P002 --to P001     # 合并（把 from 的新闻并入 to，删 from）
  python project_tools.py stats                            # 项目数/新闻数概览
"""
import io, os, re, sys, json, glob
from difflib import SequenceMatcher

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, 'data', 'projects.json')
NEWS_DIR = os.path.join(BASE, 'data', 'news')

# GBK 终端会把含非 ASCII 的打印弄崩；强制 stdout 用 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


def load_projects():
    if not os.path.isfile(PROJ):
        return {'version': 1, 'updated_at': '', 'projects': []}
    return json.load(io.open(PROJ, encoding='utf-8'))


def save_projects(d):
    d['updated_at'] = _today()
    io.open(PROJ, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2))


def _today():
    from datetime import date
    return date.today().strftime('%Y-%m-%d')


def _norm(s):
    s = s or ''
    # 去空格/标点/全半角，仅留字母数字与假名汉字，做粗略归一
    s = re.sub(r'[\s\-－‐・、。.,/()（）]', '', s)
    return s.lower()


def _sim(a, b):
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def suggest_project(news_title):
    """返回最佳匹配 project 及相似度（无则 None）。"""
    d = load_projects()
    best, best_p, best_score = None, None, 0.0
    for p in d['projects']:
        cands = [p['name']] + p.get('aliases', [])
        score = max(_sim(news_title, c) for c in cands)
        if score > best_score:
            best, best_p, best_score = p, p, score
    if best and best_score >= 0.45:
        return best_p, best_score
    return None, best_score


def add_news(title, source, date, summary='', url='', url_text=''):
    p, score = suggest_project(title)
    print('相似度匹配: %s (%.0f%%)' % (('→ 建议挂到 [%s]' % p['id'] if p else '无匹配，建议新建'), score * 100))
    if p:
        choice = input('挂到现有项目 %s (%s)? [y=挂接 / n=新建] ' % (p['id'], p['name'])).strip().lower()
    else:
        choice = 'n'
    if choice == 'y' and p:
        pid = p['id']
    else:
        name = input('新项目名称(默认用标题前20字): ').strip() or title[:20]
        dev = input('开发商(可空): ').strip()
        cat = input('类别[住宅/商业/办公/物流/酒店/工业/综合开发/其他](默认其他): ').strip() or '其他'
        pid = _new_project(name, dev, cat)
    # 写入 news 月度分片
    month = date[:7] if date else _today()[:7]
    fpath = os.path.join(NEWS_DIR, month.replace('-', os.sep)[:7], month + '.json')
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    nd = {'version': 1, 'month': month, 'news': []}
    if os.path.isfile(fpath):
        nd = json.load(io.open(fpath, encoding='utf-8'))
    nid = 'N' + (date or _today()).replace('-', '') + '%02d' % (len(nd['news']) + 1)
    nd['news'].append({
        'id': nid, 'title': title, 'summary': summary, 'url': url, 'url_text': url_text,
        'publish_date': date, 'source': source, 'source_level': 'media',
        'project_id': pid, 'created_at': _today()
    })
    io.open(fpath, 'w', encoding='utf-8').write(json.dumps(nd, ensure_ascii=False, indent=2))
    # 更新 project 计数
    bump_count(pid)
    print('[OK] 新闻 %s 已录入，关联项目 %s' % (nid, pid))


def _new_project(name, dev, cat):
    d = load_projects()
    seq = len(d['projects']) + 1
    pid = 'P%03d' % seq
    d['projects'].append({
        'id': pid, 'name': name, 'aliases': [name], 'developer': dev or '（未記載）',
        'category': cat, 'status': '规划', 'prefecture': '', 'city': '', 'district': '',
        'address': '', 'latitude': None, 'longitude': None,
        'first_seen': _today(), 'last_updated': _today(), 'news_count': 0, 'verified': False
    })
    save_projects(d)
    print('[新建项目] %s = %s' % (pid, name))
    return pid


def bump_count(pid):
    d = load_projects()
    for p in d['projects']:
        if p['id'] == pid:
            p['news_count'] = count_news(pid)
            p['last_updated'] = _today()
    save_projects(d)


def count_news(pid):
    total = 0
    for fp in glob.glob(os.path.join(NEWS_DIR, '**', '*.json'), recursive=True):
        if os.path.basename(fp) == 'projects.json':
            continue
        try:
            nd = json.load(io.open(fp, encoding='utf-8'))
        except Exception:
            continue
        total += sum(1 for n in nd.get('news', []) if n.get('project_id') == pid)
    return total


def merge(frm, to):
    d = load_projects()
    projs = {p['id']: p for p in d['projects']}
    if frm not in projs or to not in projs:
        print('[FAIL] 项目不存在'); return
    # 改所有新闻的 project_id
    for fp in glob.glob(os.path.join(NEWS_DIR, '**', '*.json'), recursive=True):
        try:
            nd = json.load(io.open(fp, encoding='utf-8'))
        except Exception:
            continue
        changed = False
        for n in nd.get('news', []):
            if n.get('project_id') == frm:
                n['project_id'] = to; changed = True
        if changed:
            io.open(fp, 'w', encoding='utf-8').write(json.dumps(nd, ensure_ascii=False, indent=2))
    # 把 from 的 alias 并入 to，删 from
    to_p = projs[to]; fr_p = projs[frm]
    to_p['aliases'] = list(dict.fromkeys(to_p.get('aliases', []) + fr_p.get('aliases', [])))
    d['projects'] = [p for p in d['projects'] if p['id'] != frm]
    save_projects(d)
    bump_count(to)
    print('[OK] %s 已并入 %s，新闻关联已更新' % (frm, to))


def list_projects():
    d = load_projects()
    print('项目数: %d' % len(d['projects']))
    for p in d['projects']:
        print('  [%s] %s | %s | %s | 新闻%d | %s' % (
            p['id'], p['name'], p.get('developer'), p.get('status'),
            count_news(p['id']), '✓官方' if p.get('verified') else '媒体报道'))


def stats():
    d = load_projects()
    total_news = 0
    for fp in glob.glob(os.path.join(NEWS_DIR, '**', '*.json'), recursive=True):
        try:
            nd = json.load(io.open(fp, encoding='utf-8'))
        except Exception:
            continue
        total_news += len(nd.get('news', []))
    print('项目总数: %d' % len(d['projects']))
    print('新闻总数: %d' % total_news)
    print('已地理编码: %d' % sum(1 for p in d['projects'] if p.get('latitude')))


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == 'list':
        list_projects()
    elif cmd == 'stats':
        stats()
    elif cmd == 'add-news':
        kw = dict(a.split('=', 1) for a in args if '=' in a)
        add_news(kw.get('--title', ''), kw.get('--source', ''),
                 kw.get('--date', _today()), kw.get('--summary', ''),
                 kw.get('--url', ''), kw.get('--url_text', ''))
    elif cmd == 'add-project':
        kw = dict(a.split('=', 1) for a in args if '=' in a)
        _new_project(kw.get('--name', ''), kw.get('--developer', ''), kw.get('--category', '其他'))
    elif cmd == 'merge':
        f = next((a.split('=', 1)[1] for a in args if a.startswith('--from=')), None)
        t = next((a.split('=', 1)[1] for a in args if a.startswith('--to=')), None)
        merge(f, t)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
