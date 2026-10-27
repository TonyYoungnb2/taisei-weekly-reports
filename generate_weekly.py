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

# 隐私统计 (Umami) — 留空则不打点；填入实例地址与站点 ID 即可全站启用
import _analytics as _an

# ─── 設定 ───────────────────────────────────────────────────────────────
def _load_github_token():
    # 1) 优先环境变量；2) 回退到仓库【外部】安全 token 文件（绝不硬编码明文 Token）
    tok = os.environ.get('GITHUB_TOKEN', '').strip()
    if tok:
        return tok
    tok_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.github_token')
    if os.path.isfile(tok_file):
        try:
            return open(tok_file, encoding='utf-8').read().strip()
        except Exception:
            pass
    return ''
GITHUB_TOKEN = _load_github_token()
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

# ─── 週間データの読み込み（cronが書き出したJSONを優先、なければハードコード fallback） ───
# ⚠️ cron 任务(大誠周报自动生成)会把真实抓取的新闻写入 data/weekly_data_sample.json
#    （deploy.yml 的 push 触发路径另用 data/weekly_data.json）。两者都チェックする。
#    这里只读「5大板块新闻」，STATS/TRENDS/热点/点评仍用下方ハードコード（cron未产出这些）。
import os as _os

def load_weekly_data():
    """读取 cron 写出的真实周报数据（5大板块 + 可选 stats/trends/hot/flat35/comment）。
    缺失的字段则用内置 DEFAULT_* 兜底，绝不空跑崩。"""
    _base = _os.path.dirname(_os.path.abspath(__file__))
    _candidates = [
        _os.path.join(_base, 'data', 'weekly_data_sample.json'),
        _os.path.join(_base, 'data', 'weekly_data.json'),
    ]
    _data = None
    for _p in _candidates:
        try:
            if not _os.path.exists(_p):
                continue
            with io.open(_p, encoding='utf-8') as _f:
                _d = json.loads(_f.read())
            if isinstance(_d, dict) and all(k in _d for k in ['policy','deals','develop','tech','survey']):
                _data = _d
                break
        except Exception:
            continue
    # 中文翻译数据（weekly_data_cn.json）：含 *_cn 字段，优先用于中文呈现
    _cn = None
    _cn_path = _os.path.join(_base, 'data', 'weekly_data_cn.json')
    if _os.path.exists(_cn_path):
        try:
            with io.open(_cn_path, encoding='utf-8') as _cf:
                _cn = json.loads(_cf.read())
        except Exception:
            _cn = None
    # 日文原文数据（weekly_data_jp.json）：含 *_jp 字段，用于日语版呈现
    _jp = None
    _jp_path = _os.path.join(_base, 'data', 'weekly_data_jp.json')
    if _os.path.exists(_jp_path):
        try:
            with io.open(_jp_path, encoding='utf-8') as _jf:
                _jp = json.loads(_jf.read())
        except Exception:
            _jp = None
    if _data is None:
        # 无 JSON：新闻也用内置 NEWS_DATA，其余用 DEFAULT_*
        _data = dict(NEWS_DATA)
    # 兜底合并（真实値優先、なければ DEFAULT_*）
    _out = {}
    for _k in ['policy','deals','develop','tech','survey']:
        _items = _data.get(_k, NEWS_DATA.get(_k, []))
        # 若中文 JSON 有对应列表，则按索引把 *_cn 字段并入（用于 default-CN 呈现）
        if isinstance(_cn, dict) and _k in _cn and isinstance(_cn[_k], list):
            _cn_items = _cn[_k]
            for _i, _it in enumerate(_items):
                if _i < len(_cn_items) and isinstance(_cn_items[_i], dict):
                    for _ck in ('title_cn','body_cn','source_cn'):
                        if _ck in _cn_items[_i] and _ck not in _it:
                            _it[_ck] = _cn_items[_i][_ck]
        if isinstance(_jp, dict) and _k in _jp and isinstance(_jp[_k], list):
            _jp_items = _jp[_k]
            for _i, _it in enumerate(_items):
                if _i < len(_jp_items) and isinstance(_jp_items[_i], dict):
                    for _jk in ('title_jp','body_jp','source_jp'):
                        if _jk in _jp_items[_i] and _jk not in _it:
                            _it[_jk] = _jp_items[_i][_jk]
        _out[_k] = _items
    _out['stats']   = _merge_cn(_data.get('stats',   DEFAULT_STATS),   _cn.get('stats')   if isinstance(_cn, dict) else None)
    _out['trends']  = _merge_cn(_data.get('trends',  DEFAULT_TRENDS), _cn.get('trends')  if isinstance(_cn, dict) else None)
    _out['hot']     = _data.get('hot',     DEFAULT_HOT)
    # 中文热点列表（hot_cn）从 cn.json 并入
    if isinstance(_cn, dict) and 'hot_cn' in _cn:
        _out['hot_cn'] = _cn['hot_cn']
    _out['flat35']  = _merge_cn(_data.get('flat35',  DEFAULT_FLAT35), _cn.get('flat35')  if isinstance(_cn, dict) else None)
    _out['comment'] = _merge_cn(_data.get('comment', DEFAULT_COMMENT), _cn.get('comment_cn') if isinstance(_cn, dict) else None)
    # comment_cn 是字符串，直接并入 _out
    if isinstance(_cn, dict) and 'comment_cn' in _cn:
        _out['comment_cn'] = _cn['comment_cn']
    # 日文原文合并：stats label_jp（按索引）、hot_jp 列表、flat35 *_jp、comment_jp
    if isinstance(_jp, dict):
        if isinstance(_jp.get('stats'), list) and isinstance(_out['stats'], list):
            for _i, _st in enumerate(_out['stats']):
                if _i < len(_jp['stats']) and isinstance(_jp['stats'][_i], dict) and isinstance(_st, dict):
                    if 'label_jp' in _jp['stats'][_i]:
                        _st['label_jp'] = _jp['stats'][_i]['label_jp']
        if isinstance(_jp.get('hot'), list):
            _out['hot_jp'] = _jp['hot']
        if isinstance(_jp.get('flat35'), dict) and isinstance(_out['flat35'], dict):
            for _jk in ('month_jp','note_jp','rate_jp'):
                if _jk in _jp['flat35']:
                    _out['flat35'][_jk] = _jp['flat35'][_jk]
        if 'comment_jp' in _jp:
            _out['comment_jp'] = _jp['comment_jp']
    # 暴露给 build_report_html 用于统计卡 cn/jp 对齐（按索引从上同源取 label_jp）
    global _WEEKLY_CN, _WEEKLY_JP
    _WEEKLY_CN = _cn
    _WEEKLY_JP = _jp
    return _out

def _merge_cn(primary, cn):
    """primary=日语/原数据；若 cn(中文json) 含 *_cn 字段则并入，键名一致便于渲染层取用。
    对 dict（flat35/comment）：直接把 *_cn 字段补进去；对 list：按索引补 *_cn。"""
    if cn is None:
        return primary
    if isinstance(primary, dict):
        out = dict(primary)
        for ck in ('title_cn','body_cn','source_cn','label_cn','note_cn','month_cn','value_cn'):
            if ck in cn:
                out[ck] = cn[ck]
        return out
    if isinstance(primary, list):
        out = []
        cn_list = cn if isinstance(cn, list) else []
        for i, it in enumerate(primary):
            if isinstance(it, dict):
                it = dict(it)
                if i < len(cn_list) and isinstance(cn_list[i], dict):
                    for ck in ('title_cn','body_cn','source_cn','label_cn','value_cn'):
                        if ck in cn_list[i] and ck not in it:
                            it[ck] = cn_list[i][ck]
            out.append(it)
        return out
    return primary

# ─── 默认（fallback）データ：cronが真实値を产出しない場合に使用 ──────────────
# これらは weekly_data*.json の同名キーで上書きされる（cron 真实抓取優先）。
DEFAULT_STATS = [
    {'value': '3.21%',   'label': 'フラット35 主力金利（7月時点）'},
    {'value': '▲+3.4%',  'label': '首都圈中古マンシ 成约件数（前年比）'},
    {'value': '1,412戸', 'label': '首都圈新建マンシ 供给户数（6月）'},
    {'value': '14个月',  'label': 'マンシ㎡单价 连续上升月数'},
    {'value': '5万/坪',  'label': '東京駅周辺 成约赁料'},
]

DEFAULT_TRENDS = [
    {'label': '首都圈中古マンシ\n㎡单价（23区）', 'value': '5,078円 ▼0.2%', 'dir': 'down'},
    {'label': '首都圈新建マンシ\n供给户数（6月）', 'value': '1,412戸 ->', 'dir': 'flat'},
    {'label': '首都圈中古マンシ\n成约件数（6月）', 'value': '3.4%減 ▼', 'dir': 'down'},
    {'label': '東京都23区中古戸建\n平均价格', 'value': '4,254万円 ▲2.8%', 'dir': 'up'},
    {'label': 'J-REIT 総合指数', 'value': '▲上昇中', 'dir': 'up'},
]

DEFAULT_HOT = [
    '国交省推进「ビデオ重説」制度 — 年内引入视频重要事项说明，减轻宅建士与买卖双方负担',
    '観光庁创设地方废旅馆再生补助制度 — 地方温泉地空置旅馆迎新生，公募至2027年2月',
    '首都圈新建マンシ持续高价 — ㎡单价连续14个月同比上升，供应户数维持1,400户以上',
    '银座五丁目大厦重建完成 — 8月17日全面开业，成为银座新地标',
    '外资持续布局日本物流不动產 — 近畿圈物流空室率趋零值得关注',
]

DEFAULT_FLAT35 = {
    'rate': '3.21%',
    'month': '连续4个月上升（2026年7月時点）',
    'note': '日本央行政策利率维持1%，市场关注7月31日金融政策决定会议（MPP）动向。主要银行固定利率区间：住信SBI 3.15%〜 / auじぶん 3.19%〜 / 三井住友銀 3.20%〜',
}

DEFAULT_COMMENT = ('贷款利率4连升，但首都圈新建マンシ价格依旧坚挺（连续14个月YoY+），供需紧张持续消化利率压力。'
                   '物流不动產方面外资与J-REIT持续扩张，近畿圈空室率趋零值得关注。中古市场成约件数3个月连减，需持续关注。')

SECTIONS_META = {
    'policy':  ('', '政策动态', '政策動向', 'POLICY',   'policy',  'label-blue'),
    'deals':   ('', '市场交易·投资', '市場取引・投資', 'DEALS',    'deal',    'label-gold'),
    'develop': ('', '开发动态', '開発動向', 'DEVELOP',  'dev',     'label-green'),
    'tech':    ('', '科技·创新', '科技・イノベーション', 'TECH', 'tech',    'label-purple'),
    'survey':  ('', '调查·趋势', '調査・トレンド', 'RESEARCH', 'survey',  'label-red'),
}

