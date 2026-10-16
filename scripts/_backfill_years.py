#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_backfill_years.py — 为 data/projects.json 回填 start_year / completion_year / window_status。

来源：
  * P020–P113 的竣工年已在 aliases 中（形如「2026年11月竣工」），自动解析。
  * P001–P126 缺年份项的人工核验结论（见 MEMORY / 调查报告），显式给出。
  * 仍未确证的（P002/P003/P114/P116/P117/P120/P122/P123/P125/P127–P134）保持 null。

window_status: completion_year 为 null 或 >= 今年-5 → active；否则 archived。
（今年-5 滚动，默认展示 active，老项目可切换显示。）
"""
import io, os, json, re
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(BASE, 'data', 'projects.json')
CUR = date.today().year  # 2026

YR = re.compile(r'(20[2-4]\d)\s*[年]')

# 人工核验竣工年（MISSING 项）
MANUAL_COMPLETION = {
    'P001': 2026, 'P004': 2030, 'P005': 2029, 'P006': 2035, 'P007': 2030,
    'P008': 2024, 'P009': 2029, 'P010': 2028, 'P011': 2030, 'P012': 2027,
    'P013': 2028, 'P014': 2026, 'P015': 2027, 'P016': 2029, 'P017': 2038,
    'P018': 2029, 'P019': 2026, 'P095': 2026, 'P115': 2026, 'P118': 2027,
    'P119': 2030, 'P121': 2027, 'P124': 2030, 'P126': 2028,
}
# 已知着工年（部分）
MANUAL_START = {
    'P004': 2025, 'P005': 2024, 'P006': 2028, 'P007': 2027, 'P009': 2024,
    'P010': 2025, 'P011': 2026, 'P013': 2023, 'P017': 2028, 'P018': 2026,
    'P124': 2025,
}
# aliases 多版本年份时的人工裁决（P034 两栋 2024/2028，已完工→取 2024）
MULTI_OVERRIDE = {'P034': 2024}


def completion_from_aliases(pid, aliases):
    if pid in MULTI_OVERRIDE:
        return MULTI_OVERRIDE[pid]
    yrs = []
    for a in (aliases or []):
        for m in YR.finditer(a):
            yrs.append(int(m.group(1)))
    if not yrs:
        return None
    return yrs[0]


def main():
    d = json.load(io.open(PROJ, encoding='utf-8'))
    n_filled = 0
    for p in d['projects']:
        pid = p['id']
        cy = None
        if pid in MANUAL_COMPLETION:
            cy = MANUAL_COMPLETION[pid]
        else:
            cy = completion_from_aliases(pid, p.get('aliases'))
        p['completion_year'] = cy
        p['start_year'] = MANUAL_START.get(pid)
        p['window_status'] = 'active' if (cy is None or cy >= CUR - 5) else 'archived'
        if cy is not None:
            n_filled += 1
    d['updated_at'] = date.today().strftime('%Y-%m-%d')
    io.open(PROJ, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2))
    with_yr = sum(1 for p in d['projects'] if p.get('completion_year'))
    print('filled=%d with_completion=%d / total=%d' % (n_filled, with_yr, len(d['projects'])))


if __name__ == '__main__':
    main()
