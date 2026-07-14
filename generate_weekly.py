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
    ('首都圈中古マンシ\n㎡单价（23区）', '5,078円 ▼0.2%', 'red'),
    ('首都圈新建マンシ\n供给户数（6月）', '1,412戸 ->', 'blue'),
    ('首都圈中古マンシ\n成约件数（6月）', '3.4%減 ▼', 'red'),
    ('東京都23区中古戸建\n平均价格', '4,254万円 ▲2.8%', 'green'),
    ('J-REIT 総合指数', '▲上昇中', 'green'),
]

FLAT35_RATE    = '3.21%'
FLAT35_MONTH   = '连续4个月上升（2026年7月時点）'
FLAT35_NOTE    = '日本央行政策利率维持1%，市场关注7月31日金融政策决定会议（MPP）动向。主要银行固定利率区间：住信SBI 3.15%〜 / auじぶん 3.19%〜 / 三井住友銀 3.20%〜'
XIAOXIA_COMMENT= ('贷款利率4连升，但首都圈新建マンシ价格依旧坚挺（连续14个月YoY+），供需紧张持续消化利率压力。'
                  '物流不动產方面外资与J-REIT持续扩张，近畿圈空室率趋零值得关注。中古市场成约件数3个月连减，需持续关注。')

SECTIONS_META = {
    'policy':  ('🏛️', '政策動向', 'POLICY',  '#0f3460'),
    'deals':   ('💼', '市場取引・投資', 'DEALS',  '#c9a959'),
    'develop': ('🏗️', '開発動向', 'DEVELOP', '#27ae60'),
    'tech':    ('🤖', '科技・イノベーション', 'TECH', '#8e44ad'),
    'survey':  ('📊', '調査・トレンド', 'RESEARCH', '#e74c3c'),
}

# ─── CSS 样式（包含在HTML中） ──────────────────────────────────────────
CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  background: #f0f2f5;
  color: #1a1a2e;
  font-size: 15px;
  line-height: 1.6;
}