# ─── CSS 样式（包含在HTML中，照搬 27/28 周大诚会社周报设计风格） ─────────────
CSS = """/* ===== 方案 2｜明亮清爽 Sky Light ===== */
:root {
  --paper: #f4f8fe;
  --surface: #ffffff;
  --ink: #0c1d33;
  --ink-2: #2a4160;
  --ink-3: #526a86;
  --ink-4: #7d90a8;
  --line: #dde8f6;
  --line-2: #bcd2ea;
  --accent: #1668dc;
  --accent-2: #3b8ef0;
  --accent-deep: #0d4ea8;
  --up: #d13b30;
  --down: #0f8a5f;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  --serif: var(--sans);
  --r: 18px; --r-sm: 12px;
  --shadow: 0 2px 6px rgba(13,78,168,.05), 0 14px 34px rgba(13,78,168,.08);
  --shadow-sm: 0 1px 3px rgba(13,78,168,.05), 0 6px 16px rgba(13,78,168,.05);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: var(--sans);
  background: var(--paper);
  color: var(--ink);
  font-size: 16px; line-height: 1.78;
  -webkit-font-smoothing: antialiased;
}
::selection { background: var(--accent); color: #fff; }
a { color: inherit; }
img { max-width: 100%; }

/* 语言切换：只写 html 后代选择器（裸 .lang-jp{display:none} 会命中 <html> 自身导致整页白屏） */
html.lang-jp .lang-cn { display: none; }
html.lang-cn .lang-jp { display: none; }
html.lang-jp .lang-jp { display: inline; }
html.lang-cn .lang-cn { display: inline; }

/* ===== 报头 ===== */
.header { background: var(--surface); position: relative; overflow: hidden; }
.header::before {
  content: ''; position: absolute; top: -140px; right: -80px; width: 380px; height: 380px;
  border-radius: 50%; background: radial-gradient(circle at 30% 30%, rgba(59,142,240,.20), rgba(59,142,240,0) 70%);
}
.header::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 5px;
  background: linear-gradient(90deg, var(--accent-deep), var(--accent), var(--accent-2), #8ec5f8);
}
.header .topbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 11px 24px; border-bottom: 1px solid var(--line); position: relative; z-index: 2;
}
.home-btn {
  color: var(--ink-2); text-decoration: none; font-size: 12px; font-weight: 800;
  letter-spacing: 3px; text-transform: uppercase; padding: 5px 0;
  border-bottom: 2px solid transparent; transition: color .15s, border-color .15s;
}
.home-btn:hover { color: var(--accent); border-bottom-color: var(--accent-2); }
.lang-switch { position: static; display: inline-flex; align-items: center; gap: 6px; }
.lang-switch .seg {
  display: inline-flex; background: #e8f1fd; border-radius: 999px; padding: 3px;
}
.lang-switch .seg button {
  border: 0; background: transparent; color: var(--ink-3); cursor: pointer;
  font-family: inherit; font-size: 12px; font-weight: 800; letter-spacing: 1px;
  padding: 5px 15px; border-radius: 999px; transition: background .15s, color .15s;
}
.lang-switch .seg button.active { background: var(--accent); color: #fff; }
.header .topbar-right { display: flex; align-items: center; gap: 10px; }
.theme-btn {
  background: #e8f1fd; border: 0; cursor: pointer; font-family: var(--sans);
  font-size: 12px; font-weight: 800; letter-spacing: 1px; color: var(--ink-3);
  padding: 5px 14px; border-radius: 999px; transition: background .15s, color .15s;
}
.theme-btn:hover { background: #d9e8fb; color: var(--accent-deep); }
.header .logo-wrap {
  display: flex; flex-direction: column; align-items: center; text-align: center;
  max-width: 1000px; margin: 0 auto; padding: 48px 24px 42px; position: relative; z-index: 1;
}
.header .logo-text {
  font-family: var(--sans); font-size: 2.5em; font-weight: 800;
  letter-spacing: 11px; text-indent: 11px; line-height: 1;
  background: linear-gradient(100deg, var(--accent-deep), var(--accent), var(--accent-2));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.header h1 {
  font-size: 1.12em; font-weight: 700; letter-spacing: 5px; color: var(--ink);
  margin-top: 20px; line-height: 1.6;
}
.header .subtitle {
  font-size: 11px; font-weight: 800; letter-spacing: 4px; color: var(--accent);
  margin-top: 12px; text-transform: uppercase;
}
.header .date-range {
  display: inline-block; margin-top: 24px; font-size: 13px; font-weight: 800;
  letter-spacing: 1px; color: var(--accent-deep);
  background: #e8f1fd; padding: 9px 22px; border-radius: 999px;
}

/* ===== 数字速览 ===== */
.stats-bar {
  display: flex; flex-wrap: wrap; align-items: stretch;
  max-width: 1000px; margin: 26px auto 44px; padding: 0 24px; background: transparent;
}
.stat-card {
  flex: 1 1 0; min-width: 0; overflow: hidden;
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--r);
  box-shadow: var(--shadow-sm); padding: 22px 20px 20px; margin-right: 14px;
  transition: box-shadow .16s, transform .16s;
}
.stat-card:last-child { margin-right: 0; }
.stat-card:hover { box-shadow: var(--shadow); transform: translateY(-2px); }
.stat-card .num {
  font-family: var(--sans); font-size: 2.3em; font-weight: 800;
  color: var(--accent-deep); line-height: 1.1; letter-spacing: -1px;
}
.stat-tag {
  display: inline-block; margin-top: 12px; font-size: 10px; font-weight: 800;
  letter-spacing: 1px; line-height: 1.5; padding: 4px 10px; border-radius: 999px;
}
.stat-tag.up { color: #fff; background: linear-gradient(100deg, #e0534a, var(--up)); }
.stat-tag.down { color: #fff; background: linear-gradient(100deg, #17a06d, var(--down)); }
.stat-tag.flat { color: var(--ink-2); background: #eef3fa; }
.stat-card .label {
  font-size: 12px; font-weight: 600; color: var(--ink-3); margin-top: 10px;
  line-height: 1.6; letter-spacing: .3px; overflow-wrap: anywhere;
}

.container { max-width: 1000px; margin: 0 auto; padding: 0 24px; }

/* ===== 章节标题 ===== */
.section { margin-bottom: 50px; }
.section-title {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  font-size: 16px; font-weight: 800; letter-spacing: 1px; color: var(--ink);
  margin-bottom: 22px;
}
.section-title::before {
  content: ''; width: 10px; height: 10px; border-radius: 3px;
  background: var(--sec-accent, var(--accent)); flex: 0 0 auto;
}
.section-title .icon { display: none; }
.section-title .tag {
  font-size: 10px; font-weight: 800; letter-spacing: 2px; color: #fff;
  background: var(--sec-accent, var(--accent)); padding: 4px 11px; border-radius: 999px;
}
.sec-policy  { --sec-accent: #1668dc; }
.sec-deals   { --sec-accent: #2b7fd4; }
.sec-develop { --sec-accent: #0f8fa3; }
.sec-tech    { --sec-accent: #5566d8; }
.sec-survey  { --sec-accent: #1180c4; }

/* ===== 新闻卡 ===== */
.card-grid { display: grid; gap: 18px; }
.card-grid.cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.card {
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--r);
  box-shadow: var(--shadow-sm); padding: 24px 24px 22px; min-width: 0; overflow: hidden;
  transition: box-shadow .16s, transform .16s, border-color .16s;
}
.card:hover { box-shadow: var(--shadow); transform: translateY(-2px); border-color: var(--line-2); }
.card.policy { border-top: 5px solid #1668dc; border-radius: var(--r); }
.card.deal  { border-top: 5px solid #2b7fd4; }
.card.price { border-top: 5px solid #1180c4; }
.card.dev   { border-top: 5px solid #0f8fa3; }
.card.tech  { border-top: 5px solid #5566d8; }
.card.survey{ border-top: 5px solid #1180c4; }
.card .date {
  font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: var(--ink-3);
  margin-bottom: 13px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.card .date .source {
  background: #e8f1fd; border-radius: 999px; padding: 3px 10px;
  font-size: 10px; font-weight: 800; letter-spacing: 1px; color: var(--accent-deep);
}
.card h3 { font-size: 16px; font-weight: 800; line-height: 1.55; color: var(--ink); margin-bottom: 10px; }
.card p { font-size: 14px; font-weight: 400; color: var(--ink-2); line-height: 1.9; }
.card .label { display: none; }
.card .source-link {
  display: inline-block; font-size: 11px; font-weight: 800; letter-spacing: 2px;
  margin-top: 18px; color: #fff; text-decoration: none;
  background: linear-gradient(100deg, var(--accent), var(--accent-2));
  border-radius: 999px; padding: 8px 18px; transition: opacity .15s;
}
.card .source-link:hover { opacity: .88; }

/* ===== 本期热点 ===== */
.key-insight {
  background: var(--surface); border: 1px solid var(--line); border-radius: 22px;
  box-shadow: var(--shadow); padding: 0; margin-bottom: 46px; overflow: hidden;
}
.key-insight h3 {
  font-size: 14px; font-weight: 800; letter-spacing: 2px; color: var(--accent-deep);
  background: linear-gradient(100deg, #eaf2fe, #dceafd); margin-bottom: 0; padding: 16px 24px;
  text-transform: uppercase; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  border-bottom: 1px solid var(--line);
}
.key-insight h3 .count {
  font-family: var(--sans); font-size: 10px; font-weight: 800; letter-spacing: 1px;
  color: #fff; background: var(--accent); padding: 3px 10px; border-radius: 999px;
}
.key-insight p, .key-insight li { font-size: 14px; font-weight: 400; color: var(--ink-2); line-height: 1.9; }
.key-insight p { padding: 18px 24px 4px; }
.key-insight p:last-of-type { padding-bottom: 20px; }
.key-insight ul { list-style: none; padding-left: 0; margin-top: 0; }
.key-insight li { margin-bottom: 0; }
.key-insight strong { color: var(--ink); font-weight: 800; }
#hotlist { list-style: none; margin: 0; padding: 8px 0; }
#hotlist li {
  display: grid; grid-template-columns: 40px minmax(0, 1fr); gap: 14px;
  align-items: start; padding: 16px 24px 16px 20px;
}
#hotlist li + li { border-top: 1px solid var(--line); }
#hotlist li:hover { background: #f3f8ff; }
#hotlist .rank {
  font-family: var(--sans); font-size: 13px; font-weight: 800; letter-spacing: 0;
  color: #fff; background: linear-gradient(150deg, var(--accent-2), var(--accent));
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; text-align: center;
}
#hotlist .hot-body { min-width: 0; }
#hotlist .hot-lead { font-weight: 800; color: var(--ink); }
#hotlist .hot-desc { display: block; margin-top: 6px; font-size: 13.5px; font-weight: 400; color: var(--ink-2); line-height: 1.85; }
#hotlist em.fig {
  font-style: normal; font-weight: 800; color: var(--accent-deep);
  background: linear-gradient(transparent 62%, rgba(22,104,220,.18) 62%); padding: 0 2px;
}

/* ===== 市场趋势 ===== */
.trend-visual { display: flex; flex-wrap: wrap; gap: 14px; margin: 14px 0 0; }
.trend-item {
  flex: 1 1 150px; min-width: 0; overflow: hidden;
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--r);
  box-shadow: var(--shadow-sm); padding: 18px 18px 16px;
}
.trend-item .trend-label { font-size: 12px; font-weight: 700; color: var(--ink-3); letter-spacing: .3px; line-height: 1.55; }
.trend-dir {
  display: inline-block; font-family: var(--sans); font-size: 10px; font-weight: 800;
  letter-spacing: 1px; line-height: 1.5; padding: 4px 10px; border-radius: 999px; margin-bottom: 10px;
}
.trend-dir.up { color: #fff; background: linear-gradient(100deg, #e0534a, var(--up)); }
.trend-dir.down { color: #fff; background: linear-gradient(100deg, #17a06d, var(--down)); }
.trend-dir.flat { color: var(--ink-2); background: #eef3fa; }
.trend-item .trend-value {
  font-family: var(--sans); font-size: 23px; font-weight: 800;
  color: var(--ink); line-height: 1.15; letter-spacing: -.5px;
}
.trend-item .trend-value .trend-delta {
  font-family: var(--sans); font-size: 13px; font-weight: 800; letter-spacing: 0;
  margin-left: 9px; white-space: nowrap;
}
.trend-value.up .trend-delta { color: var(--up); }
.trend-value.down .trend-delta { color: var(--down); }
.trend-value.flat .trend-delta { color: var(--ink-3); }

/* ===== 页脚 ===== */
.footer {
  border-top: 1px solid var(--line); margin-top: 56px; padding: 30px 24px 42px;
  color: var(--ink-3); font-size: 11px; font-weight: 600; letter-spacing: 1.5px; text-align: center;
}
.footer a { color: var(--accent-deep); text-decoration: none; border-bottom: 1px solid var(--line-2); }

/* ===== 分享 ===== */
.share-btn-fab {
  position: fixed; right: 22px; bottom: 22px; z-index: 200;
  background: linear-gradient(100deg, var(--accent), var(--accent-2)); color: #fff; border: 0; cursor: pointer;
  font-family: inherit; font-size: 12px; font-weight: 800; letter-spacing: 2px;
  padding: 13px 24px; border-radius: 999px; box-shadow: 0 12px 28px rgba(22,104,220,.32);
  transition: opacity .15s, transform .15s;
}
.share-btn-fab:hover { opacity: .92; transform: translateY(-1px); }
.share-modal {
  display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(12,29,51,.55); z-index: 9999;
  justify-content: center; align-items: center; backdrop-filter: blur(3px);
}
.share-modal.show { display: flex; }
.share-modal .modal-box {
  background: var(--surface); border-radius: 22px; padding: 22px;
  max-width: 600px; width: 95%; max-height: 92vh; overflow-y: auto;
  box-shadow: 0 30px 80px rgba(13,78,168,.3);
  display: flex; flex-direction: column; align-items: center;
}
.share-modal .modal-box .modal-header {
  display: flex; justify-content: space-between; align-items: center;
  width: 100%; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--line);
}
.share-modal .modal-box .modal-header span {
  color: var(--ink-2); font-size: 12px; font-weight: 800; letter-spacing: 3px; text-transform: uppercase;
}
.share-modal .modal-box .modal-header .close-btn {
  background: #eef4fd; border: none; color: var(--ink-3); font-size: 18px;
  cursor: pointer; line-height: 1; padding: 4px 10px; border-radius: 999px;
}
.share-modal .modal-box .modal-header .close-btn:hover { color: var(--ink); background: #e2ecfa; }
#share-card {
  width: 540px; background: var(--surface); border: 1px solid var(--line);
  border-radius: 20px; overflow: hidden; position: relative; font-family: var(--sans);
}
#share-card .card-dots { display: none; }
#share-card .card-top-accent { position: relative; z-index: 1; height: 6px;
  background: linear-gradient(90deg, var(--accent-deep), var(--accent-2)); }
#share-card .card-content { position: relative; z-index: 1; padding: 26px 30px 22px; }
#share-card .card-logo {
  font-family: var(--sans); font-size: 26px; font-weight: 800;
  letter-spacing: 8px; color: var(--accent); line-height: 1;
}
#share-card .card-meta { font-size: 9px; font-weight: 800; color: var(--ink-4); letter-spacing: 4px; margin-top: 9px; }
#share-card .card-date-badge {
  display: inline-block; background: linear-gradient(100deg, var(--accent), var(--accent-2));
  color: #fff; border-radius: 999px; padding: 8px 18px; font-size: 13px; font-weight: 800; letter-spacing: 1px; margin-top: 16px;
}
#share-card .card-divider { border: none; height: 1px; background: var(--line); margin: 18px 0; }
#share-card .card-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
#share-card .card-stat-box { background: #f2f7fe; border-radius: 16px; padding: 15px 17px; }
#share-card .card-stat-box .stat-num {
  font-family: var(--sans); font-size: 24px; font-weight: 800; color: var(--accent-deep); line-height: 1.2;
}
#share-card .card-stat-box .stat-num .stat-arrow { font-size: 13px; margin-left: 5px; }
#share-card .card-stat-box .stat-num .stat-arrow.up { color: #d0453b; }
#share-card .card-stat-box .stat-num .stat-arrow.down { color: #17a374; }
#share-card .card-stat-box .stat-num .stat-arrow.flat { color: #7d90a8; }
#share-card .card-stat-box .stat-label {
  font-size: 10px; font-weight: 600; color: var(--ink-3); margin-top: 6px; line-height: 1.5; letter-spacing: .3px;
}
#share-card .card-highlights-title { font-size: 9px; font-weight: 800; color: var(--ink-4); letter-spacing: 4px; margin-bottom: 12px; }
#share-card .card-highlights { list-style: none; padding: 0; margin: 0; }
#share-card .card-highlights li { padding: 10px 0; font-size: 13px; color: var(--ink-2); line-height: 1.6; border-bottom: 1px solid var(--line); }
#share-card .card-highlights li:last-child { border-bottom: none; }
#share-card .card-highlights .hl-icon {
  font-family: var(--sans); font-size: 11px; font-weight: 800; color: #fff;
  background: linear-gradient(150deg, var(--accent-2), var(--accent)); border-radius: 999px;
  padding: 2px 9px; margin-right: 10px;
}
#share-card .card-bottom { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--line); }
.share-modal .modal-box .download-btn {
  background: linear-gradient(100deg, var(--accent), var(--accent-2)); color: #fff; border: 0; cursor: pointer;
  font-family: inherit; font-size: 13px; font-weight: 800; letter-spacing: 2px;
  padding: 12px 26px; border-radius: 999px; margin-top: 16px; transition: opacity .15s;
}
.share-modal .modal-box .download-btn:hover { opacity: .9; }
.share-modal .modal-box .download-btn:active { transform: none; }
.share-modal .modal-box .download-btn.loading { opacity: .7; pointer-events: none; }
.share-modal .modal-box .hint { color: var(--ink-3); font-size: 11px; font-weight: 500; margin-top: 10px; text-align: center; }
.share-actions { display: flex; gap: 10px; justify-content: center; margin-top: 14px; flex-wrap: wrap; }
.share-actions .download-btn { margin-top: 0; padding: 11px 24px; font-size: 12px; }
.share-actions .download-btn.ghost { background: #eef4fd; color: var(--accent-deep); }
.share-actions .download-btn.ghost:hover { background: #e2ecfa; box-shadow: none; opacity: 1; }

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .card-grid.cols-2 { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 640px) {
  .header .topbar { padding: 9px 14px; }
  .home-btn { font-size: 11px; letter-spacing: 2px; }
  .header .logo-wrap { padding: 34px 16px 32px; }
  .header .logo-text { font-size: 1.9em; letter-spacing: 7px; text-indent: 7px; }
  .header h1 { font-size: .95em; letter-spacing: 3px; margin-top: 16px; }
  .header .subtitle { font-size: 10px; letter-spacing: 3px; }
  .header .date-range { font-size: 12px; padding: 8px 16px; margin-top: 18px; }
  .stats-bar { flex-direction: column; margin: 20px auto 30px; padding: 0 16px; }
  .stat-card { margin: 0 0 12px; padding: 18px 16px 16px; }
  .stat-card:last-child { margin-bottom: 0; }
  .stat-card .num { font-size: 1.85em; }
  .stat-card .label { font-size: 11.5px; }
  .container { padding: 0 16px; }
  .section { margin-bottom: 34px; }
  .section-title { font-size: 15px; margin-bottom: 16px; }
  .card-grid.cols-2 { grid-template-columns: minmax(0, 1fr); gap: 14px; }
  .card { padding: 19px 17px 17px; }
  .card h3 { font-size: 15px; margin-bottom: 8px; }
  .card p { font-size: 13.5px; line-height: 1.85; }
  .card .source-link { margin-top: 14px; }
  .key-insight { border-radius: 16px; margin-bottom: 32px; }
  .key-insight h3 { font-size: 13px; padding: 14px 16px; }
  .key-insight p { padding: 16px 16px 4px; }
  #hotlist { padding: 0; }
  #hotlist li { grid-template-columns: 30px minmax(0, 1fr); gap: 11px; padding: 14px 14px 14px 13px; }
  #hotlist .rank { width: 26px; height: 26px; font-size: 12px; }
  #hotlist .hot-desc { font-size: 13px; line-height: 1.75; }
  .trend-visual { flex-direction: column; gap: 12px; }
  .trend-item { padding: 16px; }
  .trend-item .trend-value { font-size: 21px; }
  .trend-item .trend-value .trend-delta { font-size: 12.5px; margin-left: 7px; }
  .trend-dir { margin-bottom: 8px; }
  .footer { margin-top: 36px; padding: 26px 16px 36px; }
  .share-btn-fab { bottom: 16px; right: 16px; padding: 11px 18px; font-size: 11px; }
  .share-modal .modal-box { width: 100%; padding: 16px 14px; border-radius: 16px; }
  #share-card { width: 100%; }
  #share-card .card-content { padding: 20px 18px; }
  #share-card .card-stats { grid-template-columns: 1fr 1fr; }
  #shareCardImg { max-width: 100%; }
}

/* ============================================================
   深色模式（html.theme-dark）—— 亮色为方案2，深色取方案1的深蓝气质
   ============================================================ */
html.theme-dark {
  --paper: #08182c;
  --surface: #102539;
  --ink: #e9f1fb;
  --ink-2: #b7c9df;
  --ink-3: #8ba2bd;
  --ink-4: #6f87a3;
  --line: #1d3a5c;
  --line-2: #2c4a70;
  --accent: #5aa5f2;
  --accent-2: #7cbbf7;
  --accent-deep: #9ccdf9;
  --up: #f2685e;
  --down: #3ecf9a;
  --shadow: 0 2px 6px rgba(0,0,0,.3), 0 16px 40px rgba(0,0,0,.38);
  --shadow-sm: 0 1px 3px rgba(0,0,0,.28), 0 8px 22px rgba(0,0,0,.3);
  color-scheme: dark;
}
html.theme-dark body { background: #08182c; }
html.theme-dark::selection { background: var(--accent); color: #04121f; }

/* 报头 */
html.theme-dark .header { background: #0b1e35; }
html.theme-dark .header::after { opacity: .85; }
html.theme-dark .header .date-range { background: #17334f; color: var(--accent-deep); border: 1px solid #25507a; }
html.theme-dark .lang-switch .seg { background: #17334f; }
html.theme-dark .lang-switch .seg button { color: var(--ink-3); }
html.theme-dark .theme-btn { background: #17334f; color: var(--accent-deep); border: 1px solid #25507a; }

/* 卡片体系 */
html.theme-dark .card,
html.theme-dark .stat-card,
html.theme-dark .trend-item { border-color: var(--line); }
html.theme-dark .card .date .source { background: #17334f; color: var(--accent-deep); }
html.theme-dark .key-insight { border-color: var(--line); }
html.theme-dark .key-insight h3 {
  background: linear-gradient(100deg, #14304e, #1a3c60);
  color: var(--accent-deep); border-bottom-color: var(--line);
}
html.theme-dark #hotlist li + li { border-top-color: var(--line); }
html.theme-dark #hotlist li:hover { background: #14304e; }
html.theme-dark #hotlist em.fig {
  background: linear-gradient(transparent 62%, rgba(90,165,242,.3) 62%);
}
html.theme-dark .footer { border-top-color: var(--line); }

/* 分享 */
html.theme-dark .share-modal { background: rgba(3,10,20,.72); }
html.theme-dark .share-modal .modal-box .modal-header .close-btn { background: #17334f; }
html.theme-dark .share-modal .modal-box .download-btn.ghost { background: #17334f; color: var(--accent-deep); }
html.theme-dark #share-card { border-color: var(--line); }
html.theme-dark #share-card .card-stat-box { background: #14304e; }
html.theme-dark #share-card .card-highlights li,
html.theme-dark #share-card .card-divider { border-color: var(--line); }
"""

