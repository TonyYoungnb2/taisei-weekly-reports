#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地生成版：不走 GitHub API（沙盒环境 _socket DLL 被应用控制策略阻止），
直接在本地生成 reports/YYYY-MM-DD/report.html 和 index.html，
之后由外部 git add/commit/push 完成发布（EdgeOne/Actions 自动部署）。
"""
import sys, os, re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# generate_weekly 导入时会自行包装 sys.stdout 为 UTF-8，这里不再重复包装
import generate_weekly as gw

def main():
    print('[1/3] 构建本周报告HTML...')
    report_html = gw.build_report_html()

    today = datetime.now()
    date_folder = today.strftime('%Y-%m-%d')
    report_dir = os.path.join(BASE, 'reports', date_folder)
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, 'report.html')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_html)
    date_range_from, date_range_to = gw.get_week_range()
    print(f'      本周: {date_range_from} -- {date_range_to}')
    print(f'      已写入: reports/{date_folder}/report.html')

    print('[2/3] 扫描本地已有报告列表...')
    folders = []
    reports_root = os.path.join(BASE, 'reports')
    for name in os.listdir(reports_root):
        if re.match(r'\d{4}-\d{2}-\d{2}$', name) and \
           os.path.isfile(os.path.join(reports_root, name, 'report.html')):
            try:
                dt = datetime.strptime(name, '%Y-%m-%d')
                folders.append({
                    'folder': name,
                    'date_str': dt.strftime('%Y年%m月%d日'),
                    'week_num': dt.isocalendar()[1],
                    'sort_key': dt,
                })
            except Exception:
                pass
    folders.sort(key=lambda x: x['sort_key'], reverse=True)
    print(f'      共有 {len(folders)} 期报告')

    print('[3/3] 更新index.html...')
    index_html = gw.build_index_html(folders)
    with open(os.path.join(BASE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print('      index.html 更新成功 OK')

    print()
    print('=' * 50)
    print('[OK] 全部完成！')
    print(f'   报告: reports/{date_folder}/report.html')
    print('   （本地生成模式，随后由 git push 发布）')
    print('=' * 50)

if __name__ == '__main__':
    main()