.main-header {
  background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 60%, #16537e 100%);
  color: white;
  padding: 40px 20px 32px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.main-header::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(45deg, transparent, transparent 20px, rgba(255,255,255,0.015) 20px, rgba(255,255,255,0.015) 40px);
}
.main-header::after {
  content: '';
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6, #60a5fa, #93c5fd, #3b82f6);
}
.header-inner { position: relative; z-index: 1; max-width: 900px; margin: 0 auto; }
.brand {
  font-size: 13px; letter-spacing: 6px; color: #60a5fa;
  font-weight: bold; margin-bottom: 8px;
}
.main-title { font-size: 28px; font-weight: bold; margin-bottom: 6px; letter-spacing: 2px; }
.subtitle { font-size: 13px; color: #a0c4e8; margin-bottom: 14px; }
.date-badge {
  display: inline-block; background: rgba(59,130,246,0.25);
  border: 1px solid rgba(59,130,246,0.5); border-radius: 20px;
  padding: 4px 18px; font-size: 13px; color: #93c5fd;
}

.stats-bar {
  display: flex; gap: 0; background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px;
}
.stat-item {
  flex: 1; text-align: center; padding: 16px 8px;
  border-right: 1px solid #e8ecf0;
}
.stat-item:last-child { border-right: none; }
.stat-num { font-size: 22px; font-weight: bold; margin-bottom: 4px; }
.stat-num.gold { color: #c9a959; }
.stat-num.red  { color: #e74c3c; }
.stat-num.green{ color: #27ae60; }
.stat-num.blue { color: #0f3460; }
.stat-label { font-size: 11px; color: #888; line-height: 1.3; }

.container { max-width: 960px; margin: 0 auto; padding: 0 16px 40px; }

.hot-section, .trend-section, .rate-section { margin-bottom: 24px; }
.section-header {
  font-size: 15px; font-weight: bold; color: white;
  background: linear-gradient(90deg, #0f3460, #16537e);
  padding: 10px 16px; border-radius: 8px 8px 0 0;
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 0;
}
.section-icon { font-size: 18px; }
.hot-list {
  background: #fff8e1; border: 1px solid #ffe082;
  border-top: none; border-radius: 0 0 8px 8px;
  padding: 14px 18px;
}
.hot-item {
  padding: 5px 0; font-size: 14px; color: #555;
  border-bottom: 1px dashed #ffe082;
  display: flex; align-items: flex-start; gap: 8px;
}
.hot-item:last-child { border-bottom: none; }
.hot-item::before { content: '•'; color: #f59e0b; font-weight: bold; flex-shrink: 0; }

.trend-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-top: none; border-radius: 0 0 8px 8px; padding: 14px;
}
.trend-cell { background: white; border-radius: 6px; padding: 12px 8px; text-align: center; }
.trend-val { font-size: 15px; font-weight: bold; margin-bottom: 4px; }
.trend-val.red  { color: #e74c3c; }
.trend-val.blue { color: #3b82f6; }
.trend-val.green{ color: #27ae60; }
.trend-lbl { font-size: 11px; color: #888; line-height: 1.3; white-space: pre-line; }

.news-section { margin-bottom: 20px; }
.news-header {
  display: flex; align-items: center; justify-content: space-between;
  background: #f0f2f5; padding: 8px 14px; border-radius: 8px 8px 0 0;
  border-bottom: 3px solid;
}
.news-header-left { display: flex; align-items: center; gap: 8px; font-weight: bold; font-size: 14px; }
.news-tag {
  background: white; color: #666; font-size: 11px; padding: 2px 8px;
  border-radius: 10px; font-weight: normal;
}
.news-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 10px 0; }
.news-card {
  background: white; border-radius: 6px; border: 1px solid #e8ecf0;
  overflow: hidden; padding: 12px 14px;
  border-left: 4px solid;
  transition: box-shadow 0.2s;
}
.news-card:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
.news-meta { font-size: 12px; color: #888; margin-bottom: 5px; }
.news-title { font-size: 13px; font-weight: bold; color: #1a1a2e; margin-bottom: 6px; line-height: 1.4; }
.news-body { font-size: 12px; color: #666; line-height: 1.5; margin-bottom: 8px; }
.news-link { font-size: 12px; }
.news-link a { color: #3b82f6; text-decoration: none; }
.news-link a:hover { text-decoration: underline; }

.rate-box {
  background: #fff8e1; border: 1px solid #ffe082;
  border-radius: 0 0 8px 8px; padding: 16px 20px;
  font-size: 14px; line-height: 1.7;
}
.rate-box p { margin-bottom: 8px; }
.rate-box p:last-child { margin-bottom: 0; }
.comment {
  background: #fff; border-radius: 6px; padding: 12px 14px;
  border: 1px solid #e8ecf0; margin-top: 10px;
}

.main-footer {
  background: #1a1a2e; color: #a0aabb; text-align: center;
  padding: 20px; font-size: 12px; line-height: 1.8;
}
.main-footer p:last-child { margin-top: 4px; color: #606880; }

@media (max-width: 700px) {
  .stats-bar { flex-wrap: wrap; }
  .stat-item { flex: 1 1 40%; }
  .news-grid { grid-template-columns: 1fr; }
  .trend-grid { grid-template-columns: repeat(2, 1fr); }
}

/* Share Screenshot Button */
.share-btn {
  position: fixed; bottom: 24px; right: 24px; z-index: 9999;
  background: #3b82f6; color: white; border: none;
  border-radius: 50%; width: 56px; height: 56px;
  font-size: 22px; cursor: pointer;
  box-shadow: 0 4px 16px rgba(59,130,246,0.4);
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.share-btn:hover { transform: scale(1.1); box-shadow: 0 6px 20px rgba(59,130,246,0.5); }
.share-btn:active { transform: scale(0.95); }
.share-btn.loading { pointer-events: none; opacity: 0.7; }
.share-toast {
  position: fixed; bottom: 90px; right: 24px; z-index: 10000;
  background: #1a1a2e; color: white; padding: 12px 18px;
  border-radius: 10px; font-size: 14px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  opacity: 0; transform: translateY(10px);
  transition: all 0.3s;
}
.share-toast.show { opacity: 1; transform: translateY(0); }

/* ─── Share Card (mobile-optimized 3:4 card) ─── */
.share-card {
  display: none;
  width: 540px;
  background: #ffffff;
  font-family: 'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  overflow: hidden;
  /* card frame shadow */
  box-shadow: 0 12px 48px rgba(0,0,0,0.18);
}
.share-card-inner {
  background: #f0f2f5;
  padding: 0 0 24px;
}
/* Card Header */
.sc-header {
  background: linear-gradient(135deg, #0f3460 0%, #16213e 60%, #1a1a2e 100%);
  padding: 28px 28px 24px;
  position: relative;
  overflow: hidden;
}
.sc-header::before {
  content: ''; position: absolute; inset: 0;
  background-image: radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px);
  background-size: 20px 20px;
}
.sc-header-top {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 18px;
}
.sc-logo {
  font-size: 22px; font-weight: 900; letter-spacing: 5px;
  color: #3b82f6; text-shadow: 0 0 20px rgba(59,130,246,0.6);
  font-style: normal;
}
.sc-badge {
  background: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.9); font-size: 11px;
  padding: 4px 12px; border-radius: 20px;
  letter-spacing: 1px;
}
.sc-title {
  color: white; font-size: 18px; font-weight: 700;
  margin: 0 0 6px; line-height: 1.3;
}
.sc-date-range {
  color: rgba(255,255,255,0.7); font-size: 13px; margin: 0;
  letter-spacing: 0.5px;
}
/* Card Divider */
.sc-divider {
  height: 3px;
  background: linear-gradient(90deg, #3b82f6 0%, #06b6d4 50%, #10b981 100%);
}
/* Card Body */
.sc-body { padding: 20px 24px 0; }
/* Stats Row */
.sc-stats {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 10px; margin-bottom: 20px;
}
.sc-stat {
  background: white; border-radius: 12px; padding: 12px 8px;
  text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.sc-stat-val {
  font-size: 18px; font-weight: 800;
  background: linear-gradient(135deg, #0f3460, #3b82f6);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; display: block; line-height: 1.2;
}
.sc-stat-lbl {
  font-size: 10px; color: #888; margin-top: 4px;
  display: block; line-height: 1.3;
}
/* Hot Topics */
.sc-hot { margin-bottom: 0; }
.sc-hot-title {
  font-size: 12px; font-weight: 700; color: #0f3460;
  margin: 0 0 10px; letter-spacing: 1px; text-transform: uppercase;
  display: flex; align-items: center; gap: 6px;
}
.sc-hot-title::after {
  content: ''; flex: 1; height: 1px; background: #e0e0e0;
}
.sc-hot-list { list-style: none; margin: 0; padding: 0; }
.sc-hot-item {
  display: flex; align-items: flex-start; gap: 10px;
  background: white; border-radius: 10px; padding: 11px 14px;
  margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  font-size: 13px; color: #222; line-height: 1.5;
}
.sc-hot-num {
  background: linear-gradient(135deg, #0f3460, #3b82f6);
  color: white; font-size: 10px; font-weight: 700;
  width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 1px;
}
/* Card Footer */
.sc-footer {
  margin: 18px 24px 0;
  background: linear-gradient(135deg, #0f3460, #16213e);
  border-radius: 12px; padding: 12px 16px;
  display: flex; align-items: center; justify-content: space-between;
}
.sc-footer-left { color: rgba(255,255,255,0.8); font-size: 11px; }
.sc-footer-brand {
  color: #3b82f6; font-weight: 700; font-size: 13px;
  letter-spacing: 1px;
}
.sc-footer-right {
  color: rgba(255,255,255,0.5); font-size: 10px; text-align: right;
  line-height: 1.5;
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

def render_news_card(news, accent_color):
    meta  = f'<span style="color:#888;font-size:12px">{news["date"]}</span> <span style="color:#0f3460;font-size:12px">【{news["source"]}】</span>'
    title = f'<b>{news["title"]}</b>'
    body  = news['body']
    link  = f'<a href="{news["url"]}" target="_blank" rel="noopener">📖 {news["url_text"]} -></a>'
    return f'''<div class="news-card" style="border-left-color:{accent_color}">
  <div class="news-meta">{meta}</div>
  <div class="news-title">{title}</div>
  <div class="news-body">{body}</div>
  <div class="news-link">{link}</div>
</div>'''

def render_news_section(key):
    meta = SECTIONS_META[key]
    icon, title, tag, color = meta
    items = NEWS_DATA.get(key, [])
    cards_html = '\n'.join(render_news_card(n, color) for n in items)
    return f'''<div class="news-section">
  <div class="news-header" style="border-bottom-color:{color}">
    <div class="news-header-left">
      <span>{icon}</span>
      <span>{title}</span>
    </div>
    <span class="news-tag">{tag}</span>
  </div>
  <div class="news-grid">{cards_html}</div>
</div>'''

def build_report_html():
    """构建本周报告HTML"""
    date_from, date_to = get_week_range()
    date_range = f'{date_from} -- {date_to}'
    today_str  = datetime.now().strftime('%Y年%m月%d日')
    week_num   = week_number()

    hot_items = [
        '国交省推进「ビデオ重説」制度 -- 年内引入视频重要事项说明，减轻宅建士与买卖双方负担',
        '観光庁创设地方废旅馆再生补助制度 -- 地方温泉地空置旅馆迎新生，公募至2027年2月',
        '首都圈新建マンシ持续高价 -- ㎡单价连续14个月同比上升，供应户数维持1,400户以上',
        '银座五丁目大厦重建完成 -- 8月17日全面开业，成为银座新地标',
        '外资持续布局日本物流不动產 -- 近畿圈物流空室率趋零值得关注',
    ]
    hot_html = '\n'.join(f'<div class="hot-item">{item}</div>' for item in hot_items)
    hot_items_html = '\n'.join(
        f'<li class="sc-hot-item"><span class="sc-hot-num">{i+1}</span>{item.split(" -- ")[0]}</li>'
        for i, item in enumerate(hot_items[:3])
    )

    trend_html = ''
    for label, value, color_cls in TRENDS:
        trend_html += f'''<div class="trend-cell">
  <div class="trend-val {color_cls}">{value}</div>
  <div class="trend-lbl">{label}</div>
</div>'''

    news_sections_html = '\n'.join(render_news_section(k) for k in ['policy','deals','develop','tech','survey'])

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="大誠有限会社专用不动產週報 {date_range}">
<title>大誠不动產週報 {date_range}</title>
<style>{CSS}</style>
</head>
<body>
<header class="main-header">
  <div class="header-inner">
    <div class="brand">TAISEI</div>
    <h1 class="main-title">大誠有限会社専用不动產週報</h1>
    <p class="subtitle">政策 · 市場 · 開発 · トレンド</p>
    <p class="date-badge">[REPORT] {date_range}（第{week_num}週）</p>
  </div>
</header>

<div class="stats-bar">
  <div class="stat-item"><div class="stat-num gold">{STATS["stat_1"]}</div><div class="stat-label">フラット35主力金利</div></div>
  <div class="stat-item"><div class="stat-num red">{STATS["stat_2"]}</div><div class="stat-label">首都圈中古マンシ成约件数</div></div>
  <div class="stat-item"><div class="stat-num green">{STATS["stat_3"]}</div><div class="stat-label">首都圈新建マンシ供给户数</div></div>
  <div class="stat-item"><div class="stat-num blue">{STATS["stat_4"]}</div><div class="stat-label">マンシ㎡单价连续上升月数</div></div>
  <div class="stat-item"><div class="stat-num gold">{STATS["stat_5"]}</div><div class="stat-label">東京駅周辺成约赁料</div></div>
</div>

<div class="container">
  <section class="hot-section">
    <h2 class="section-header"><span class="section-icon">🔥</span> 本週ホット topics</h2>
    <div class="hot-list">{hot_html}</div>
  </section>

  <section class="trend-section">
    <h2 class="section-header"><span class="section-icon">📊</span> Market Trend</h2>
    <div class="trend-grid">{trend_html}</div>
  </section>

  {news_sections_html}

  <section class="rate-section">
    <h2 class="section-header"><span class="section-icon">📈</span> 贷款利率趋势 & 小虾点评</h2>
    <div class="rate-box">
      <p><strong>フラット35：</strong>{FLAT35_RATE}（{FLAT35_MONTH}）。{FLAT35_NOTE}</p>
      <p class="comment"><strong>💡 小虾点评：</strong>{XIAOXIA_COMMENT}</p>
    </div>
  </section>
</div>

<footer class="main-footer">
  <p>📡 データソース：国土交通省 / 日経不动產マーケット情報 / 週刊住宅タイムズ / 週刊不动產経営 / 東京カンティ / SUUMO / 不動产経済研究所 / SMTRI / 信義日本</p>
  <p>Generated by 大誠 · {today_str} · 东京 · 大誠有限会社 専用</p>
</footer>

<!-- Share Card (hidden, captured as screenshot) -->
<div class="share-card" id="shareCard">
  <div class="share-card-inner">
    <div class="sc-header">
      <div class="sc-header-top">
        <i class="sc-logo">TAISEI</i>
        <span class="sc-badge">週 報</span>
      </div>
      <p class="sc-title">大誠有限会社 不動產週報</p>
      <p class="sc-date-range">{date_range}</p>
    </div>
    <div class="sc-divider"></div>
    <div class="sc-body">
      <div class="sc-stats">
        <div class="sc-stat">
          <span class="sc-stat-val">{TRENDS[0][1]}</span>
          <span class="sc-stat-lbl">{TRENDS[0][0]}</span>
        </div>
        <div class="sc-stat">
          <span class="sc-stat-val">{TRENDS[1][1]}</span>
          <span class="sc-stat-lbl">{TRENDS[1][0]}</span>
        </div>
        <div class="sc-stat">
          <span class="sc-stat-val">{TRENDS[2][1]}</span>
          <span class="sc-stat-lbl">{TRENDS[2][0]}</span>
        </div>
        <div class="sc-stat">
          <span class="sc-stat-val">{TRENDS[3][1]}</span>
          <span class="sc-stat-lbl">{TRENDS[3][0]}</span>
        </div>
      </div>
      <div class="sc-hot">
        <div class="sc-hot-title">🔥 本週ホット topics</div>
        <ul class="sc-hot-list">
{hot_items_html}
        </ul>
      </div>
    </div>
    <div class="sc-footer">
      <div class="sc-footer-left">
        <div class="sc-footer-brand">TAISEI</div>
        <div style="font-size:10px;color:rgba(255,255,255,0.6);margin-top:2px">大誠有限会社</div>
      </div>
      <div class="sc-footer-right">Generated by 大誠<br>东京 · {today_str}</div>
    </div>
  </div>
</div>

<!-- Share Screenshot Button -->
<button class="share-btn" id="shareBtn" title="生成分享截图">[SHARE]</button>
<div class="share-toast" id="shareToast">截图生成中...</div>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script>
document.getElementById('shareBtn').addEventListener('click', async function() {{
  var btn = this, toast = document.getElementById('shareToast');
  btn.classList.add('loading'); btn.textContent = '...';
  toast.textContent = '生成分享卡中...'; toast.classList.add('show');
  try {{
    var card = document.getElementById('shareCard');
    var canvas = await html2canvas(card, {{
      useCORS: true, allowTaint: true,
      backgroundColor: '#f0f2f5', scale: 2,
      width: 540, height: card.offsetHeight,
      logging: false, pixelRatio: 2
    }});
    var badge = (document.querySelector('.date-badge') || {{}}).textContent || '';
    var link = document.createElement('a');
    link.download = '\u5927\u8bfa\u4e0d\u52a8\u7522\u9031\u5831_' + badge.trim() + '.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
    toast.textContent = '分享卡已保存!';
  }} catch(e) {{
    toast.textContent = '截图失败，请重试';
  }}
  setTimeout(function() {{ toast.classList.remove('show'); }}, 2500);
  btn.classList.remove('loading'); btn.textContent = '[SHARE]';
}});
</script>
</body>
</html>'''
    return html

def build_index_html(reports):
    """构建索引页HTML"""
    today_str = datetime.now().strftime('%Y年%m月%d日')
    year = datetime.now().year

    report_cards = ''
    for r in reports:
        # r = {date_folder, date_str, week_num}
        folder = r['folder']
        date_str = r['date_str']
        week_num = r['week_num']
        report_cards += f'''
    <div class="report-card">
      <a href="reports/{folder}/report.html" class="card-link">
        <div class="card-date">{date_str}</div>
        <div class="card-title">第{week_num}週 不动產週報</div>
        <div class="card-arrow">-> 閲覧</div>
      </a>
    </div>'''

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大誠不动產週報 -- レポート一覧</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', sans-serif; background: #f0f2f5; color: #1a1a2e; min-height: 100vh; }}
.hero {{
  background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 60%);
  color: white; text-align: center; padding: 50px 20px 40px;
  position: relative;
}}
.hero::after {{
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg, #3b82f6, #60a5fa, #93c5fd, #3b82f6);
}}
.hero-brand {{ font-size: 12px; letter-spacing: 6px; color: #60a5fa; margin-bottom: 8px; }}
.hero h1 {{ font-size: 26px; font-weight: bold; margin-bottom: 8px; }}
.hero p {{ font-size: 14px; color: #a0c4e8; }}
.hero-updated {{ margin-top: 14px; font-size: 12px; color: #6080a0; }}
.container {{ max-width: 800px; margin: 0 auto; padding: 30px 16px 60px; }}
.section-title {{
  font-size: 15px; color: #555; margin-bottom: 16px;
  padding-bottom: 8px; border-bottom: 2px solid #0f3460;
  display: flex; align-items: center; gap: 8px;
}}
.report-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }}
.report-card {{
  background: white; border-radius: 10px; overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}}
.report-card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.14); }}
.card-link {{
  display: block; padding: 22px 20px; text-decoration: none; color: inherit;
  background: linear-gradient(135deg, #0f3460, #16537e);
  color: white; height: 100%;
}}
.card-date {{ font-size: 12px; color: #93c5fd; margin-bottom: 8px; }}
.card-title {{ font-size: 15px; font-weight: bold; margin-bottom: 12px; line-height: 1.4; }}
.card-arrow {{ font-size: 13px; color: #60a5fa; }}
.footer {{
  background: #1a1a2e; color: #606880; text-align: center;
  padding: 20px; font-size: 12px;
}}
</style>
</head>
<body>
<header class="hero">
  <div class="hero-brand">TAISEI</div>
  <h1>大誠有限会社 不动產週報</h1>
  <p>東京不动產市場の最新動向を毎週配信</p>
  <div class="hero-updated">更新：{today_str}</div>
</header>

<div class="container">
  <div class="section-title">📋 全レポート一覧（第{year}年）</div>
  <div class="report-grid">{report_cards}
  </div>
</div>

<footer class="footer">
  <p>Generated by 大誠 · 大誠有限会社 専用</p>
</footer>
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