# ─── 辅助函数 ──────────────────────────────────────────────────────────

# 关键数字高亮：带单位/量词的数值（3.830% / 3万5,146日元 / 5.2公顷 / 9,754户 …）
_FIG_UNITS = (r'(?:%|pt|‰|户|戸|戶|円|万円|万|日元|日円|億元|亿|億|ha|公顷'
              r'|㎡|平米|階|阶|米|件|室|期|号|栋|栋|套|个月|ヶ月|社|人)')
_FIG_RE = re.compile(r'(\d[\d,\.]*(?:万|億|亿)?[\d,\.]*\s*' + _FIG_UNITS + r')')
_ARROWS = ('▲', '▼', '△', '▽', '↑', '↓')


def highlight_figures(text):
    """把热点条目里的关键数字（含量词）包一层 <em class="fig">，便于扫读定位。"""
    if not text:
        return text
    return _FIG_RE.sub(r'<em class="fig">\1</em>', text)


def split_hot_item(text):
    """拆成「小标题 / 说明」两段（无分隔符时说明为空）。"""
    for sep in (' — ', ' ― ', '——', '――', '－', '：'):
        if sep in text:
            a, b = text.split(sep, 1)
            return a.strip(), b.strip()
    return (text or '').strip(), ''


def split_trend_delta(value):
    """把 '3.830% ▲0.37pt' 拆成 ('3.830%', '▲0.37pt')；无箭头则 delta 为空串。"""
    v = (value or '').strip()
    for a in _ARROWS:
        if a in v:
            i = v.index(a)
            return v[:i].strip(), v[i:].strip()
    return v, ''


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

