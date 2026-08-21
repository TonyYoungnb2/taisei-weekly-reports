#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
release.py — 周报一键发布（生成 -> 校验 -> 推送）。
把原先「generate_local.py + 人工验证 + publish.py」三步合一，
校验不过则中止、绝不推送，从源头消灭「漏推 / 推了坏版」。
用法:
  python release.py            # 走完整流程
  python release.py --no-push  # 只生成+校验，不推送（本地验证用）
退出码: 0 = 发布成功, 1 = 校验失败中止, 2 = 推送失败
"""
import io, os, sys, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import generate_weekly as gw
import verify_report as vr
import publish as pb


def generate():
    print('[1/3] 构建本周报告 + 更新 index.html ...')
    report_html = gw.build_report_html()
    from datetime import datetime
    today = datetime.now()
    date_folder = today.strftime('%Y-%m-%d')
    report_dir = os.path.join(BASE, 'reports', date_folder)
    os.makedirs(report_dir, exist_ok=True)
    with io.open(os.path.join(report_dir, 'report.html'), 'w', encoding='utf-8') as f:
        f.write(report_html)
    # index.html 复用 generate_local 的扫描逻辑
    import re
    folders = []
    reports_root = os.path.join(BASE, 'reports')
    for name in os.listdir(reports_root):
        if re.match(r'\d{4}-\d{2}-\d{2}$', name) and \
           os.path.isfile(os.path.join(reports_root, name, 'report.html')):
            try:
                dt = datetime.strptime(name, '%Y-%m-%d')
                folders.append({'folder': name,
                                'date_str': dt.strftime('%Y年%m月%d日'),
                                'week_num': dt.isocalendar()[1], 'sort_key': dt})
            except Exception:
                pass
    folders.sort(key=lambda x: x['sort_key'], reverse=True)
    index_html = gw.build_index_html(folders)
    with io.open(os.path.join(BASE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print('      已生成: reports/%s/report.html  (index.html 已更新)' % date_folder)
    # 租金地图（方案B 独立页）随每次发布重生成
    # 賃貸相場データ（e-Stat 抽出 + GSI ジオコード）を毎回再生成
    try:
        import build_rent_data as brd
        brd.main()
        print('      [OK] 賃貸データ再生成: data/rent/*.json')
    except Exception as e:
        print('      [WARN] rent data 生成スキップ: %s' % e)
    try:
        import build_rentmap as brm
        brm.main()
        print('      已生成: rentmap.html （东京23区賃貸相場）')
    except Exception as e:
        print('      [WARN] rentmap 生成跳过: %s' % e)
    # 平台主界面（含「賃貸相場」入口）随每次发布重生成
    try:
        import build_projects as bp
        bp.main()
        print('      已生成: projects.html （平台主界面）')
    except Exception as e:
        print('      [WARN] projects 生成跳过: %s' % e)
    return date_folder


def main():
    no_push = '--no-push' in sys.argv
    date_folder = generate()

    print('[2/3] 校验报告 ...')
    ok = vr.verify(date_folder)
    if not ok:
        print('[ABORT] 校验未通过，已中止，未推送。请修复后再发布。')
        sys.exit(1)
    print('      [OK] 校验全部通过')

    if no_push:
        print('[3/3] --no-push 模式：跳过推送（本地已生成+校验通过）')
        sys.exit(0)

    print('[3/3] 推送到 GitHub（触发 EdgeOne 自动部署）...')
    pb.main()
    # publish.main 内部已 print 结果；这里不再二次判断退出码
    print('[DONE] 发布流程结束。EdgeOne 约 1-2 分钟生效。')


if __name__ == '__main__':
    main()
