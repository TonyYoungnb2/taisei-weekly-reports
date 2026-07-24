#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
大誠不动產週報 生成スクリプト
使い方: python generate_weekly.py
每周実行 -> HTML生成 -> index.html更新 -> GitHubにpush -> EdgeOne Pages自動发布
"""
import os, sys, re, json
from datetime import datetime, timedelta

# ─── 設定 ───────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
REPO_OWNER   = 'TonyYoungnb2'
REPO_NAME    = 'taisei-weekly-reports'
BRANCH       = 'main'

# ⚠️ 公司名称规则（唯一真相源）：
# 我们是大誠「有限会社」，不是「株式会社」。
# 所有页面（报告页 / 分享卡 / 主页 / 仓库描述）统一引用此常量，
# 禁止在别处硬写「株式会社」，避免定时任务重生成时把名称写回错误版本。
COMPANY_NAME_CN = '大誠有限会社'   # 中文页面 / 主页
COMPANY_NAME_JP = '大誠有限会社'   # 日文页面（同样用「有限会社」）
COMPANY_SITE    = 'https://www.taisei-r.com/'

# ─── ニュースデータ（每周更新） ─────────────────────────────────────────
# [NOTE] 每周ここにデータを追加・編集してください
NEWS_DATA = {
    'policy': [
        {'date':'7月3日', 'source':'国土交通省', 'title':'国交省推进「ビデオ重説」活用 -- 年内正式引入宅建士视频立会免除制度',
         'body':'国交省为减轻宅建士及买卖双方的负担，推动将事先录制的「ビデオ重説」正式纳入活用体系，计划于年内实现正式运用。',
         'url':'https://www.fudousankeizai.co.jp/', 'url_text':'不动産経済新聞'},
        {'date':'7月3日', 'source':'観光庁', 'title':'観光庁创设地方废旅馆再生补助制度 -- 公募至2027年2月',
         'body':'観光庁创设针对地方温泉地等空置旅馆的拆除及迹地再生补助制度，与当地自治体合作，共同推进地区活化。',
         'url':'https://www.mlit.go.jp/index.html', 'url_text':'旅游局官网'},
        {'date':'7月10日', 'source':'国土交通省', 'title':'国交省发布25周年新政策宣传页',
         'body':'国交省迎来创设25周年，发布新版政策宣传页面，系统展示政策成果与未来方向。',
         'url':'https://www.mlit.go.jp/index.html', 'url_text':'国交省官网'},
    ],
    'deals': [
        {'date':'7月10日', 'source':'三井住友トラスト基礎研究所', 'title':'J-REIT不动产地价指数（6月）发布 -- 物流施设板块持续走强',
         'body':'SMTRI发布6月J-REIT不动产地价指数，物流施设类继续领跑，オフィス类温和复苏，整体NAV倍率改善。',
         'url':'https://www.smtri.jp/', 'url_text':'SMTRI官网'},
        {'date':'7月9日', 'source':'信義日本', 'title':'2026年以后摩天公寓达10万7408户',
         'body':'不动産経済研究所调查显示，日本20层以上摩天公寓2026年后期供给量比上次调查增加103栋、约2.6万户。',
         'url':'https://www.sinyijapan.com/', 'url_text':'信義日本'},
        {'date':'7月8日', 'source':'ニッセイ基礎研究所', 'title':'ESG因子对J-REIT个别股票表现的影响研究报告发布',
         'body':'SMTRI发布研究报告，分析ESG因子对J-REIT各銘柄的收益率差异影响，揭示可持续投资趋势。',
         'url':'https://www.smtri.jp/', 'url_text':'SMTRI官网'},
    ],
    'develop': [
        {'date':'7月9日', 'source':'信義日本', 'title':'银座五丁目大厦重建完成 -- 8月17日全面开业',
         'body':'银座五丁目的大型重建项目竣工，将于8月17日全面开业，成为银座核心区新地标，吸引全球高端品牌入驻。',
         'url':'https://www.sinyijapan.com/', 'url_text':'信義日本'},
        {'date':'7月上旬', 'source':'日刊不动産経済通信', 'title':'東京建物・穴吹兴産：高崎218戸分譲マンシ「アルファレジデンシア」',
         'body':'東京建物与穴吹兴産在群马县高崎市共同开发分譲マンシ，共218戸。',
         'url':'https://www.fudousankeizai.co.jp/', 'url_text':'不动産経済新聞'},
        {'date':'6月下旬', 'source':'週刊不动産経営', 'title':'大阪天王寺区最高层塔楼 The Park House 上本町 Tower 公开',
         'body':'三菱地所Residence开发的大阪天王寺区最高层塔楼开放样板间，大阪高端住宅市场竞争加剧。',
         'url':'https://www.biru-mall.com/', 'url_text':'ビルMall'},
        {'date':'6月28日', 'source':'日経不动産', 'title':'三菱地所Residence：品川区西五反田租赁マンシ 约1.6万㎡',
         'body':'三菱地所レジ在品川区西五反田开发大型租赁公寓，总开发面积约1.6万㎡，强化都心租赁住宅布局。',
         'url':'https://nfm.nikkeibp.co.jp/', 'url_text':'日経不动産'},
    ],
    'tech': [
        {'date':'7月上旬', 'source':'週刊住宅タイムズ', 'title':'分譲マンシ首次引入电梯联动清扫机器人STRIVER2',
         'body':'野村不动産引入可自动搭乘电梯的清扫机器人STRIVER2，预计削减20%清扫人力，开启智慧公寓管理新篇章。',
         'url':'https://www.sjt.co.jp/', 'url_text':'週刊住宅タイムズ'},
        {'date':'7月上旬', 'source':'週刊住宅タイムズ', 'title':'三井不Residential全面导入人脸识别＋智能家居系统',
         'body':'三井不动産レジデンシャル在「船桥」项目中全面引入人脸识别门禁与スマートホーム系统，提升安全与便利性。',
         'url':'https://www.sjt.co.jp/', 'url_text':'週刊住宅タイムズ'},
        {'date':'7月上旬', 'source':'週刊住宅タイムズ', 'title':'ミサワHome引入生成AI辅助通话内容登记',
         'body':'ミサワホーム引入生成AI实现通话自动摘要与行政登记，大幅削减事务负担，AI应用向住宅制造延伸。',
         'url':'https://www.sjt.co.jp/', 'url_text':'週刊住宅タイムズ'},
    ],
    'survey': [
        {'date':'7月上旬', 'source':'SUUMO', 'title':'50~60代居住不安调查：「修缮费增加」连续居首',
         'body':'SUUMO调查显示，37%对房屋老化与修缮成本感到不安，49%向往便利的都心·车站附近居住环境。',
         'url':'https://suumo.jp/', 'url_text':'SUUMO'},
        {'date':'6月下旬', 'source':'不动産経済研究所', 'title':'首都圈分譲マンシ㎡单价连续14个月同比上升',
         'body':'首都圈分譲マンしの㎡单价维持14个月连续前年同月比正增长，显示需求端韧性十足。',
         'url':'https://www.fudousankeizai.co.jp/', 'url_text':'不动産経済新聞'},
        {'date':'6月中旬', 'source':'全日本住宅産業協会', 'title':'5月新建住宅着工超5.7万戸 -- 前年比33.9%大幅增长',
         'body':'国交省数据显示，5月新建住宅着工件数同比大增33.9%，持家、贷家、分譲住宅全面增长。',
         'url':'https://www.zenjukyo.jp/', 'url_text':'全住協'},
        {'date':'6月中旬', 'source':'土地総合研究所', 'title':'不动产业业况等调查：経営状況悪化0.3P至7.1P',
         'body':'土地総研4月调查结果显示，不动产业経営状況恶化0.3个百分点至7.1P，中小开发商压力加大。',
         'url':'https://www.smtri.jp/', 'url_text':'SMTRI'},
        {'date':'6月中旬', 'source':'東日本レインズ', 'title':'中古マン成约件数3个月连续减少 -- 价格韧性尚存',
         'body':'東日本レインズ数据显示，首都圈中古マンシ成约件数连续3个月减少，但成交价格仍有支撑。',
         'url':'https://www.sjt.co.jp/', 'url_text':'週刊住宅タイムズ'},
    ],
}

# ─── 固定データ（每周更新） ─────────────────────────────────────────────
STATS = {
    'stat_1': '3.21%',   # フラット35主力金利
    'stat_2': '▲+3.4%',   # 首都圈中古成约（相对前年）
    'stat_3': '1,412戸',  # 新建マンシ供给
    'stat_4': '14个月',   # 连续上升月数
    'stat_5': '5万/坪',   # 東京駅周辺
}

TRENDS = [
    ('首都圈中古マンシ\n㎡单价（23区）', '5,078円 ▼0.2%', 'down'),
    ('首都圈新建マンシ\n供给户数（6月）', '1,412戸 ->', 'flat'),
    ('首都圈中古マンシ\n成约件数（6月）', '3.4%減 ▼', 'down'),
    ('東京都23区中古戸建\n平均价格', '4,254万円 ▲2.8%', 'up'),
    ('J-REIT 総合指数', '▲上昇中', 'up'),
]

FLAT35_RATE    = '3.21%'
FLAT35_MONTH   = '连续4个月上升（2026年7月時点）'
FLAT35_NOTE    = '日本央行政策利率维持1%，市场关注7月31日金融政策决定会议（MPP）动向。主要银行固定利率区间：住信SBI 3.15%〜 / auじぶん 3.19%〜 / 三井住友銀 3.20%〜'
XIAOXIA_COMMENT= ('贷款利率4连升，但首都圈新建マンシ价格依旧坚挺（连续14个月YoY+），供需紧张持续消化利率压力。'
                  '物流不动產方面外资与J-REIT持续扩张，近畿圈空室率趋零值得关注。中古市场成约件数3个月连减，需持续关注。')

SECTIONS_META = {
    'policy':  ('🏛️', '政策動向', 'POLICY',   'policy',  'label-blue'),
    'deals':   ('💼', '市場取引・投資', 'DEALS',    'deal',    'label-gold'),
    'develop': ('🏗️', '開発動向', 'DEVELOP',  'dev',     'label-green'),
    'tech':    ('🤖', '科技・イノベーション', 'TECH', 'tech',    'label-purple'),
    'survey':  ('📊', '調査・トレンド', 'RESEARCH', 'survey',  'label-red'),
}

# ─── CSS 样式（包含在HTML中，照搬 27/28 周大诚会社周报设计风格） ─────────────
CSS = """
  /* 不使用 Google Fonts：国内/微信环境会挂起导致截图卡死，改用系统字体 */
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Noto Sans SC', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #f0f2f5;
    color: #1a1a2e;
    line-height: 1.6;
  }
  /* Header */
  .header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #fff;
    padding: 40px 20px 30px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 30px 30px;
    animation: drift 20s linear infinite;
  }
  @keyframes drift { 0% { transform: translate(0,0); } 100% { transform: translate(30px,30px); } }
  .header .logo-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 18px;
    flex-wrap: wrap;
    position: relative;
    z-index: 1;
  }
  /* 返回主页按钮 */
  .home-btn {
    position: absolute;
    top: 14px; left: 16px;
    z-index: 2;
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,.16);
    color: #fff; text-decoration: none;
    font-size: 13px; font-weight: 700;
    padding: 7px 14px; border-radius: 20px;
    border: 1px solid rgba(255,255,255,.35);
    transition: background .15s;
  }
  .home-btn:hover { background: rgba(255,255,255,.30); }
  @media (max-width: 600px) {
    .home-btn { top: 10px; left: 10px; font-size: 12px; padding: 6px 11px; }
  }
  .header .logo-text {
    font-size: 2em;
    font-weight: 900;
    letter-spacing: 6px;
    color: #3b82f6;
    text-shadow: 0 0 20px rgba(59,130,246,0.4);
    line-height: 1;
  }
  .header .logo-wrap .title-group { text-align: left; }
  .header h1 {
    font-size: 1.8em;
    font-weight: 900;
    letter-spacing: 4px;
    position: relative;
    z-index: 1;
  }
  .header .subtitle {
    font-size: 0.95em;
    opacity: 0.7;
    margin-top: 8px;
    letter-spacing: 2px;
    position: relative;
    z-index: 1;
  }
  .header .date-range {
    display: inline-block;
    background: rgba(255,255,255,0.12);
    padding: 4px 18px;
    border-radius: 20px;
    font-size: 0.85em;
    margin-top: 12px;
    position: relative;
    z-index: 1;
  }
  .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
  /* Stats bar */
  .stats-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin: -30px auto 30px;
    max-width: 1000px;
    padding: 0 20px;
    position: relative;
    z-index: 2;
  }
  .stat-card {
    background: #fff;
    border-radius: 14px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
  }
  .stat-card .num {
    font-size: 1.6em;
    font-weight: 700;
    color: #0f3460;
  }
  .stat-card .num.gold { color: #c9a959; }
  .stat-card .num.orange { color: #e67e22; }
  .stat-card .num.green { color: #27ae60; }
  .stat-card .label {
    font-size: 0.75em;
    color: #888;
    margin-top: 4px;
  }
  /* Section */
  .section { margin-bottom: 28px; }
  .section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.2em;
    font-weight: 700;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 3px solid #0f3460;
  }
  .section-title .icon { font-size: 1.4em; }
  .section-title .tag {
    font-size: 0.55em;
    background: #0f3460;
    color: #fff;
    padding: 2px 10px;
    border-radius: 10px;
    font-weight: 500;
  }
  /* Grid for cards */
  .card-grid { display: grid; gap: 12px; }
  .card-grid.cols-2 {
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  }
  .card {
    background: #fff;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    transition: transform 0.15s, box-shadow 0.15s;
    border-left: 4px solid transparent;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.1);
  }
  .card.policy { border-left-color: #0f3460; }
  .card.deal { border-left-color: #c9a959; }
  .card.price { border-left-color: #e67e22; }
  .card.dev   { border-left-color: #27ae60; }
  .card.tech  { border-left-color: #8e44ad; }
  .card.survey { border-left-color: #e74c3c; }
  
  .card .date {
    font-size: 0.75em;
    color: #999;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .card .date .source {
    background: #f0f0f0;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 0.85em;
  }
  .card h3 {
    font-size: 0.95em;
    font-weight: 600;
    margin-bottom: 6px;
    line-height: 1.5;
  }
  .card p {
    font-size: 0.82em;
    color: #555;
    line-height: 1.6;
  }
  .card .source-link {
    display: block;
    font-size: 0.72em;
    margin-top: 8px;
    text-decoration: none;
    color: #0f3460;
    font-weight: 500;
    opacity: 0.7;
    transition: opacity 0.15s;
  }
  .card:hover .source-link { opacity: 1; }
  .card .source-link:hover { text-decoration: underline; }
  .card .label {
    display: inline-block;
    font-size: 0.65em;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 4px;
    margin-top: 6px;
  }
  .label-blue { background: #e8f0fe; color: #0f3460; }
  .label-gold { background: #fef8e0; color: #8a6d0b; }
  .label-green { background: #e6f7ed; color: #1a7a3a; }
  .label-orange { background: #fef0e0; color: #b8590a; }
  .label-purple { background: #f0e6ff; color: #6b2fa0; }
  .label-red { background: #fde8e8; color: #c0392b; }

  /* Key insight */
  .key-insight {
    background: linear-gradient(135deg, #fff8e1, #fff3cd);
    border: 1px solid #ffe082;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 28px;
  }
  .key-insight h3 {
    font-size: 1em;
    color: #b8860b;
    margin-bottom: 8px;
  }
  .key-insight p, .key-insight li {
    font-size: 0.85em;
    color: #666;
    line-height: 1.7;
  }
  .key-insight ul { padding-left: 18px; margin-top: 6px; }
  .key-insight li { margin-bottom: 4px; }
  .key-insight strong { color: #333; }

  /* Trend chart (CSS-based visual) */
  .trend-visual {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 16px 0;
  }
  .trend-item {
    flex: 1;
    min-width: 140px;
    background: #fff;
    border-radius: 10px;
    padding: 14px;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  }
  .trend-item .trend-label {
    font-size: 0.72em;
    color: #999;
  }
  .trend-item .trend-value {
    font-size: 1.3em;
    font-weight: 700;
    margin-top: 4px;
  }
  .trend-item .trend-value.up { color: #e74c3c; }
  .trend-item .trend-value.down { color: #27ae60; }
  .trend-item .trend-value.flat { color: #f39c12; }
  .trend-item .trend-arrow { font-size: 0.7em; margin-left: 2px; }

  /* Footer */
  .footer {
    text-align: center;
    padding: 30px 20px;
    color: #999;
    font-size: 0.75em;
    border-top: 1px solid #e0e0e0;
    margin-top: 20px;
  }
  .footer a { color: #0f3460; text-decoration: none; }

  /* Share card & modal */
  .share-btn-fab {
    position: fixed; bottom: 30px; right: 30px; z-index: 999;
    width: 56px; height: 56px; border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: #fff; border: none;
    box-shadow: 0 4px 20px rgba(59,130,246,0.4);
    cursor: pointer; font-size: 22px;
    display: flex; align-items: center; justify-content: center;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .share-btn-fab:hover { transform: scale(1.1); box-shadow: 0 6px 28px rgba(59,130,246,0.55); }
  .share-btn-fab:active { transform: scale(0.95); }
  .share-btn-fab .tooltip {
    position: absolute; right: 64px;
    background: rgba(0,0,0,0.8); color: #fff;
    padding: 6px 12px; border-radius: 6px; font-size: 13px;
    white-space: nowrap; opacity: 0; pointer-events: none;
    transition: opacity 0.2s;
  }
  .share-btn-fab:hover .tooltip { opacity: 1; }
  .share-modal {
    display: none; position: fixed; top:0; left:0; width:100%; height:100%;
    background: rgba(0,0,0,0.65); z-index: 9999;
    justify-content: center; align-items: center; backdrop-filter: blur(4px);
  }
  .share-modal.show { display: flex; }
  .share-modal .modal-box {
    background: #fff; border-radius: 20px; padding: 24px;
    max-width: 580px; width: 95%;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    display: flex; flex-direction: column; align-items: center;
  }
  .share-modal .modal-box .modal-header {
    display: flex; justify-content: space-between; align-items: center;
    width: 100%; margin-bottom: 16px;
  }
  .share-modal .modal-box .modal-header span { color: #475569; font-size: 14px; font-weight: 600; }
  .share-modal .modal-box .modal-header .close-btn {
    background: none; border: none; color: #666;
    font-size: 28px; cursor: pointer; line-height: 1;
  }
  .share-modal .modal-box .modal-header .close-btn:hover { color: #1e293b; }
  #share-card {
    width: 540px;
    background: #fff;
    border-radius: 16px; overflow: hidden; position: relative;
    font-family: "Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
  }
  #share-card .card-dots {
    position: absolute; top:0; left:0; width:100%; height:100%;
    background: radial-gradient(circle, rgba(59,130,246,0.06) 1px, transparent 1px);
    background-size: 22px 22px; pointer-events: none; z-index: 0;
  }
  #share-card .card-top-accent {
    position: relative; z-index: 1; height: 6px;
    background: linear-gradient(90deg, #3b82f6, #60a5fa, #3b82f6);
  }
  #share-card .card-content { position: relative; z-index: 1; padding: 28px 32px 24px; }
  #share-card .card-logo {
    font-size: 34px; font-weight: 900; letter-spacing: 8px;
    color: #1a56db; line-height: 1;
  }
  #share-card .card-meta { font-size: 11px; color: #94a3b8; letter-spacing: 3px; margin-top: 4px; text-transform: uppercase; }
  #share-card .card-date-badge {
    display: inline-block; background: #eff6ff;
    border: 1px solid #bfdbfe;
    padding: 4px 16px; border-radius: 20px; font-size: 13px; color: #2563eb; margin-top: 14px;
  }
  #share-card .card-divider {
    border: none; height: 1px;
    background: linear-gradient(90deg, transparent, #dbeafe, transparent);
    margin: 16px 0;
  }
  #share-card .card-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 14px 0; }
  #share-card .card-stat-box {
    background: #f8fafc; border: 1px solid #e2e8f0
    border-radius: 12px; padding: 14px 16px;
  }
  #share-card .card-stat-box .stat-num { font-size: 24px; font-weight: 700; color: #1e293b; line-height: 1.2; }
  #share-card .card-stat-box .stat-num .stat-arrow { font-size: 14px; margin-left: 4px; }
  #share-card .card-stat-box .stat-num .stat-arrow.up { color: #f87171; }
  #share-card .card-stat-box .stat-num .stat-arrow.down { color: #34d399; }
  #share-card .card-stat-box .stat-num .stat-arrow.flat { color: #fbbf24; }
  #share-card .card-stat-box .stat-label { font-size: 11px; color: #64748b; margin-top: 4px; line-height: 1.4; }
  #share-card .card-highlights-title { font-size: 13px; color: #64748b; letter-spacing: 2px; margin-bottom: 10px; }
  #share-card .card-highlights { list-style: none; padding: 0; margin: 0; }
  #share-card .card-highlights li {
    padding: 7px 0; font-size: 13px; color: #475569; line-height: 1.5;
    border-bottom: 1px solid #f1f5f9;
  }
  #share-card .card-highlights li:last-child { border-bottom: none; }
  #share-card .card-bottom {
    margin-top: 16px; padding-top: 14px;
    border-top: 1px solid #e2e8f0;
    display: flex; justify-content: space-between; align-items: center;
  }
  #share-card .card-bottom .brand { font-size: 11px; color: #64748b; }
  #share-card .card-bottom .cta { font-size: 11px; color: #3b82f6; font-weight: 500; }
  .share-modal .modal-box .download-btn {
    margin-top: 18px; padding: 12px 40px; border: none; border-radius: 30px;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: #fff; font-size: 15px; font-weight: 600; cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
    box-shadow: 0 4px 15px rgba(59,130,246,0.35);
  }
  .share-modal .modal-box .download-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(59,130,246,0.45); }
  .share-modal .modal-box .download-btn:active { transform: scale(0.97); }
  .share-modal .modal-box .download-btn.loading { opacity: 0.7; pointer-events: none; }
  .share-modal .modal-box .hint { color: #94a3b8; font-size: 12px; margin-top: 8px; }
  #share-card-container { margin: 12px auto; }
  #share-card-container .share-card { max-width: 340px; margin: 0 auto; }
    @media (max-width: 640px) {
    .header h1 { font-size: 1.5em; }
    .stats-bar { grid-template-columns: repeat(2, 1fr); margin-top: -20px; }
    .card-grid.cols-2 { grid-template-columns: 1fr; }
    .share-btn-fab { bottom: 18px; right: 18px; width: 48px; height: 48px; font-size: 18px; }
    .share-modal .modal-box { padding: 16px; }
    #share-card { width: 100%; }
    #share-card .card-content { padding: 20px 18px; }
  }
"""

# ─── 辅助函数 ──────────────────────────────────────────────────────────

def get_week_range():
    """获取本周的日期范围（周一~周日）"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    def fmt(d):
        s = d.strftime('%Y年%m月%d日')
        # strip leading zeros
        s = s.replace('年0','年').replace('月0','月')
        return s
    return fmt(monday), fmt(sunday)

def week_number():
    """今年的第几周"""
    today = datetime.now()
    return today.isocalendar()[1]

def render_news_card(news, accent_class, label_class):
    meta  = f'<div class="date">{news["date"]} <span class="source">{news["source"]}</span></div>'
    title = f'<h3>{news["title"]}</h3>'
    body  = f'<p>{news["body"]}</p>'
    link  = f'<a href="{news["url"]}" target="_blank" rel="noopener" class="source-link">📖 阅读原文 →</a>'
    return f'''<div class="card {accent_class}">
  {meta}
  {title}
  {body}
  <span class="label {label_class}">{news["source"]}</span>
  {link}
</div>'''

def render_news_section(key):
    meta = SECTIONS_META[key]
    icon, title, tag, accent_class, label_class = meta
    items = NEWS_DATA.get(key, [])
    cards_html = '\n'.join(render_news_card(n, accent_class, label_class) for n in items)
    return f'''<div class="section">
  <div class="section-title">
    <span class="icon">{icon}</span> {title}
    <span class="tag">{tag}</span>
  </div>
  <div class="card-grid cols-2">
{cards_html}
  </div>
</div>'''

def build_report_html():
    """构建本周报告HTML（设计风格照搬 27/28 周大诚会社周报）"""
    date_from, date_to = get_week_range()
    date_range = f'{date_from} — {date_to}'
    today_str  = datetime.now().strftime('%Y年%m月%d日')
    week_num   = week_number()

    # 热点速览（用于分享卡自动抓取 #hotlist）
    hot_items = [
        '国交省推进「ビデオ重説」制度 — 年内引入视频重要事项说明，减轻宅建士与买卖双方负担',
        '観光庁创设地方废旅馆再生补助制度 — 地方温泉地空置旅馆迎新生，公募至2027年2月',
        '首都圈新建マンシ持续高价 — ㎡单价连续14个月同比上升，供应户数维持1,400户以上',
        '银座五丁目大厦重建完成 — 8月17日全面开业，成为银座新地标',
        '外资持续布局日本物流不动產 — 近畿圈物流空室率趋零值得关注',
    ]
    hot_html = '\n'.join(f'<li><strong>{item.split(" — ")[0]}</strong> — {item.split(" — ")[1]}</li>' for item in hot_items)

    # 顶部统计卡（#statsBar，分享卡自动抓取）
    stat_cards = [
        ('gold',   STATS["stat_1"], 'フラット35 主力金利（7月時点）'),
        ('orange', STATS["stat_2"], '首都圈中古マンシ 成约件数（前年比）'),
        ('green',  STATS["stat_3"], '首都圈新建マンシ 供给户数（6月）'),
        ('',       STATS["stat_4"], 'マンシ㎡单价 连续上升月数'),
        ('gold',   STATS["stat_5"], '東京駅周辺 成约赁料'),
    ]
    stats_html = ''
    for color, num, label in stat_cards:
        cls = f' num {color}' if color else ' num'
        stats_html += f'''    <div class="stat-card">
      <div class="{cls.strip()}">{num}</div>
      <div class="label">{label}</div>
    </div>
'''

    # 市场趋势（trend-visual）
    trend_html = ''
    for label, value, color_cls in TRENDS:
        arrow = ''
        if '▲' in value: arrow = ' ▲'
        elif '▼' in value: arrow = ' ▼'
        trend_html += f'''    <div class="trend-item">
      <div class="trend-label">{label}</div>
      <div class="trend-value {color_cls}">{value}{arrow}</div>
    </div>
'''

    news_sections_html = '\n'.join(render_news_section(k) for k in ['policy','deals','develop','tech','survey'])

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="大誠有限会社専用不動產週報 {date_range}">
<title>大誠不动產週報 {date_range}</title>
<style>{CSS}</style>
</head>
<body>

<div class="header">
  <a href="../../index.html" class="home-btn">🏠 返回主页</a>
  <div class="logo-wrap">
    <span class="logo-text">TAISEI</span>
    <div class="title-group">
      <h1>大诚会社専用不動產週報</h1>
      <div class="subtitle">政策 · 市場 · 開発 · トレンド</div>
      <div class="date-range" id="headerDateRange">📅 {date_range}</div>
    </div>
  </div>
</div>

<!-- Stats -->
<div class="stats-bar" id="statsBar">
{stats_html}</div>

<div class="container">

<!-- 热点速览 -->
<div class="key-insight">
  <h3>🔥 本周热点速览</h3>
  <ul id="hotlist">
{hot_html}
  </ul>
</div>

<!-- Market Trend -->
<div class="section">
  <div class="section-title">
    <span class="icon">📊</span> 市場トレンド
    <span class="tag">MARKET</span>
  </div>
  <div class="trend-visual">
{trend_html}  </div>
</div>

{news_sections_html}

<!-- 贷款利率趋势 -->
<div class="key-insight">
  <h3>📈 贷款利率趋势</h3>
  <p><strong>フラット35：</strong>{FLAT35_RATE}（{FLAT35_MONTH}）。{FLAT35_NOTE}</p>
  <p style="margin-top:10px;"><strong>💡 小虾点评：</strong>{XIAOXIA_COMMENT}</p>
</div>

</div>

<div class="footer">
  <p>📡 数据来源：国土交通省 / 日経不動産マーケット情報 / 週刊住宅タイムズ / 週刊不動産経営 / 東京カンテイ / SUUMO / 不動産経済研究所 / 東日本レインズ / R.E.port</p>
  <p style="margin-top:4px;">Generated by 🦐 小虾 · {today_str} · 东京 · {COMPANY_NAME_JP} 専用</p>
</div>

<!-- ===== Floating Share Button ===== -->
<button class="share-btn-fab" id="shareBtn" onclick="openShareModal()">
  📸
  <span class="tooltip">生成朋友圈卡片</span>
</button>

<!-- ===== Share Modal ===== -->
<div class="share-modal" id="shareModal">
  <div class="modal-box">
    <div class="modal-header">
      <span>📸 朋友圈卡片预览</span>
      <button class="close-btn" onclick="closeShareModal()">✕</button>
    </div>
    <div id="share-card-container"></div>
    <button class="download-btn" id="downloadBtn" onclick="copyCard()">📋 复制文案</button>
    <div class="hint">手机：长按上方卡片截图保存 · 电脑：截图保存 · 或点按钮复制文字发朋友圈</div>
  </div>
</div>

<script>
const COMPANY_NAME_JP = '大誠有限会社';
const COMPANY_SITE = 'https://www.taisei-r.com/';
function getDateRange() {{
  const el = document.getElementById('headerDateRange');
  return el ? el.textContent.trim() : '📅 2026年6月 — 6月';
}}

function getStats() {{
  const cards = document.querySelectorAll('#statsBar .stat-card');
  const stats = [];
  cards.forEach(c => {{
    const num = c.querySelector('.num');
    const label = c.querySelector('.label');
    if (num && label) {{
      stats.push({{
        num: num.textContent.trim(),
        label: label.textContent.trim().replace(/\\s+/g, ' ')
      }});
    }}
  }});
  return stats;
}}

function getHighlights() {{
  const items = document.querySelectorAll('#hotlist li');
  const highlights = [];
  items.forEach(li => {{
    const txt = li.textContent.trim().replace(/^\\s*[—\\-–]\\s*/, '');
    if (txt) highlights.push(txt);
  }});
  return highlights.slice(0, 4);
}}

function buildShareCard() {{
  const dateRange = getDateRange();
  const stats = getStats();
  const highlights = getHighlights();

  const arrowClass = (txt) => {{
    if (txt.includes('▼') || txt.includes('下落') || txt.includes('減')) return 'down';
    if (txt.includes('▲') || txt.includes('上昇') || txt.includes('増')) return 'up';
    return 'flat';
  }};
  const arrowSymbol = (txt) => {{
    if (txt.includes('▼')) return '▼';
    if (txt.includes('▲')) return '▲';
    return '→';
  }};

  let statsHTML = '';
  stats.forEach((s, i) => {{
    if (i >= 4) return;
    const isUp = arrowClass(s.num);
    const arrow = arrowSymbol(s.num);
    statsHTML += '<div class="card-stat-box">' +
      '<div class="stat-num">' + s.num + ' <span class="stat-arrow ' + isUp + '">' + arrow + '</span></div>' +
      '<div class="stat-label">' + s.label + '</div>' +
    '</div>';
  }});

  let hlHTML = '';
  const icons = ['🔴', '🟡', '🟢', '🔵'];
  highlights.forEach((h, i) => {{
    hlHTML += '<li><span class="hl-icon">' + (icons[i] || '▸') + '</span>' + h + '</li>';
  }});

  return '<div id="share-card">' +
    '<div class="card-dots"></div>' +
    '<div class="card-top-accent"></div>' +
    '<div class="card-content">' +
      '<div class="card-logo">TAISEI</div>' +
      '<div class="card-meta">WEEKLY REAL ESTATE REPORT</div>' +
      '<div class="card-date-badge">📅 ' + dateRange.replace('📅 ', '') + '</div>' +
      '<hr class="card-divider">' +
      '<div class="card-stats">' + statsHTML + '</div>' +
      '<hr class="card-divider">' +
      '<div class="card-highlights-title">✦ WEEKLY HIGHLIGHTS</div>' +
      '<ul class="card-highlights">' + hlHTML + '</ul>' +
      '<div class="card-bottom">' +
        '<span class="brand">' + COMPANY_NAME_JP + ' · 不動産専門</span>' +
        '<span class="cta">🔍 詳細は公式チャンネルで</span>' +
      '</div>' +
    '</div>' +
  '</div>';
}}

function buildCardText() {{
  const dateRange = getDateRange();
  const stats = getStats();
  const highlights = getHighlights();
  let t = '【' + COMPANY_NAME_JP + ' 日本不动产周报】\\n' + dateRange + '\\n\\n';
  stats.slice(0,4).forEach(function(s) {{ t += '• ' + s.label + '：' + s.num + '\n'; }});
  t += '\\n本周焦点：\\n';
  highlights.forEach(function(h) {{ t += '▸ ' + h + '\n'; }});
  t += '\\n详情见官方频道 / ' + COMPANY_SITE;
  return t;
}}

function openShareModal() {{
  document.getElementById('shareModal').classList.add('show');
  document.body.style.overflow = 'hidden';
  const container = document.getElementById('share-card-container');
  container.innerHTML = buildShareCard();
}}

function closeShareModal() {{
  document.getElementById('shareModal').classList.remove('show');
  document.body.style.overflow = '';
}}

document.getElementById('shareModal').addEventListener('click', function(e) {{
  if (e.target === this) closeShareModal();
}});

document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') closeShareModal();
}});

function copyCard() {{
  const btn = document.getElementById('downloadBtn');
  const text = buildCardText();
  function ok() {{
    const old = btn.textContent;
    btn.textContent = '✅ 已复制，去粘贴吧';
    setTimeout(function() {{ btn.textContent = old; }}, 1800);
  }}
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(ok).catch(function() {{ fallbackCopy(text); }});
  }} else {{
    fallbackCopy(text);
  }}
}}

function fallbackCopy(text) {{
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {{ document.execCommand('copy'); }} catch (e) {{}}
  document.body.removeChild(ta);
  const btn = document.getElementById('downloadBtn');
  btn.textContent = '✅ 已复制，去粘贴吧';
  setTimeout(function() {{ btn.textContent = '📋 复制文案'; }}, 1800);
}}
</script>
</body>
</html>'''

    return html

def build_index_html(reports):
    """构建中文可视化索引页HTML（精美主页）"""
    today_str = datetime.now().strftime('%Y年%m月%d日')
    year = datetime.now().year

    reports_sorted = list(reports)
    latest = reports_sorted[0] if reports_sorted else None

    REPORT_LIMIT = 3  # 首页「往期周报」默认展示数量；超过则显示「查看更多」按钮
    total_reports = len(reports_sorted)

    # 报告网格（最新一期标记「最新」徽标，超出限制部分默认折叠）
    report_cards = ''
    for idx, r in enumerate(reports_sorted):
        folder = r['folder']
        date_str = r['date_str']
        week_num = r['week_num']
        badge = '<span class="card-badge">最新</span>' if idx == 0 else ''
        hidden = ' report-hidden' if idx >= REPORT_LIMIT else ''
        report_cards += f'''
    <div class="report-card{' latest' if idx==0 else ''}{hidden}">
      <a href="reports/{folder}/report.html" class="card-link">
        {badge}
        <div class="card-date">{date_str}</div>
        <div class="card-title">第 {week_num} 期 · 日本不动产周报</div>
        <div class="card-meta">{year}年 · 东京市场动态</div>
        <div class="card-arrow">阅读全文 →</div>
      </a>
    </div>'''

    # 查看更多按钮（仅当往期超过限制时显示）
    if total_reports > REPORT_LIMIT:
        show_more = f'''
  <div class="more-wrap">
    <button class="more-btn" id="moreBtn" onclick="toggleMore()">查看更多往期周报（共 {total_reports} 期） ↓</button>
  </div>'''
    else:
        show_more = ''

    # 客户端展开/收起脚本（无需独立归档页）
    script_js = '''
<script>
function toggleMore(){
  var hidden = document.querySelectorAll('.report-hidden');
  var btn = document.getElementById('moreBtn');
  var currentlyHidden = hidden.length && hidden[0].style.display !== 'block';
  for (var i=0;i<hidden.length;i++){ hidden[i].style.display = currentlyHidden ? 'block' : 'none'; }
  btn.textContent = currentlyHidden ? '收起 ↑' : '查看更多往期周报（共 N 期） ↓';
}
</script>'''
    script_js = script_js.replace('N', str(total_reports))

    # 最新一期特写卡
    if latest:
        feat_date = latest['date_str']
        feat_week = latest['week_num']
        feat_folder = latest['folder']
        featured_html = f'''
    <a href="reports/{feat_folder}/report.html" class="featured">
      <div class="featured-left">
        <span class="featured-tag">📌 最新一期</span>
        <h2 class="featured-title">日本不动产周报</h2>
        <div class="featured-date">{feat_date} · 第 {feat_week} 期</div>
        <p class="featured-desc">覆盖政策动向、市场交易、开发动态、科技前沿与调查数据五大板块，
        精选本周日本（以东京圈为主）不动产核心资讯，附小虾点评。</p>
        <span class="featured-cta">立即阅读 →</span>
      </div>
      <div class="featured-right">
        <div class="ring"><span>{feat_week}</span><em>期</em></div>
      </div>
    </a>'''
    else:
        featured_html = ''

    # 栏目覆盖
    sections_cov = [
        ('🏛️', '政策动向', '地价 · 税制 · 金融政策'),
        ('💹', '市场交易', '新盘 · 房贷 · 投资回报'),
        ('🏗️', '开发动态', '新项目 · 城市更新'),
        ('🤖', '科技前沿', '建设DX · GIS · 智能家居'),
        ('📊', '调查数据', '地价指数 · 区域行情'),
    ]
    cov_html = ''
    for icon, name, sub in sections_cov:
        cov_html += f'''
      <div class="cov-item">
        <div class="cov-icon">{icon}</div>
        <div class="cov-name">{name}</div>
        <div class="cov-sub">{sub}</div>
      </div>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大誠有限会社 · 日本不动产周报</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', sans-serif;
  background: #f4f7fb; color: #1f2733; line-height: 1.7; min-height: 100vh;
}}
/* Hero */
.hero {{
  background: linear-gradient(135deg, #12457f 0%, #1a5fb4 55%, #2a7fd4 100%);
  color: #fff; text-align: center; padding: 56px 20px 64px;
  position: relative; overflow: hidden;
}}
.hero::before {{
  content: ''; position: absolute; top: -120px; right: -80px; width: 320px; height: 320px;
  background: radial-gradient(circle, rgba(255,255,255,.14), transparent 70%); border-radius: 50%;
}}
.hero::after {{
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg, #ffd479, #fff3cd, #ffd479);
}}
.hero-brand {{ font-size: 13px; letter-spacing: 7px; color: #cfe4ff; margin-bottom: 10px; font-weight: 700; }}
.hero h1 {{ font-size: 30px; font-weight: 900; letter-spacing: 2px; margin-bottom: 10px; }}
.hero p {{ font-size: 14px; color: #d6e8ff; }}
.hero-updated {{ margin-top: 16px; font-size: 12px; color: #a9cdf2; }}
.container {{ max-width: 960px; margin: 0 auto; padding: 0 16px 60px; }}
/* Featured */
.featured {{
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  background: #fff; border-radius: 20px; padding: 30px 34px; margin: -34px auto 36px;
  position: relative; z-index: 2; text-decoration: none; color: inherit;
  box-shadow: 0 12px 36px rgba(26,95,180,.18); border: 1px solid #e3edf9;
  transition: transform .15s ease, box-shadow .15s ease;
}}
.featured:hover {{ transform: translateY(-3px); box-shadow: 0 16px 44px rgba(26,95,180,.26); }}
.featured-tag {{ display: inline-block; background: #fff3cd; color: #b8860b; font-size: 12px;
  font-weight: 700; padding: 3px 12px; border-radius: 20px; }}
.featured-title {{ font-size: 25px; font-weight: 900; color: #12457f; margin: 10px 0 4px; }}
.featured-date {{ font-size: 13px; color: #5a6675; font-weight: 600; }}
.featured-desc {{ font-size: 13.5px; color: #5a6675; margin: 12px 0 14px; max-width: 560px; }}
.featured-cta {{ display: inline-block; background: linear-gradient(135deg,#1a5fb4,#2a7fd4);
  color: #fff; font-size: 14px; font-weight: 700; padding: 10px 26px; border-radius: 24px; }}
.featured-right {{ flex-shrink: 0; }}
.ring {{
  width: 110px; height: 110px; border-radius: 50%;
  background: conic-gradient(#1a5fb4 0 78%, #e3edf9 78% 100%);
  display: flex; align-items: center; justify-content: center; position: relative;
}}
.ring::before {{ content: ''; position: absolute; inset: 12px; background: #fff; border-radius: 50%; }}
.ring span {{ position: relative; font-size: 38px; font-weight: 900; color: #1a5fb4; line-height: 1; }}
.ring em {{ position: relative; font-size: 13px; color: #5a6675; font-style: normal; margin-left: 2px; }}
/* Coverage */
.cov-title {{ font-size: 16px; color: #12457f; font-weight: 800; margin: 8px 0 16px;
  display: flex; align-items: center; gap: 8px; }}
.cov-title::before {{ content: ''; width: 5px; height: 18px; background: #c99a3f; border-radius: 3px; }}
.cov-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 38px; }}
.cov-item {{ background: #fff; border: 1px solid #e6ebf2; border-radius: 14px; padding: 18px 12px;
  text-align: center; box-shadow: 0 2px 10px rgba(31,39,51,.05); }}
.cov-icon {{ font-size: 26px; }}
.cov-name {{ font-size: 14px; font-weight: 700; color: #1f2733; margin-top: 6px; }}
.cov-sub {{ font-size: 11px; color: #8a95a5; margin-top: 3px; }}
/* Reports */
.sec-title {{ font-size: 16px; color: #12457f; font-weight: 800; margin: 8px 0 16px;
  display: flex; align-items: center; gap: 8px; }}
.sec-title::before {{ content: ''; width: 5px; height: 18px; background: #1a5fb4; border-radius: 3px; }}
.report-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }}
.report-card {{ background: #fff; border-radius: 14px; overflow: hidden;
  box-shadow: 0 2px 10px rgba(31,39,51,.06); border: 1px solid #e6ebf2;
  transition: transform .15s, box-shadow .15s; }}
.report-card.latest {{ border: 2px solid #1a5fb4; }}
.report-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 24px rgba(31,39,51,.14); }}
.card-link {{ display: block; padding: 20px; text-decoration: none; color: inherit; position: relative; }}
.card-badge {{ position: absolute; top: 12px; right: 12px; background: #1a5fb4; color: #fff;
  font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 12px; }}
.card-date {{ font-size: 12px; color: #8a95a5; margin-bottom: 6px; }}
.card-title {{ font-size: 15px; font-weight: 800; color: #1f2733; margin-bottom: 6px; }}
.card-meta {{ font-size: 12px; color: #a0aab8; margin-bottom: 12px; }}
.card-arrow {{ font-size: 13px; color: #1a5fb4; font-weight: 700; }}
/* Footer */
.footer {{ background: #1a1a2e; color: #7e8aa0; text-align: center; padding: 26px 20px; font-size: 12.5px; }}
.footer-brand {{ color: #cfe4ff; text-decoration: none; font-weight: 700; }}
.footer-brand:hover {{ text-decoration: underline; }}
.report-hidden {{ display: none; }}
.more-wrap {{ text-align: center; margin-top: 10px; }}
.more-btn {{ background: #fff; border: 1.5px solid #1a5fb4; color: #1a5fb4; font-size: 14px; font-weight: 700; padding: 11px 30px; border-radius: 24px; cursor: pointer; transition: all .15s; }}
.more-btn:hover {{ background: #1a5fb4; color: #fff; }}
@media (max-width: 720px) {{
  .cov-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .featured {{ flex-direction: column; text-align: center; }}
  .featured-desc {{ margin-left: auto; margin-right: auto; }}
  .hero h1 {{ font-size: 24px; }}
}}
</style>
</head>
<body>
<header class="hero">
  <div class="hero-brand">TAISEI</div>
  <h1>大誠有限会社 · 日本不动产周报</h1>
  <p>东京不动产市场最新动态 · 每周精选推送</p>
  <div class="hero-updated">更新于 {today_str}</div>
</header>

<div class="container">
  {featured_html}

  <div class="cov-title">栏目覆盖</div>
  <div class="cov-grid">{cov_html}
  </div>

  <div class="sec-title">往期周报（{year}年）</div>
  <div class="report-grid">{report_cards}
  </div>{show_more}
</div>

<footer class="footer">
  <p><a href="https://www.taisei-r.com/" target="_blank" rel="noopener" class="footer-brand">大誠有限会社</a> · 日本不动产周报</p>
  <p style="margin-top:6px;opacity:.7;">内容仅供参考，投资需谨慎</p>
</footer>{script_js}
</body>
</html>'''

# ─── GitHub 操作 ─────────────────────────────────────────────────────────
import base64, hashlib, time

def github_api(method, path, data=None):
    import requests
    url = f'https://api.github.com{path}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
    }
    if data:
        resp = requests.request(method, url, headers=headers, json=data, timeout=30)
    else:
        resp = requests.request(method, url, headers=headers, timeout=30)
    return resp

def get_sha(owner, repo, path, branch=BRANCH):
    resp = github_api('GET', f'/repos/{owner}/{repo}/contents/{path}?ref={branch}')
    if resp.status_code == 200:
        return resp.json().get('sha')
    return None

def upsert_file(owner, repo, path, content, message, branch=BRANCH):
    sha = get_sha(owner, repo, path, branch)
    data = {
        'message': message,
        'content': base64.b64encode(content.encode('utf-8')).decode(),
        'branch': branch,
    }
    if sha:
        data['sha'] = sha
    resp = github_api('PUT', f'/repos/{owner}/{repo}/contents/{path}', data)
    return resp

# ─── 主流程 ──────────────────────────────────────────────────────────────

def main():
    import requests, os

    print('[1/5] 构建本周报告HTML...')
    report_html = build_report_html()

    # 生成本周文件夹名
    today = datetime.now()
    date_folder = today.strftime('%Y-%m-%d')
    report_path = f'reports/{date_folder}/report.html'
    week_num = week_number()
    date_range_from, date_range_to = get_week_range()

    print(f'      本周: {date_range_from} -- {date_range_to}')

    # ── 检查仓库是否存在 ────────────────────────────────────────────
    print('[2/5] 检查/创建GitHub仓库...')
    resp = github_api('GET', f'/repos/{REPO_OWNER}/{REPO_NAME}')
    if resp.status_code == 404:
        print('      仓库不存在，创建中...')
        resp = github_api('POST', '/user/repos', {
            'name': REPO_NAME,
            'description': '大誠有限会社专用不动產週報 -- 東京不动產市場最新動向',
            'private': False,
            'auto_init': False,
        })
        if resp.status_code not in (200, 201):
            print(f'      创建仓库失败: {resp.status_code} {resp.text[:200]}')
            return
        print(f'      仓库创建成功: {REPO_NAME}')
        time.sleep(2)  # 等待仓库创建完成
    else:
        print(f'      仓库已存在 OK')

    # ── 上传本周报告 ─────────────────────────────────────────────────
    print(f'[3/5] 上传本周报告 ({report_path})...')
    commit_msg = f'📋 Add weekly report: {date_range_from} -- {date_range_to} (Week {week_num})'
    resp = upsert_file(REPO_OWNER, REPO_NAME, report_path, report_html, commit_msg)
    if resp.status_code in (200, 201):
        print(f'      报告上传成功 OK')
    else:
        print(f'      报告上传失败: {resp.status_code} {resp.text[:200]}')
        return

    # ── 更新index.html ───────────────────────────────────────────────
    print('[4/5] 获取已有报告列表...')
    resp = github_api('GET', f'/repos/{REPO_OWNER}/{REPO_NAME}/contents/reports?ref={BRANCH}')
    folders = []
    if resp.status_code == 200:
        for item in resp.json():
            if item['type'] == 'dir' and re.match(r'\d{4}-\d{2}-\d{2}', item['name']):
                # 检查是否有report.html
                folder = item['name']
                r_resp = github_api('GET', f'/repos/{REPO_OWNER}/{REPO_NAME}/contents/reports/{folder}/report.html?ref={BRANCH}')
                if r_resp.status_code == 200:
                    try:
                        dt = datetime.strptime(folder, '%Y-%m-%d')
                        folders.append({
                            'folder': folder,
                            'date_str': dt.strftime('%Y年%m月%d日'),
                            'week_num': dt.isocalendar()[1],
                            'sort_key': dt,
                        })
                    except:
                        pass

    folders.sort(key=lambda x: x['sort_key'], reverse=True)
    index_html = build_index_html(folders)

    print(f'      共有 {len(folders)} 期报告')
    print('[5/5] 更新index.html...')
    resp = upsert_file(REPO_OWNER, REPO_NAME, 'index.html', index_html,
                        f'🔄 Auto-update index.html -- added {date_folder}')
    if resp.status_code in (200, 201):
        print('      index.html 更新成功 OK')
    else:
        print(f'      index.html 更新失败: {resp.status_code} {resp.text[:200]}')

    print()
    print('=' * 50)
    print('[OK] 全部完成！')
    print(f'   报告: reports/{date_folder}/report.html')
    print(f'   GitHub: https://github.com/{REPO_OWNER}/{REPO_NAME}')
    print()
    print('[NOTE] 下一步：在 EdgeOne Pages 控制台导入此仓库')
    print(f'   👉 https://console.cloud.tencent.com/edgeone/pages')
    print('   1. 点击「创建站点」->「从 Git 导入」-> 选择 GitHub')
    print(f'   2. 选择仓库: {REPO_OWNER}/{REPO_NAME}')
    print('   3. 分支: main，输出目录: /，构建命令: 留空')
    print('   4. 创建完成后，EdgeOne 会自动发布')
    print('=' * 50)

if __name__ == '__main__':
    main()