def _ym_cn(dt):
    """2026年8月（去前导零）"""
    return dt.strftime('%Y年%m月').replace('年0', '年').replace('月0', '月')

def get_half_month_label(dt=None):
    """上旬号 / 下旬号（基于日期）"""
    if dt is None:
        dt = datetime.now()
    return '上旬号' if dt.day <= 15 else '下旬号'

def report_issue_label(dt=None):
    """半月报期数标签，例如 '2026年8月 上旬号'"""
    if dt is None:
        dt = datetime.now()
    return f'{_ym_cn(dt)} {get_half_month_label(dt)}'

def get_half_month_range(dt=None):
    """本期覆盖的日期区间（上旬 1~15 / 下旬 16~月末）"""
    import calendar
    if dt is None:
        dt = datetime.now()
    if dt.day <= 15:
        start = dt.replace(day=1)
        end = dt.replace(day=15)
    else:
        start = dt.replace(day=16)
        last = calendar.monthrange(dt.year, dt.month)[1]
        end = dt.replace(day=last)
    fmt = lambda d: d.strftime('%Y年%m月%d日').replace('年0', '年').replace('月0', '月')
    return f'{fmt(start)} — {fmt(end)}'

def render_news_card(news, accent_class, label_class):
    meta  = f'<div class="date">{news["date"]} <span class="source">{news["source"]}</span></div>'
    # 双语：默认显示中文(title_cn/body_cn)，日文作 data-jp 后备
    _title_cn = news.get('title_cn', news['title'])
    _body_cn  = news.get('body_cn', news['body'])
    _title_jp = news.get('title_jp', news['title'])
    _body_jp  = news.get('body_jp', news['body'])
    title = (f'<h3><span class="lang-cn">{_title_cn}</span>'
            f'<span class="lang-jp" data-jp="{_title_jp.replace(chr(34), chr(39))}">{_title_jp}</span></h3>')
    body  = (f'<p><span class="lang-cn">{_body_cn}</span>'
           f'<span class="lang-jp" data-jp="{_body_jp.replace(chr(34), chr(39))}">{_body_jp}</span></p>')
    link  = f'<a href="{news["url"]}" target="_blank" rel="noopener" class="source-link">阅读原文 →</a>'
    return f'''<div class="card {accent_class}">
  {meta}
  {title}
  {body}
  <span class="label {label_class}">{news["source"]}</span>
  {link}
</div>'''

def render_news_section(key):
    meta = SECTIONS_META[key]
    icon, title_cn, title_jp, tag, accent_class, label_class = meta
    items = NEWS_DATA.get(key, [])
    cards_html = '\n'.join(render_news_card(n, accent_class, label_class) for n in items)
    return f'''<div class="section newssec sec-{key}">
  <div class="section-title">
    <span class="icon">{icon}</span>
    <span class="lang-cn">{title_cn}</span><span class="lang-jp" data-jp="{title_jp}">{title_jp}</span>
    <span class="tag">{tag}</span>
  </div>
  <div class="card-grid cols-2">
{cards_html}
  </div>
</div>'''

