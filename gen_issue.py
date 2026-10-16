#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_issue.py — 补发/生成指定期号的半月报（reports/<date>/report.html）。
用法: python gen_issue.py 2026-10-15
generate_weekly.build_report_html(dt) 已支持指定基准日期，本脚本只是薄封装。"""
import io, os, sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import generate_weekly as gw


def build(date_str, write=True):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    html = gw.build_report_html(dt)
    if not write:
        return html, dt
    out_dir = os.path.join(BASE, 'reports', date_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'report.html')
    with io.open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return out_path, dt


if __name__ == '__main__':
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    path, dt = build(date_str)
    print('[OK] %s  (%s)' % (path, gw.report_issue_label(dt)))
    print('      date_range: %s' % gw.get_half_month_range(dt))