def build_report_html(dt=None):
    """构建本期报告HTML（2026-10 杂志风重构：纸感/细线/克制单色+单一深蓝墨色强调）
    dt: 可指定「本期」的基准日期（datetime）；缺省为今天。用于回溯/补发指定期号。
        例：dt=datetime(2026,10,15) -> 「2026年10月 上旬号」，覆盖 2026/10/1–10/15。"""
    _today = dt if dt is not None else datetime.now()
    today_str  = _today.strftime('%Y年%m月%d日')\
        .replace('年0','年').replace('月0','月')
    date_range = get_half_month_range(_today)   # 本期覆盖的半月区间
    issue_label = report_issue_label(_today)    # 例如「2026年8月 上旬号」

    # ⚠️ 读取真实周报数据（cron 抓取的 JSON 优先；缺失则退回内置 NEWS_DATA）
    #    用 global 覆盖，使下方 render_news_section 读到最新数据
    global NEWS_DATA
    NEWS_DATA = load_weekly_data()

    # 贷款利率趋势 + 小虾点评（真实抓取優先、なければ DEFAULT_* 兜底）
    _f35 = NEWS_DATA.get('flat35', DEFAULT_FLAT35)
    FLAT35_RATE    = _f35.get('rate', DEFAULT_FLAT35['rate'])
    FLAT35_MONTH   = _f35.get('month_cn', _f35.get('month', DEFAULT_FLAT35['month']))
    FLAT35_NOTE    = _f35.get('note_cn', _f35.get('note', DEFAULT_FLAT35['note']))
    FLAT35_MONTH_JP = _f35.get('month_jp', _f35.get('month', DEFAULT_FLAT35['month']))
    FLAT35_NOTE_JP  = _f35.get('note_jp', _f35.get('note', DEFAULT_FLAT35['note']))
    XIAOXIA_COMMENT = NEWS_DATA.get('comment_cn', NEWS_DATA.get('comment', DEFAULT_COMMENT))
    XIAOXIA_COMMENT_JP = NEWS_DATA.get('comment_jp', NEWS_DATA.get('comment', DEFAULT_COMMENT))

    # 热点速览（中文优先；原 JP 作 data-jp 后备）
    hot_items = NEWS_DATA.get('hot_cn', NEWS_DATA.get('hot', DEFAULT_HOT))
    _hot_jp = NEWS_DATA.get('hot_jp', NEWS_DATA.get('hot', hot_items))
    _hot_rows = []
    for _hi, item in enumerate(hot_items):
        _jp_item = _hot_jp[_hi] if _hi < len(_hot_jp) else item
        _lead_cn, _desc_cn = split_hot_item(item)
        _lead_jp, _desc_jp = split_hot_item(_jp_item)
        _rank = '%02d' % (_hi + 1)
        _cn_html = ('<strong class="hot-lead">' + highlight_figures(_lead_cn) + '</strong>'
                    + ('<span class="hot-desc"> — ' + highlight_figures(_desc_cn) + '</span>' if _desc_cn else ''))
        _jp_html = ('<strong class="hot-lead">' + highlight_figures(_lead_jp) + '</strong>'
                    + ('<span class="hot-desc"> ― ' + highlight_figures(_desc_jp) + '</span>' if _desc_jp else ''))
        _hot_rows.append('<li><span class="rank">' + _rank + '</span>'
                         '<span class="hot-body">'
                         '<span class="lang-cn">' + _cn_html + '</span>'
                         '<span class="lang-jp" data-jp="' + _jp_item.replace(chr(34), chr(39)) + '">' + _jp_html + '</span>'
                         '</span></li>')
    hot_html = '\n'.join(_hot_rows)

    # 顶部统计卡（中文 label_cn 优先；JP 作 data-jp 后备）
    # 每张卡附「性质标签」：升=红 / 降=绿 / 中性=灰，与市场趋势同一套语义色。
    _tag_default = [
        ('up',   '现行制度以来最高', '現行制度以来最高'),
        ('up',   '31年来新高',      '31年ぶり高値'),
        ('up',   '连续5个月增加',   '5カ月連続増'),
        ('down', '连续6个月下降',   '6カ月連続低下'),
        ('flat', '街区开发规模',    '街区開発規模'),
    ]
    stats_html = ''
    # ★ 修复 CN/JP 错位（2026-08-04）：
    #   原始 primary(cn/sample) 与 jp 的 stats 列表【按索引不对齐】，
    #   旧渲染把 primary 的 value 与 cn/jp 的 label 按同索引硬拼 -> 值/标签描述不同指标。
    #   现统一以中文数据(cn)为权威源（含 value + label_cn），再按索引叠加 jp 的 label_jp，
    #   保证「同一指标的数值与中/日标签」必然对应。cn 缺失时退回 sample 兜底。
    _stats_src = None
    if isinstance(_WEEKLY_CN, dict) and isinstance(_WEEKLY_CN.get('stats'), list) and _WEEKLY_CN['stats']:
        _stats_src = _WEEKLY_CN['stats']
    elif isinstance(NEWS_DATA.get('stats'), list) and NEWS_DATA['stats']:
        _stats_src = NEWS_DATA['stats']
    else:
        _stats_src = DEFAULT_STATS
    _jp_stats = _WEEKLY_JP.get('stats') if isinstance(_WEEKLY_JP, dict) else None
    for _i, _s in enumerate(_stats_src):
        _s = _s if isinstance(_s, dict) else {'label': str(_s)}
        _lbl_cn = _s.get('label_cn', _s.get('label', ''))
        _lbl_jp = _s.get('label_jp', '')
        if not _lbl_jp and isinstance(_jp_stats, list) and _i < len(_jp_stats) and isinstance(_jp_stats[_i], dict):
            _lbl_jp = _jp_stats[_i].get('label_jp', '')
        _d, _tag_cn, _tag_jp = _tag_default[_i] if _i < len(_tag_default) else ('', '', '')
        _d     = _s.get('dir') or _d
        _tag_cn = _s.get('tag_cn') or _tag_cn
        _tag_jp = _s.get('tag_jp') or _tag_jp
        _tag_jp_esc = (_tag_jp or '').replace(chr(34), chr(39))
        _tag_html = ''
        if _tag_cn or _tag_jp:
            _tag_html = ('      <div class="stat-tag ' + _d + '">'
                         '<span class="lang-cn">' + _tag_cn + '</span>'
                         '<span class="lang-jp" data-jp="' + _tag_jp_esc + '">' + _tag_jp + '</span></div>\n')
        stats_html += ('    <div class="stat-card">\n'
                       '      <div class="num">' + _s.get('value_cn', _s.get('value', '')) + '</div>\n'
                       + _tag_html +
                       '      <div class="label"><span class="lang-cn">' + _lbl_cn + '</span>'
                       '<span class="lang-jp" data-jp="' + _lbl_jp.replace(chr(34), chr(39)) + '">' + _lbl_jp + '</span></div>\n'
                       '    </div>\n')

    # 市场趋势（中文 label_cn 优先；JP 作 data-jp 后备）
    _dir_txt = {'up': ('上涨', '上昇'), 'down': ('下跌', '下落'), 'flat': ('持平', '横ばい')}
    trend_html = ''
    for _t in NEWS_DATA.get('trends', DEFAULT_TRENDS):
        _label, _value, _dir = _t.get('label_cn', _t['label']), _t.get('value_cn', _t['value']), _t.get('dir', 'flat')
        _label_jp = _t['label'].replace('\n', '<br>')
        _val_cn, _delta_cn = split_trend_delta(_value)
        _val_jp, _delta_jp = split_trend_delta(_t['value'])
        _d_cn, _d_jp = _dir_txt.get(_dir, _dir_txt['flat'])
        _delta_jp_html = ('<span class="trend-delta">' + _delta_jp + '</span>') if _delta_jp else ''
        trend_html += ('    <div class="trend-item">\n'
                       '      <div class="trend-label"><span class="lang-cn">' + _label.replace(chr(10), '<br>') + '</span>'
                       '<span class="lang-jp" data-jp="' + _label_jp.replace(chr(34), chr(39)) + '">' + _label_jp + '</span></div>\n'
                       '      <div class="trend-dir ' + _dir + '"><span class="lang-cn">' + _d_cn + '</span>'
                       '<span class="lang-jp" data-jp="' + _d_jp + '">' + _d_jp + '</span></div>\n'
                       '      <div class="trend-value ' + _dir + '">'
                       '<span class="lang-cn"><span class="trend-num">' + _val_cn + '</span>'
                       '<span class="trend-delta">' + _delta_cn + '</span></span>'
                       '<span class="lang-jp" data-jp="' + (_val_jp + _delta_jp_html).replace(chr(34), chr(39)) + '">'
                       + _val_jp + _delta_jp_html + '</span></div>\n'
                       '    </div>\n')

    news_sections_html = '\n'.join(render_news_section(k) for k in ['policy','deals','develop','tech','survey'])

    # Pagefind 搜索框 + 隐私统计(Umami) 注入所需变量（占位串，避免 f-string 内花括号冲突）
    PAGELOAD_CSS = '<style>.pf-search{position:relative;z-index:30;max-width:340px;margin:-22px 16px 10px auto;padding:0 4px;}.pf-search .pagefind-ui{--pagefind-ui-scale:0.82;--pagefind-ui-primary:#0f3460;--pagefind-ui-text:#1a1a2e;--pagefind-ui-background:#ffffff;--pagefind-ui-border:#d7dce5;--pagefind-ui-tag:#eef1f7;--pagefind-ui-border-width:1px;--pagefind-ui-border-radius:10px;--pagefind-ui-font:inherit;}.pf-search .pagefind-ui__drawer{position:relative;z-index:31;}@media (max-width:640px){.pf-search{max-width:none;margin:8px 12px 12px;}.pf-search .pagefind-ui{--pagefind-ui-scale:0.9;}}</style>'
    PAGELOAD_JS = '<div class="pf-search" data-pagefind-ignore><div id="pfsearch"></div></div><script src="/pagefind/pagefind-ui.js"></script><script>window.addEventListener("DOMContentLoaded",function(){new PagefindUI({element:"#pfsearch",showSubResults:true});});</script>'
    ANALYTICS = _an.snippet()

    html = f'''<!DOCTYPE html>
<html lang="ja" class="lang-cn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/pagefind/pagefind-ui.css">
<meta name="description" content="大誠有限会社専用不動產半月報 {date_range}">
<title>大誠不动產半月報 {date_range}</title>
<style>{CSS}</style>
{PAGELOAD_CSS}
{ANALYTICS}
</head>
<body>

<div class="header">
  <div class="topbar">
    <a href="../../index.html" class="home-btn">返回主页</a>
    <div class="topbar-right">
      <button type="button" class="theme-btn" id="themeBtn" onclick="toggleTheme()"><span class="lang-cn">暗色</span><span class="lang-jp">ダーク</span></button>
      <div class="lang-switch" id="langSwitch">
        <div class="seg">
          <button type="button" data-lang="cn" class="active">中文</button>
          <button type="button" data-lang="jp">日本語</button>
        </div>
      </div>
    </div>
  </div>
  <div class="logo-wrap">
    <span class="logo-text">TAISEI</span>
    <div class="title-group">
      <h1><span class="lang-cn">{COMPANY_NAME_CN}专用不动产半月报</span><span class="lang-jp" data-jp="{COMPANY_NAME_JP}専用不動產半月報">{COMPANY_NAME_JP}専用不動產半月報</span></h1>
      <div class="subtitle"><span class="lang-cn">政策 · 市场 · 开发 · 趋势</span><span class="lang-jp" data-jp="政策 · 市場 · 開発 · トレンド">政策 · 市場 · 開発 · トレンド</span></div>
      <div class="date-range" id="headerDateRange">{date_range}</div>
    </div>
  </div>
</div>

{PAGELOAD_JS}

<!-- Stats -->
<div class="stats-bar" id="statsBar">
{stats_html}</div>

<div class="container" data-pagefind-body>

<!-- 热点速览 -->
<div class="key-insight">
  <h3><span class="lang-cn">本期热点速览</span><span class="lang-jp" data-jp="今期の注目トピックス">今期の注目トピックス</span><span class="count"><span class="lang-cn">{len(hot_items)} 条</span><span class="lang-jp" data-jp="全{len(hot_items)}件">全{len(hot_items)}件</span></span></h3>
  <ul id="hotlist">
{hot_html}
  </ul>
</div>

<!-- Market Trend -->
<div class="section">
  <div class="section-title">
    <span class="icon"></span> <span class="lang-cn">市场趋势</span><span class="lang-jp" data-jp="市場トレンド">市場トレンド</span>
    <span class="tag">MARKET</span>
  </div>
  <div class="trend-visual">
{trend_html}  </div>
</div>

{news_sections_html}

<!-- 贷款利率趋势 -->
<div class="key-insight">
  <h3><span class="lang-cn">贷款利率趋势</span><span class="lang-jp" data-jp="住宅ローン金利トレンド">住宅ローン金利トレンド</span></h3>
  <p><span class="lang-cn"><strong>Flat35：</strong>{FLAT35_RATE}（{FLAT35_MONTH}）。{FLAT35_NOTE}</span><span class="lang-jp" data-jp="フラット35：{FLAT35_RATE}（{FLAT35_MONTH_JP}）。{FLAT35_NOTE_JP}">フラット35：{FLAT35_RATE}（{FLAT35_MONTH_JP}）。{FLAT35_NOTE_JP}</span></p>
  <p style="margin-top:10px;"><strong>💡 小虾点评：</strong><span class="lang-cn">{XIAOXIA_COMMENT}</span><span class="lang-jp" data-jp="{XIAOXIA_COMMENT_JP}">{XIAOXIA_COMMENT_JP}</span></p>
</div>

</div>

<div class="footer">
  <p>数据来源：国土交通省 / 日経不動産マーケット情報 / 週刊住宅タイムズ / 週刊不動産経営 / 東京カンテイ / SUUMO / 不動産経済研究所 / 東日本レインズ / R.E.port</p>
  <p style="margin-top:4px;">Generated by Taisei AI · {today_str} · 东京 · {COMPANY_NAME_JP} 専用</p>
</div>

<!-- ===== Floating Share Button ===== -->
<button class="share-btn-fab" id="shareBtn" onclick="openShareModal()">生成分享卡片</button>

<!-- ===== Share Modal ===== -->
<div class="share-modal" id="shareModal">
  <div class="modal-box">
    <div class="modal-header">
      <span>朋友圈卡片预览</span>
      <button class="close-btn" onclick="closeShareModal()">✕</button>
    </div>
    <div id="share-card-container"></div>
    <img id="shareCardImg" alt="朋友圈卡片" style="display:none" />
    <div class="share-actions">
      <button class="download-btn" id="downloadBtn" onclick="generateImage()">📥 保存图片</button>
      <button class="download-btn ghost" id="copyBtn" onclick="copyCard()">📋 复制文案</button>
    </div>
    <div class="hint">手机：长按下方图片 → 保存到相册 / 转发朋友圈 · 电脑：点「保存图片」下载 PNG</div>
  </div>
</div>

<!-- HTML2CANVAS_INLINE -->
<!-- WARNING 勿删上方占位符：运行时注入内联 html2canvas 库；
     库文件=仓库根 html2canvas.min.js，改 CDN 外链会被墙或微信拦截。
     注入必须在 f-string 之外做，否则库内花括号会破坏 f-string 语法。
     此占位符若缺失，分享图片功能直接崩。 -->

<script>
const COMPANY_NAME_JP = '大誠有限会社';
const COMPANY_SITE = 'https://www.taisei-r.com/';
function getDateRange() {{
  const el = document.getElementById('headerDateRange');
  return el ? el.textContent.trim() : '2026年6月 下半期';
}}

function visibleText(el) {{
  if (!el) return '';
  var cur = document.documentElement.classList.contains('lang-jp') ? 'lang-jp' : 'lang-cn';
  var sel = el.querySelector('.' + cur);
  if (sel) return sel.textContent;
  return el.textContent;
}}

function getStats() {{
  const cards = document.querySelectorAll('#statsBar .stat-card');
  const stats = [];
  cards.forEach(c => {{
    const num = c.querySelector('.num');
    const label = c.querySelector('.label');
    if (num && label) {{
      stats.push({{
        num: visibleText(num).trim(),
        label: visibleText(label).trim().replace(/\\s+/g, ' ')
      }});
    }}
  }});
  return stats;
}}

function getHighlights() {{
  const items = document.querySelectorAll('#hotlist li');
  const highlights = [];
  items.forEach(li => {{
    const txt = visibleText(li).trim().replace(/^\\s*[—\\-–]\\s*/, '');
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
  const icons = ['01', '02', '03', '04'];
  highlights.forEach((h, i) => {{
    hlHTML += '<li><span class="hl-icon">' + (icons[i] || '▸') + '</span>' + h + '</li>';
  }});

  return '<div id="share-card">' +
    '<div class="card-dots"></div>' +
    '<div class="card-top-accent"></div>' +
    '<div class="card-content">' +
      '<div class="card-logo">TAISEI</div>' +
      '<div class="card-meta">BI-WEEKLY REAL ESTATE REPORT</div>' +
      '<div class="card-date-badge">' + dateRange + '</div>' +
      '<hr class="card-divider">' +
      '<div class="card-stats">' + statsHTML + '</div>' +
      '<hr class="card-divider">' +
      '<div class="card-highlights-title">HIGHLIGHTS</div>' +
      '<ul class="card-highlights">' + hlHTML + '</ul>' +
      '<div class="card-bottom">' +
        '<span class="brand">' + COMPANY_NAME_JP + ' · 不動産専門</span>' +
        '<span class="cta">taisei-r.com</span>' +
      '</div>' +
    '</div>' +
  '</div>';
}}

function buildCardText() {{
  const dateRange = getDateRange();
  const stats = getStats();
  const highlights = getHighlights();
  const NL = String.fromCharCode(10);
  let t = '【' + COMPANY_NAME_JP + ' 大诚不动产半月报】' + NL + dateRange + NL + NL;
  stats.slice(0,4).forEach(function(s) {{ t += '\u2022 ' + s.label + '\uff1a' + s.num + NL; }});
  t += NL + '本期焦点：' + NL;
  highlights.forEach(function(h) {{ t += '\u25b8 ' + h + NL; }});
  t += NL + '详情见官方频道 / ' + COMPANY_SITE;
  return t;
}}

function openShareModal() {{
  document.getElementById('shareModal').classList.add('show');
  document.body.style.overflow = 'hidden';
  const container = document.getElementById('share-card-container');
  const img = document.getElementById('shareCardImg');
  container.innerHTML = buildShareCard();
  container.style.display = 'block';   // 先显示HTML卡片
  img.style.display = 'none';          // 图片先隐藏，渲染成功后再切换
  img.removeAttribute('src');
  renderCardImage();
}}

function renderCardImage() {{
  // ⚠️ 关键：HTML卡片 与 渲染图片 同一时刻只能显示一个，否则出现「大图套小图」+
  // 高度翻倍把按钮挤出屏幕。流程：先显HTML → 渲染PNG → 成功则隐藏HTML只留图片。
  const src = document.getElementById('share-card-container');
  const img = document.getElementById('shareCardImg');
  if (typeof html2canvas === 'undefined') return; // 库未加载则只显示HTML卡片(退化)
  try {{
    html2canvas(src, {{ backgroundColor: null, scale: 2, useCORS: true }}).then(function(canvas) {{
      img.src = canvas.toDataURL('image/png');
      img.style.display = 'block';
      src.style.display = 'none';      // 图片就绪后隐藏HTML卡片，避免大图套小图
    }}).catch(function() {{ /* 失败则保留HTML卡片 */ }});
  }} catch (e) {{ /* 忽略 */ }}
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

function generateImage() {{
  const btn = document.getElementById('downloadBtn');
  const img = document.getElementById('shareCardImg');
  if (img && img.src && img.style.display !== 'none') {{
    // 图片已生成：直接触发下载
    const a = document.createElement('a');
    a.href = img.src;
    a.download = 'taisei-weekly-card.png';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    const old = btn.textContent;
    btn.textContent = '✅ 已保存';
    setTimeout(function() {{ btn.textContent = old; }}, 1500);
  }} else if (typeof html2canvas !== 'undefined') {{
    // 图片还没生成：现生成再下载
    const src = document.getElementById('share-card-container');
    html2canvas(src, {{ backgroundColor: null, scale: 2, useCORS: true }}).then(function(canvas) {{
      const a = document.createElement('a');
      a.href = canvas.toDataURL('image/png');
      a.download = 'taisei-weekly-card.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }});
  }} else {{
    alert('图片生成库未加载，请用「复制文案」');
  }}
}}

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

/* ===== 语言切换（与主页共用 localStorage『taisei_lang』） ===== */
function applyReportLang(lang) {{
  document.documentElement.classList.toggle('lang-cn', lang === 'cn');
  document.documentElement.classList.toggle('lang-jp', lang === 'jp');
  document.documentElement.lang = (lang === 'jp') ? 'ja' : 'zh-CN';
  document.querySelectorAll('#langSwitch .seg button').forEach(function(b) {{
    b.classList.toggle('active', b.getAttribute('data-lang') === lang);
  }});
  // 日文：用 data-jp 文本替换同级 .lang-jp 的展示（兼容多段/标题）
  // ⚠️ 必须排除 <html> 自身：切换时 lang-jp 这个 class 是加在 documentElement 上的，
  //    querySelectorAll('.lang-jp') 会把 <html> 也选进来（曾导致根元素 display 被改写）。
  document.querySelectorAll('.lang-jp').forEach(function(el) {{
    if (el === document.documentElement) return;
    const jp = el.getAttribute('data-jp');
    if (jp !== null) el.innerHTML = jp;  // 用 innerHTML 以渲染 <br> 等换行
  }});
  // 双保险：直接内联样式控制显示。即使 CSS 规则缺失/被缓存旧版覆盖，也绝不会两种语言同时隐藏（白屏）。
  document.querySelectorAll('.lang-cn').forEach(function(el) {{ if (el !== document.documentElement) el.style.display = (lang === 'jp') ? 'none' : 'inline'; }});
  document.querySelectorAll('.lang-jp').forEach(function(el) {{ if (el !== document.documentElement) el.style.display = (lang === 'jp') ? 'inline' : 'none'; }});
}}
function setReportLang(lang) {{
  applyReportLang(lang);
  try {{ localStorage.setItem('taisei_lang', lang); }} catch(e) {{}}
}}
/* ===== 深浅色主题（默认跟随系统，可手动覆盖并记忆） ===== */
function applyTheme(mode) {{
  const dark = (mode === 'dark');
  document.documentElement.classList.toggle('theme-dark', dark);
  const cn = document.querySelector('#themeBtn .lang-cn');
  const jp = document.querySelector('#themeBtn .lang-jp');
  if (cn) cn.textContent = dark ? '亮色' : '暗色';
  if (jp) jp.textContent = dark ? 'ライト' : 'ダーク';
  try {{ localStorage.setItem('taisei_theme', dark ? 'dark' : 'light'); }} catch(e) {{}}
}}
function toggleTheme() {{
  applyTheme(document.documentElement.classList.contains('theme-dark') ? 'light' : 'dark');
}}
(function() {{
  const sw = document.getElementById('langSwitch');
  if (sw) {{
    sw.querySelectorAll('.seg button').forEach(function(b) {{
      b.addEventListener('click', function() {{ setReportLang(b.getAttribute('data-lang')); }});
    }});
  }}
  let saved = null;
  try {{ saved = localStorage.getItem('taisei_lang'); }} catch(e) {{}}
  applyReportLang(saved || 'cn');  // 默认中文
  let theme = null;
  try {{ theme = localStorage.getItem('taisei_theme'); }} catch(e) {{}}
  if (!theme) {{
    theme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }}
  applyTheme(theme);
}})();
</script>
</body>
</html>'''

    # 内联 html2canvas 库（绕过 CDN 被墙，且不在 f-string 内，避免花括号冲突）
    try:
        with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'html2canvas.min.js'), encoding='utf-8') as _f:
            _lib = _f.read()
        _inline = '<script>\n/* html2canvas 内联（绕过 CDN 被墙） */\n' + _lib + '\n</script>\n'
        html = html.replace('<!-- HTML2CANVAS_INLINE -->', _inline, 1)
    except Exception as _e:
        pass

    return html

# ─── 主页视觉（2026-10 重构 · 杂志风蓝调，与周报页同token） ────────────────────
# 设计目标：一眼看懂「这是什么站 / 提供什么功能」
#   - 报头（kicker + 衬线大标题 + 一句定位）+ 四项功能卡 + 最新一期 + 往期
#   - 与周报页共用 --paper/--ink/--accent 与细线分隔，视觉语言统一
#   - 双语：沿用 I18N JS 字典 + data-i18n，另加 lang-cn/lang-jp 双 span（同一套规则）
HOME_CSS = """:root {
  --paper: #f4f8fe;
  --surface: #ffffff;
  --ink: #0c1d33;
  --ink-2: #2a4160;
  --ink-3: #526a86;
  --ink-4: #7d90a8;
  --rule: #dde8f6;
  --rule-2: #bcd2ea;
  --accent: #1668dc;
  --accent-2: #3b8ef0;
  --accent-deep: #0d4ea8;
  --serif: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  --r: 18px; --r-sm: 12px;
  --shadow: 0 2px 6px rgba(13,78,168,.05), 0 14px 34px rgba(13,78,168,.08);
  --shadow-sm: 0 1px 3px rgba(13,78,168,.05), 0 6px 16px rgba(13,78,168,.05);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: var(--sans); background: var(--paper); color: var(--ink);
  font-size: 16px; line-height: 1.78; counter-reset: hsec; -webkit-font-smoothing: antialiased;
}
::selection { background: var(--accent); color: #fff; }
a { color: inherit; }
html.lang-jp .lang-cn { display: none; }
html.lang-cn .lang-jp { display: none; }
html.lang-jp .lang-jp { display: inline; }
html.lang-cn .lang-cn { display: inline; }

/* ===== 顶栏 ===== */
.topbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 11px 24px; background: var(--surface); border-bottom: 1px solid var(--rule);
}
.brand { display: flex; align-items: baseline; gap: 12px; text-decoration: none; color: var(--ink-2); min-width: 0; }
.brand .mark { font-size: 16px; font-weight: 800; letter-spacing: 5px; color: var(--accent-deep); }
.brand .co { font-size: 11px; letter-spacing: 2px; color: var(--ink-4); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lang-switch { flex: 0 0 auto; display: flex; align-items: center; gap: 4px;
  border: 1px solid var(--line-2); background: #eef4fd; border-radius: 999px; padding: 3px; }
.lang-btn { background: transparent; border: 0; cursor: pointer; font-family: inherit;
  font-size: 12px; font-weight: 800; color: var(--ink-3); padding: 5px 14px; border-radius: 999px;
  transition: background .15s, color .15s; }
.lang-btn.active { background: var(--accent); color: #fff; }
.topbar-right { display: flex; align-items: center; gap: 10px; }
.theme-btn {
  background: #eef4fd; border: 1px solid var(--line-2); cursor: pointer; font-family: inherit;
  font-size: 12px; font-weight: 800; color: var(--ink-3); padding: 5px 14px; border-radius: 999px;
  transition: background .15s, color .15s, border-color .15s;
}
.theme-btn:hover { background: #e2ecfa; color: var(--accent-deep); border-color: var(--accent-2); }

/* ===== 报头 ===== */
.masthead {
  padding: 54px 22px 44px; text-align: center; background: var(--surface);
  position: relative; overflow: hidden; border-bottom: 1px solid var(--rule);
}
.masthead::before {
  content: ''; position: absolute; top: -160px; left: 50%; transform: translateX(-50%);
  width: 620px; height: 380px; border-radius: 50%;
  background: radial-gradient(ellipse at center, rgba(59,142,240,.18), rgba(59,142,240,0) 70%);
}
.masthead-in { max-width: 780px; margin: 0 auto; position: relative; }
.kicker { font-size: 11px; font-weight: 800; letter-spacing: 4px; text-transform: uppercase; color: var(--accent); margin-bottom: 18px; }
.masthead h1 { font-size: clamp(30px, 6vw, 48px); line-height: 1.22; font-weight: 800;
  background: linear-gradient(100deg, var(--accent-deep), var(--accent), var(--accent-2));
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.masthead h1 .thin { color: var(--ink-4); font-weight: 600;
  -webkit-text-fill-color: var(--ink-4); }
.titlerule { width: 52px; height: 5px; background: linear-gradient(90deg, var(--accent), var(--accent-2)); border-radius: 999px; margin: 24px auto 0; }
.lede { margin: 20px auto 0; max-width: 620px; font-size: 15px; color: var(--ink-3); line-height: 2; }
.masthead-meta { margin-top: 22px; display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px 14px; font-size: 12px; color: var(--ink-4); }
.masthead-meta .dot { width: 4px; height: 4px; border-radius: 50%; background: var(--rule-2); flex: 0 0 auto; }

/* ===== 搜索条 ===== */
.searchstrip { background: var(--surface); border-bottom: 1px solid var(--rule); }
.searchstrip-in { max-width: 1000px; margin: 0 auto; padding: 13px 22px;
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.searchstrip-label { font-size: 11px; font-weight: 800; letter-spacing: 3px; color: var(--ink-4); text-transform: uppercase; white-space: nowrap; }
.pf-wrap { flex: 1 1 260px; min-width: 0; }

/* ===== 版面 ===== */
.wrap { max-width: 1000px; margin: 0 auto; padding: 0 22px 52px; }
.sec { margin-top: 44px; }
.sec-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.sec-no { display: none; }
.sec-title { font-size: 19px; font-weight: 800; color: var(--ink); line-height: 1.3; }
.sec-en { margin-left: auto; font-size: 10px; font-weight: 800; letter-spacing: 3px; text-transform: uppercase; color: var(--ink-4); }
.sec-note { font-size: 12px; color: var(--ink-4); }

/* ===== 功能卡 ===== */
.fx-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.fx { position: relative; display: flex; flex-direction: column; gap: 9px; min-width: 0;
  background: var(--surface); border: 1px solid var(--line); border-radius: 20px;
  padding: 22px 20px 20px; text-decoration: none; box-shadow: var(--shadow-sm);
  transition: box-shadow .16s, transform .16s, border-color .16s; }
.fx:hover { box-shadow: var(--shadow); transform: translateY(-3px); border-color: var(--accent-2); }
.fx-no { font-size: 12px; font-weight: 800; color: #fff; background: linear-gradient(150deg, var(--accent-2), var(--accent));
  width: 26px; height: 26px; border-radius: 9px; display: flex; align-items: center; justify-content: center; }
.fx-arrow { position: absolute; top: 22px; right: 18px; color: var(--accent); font-weight: 800; opacity: .5; }
.fx-title { font-size: 15px; font-weight: 800; color: var(--ink); line-height: 1.4; }
.fx-title .fx-en { display: block; font-style: normal; font-size: 9.5px; font-weight: 800;
  letter-spacing: 2px; text-transform: uppercase; color: var(--ink-4); margin-top: 4px; }
.fx-desc { font-size: 12.5px; font-weight: 400; color: var(--ink-3); line-height: 1.75; }
.fx-stat { margin-top: auto; font-size: 12px; font-weight: 800; color: var(--accent-deep); }

/* ===== 最新一期 ===== */
.featured { display: flex; align-items: stretch; gap: 22px; min-width: 0;
  background: var(--surface); border: 1px solid var(--line); border-radius: 24px;
  padding: 28px 30px; text-decoration: none; box-shadow: var(--shadow);
  transition: box-shadow .16s, transform .16s; }
.featured:hover { box-shadow: 0 20px 48px rgba(13,78,168,.16); transform: translateY(-2px); }
.featured-left { flex: 1 1 auto; min-width: 0; }
.featured-tag { display: inline-block; font-size: 10px; font-weight: 800; letter-spacing: 2px;
  color: #fff; background: linear-gradient(100deg, var(--accent), var(--accent-2)); border-radius: 999px; padding: 4px 13px; }
.featured-title { font-size: 25px; font-weight: 800; color: var(--ink); line-height: 1.3; margin-top: 12px; }
.featured-date { font-size: 12px; font-weight: 700; color: var(--ink-4); margin-top: 8px; letter-spacing: 1px; }
.featured-desc { font-size: 13.5px; color: var(--ink-2); line-height: 1.85; margin-top: 12px; }
.featured-cta { display: inline-block; margin-top: 16px; font-size: 12px; font-weight: 800;
  letter-spacing: 1px; color: #fff; background: linear-gradient(100deg, var(--accent-deep), var(--accent-2));
  border-radius: 999px; padding: 11px 24px; }
.featured-right { flex: 0 0 auto; display: flex; align-items: center; justify-content: center; }
.featured-right .ring {
  width: 88px; height: 88px; border-radius: 50%;
  background: conic-gradient(from 210deg, var(--accent-deep), var(--accent-2), var(--accent-deep));
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 800; box-shadow: 0 14px 30px rgba(22,104,220,.28);
}
.featured-right .ring em { font-style: normal; font-size: 15px; }
.featured-right .ring span { font-size: 24px; }

/* ===== 往期 ===== */
.report-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.report-card { background: var(--surface); border: 1px solid var(--line); border-radius: 18px;
  box-shadow: var(--shadow-sm); transition: box-shadow .16s, transform .16s, border-color .16s; }
.report-card:hover { box-shadow: var(--shadow); transform: translateY(-2px); border-color: var(--accent-2); }
.card-link { display: block; padding: 18px 18px 16px; text-decoration: none; }
.card-badge { display: inline-block; font-size: 10px; font-weight: 800; letter-spacing: 1px;
  color: #fff; background: linear-gradient(100deg, var(--accent), var(--accent-2)); border-radius: 999px; padding: 3px 11px; margin-bottom: 9px; }
.card-date { font-size: 11px; font-weight: 700; color: var(--ink-4); letter-spacing: 1px; }
.card-title { font-size: 14.5px; font-weight: 800; color: var(--ink); line-height: 1.5; margin-top: 6px; }
.card-meta { font-size: 11.5px; color: var(--ink-3); margin-top: 8px; }
.card-arrow { font-size: 11.5px; font-weight: 800; color: var(--accent); margin-top: 12px; }
.report-hidden { display: none; }
.more-wrap { text-align: center; margin-top: 20px; }
.more-btn { background: var(--surface); border: 1px solid var(--line-2); color: var(--accent-deep);
  cursor: pointer; font-family: inherit; font-size: 12px; font-weight: 800; letter-spacing: 1px;
  padding: 11px 24px; border-radius: 999px; transition: background .15s, border-color .15s; }
.more-btn:hover { background: #eef4fd; border-color: var(--accent-2); }

/* ===== 页脚 ===== */
.footer { border-top: 1px solid var(--rule); margin-top: 44px; padding: 30px 22px 44px;
  color: var(--ink-3); font-size: 11px; font-weight: 600; letter-spacing: 1.5px; text-align: center; }
.footer-brand { color: var(--ink); font-weight: 800; text-decoration: none; }
.footer .sig { margin-top: 8px; color: var(--ink-4); }

@media (max-width: 900px) {
  .fx-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .report-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .featured { flex-direction: column; }
  .featured-right { justify-content: flex-start; }
}
@media (max-width: 640px) {
  .topbar { padding: 10px 14px; }
  .brand .co { display: none; }
  .masthead { padding: 38px 16px 32px; }
  .kicker { font-size: 10px; letter-spacing: 3px; margin-bottom: 14px; }
  .masthead h1 { font-size: 27px; }
  .titlerule { margin-top: 18px; }
  .lede { font-size: 13.5px; line-height: 1.9; margin-top: 16px; }
  .masthead-meta { font-size: 11px; margin-top: 16px; }
  .searchstrip-in { padding: 11px 14px; }
  .wrap { padding: 0 14px 40px; }
  .sec { margin-top: 32px; }
  .sec-title { font-size: 17px; }
  .fx-grid { grid-template-columns: minmax(0, 1fr); gap: 12px; }
  .fx { padding: 18px 16px; border-radius: 16px; }
  .report-grid { grid-template-columns: minmax(0, 1fr); }
  .featured { padding: 20px 18px; border-radius: 18px; }
  .featured-title { font-size: 21px; }
  .featured-right .ring { width: 72px; height: 72px; }
  .footer { padding: 26px 14px 36px; }
}

/* ===== 深色模式（html.theme-dark） ===== */
html.theme-dark {
  --paper: #08182c;
  --surface: #102539;
  --ink: #e9f1fb;
  --ink-2: #b7c9df;
  --ink-3: #8ba2bd;
  --ink-4: #6f87a3;
  --rule: #1d3a5c;
  --rule-2: #2c4a70;
  --accent: #5aa5f2;
  --accent-2: #7cbbf7;
  --accent-deep: #9ccdf9;
  --shadow: 0 2px 6px rgba(0,0,0,.3), 0 16px 40px rgba(0,0,0,.38);
  --shadow-sm: 0 1px 3px rgba(0,0,0,.28), 0 8px 22px rgba(0,0,0,.3);
  color-scheme: dark;
}
html.theme-dark body { background: #08182c; }

/* 顶栏 / 报头 */
html.theme-dark .topbar { background: #0b1e35; border-bottom-color: var(--rule); }
html.theme-dark .brand { color: var(--ink); }
html.theme-dark .lang-switch { border-color: var(--rule-2); background: #17334f; }
html.theme-dark .lang-btn { color: var(--ink-3); }
html.theme-dark .lang-btn.active { background: var(--accent); color: #04121f; }
html.theme-dark .theme-btn { background: #17334f; color: var(--accent-deep); border: 1px solid #25507a; }
html.theme-dark .masthead { background: #0b1e35; border-bottom-color: var(--rule); }
html.theme-dark .masthead::before { opacity: .55; }

/* 卡片体系 */
html.theme-dark .fx,
html.theme-dark .report-card { border-color: var(--line); }
html.theme-dark .searchstrip { background: var(--surface); border-bottom-color: var(--rule); }
html.theme-dark .featured { border-color: var(--line); }
html.theme-dark .more-btn { border-color: var(--line-2); }
html.theme-dark .more-btn:hover { background: #17334f; }
html.theme-dark .footer { border-top-color: var(--rule); }
"""


def build_index_html(reports):
    """构建可视化索引页HTML（2026-10 重构 · 杂志风蓝调）。
    版面：报头(这是什么) -> 四项功能 -> 最新一期 -> 往期 -> 页脚。"""
    _build_v = datetime.now().strftime('%Y%m%d%H%M')  # cache-busting 版本号
    PAGELOAD_CSS = '<style>.searchstrip{position:relative;z-index:30;}</style>'
    ANALYTICS = _an.snippet()
    today_str = datetime.now().strftime('%Y年%m月%d日').replace('年0', '年').replace('月0', '月')
    year = datetime.now().year

    reports_sorted = list(reports)
    latest = reports_sorted[0] if reports_sorted else None

    # 项目库 / 租金地图的真实条目数（读不到就不显示，绝不崩）
    _proj_n, _muni_n = 0, 0
    try:
        with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'projects.json'), encoding='utf-8') as _f:
            _proj_n = len(json.load(_f).get('projects', []))
    except Exception:
        _proj_n = 0
    try:
        with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'rent', '2026-07.json'), encoding='utf-8') as _f:
            _muni_n = len(json.load(_f).get('municipalities', []))
    except Exception:
        _muni_n = 0

    REPORT_LIMIT = 6  # 首页「往期半月报」默认展示数量；超过则显示「查看更多」按钮
    total_reports = len(reports_sorted)

    # 往期卡片网格
    report_cards = ''
    for idx, r in enumerate(reports_sorted):
        folder = r['folder']
        date_str = r['date_str']
        day = r['sort_key'].day
        hm = '上旬号' if day <= 15 else '下旬号'
        ym = r['sort_key'].strftime('%Y年%m月').replace('年0', '年').replace('月0', '月')
        issue = f'{ym} {hm}'
        badge = '<span class="card-badge">最新</span>' if idx == 0 else ''
        hidden = ' report-hidden' if idx >= REPORT_LIMIT else ''
        report_cards += f'''
    <div class="report-card{' latest' if idx == 0 else ''}{hidden}">
      <a href="reports/{folder}/report.html?v={_build_v}" class="card-link">
        {badge}
        <div class="card-date">{date_str}</div>
        <div class="card-title">{issue} · 大诚不动产半月报</div>
        <div class="card-meta">{year}年 · <span class="lang-cn">东京市场动态</span><span class="lang-jp">東京市場動向</span></div>
        <div class="card-arrow">阅读全文 →</div>
      </a>
    </div>'''

    # 查看更多按钮（仅当往期超过限制时显示）
    if total_reports > REPORT_LIMIT:
        show_more = f'''
  <div class="more-wrap">
    <button class="more-btn" id="moreBtn" onclick="toggleMore()"><span class="lang-cn">查看更多往期半月报（共 {total_reports} 期）↓</span><span class="lang-jp">過去の半月報をもっと見る（全 {total_reports} 号）↓</span></button>
  </div>'''
    else:
        show_more = ''

    # 最新一期特写卡
    if latest:
        feat_date = latest['date_str']
        fday = latest['sort_key'].day
        fhm = '上旬号' if fday <= 15 else '下旬号'
        fym = latest['sort_key'].strftime('%Y年%m月').replace('年0', '年').replace('月0', '月')
        feat_issue = f'{fym} {fhm}'
        feat_hm_char = '上' if fday <= 15 else '下'
        feat_folder = latest['folder']
        featured_html = f'''
    <a href="reports/{feat_folder}/report.html?v={_build_v}" class="featured">
      <div class="featured-left" style="min-width:0">
        <span class="featured-tag"><span class="lang-cn">最新一期</span><span class="lang-jp">最新号</span></span>
        <h2 class="featured-title"><span class="lang-cn">大诚不动产半月报</span><span class="lang-jp">大誠不動産半月報</span></h2>
        <div class="featured-date">{feat_date} · {feat_issue}</div>
        <p class="featured-desc"><span class="lang-cn">政策动向 · 市场交易 · 开发动态 · 科技前沿 · 调查数据五大板块，精选本半月日本（以东京圈为主）不动产核心资讯，附利率解读与本期点评。</span><span class="lang-jp">政策動向・市場取引・開発動向・テクノロジー・調査データの5分野を網羅。この半月の日本（東京圏中心）不動産の核心情報を厳選し、金利解説と今期の総括付き。</span></p>
        <span class="featured-cta"><span class="lang-cn">立即阅读 →</span><span class="lang-jp">今すぐ読む →</span></span>
      </div>
      <div class="featured-right">
        <div class="ring"><span>{feat_hm_char}</span><em>旬</em></div>
      </div>
    </a>'''
    else:
        featured_html = ''

    # 四项功能入口的统计文案
    _fx_proj_stat = f'{_proj_n} <span class="lang-cn">个项目</span><span class="lang-jp">件</span>' if _proj_n else ''
    _fx_map_stat = '<span class="lang-cn">地图视图</span><span class="lang-jp">地図ビュー</span>'
    _fx_rent_stat = (f'{_muni_n} <span class="lang-cn">个市区町村</span><span class="lang-jp">市区町村</span>' if _muni_n
                     else '<span class="lang-cn">租金一图看懂</span><span class="lang-jp">賃料を1枚で</span>')

    script_js = '''
<script>
/* ===== 语言切换（中/日） ===== */
var I18N = {
  cn: {
    search_label: '全站搜索',
    footer_note: '内容仅供参考，投资需谨慎',
    more_view: function(n){ return '查看更多往期半月报（共 ' + n + ' 期）↓'; },
    more_collapse: '收起 ↑'
  },
  jp: {
    search_label: 'サイト内検索',
    footer_note: '内容は参考用です。投資は慎重に。',
    more_view: function(n){ return '過去の半月報をもっと見る（全 ' + n + ' 号）↓'; },
    more_collapse: '折りたたむ ↑'
  }
};
function i18nText(key, arg){
  var lang = (window.__lang || 'cn');
  var v = I18N[lang][key];
  if (typeof v === 'function') return v(arg);
  return v;
}
function applyI18n(lang){
  window.__lang = lang;
  var dict = I18N[lang];
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    var key = el.getAttribute('data-i18n');
    var v = dict[key];
    if (v && typeof v !== 'function'){ el.textContent = v; }
  });
  document.querySelectorAll('.lang-btn').forEach(function(b){
    b.classList.toggle('active', b.getAttribute('data-lang') === lang);
  });
  document.documentElement.classList.toggle('lang-jp', lang === 'jp');
  document.documentElement.classList.toggle('lang-cn', lang !== 'jp');
  document.documentElement.lang = (lang === 'jp') ? 'ja' : 'zh-CN';
}
function setLang(lang){
  applyI18n(lang);
  try { localStorage.setItem('taisei_lang', lang); } catch(e){}
}
/* ===== 深浅色主题（默认跟随系统，可手动覆盖并记忆） ===== */
function applyTheme(mode){
  var dark = (mode === 'dark');
  document.documentElement.classList.toggle('theme-dark', dark);
  var cn = document.querySelector('#themeBtn .lang-cn');
  var jp = document.querySelector('#themeBtn .lang-jp');
  if (cn) cn.textContent = dark ? '亮色' : '暗色';
  if (jp) jp.textContent = dark ? 'ライト' : 'ダーク';
  try { localStorage.setItem('taisei_theme', dark ? 'dark' : 'light'); } catch(e){}
}
function toggleTheme(){
  applyTheme(document.documentElement.classList.contains('theme-dark') ? 'light' : 'dark');
}
document.addEventListener('DOMContentLoaded', function(){
  var saved = null;
  try { saved = localStorage.getItem('taisei_lang'); } catch(e){}
  applyI18n(saved || 'cn');
  var theme = null;
  try { theme = localStorage.getItem('taisei_theme'); } catch(e){}
  if (!theme) {
    theme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }
  applyTheme(theme);
});
/* ===== 往期展开/收起 ===== */
function toggleMore(){
  var hidden = document.querySelectorAll('.report-hidden');
  var btn = document.getElementById('moreBtn');
  var total = document.querySelectorAll('.report-card').length;
  var currentlyHidden = hidden.length && hidden[0].style.display !== 'block';
  for (var i = 0; i < hidden.length; i++){ hidden[i].style.display = currentlyHidden ? 'block' : 'none'; }
  btn.innerHTML = '<span class="lang-cn">' + (currentlyHidden ? '收起 ↑' : i18nText('more_view', total)) + '</span>'
                + '<span class="lang-jp">' + (currentlyHidden ? '折りたたむ ↑' : i18nText('more_view', total)) + '</span>';
}
</script>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN" class="lang-cn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大誠有限会社 · 大诚不动产半月报 · 项目库 · 项目地图 · 租金地图</title>
<meta name="description" content="大誠有限会社维护的日本不动产情报站：每半月一期的东京市场简报（政策·市场·开发·科技·调查），另附可按企业·地区筛选的项目库、项目地图与租金地图。">
<style>{HOME_CSS}</style>
<link rel="stylesheet" href="/pagefind/pagefind-ui.css">
{PAGELOAD_CSS}
{ANALYTICS}
</head>
<body data-pagefind-body>

<header class="topbar">
  <a class="brand" href="index.html">
    <span class="mark">TAISEI</span>
    <span class="co">大誠有限会社 · <span class="lang-cn">大诚不动产情报</span><span class="lang-jp">大誠不動産情報</span></span>
  </a>
  <div class="topbar-right">
    <button type="button" class="theme-btn" id="themeBtn" onclick="toggleTheme()"><span class="lang-cn">暗色</span><span class="lang-jp">ダーク</span></button>
    <div class="lang-switch" id="langSwitch">
      <button type="button" class="lang-btn" data-lang="cn" onclick="setLang('cn')">中文</button>
      <button type="button" class="lang-btn" data-lang="jp" onclick="setLang('jp')">日本語</button>
    </div>
  </div>
</header>

<section class="masthead">
  <div class="masthead-in">
    <div class="kicker">Taisei Property Intelligence · 大誠有限会社</div>
    <h1><span class="lang-cn">大诚不动产半月报</span><span class="lang-jp">大誠不動産半月報</span><br><span class="thin"><span class="lang-cn">与不动产情报平台</span><span class="lang-jp">と不動産情報プラットフォーム</span></span></h1>
    <div class="titlerule"></div>
    <p class="lede"><span class="lang-cn">每半月一期，覆盖东京圈政策动向、市场交易、开发动态、科技前沿与调查数据；另附可按企业·地区筛选的项目库，以及项目地图与租金地图。一个页面看懂日本不动产正在发生什么。</span><span class="lang-jp">半月に1号、東京圏の政策動向・市場取引・開発動向・テクノロジー・調査データを網羅。企業・地区で絞り込めるプロジェクト一覧と、プロジェクト地図・賃貸相場マップも備えています。日本不動産のいまが、この1ページで分かります。</span></p>
    <div class="masthead-meta">
      <span><span class="lang-cn">更新于 {today_str}</span><span class="lang-jp">更新日 {today_str}</span></span>
      <span class="dot"></span>
      <span>{total_reports} <span class="lang-cn">期半月报</span><span class="lang-jp">号の半月報</span></span>
      <span class="dot"></span>
      <span>{_proj_n} <span class="lang-cn">个项目</span><span class="lang-jp">件のプロジェクト</span></span>
      <span class="dot"></span>
      <span><span class="lang-cn">东京</span><span class="lang-jp">東京</span></span>
    </div>
  </div>
</section>

<div class="searchstrip">
  <div class="searchstrip-in">
    <span class="searchstrip-label" data-i18n="search_label">全站搜索</span>
    <div class="pf-wrap" data-pagefind-ignore><div id="pfsearch"></div></div>
  </div>
</div>

<div class="wrap">

  <section class="sec">
    <div class="sec-head">
      <span class="sec-no"></span>
      <span class="sec-title"><span class="lang-cn">本站提供什么</span><span class="lang-jp">このサイトでできること</span></span>
      <span class="sec-en">What's inside</span>
    </div>
    <div class="fx-grid">
      <a class="fx" href="#latest">
        <span class="fx-no">01</span>
        <span class="fx-arrow">→</span>
        <span class="fx-title"><span class="lang-cn">不动产半月报</span><span class="lang-jp">不動産半月報</span><em class="fx-en">Half-month Report</em></span>
        <span class="fx-desc"><span class="lang-cn">半月一期东京市场简报：政策、交易、开发、科技、调查五大板块，附利率趋势与本期点评。</span><span class="lang-jp">東京市場の半月報。政策・取引・開発・技術・調査の5分野に、金利トレンドと今号の総括を添えて。</span></span>
        <span class="fx-stat">{total_reports} <span class="lang-cn">期</span><span class="lang-jp">号</span></span>
      </a>
      <a class="fx" href="projects.html">
        <span class="fx-no">02</span>
        <span class="fx-arrow">→</span>
        <span class="fx-title"><span class="lang-cn">项目库</span><span class="lang-jp">プロジェクト一覧</span><em class="fx-en">Project List</em></span>
        <span class="fx-desc"><span class="lang-cn">在开发·规划中的不动产项目一览，可按企业·地区·竣工时期筛选，附相关新闻时间轴。</span><span class="lang-jp">開発・計画中の不動産プロジェクトを網羅。企業・地区・竣工時期で絞り込み、関連ニュースのタイムラインも。</span></span>
        <span class="fx-stat">{_fx_proj_stat}</span>
      </a>
      <a class="fx" href="map.html">
        <span class="fx-no">03</span>
        <span class="fx-arrow">→</span>
        <span class="fx-title"><span class="lang-cn">项目地图</span><span class="lang-jp">プロジェクト地図</span><em class="fx-en">Project Map</em></span>
        <span class="fx-desc"><span class="lang-cn">把项目库落到地图上：项目位置、开发阶段与周边环境一图掌握。</span><span class="lang-jp">プロジェクト一覧を地図に展開。立地・開発段階・周辺環境を1枚で把握できます。</span></span>
        <span class="fx-stat">{_fx_map_stat}</span>
      </a>
      <a class="fx" href="rentmap.html">
        <span class="fx-no">04</span>
        <span class="fx-arrow">→</span>
        <span class="fx-title"><span class="lang-cn">租金地图</span><span class="lang-jp">賃貸相場マップ</span><em class="fx-en">Rent Map</em></span>
        <span class="fx-desc"><span class="lang-cn">一都三县租金一图看懂：以月额租金中位数统一比较，近6个月趋势可查。</span><span class="lang-jp">一都三県の賃料を1枚で。月額賃料の中央値で比較でき、直近6か月の推移も確認可能。</span></span>
        <span class="fx-stat">{_fx_rent_stat}</span>
      </a>
    </div>
  </section>

  <section class="sec" id="latest">
    <div class="sec-head">
      <span class="sec-no"></span>
      <span class="sec-title"><span class="lang-cn">最新一期</span><span class="lang-jp">最新号</span></span>
      <span class="sec-en">Latest issue</span>
    </div>
    {featured_html}
  </section>

  <section class="sec">
    <div class="sec-head">
      <span class="sec-no"></span>
      <span class="sec-title"><span class="lang-cn">往期半月报</span><span class="lang-jp">過去の半月報</span></span>
      <span class="sec-en">Archive</span>
    </div>
    <div class="report-grid">{report_cards}
    </div>{show_more}
  </section>

</div>

<footer class="footer">
  <p><a href="https://www.taisei-r.com/" target="_blank" rel="noopener" class="footer-brand">大誠有限会社</a> · <span class="lang-cn">大诚不动产半月报</span><span class="lang-jp">大誠不動産半月報</span></p>
  <p class="sig"><span data-i18n="footer_note">内容仅供参考，投资需谨慎</span></p>
  <p class="sig">Generated by Taisei AI · {today_str} · <span class="lang-cn">东京</span><span class="lang-jp">東京</span></p>
</footer>
<script src="/pagefind/pagefind-ui.js"></script>
<script>
  window.addEventListener("DOMContentLoaded", function () {{
    new PagefindUI({{ element: "#pfsearch", showSubResults: true }});
  }});
</script>
{script_js}
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

    print('[1/5] 构建本期报告HTML...')
    report_html = build_report_html()

    # 生成本期文件夹名（按发布当天）
    today = datetime.now()
    date_folder = today.strftime('%Y-%m-%d')
    report_path = f'reports/{date_folder}/report.html'
    issue_label = report_issue_label()
    date_range = get_half_month_range()

    print(f'      {issue_label}: {date_range}')

    # ── 检查仓库是否存在 ────────────────────────────────────────────
    print('[2/5] 检查/创建GitHub仓库...')
    resp = github_api('GET', f'/repos/{REPO_OWNER}/{REPO_NAME}')
    if resp.status_code == 404:
        print('      仓库不存在，创建中...')
        resp = github_api('POST', '/user/repos', {
            'name': REPO_NAME,
            'description': '大誠有限会社专用不动產半月報 -- 東京不动產市場最新動向',
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

    # ── 上传本期报告 ─────────────────────────────────────────────────
    print(f'[3/5] 上传本期报告 ({report_path})...')
    commit_msg = f'📋 Add half-month report: {date_range} ({issue_label})'
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
