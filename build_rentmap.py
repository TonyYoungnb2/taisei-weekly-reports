#!/usr/bin/env python3
# -*- coding: utf-8 -*-
u"""
build_rentmap.py — 生成「一都三県 賃貸相場マップ」（方案B 独立页 rentmap.html）。
纯静态：data/rent/YYYY-MM.json 内联进 HTML，本地 vendor Leaflet + GSI 国土地理院瓦片。
零后端、零 CDN 外链、国内/微信可开。品牌蓝 #0b3d91。

データソース（誠実な明示）:
- メイン指標「月額賃料 中央値（全規模）」: 総務省 e-Stat 2023 住宅・土地統計調査 (Rent116)
  → 市区町村まで同一手法で比較可能な、全国統一の公的統計。
- 23区限定サブ指標「1K 中位月額 + 推移」: housingassist Tokyo Rent Index（掲載事例 19,000+ 件）
  既存 rentmap との連続性のため、23区カードにのみ副表示。
- 該市区 収益物件件数: data/projects.json の city フィールドから動的集計。
- 緯度経度: 国土地理院 住所検索 API (GSI, 無料・key不要) で事前取得。

用法: python build_rentmap.py  -> 写入 rentmap.html
"""
import io, os, json, glob, sys
import _analytics as _an
import _theme

BASE = os.path.dirname(os.path.abspath(__file__))
RENT_DIR = os.path.join(BASE, 'data', 'rent')
PROJ = os.path.join(BASE, 'data', 'projects.json')
OUT = os.path.join(BASE, 'rentmap.html')

BRAND = '#0b3d91'
AVG_RESIDUAL_SQMPRICE = 1080000   # 表面利回り概算用（23区平均中古㎡単価・目安）
SQMPER_TSUBO = 3.30578
TYPICAL_SIZE = 25

# 家賃帯（雨量警戒色風・5段階）— 色が主信号、円の大きさは補助。
# 境界は build 時にデータの「5分位」で動的決定（市区町村数に依存しない）。
TIERS = [
    {'id': 1, 'label_jp': '安値圏', 'label_cn': '低价圈', 'color': '#2f6fd6', 'text': '#ffffff'},
    {'id': 2, 'label_jp': 'やや安', 'label_cn': '偏低',   'color': '#2faa55', 'text': '#ffffff'},
    {'id': 3, 'label_jp': '中値圏', 'label_cn': '中等',   'color': '#f5c518', 'text': '#1a2233'},
    {'id': 4, 'label_jp': 'やや高', 'label_cn': '偏高',   'color': '#f08a24', 'text': '#ffffff'},
    {'id': 5, 'label_jp': '高値圏', 'label_cn': '高价圈', 'color': '#e23b3b', 'text': '#ffffff'},
]
PREF_NAME = {11: '埼玉県', 12: '千葉県', 13: '東京都', 14: '神奈川県'}
PREF_CN = {11: '埼玉县', 12: '千叶县', 13: '东京都', 14: '神奈川县'}
PREF_CENTER = {
    11: [35.86, 139.65], 12: [35.61, 140.10], 13: [35.69, 139.70], 14: [35.45, 139.64],
}
PREF_ZOOM = {11: 10, 12: 10, 13: 11, 14: 10}

def latest_rent_file():
    files = sorted(glob.glob(os.path.join(RENT_DIR, '*.json')))
    cand = [f for f in files if os.path.basename(f)[:7].replace('-', '').isdigit()]
    if not cand:
        return files[-1] if files else None
    return sorted(cand)[-1]


def build_html():
    rf = latest_rent_file()
    if not rf:
        raise SystemExit('[ERR] data/rent/*.json が見つかりません')
    rent = json.load(io.open(rf, encoding='utf-8'))
    meta = rent.get('meta', {})
    munis = rent.get('municipalities', [])
    # ランク付け（中央値降順）は build_rent_data 側で済みだが再計算して安全
    for i, m in enumerate(sorted(munis, key=lambda x: -x['rent_median']), 1):
        m['rank'] = i
    # 5分位ティアは build_rent_data 側で付与済

    data_inline = json.dumps({'meta': meta, 'municipalities': munis, 'tiers': TIERS,
                              'pref_name': PREF_NAME, 'pref_cn': PREF_CN,
                              'avg_sqm_price': AVG_RESIDUAL_SQMPRICE,
                              'sqm_per_tsubo': SQMPER_TSUBO,
                              'typical_size': TYPICAL_SIZE},
                             ensure_ascii=False)

    return '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>大誠 · 一都三県 賃貸相場マップ</title>
<link rel="stylesheet" href="vendor/leaflet/leaflet.css">
<style>__THEME_TOKENS__
  :root { --listw: 344px; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f4f6fb; color: #1a2233; }
  #top { position: sticky; top: 0; z-index: 1500; background: __BRAND__; color: #fff;
    padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
  #top h1 { font-size: 16px; margin: 0; font-weight: 600; line-height: 1.3; }
  #top .sub { font-size: 11px; opacity: .82; margin-top: 2px; font-weight: 400; }
  #top .t-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
  #top .home-btn { flex: 0 0 auto; background: rgba(255,255,255,.16); color: #fff; text-decoration: none;
    font-size: 12px; font-weight: 700; letter-spacing: 1px; padding: 5px 12px; border-radius: 8px; white-space: nowrap; }
  #top .home-btn:hover { background: rgba(255,255,255,.3); }
  #top .top-actions { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; }
  #top .list-toggle { background: rgba(255,255,255,.15); color: #fff; border: 0; border-radius: 8px;
    padding: 6px 13px; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; }
  #top .list-toggle.on { background: #fff; color: __BRAND__; }
  #top .list-toggle .cnt { opacity: .75; font-size: 11px; margin-left: 5px; }
  #pfilt { display: flex; gap: 6px; flex: 1 1 100%; flex-wrap: wrap; margin-top: 4px; }
  #pfilt button { background: rgba(255,255,255,.15); color: #fff; border: 0; border-radius: 14px;
    padding: 4px 12px; font-size: 12px; cursor: pointer; }
  #pfilt button.on { background: #fff; color: __BRAND__; font-weight: 700; }
  /* 地图与右侧列表并排：列表打开时地图宽度收缩 */
  #map { height: calc(100vh - var(--toph)); width: 100%; transition: width .22s ease; }
  body.list-open #map { width: calc(100% - var(--listw)); }
  #list { display: none; position: fixed; top: var(--toph); right: 0; bottom: 0; z-index: 2000;
    width: var(--listw); max-width: 92vw; background: #eef2f9;
    box-shadow: -6px 0 24px rgba(11,61,145,.18); overflow-y: auto; padding: 0 12px 24px; }
  #list.show { display: block; }
  #list .list-head { position: sticky; top: 0; z-index: 6; background: #eef2f9; margin: 0 -12px; padding: 11px 14px;
    border-bottom: 1px solid #dde4f0; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  #list .lh-t { font-size: 13px; font-weight: 800; color: #1a2233; }
  #list .lh-close { border: 0; background: #eef1f7; color: #46546e; width: 28px; height: 28px;
    border-radius: 8px; cursor: pointer; font-size: 16px; line-height: 1; flex: 0 0 auto; }
  #list .lh-close:hover { background: #e2e8f3; }
  /* 図例：雨量警戒色風 5段階 */
  #legend { position: absolute; left: 10px; bottom: 12px; z-index: 1200; background: rgba(255,255,255,.95);
    border: 1px solid #e3e8f2; border-radius: 10px; padding: 11px 13px; font-size: 11px; line-height: 1.7;
    color: #1a2233; box-shadow: 0 2px 10px rgba(0,0,0,.12); max-width: 250px; }
  #legend .lt { font-size: 11px; font-weight: 700; color: #46546e; margin-bottom: 7px; }
  #legend .tier { display: flex; align-items: center; gap: 8px; margin: 5px 0; }
  #legend .sw { flex: 0 0 16px; width: 16px; height: 16px; border-radius: 4px; box-shadow: 0 0 0 1px rgba(0,0,0,.08) inset; }
  #legend .tn { flex: 1 1 auto; font-weight: 600; }
  #legend .tr { color: #5a6a85; font-size: 10.5px; }
  #legend .note { margin-top: 8px; font-size: 10px; color: #8a96ac; line-height: 1.5; }
  .proj-label { background: rgba(255,255,255,.95); color: __BRAND__; border: 1px solid #cdd9f3;
    border-radius: 8px; padding: 2px 8px; font-size: 12px; font-weight: 600; box-shadow: 0 1px 4px rgba(11,61,145,.18); }
  .proj-label::before { display: none; }
  #panel { position: fixed; top: 0; right: 0; height: 100vh; width: 380px; max-width: 92vw; background: #fff;
    z-index: 2500; box-shadow: -6px 0 24px rgba(11,61,145,.18); transform: translateX(105%); transition: transform .22s ease;
    overflow-y: auto; padding: 0 0 24px; }
  #panel.show { transform: translateX(0); }
  #panel .ph { background: __BRAND__; color: #fff; padding: 16px 18px; position: sticky; top: 0; }
  #panel .ph .close { float: right; cursor: pointer; font-size: 22px; line-height: 1; border: 0; background: none; color: #fff; }
  #panel .ph .nm { font-size: 20px; font-weight: 700; }
  #panel .ph .rk { font-size: 12px; opacity: .85; margin-top: 3px; }
  #panel .body { padding: 16px 18px; }
  .rc-main { font-size: 30px; font-weight: 800; color: __BRAND__; letter-spacing: .5px; }
  .rc-main small { font-size: 13px; font-weight: 500; color: #5a6a85; margin-left: 6px; }
  .rc-units { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 14px 0; }
  .rc-units .u { background: #f4f6fb; border-radius: 10px; padding: 10px; }
  .rc-units .u .num { font-size: 16px; font-weight: 700; color: #1a2233; }
  .rc-units .u .lab { display: block; font-size: 10.5px; color: #8a96ac; margin-top: 3px; line-height: 1.4; }
  .rc-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 12px; }
  .rc-chips .chip { font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 600; border: 1px solid transparent; }
  .rc-chips .up { background: rgba(11,61,145,.10); color: __BRAND__; }
  .rc-chips .down { background: rgba(13,148,136,.12); color: #0d9488; }
  .rc-chips .band { box-shadow: 0 1px 3px rgba(0,0,0,.15); }
  .rc-sub { background: #f0f4fb; border-left: 3px solid __BRAND__; border-radius: 6px; padding: 8px 10px; margin: 8px 0; font-size: 11.5px; color: #46546e; }
  .rc-sub b { color: __BRAND__; }
  .rc-spark { background: #f4f6fb; border-radius: 10px; padding: 12px; margin: 8px 0; }
  .rc-spark .t { font-size: 11px; color: #5a6a85; margin-bottom: 6px; }
  .rc-yield { font-size: 14px; font-weight: 700; color: #1a2233; margin: 12px 0 6px; }
  .rc-yield small { font-size: 11px; color: #8a96ac; font-weight: 400; display: block; margin-top: 2px; }
  .rc-link { margin: 14px 0 8px; }
  .rc-link a { color: __BRAND__; text-decoration: none; font-weight: 600; font-size: 14px;
    display: inline-block; padding: 9px 14px; border: 1px solid #cdd9f3; border-radius: 10px; width: 100%; text-align: center; }
  .rc-link a.none { color: #9aa5b8; pointer-events: none; border-color: #e3e8f2; }
  .rc-src { font-size: 10.5px; color: #8a96ac; line-height: 1.6; border-top: 1px solid #eef1f7; padding-top: 10px; margin-top: 8px; }
  #list .lrow { background: #fff; border: 1px solid #e3e8f2; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px;
    display: flex; align-items: center; gap: 12px; cursor: pointer; }
  .lrow:active { background: #f0f4fb; }
  .lrank { flex: 0 0 34px; height: 34px; border-radius: 50%; background: #eef1f7; color: #46546e; font-weight: 700;
    display: flex; align-items: center; justify-content: center; font-size: 13px; }
  .lname { flex: 1 1 auto; font-size: 15px; font-weight: 600; }
  .ldot { flex: 0 0 14px; width: 14px; height: 14px; border-radius: 50%; box-shadow: 0 0 0 1px rgba(0,0,0,.08) inset; }
  .lval { font-size: 15px; font-weight: 800; color: __BRAND__; }
  .lval small { font-size: 11px; color: #8a96ac; font-weight: 500; margin-left: 4px; }
  @media (max-width: 640px) {
    #legend { max-width: 180px; font-size: 10px; padding: 8px 9px; }
    #top h1 { font-size: 14px; }
    #map { height: calc(100vh - 132px); }
    /* 手机：列表变成全屏覆盖层 */
    #list { width: 100%; max-width: 100%; top: 0; }
    body.list-open #map { width: 100%; }
    #list .list-head { padding-top: 15px; }
  }
  /* 桌面：详情面板让位给右侧列表，不互相遮挡。
     注意：面板靠 transform: translateX(105%) 收起，改了 right 之后必须把位移量补上
     列表宽度，否则面板只滑出 105% 自身宽度，会半遮住列表（表现为列表一片空白）。 */
  @media (min-width: 641px) {
    body.list-open #panel { right: var(--listw); }
    body.list-open #panel:not(.show) { transform: translateX(calc(100% + var(--listw))); }
  }
__RESKIN__
</style>
</head>
<body>
__NAV__<div id="map"></div>
<div id="legend">
  <div class="lt">家賃帯（月額中央値・5分位）</div>
  <div id="legendTiers"></div>
  <div class="note">色＝家賃帯（安→高）。円の大きさは目安。<br>出所: e-Stat 2023 住宅・土地統計調査（確定値）。</div>
</div>
<div id="list">
  <div class="list-head">
    <span class="lh-t">賃料ランキング（月額中央値）</span>
    <button class="lh-close" onclick="toggleList()" title="关闭列表">×</button>
  </div>
  <div id="listBody"></div>
</div>

<div id="panel" onclick="if(event.target===this)closePanel()">
  <div class="ph">
    <button class="close" onclick="closePanel()">×</button>
    <div class="nm" id="pNm"></div>
    <div class="rk" id="pRk"></div>
  </div>
  <div class="body" id="pBody"></div>
</div>

<script src="vendor/leaflet/leaflet.js"></script>
<script>
var DATA = __DATA__;
var MUNIS = DATA.municipalities;
var META = DATA.meta;
var TIERS = DATA.tiers;
var PREF_NAME = DATA.pref_name, PREF_CN = DATA.pref_cn;
var BRAND = '__BRAND__';
var map = null, markers = {}, byCode = {};
var state = { pref: 0 };
MUNIS.forEach(function(m){ byCode[m.code] = m; });

function tierById(id){ return TIERS.filter(function(t){ return t.id === id; })[0]; }
function colorForTier(tid){ var t = tierById(tid) || TIERS[TIERS.length-1]; return t.color; }
function fmt(n){ return n.toLocaleString('ja-JP'); }
function nameCn(m){ return m.name.replace(/区$|市$|町$|村$/, '') || m.name; }

function radiusFor(v){
  var vals = MUNIS.map(function(m){ return m.rent_median; });
  var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
  var t = (v - mn) / (mx - mn || 1);
  return 8 + t * 16; // 8..24 px（補助）
}
function visMuni(m){ return state.pref === 0 || m.pref === state.pref; }

function sparkline(){
  var tr = (META.trend_23w || []).map(function(p){ return p.v; });
  if (tr.length < 2) return '';
  var W = 320, H = 64, pad = 6;
  var mn = Math.min.apply(null, tr), mx = Math.max.apply(null, tr);
  var span = (mx - mn) || 1;
  var pts = tr.map(function(v, i){
    var x = pad + i * (W - pad*2) / (tr.length - 1);
    var y = H - pad - (v - mn) / span * (H - pad*2);
    return [x, y];
  });
  var d = pts.map(function(p, i){ return (i?'L':'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' ');
  var last = pts[pts.length - 1];
  return '<svg width="100%" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" style="display:block">'+
    '<path d="'+d+'" fill="none" stroke="'+BRAND+'" stroke-width="2.5" stroke-linejoin="round"/>'+
    '<circle cx="'+last[0].toFixed(1)+'" cy="'+last[1].toFixed(1)+'" r="3.5" fill="'+BRAND+'"/></svg>';
}
function cardHtml(m){
  var tier = tierById(m.tier);
  var median = m.rent_median;
  var perSqm = Math.round(median / DATA.typical_size);
  var perTsubo = Math.round(perSqm * DATA.sqm_per_tsubo);
  var annual = median * 12;
  var price = DATA.typical_size * DATA.avg_sqm_price;
  var yieldPct = (annual / price * 100);
  var mom = (m.mom_pct >= 0 ? '+' : '') + (m.mom_pct||0).toFixed(1) + '%';
  var yoy = (m.yoy_pct >= 0 ? '+' : '') + (m.yoy_pct||0).toFixed(1) + '%';
  var bandChip = tier
    ? '<span class="chip band" style="background:'+tier.color+';color:'+tier.text+';border-color:'+tier.color+'">'+tier.label_jp+' / '+tier.label_cn+'</span>'
    : '';
  var link = m.proj_count > 0
    ? '<a href="projects.html?city='+encodeURIComponent(m.name)+'">該市区の収益物件 '+m.proj_count+'件を見る ›</a>'
    : '<a class="none">該市区の収益物件はまだ登録なし</a>';
  var sub = '';
  if (m.is_ward) {
    sub = '<div class="rc-sub">🏙 <b>23区 1K 専有面積 中位月額</b>：¥'+(m.rent_1k/10000).toFixed(1)+'万<br>'+
      '前月比 '+mom+' / 前年比 '+yoy+'（推定）・出所: housingassist</div>';
  }
  return '' +
    '<div class="rc-main">¥' + (median/10000).toFixed(1) + '万<small>月額賃料 中央値（全規模）</small></div>' +
    '<div class="rc-units">' +
      '<div class="u"><span class="num">¥' + fmt(perSqm) + '</span><span class="lab">¥/㎡（推算: 中央値÷25㎡）</span></div>' +
      '<div class="u"><span class="num">¥' + fmt(perTsubo) + '</span><span class="lab">坪単価（推算）</span></div>' +
    '</div>' +
    '<div class="rc-chips">' + bandChip + '</div>' +
    sub +
    (m.is_ward ? '<div class="rc-spark"><div class="t">' + nameCn(m) + ' 1K 月额推移(自集計)</div>' + sparkline(m.trend, m.name) + '</div>' : '') +
    '<div class="rc-yield">表面利回り(概算): 約 ' + yieldPct.toFixed(1) + '%' +
      '<small>年賃料 ÷ 23区平均中古㎡単価(約108万円) を目安に概算（25㎡想定）</small></div>' +
    '<div class="rc-link">' + link + '</div>' +
    '<div class="rc-src">メイン出所: ' + (META.source || 'e-Stat') + '（'+ (META.metric||'') +'）<br>' +
      (META.note || '') + '<br>' +
      (m.is_ward ? '<span style="color:#2f6fd6">●</span> '+nameCn(m)+' 1K 趋势为每月自集計快照(2026-07 起), 点数累积中。' + '<br>' : '') +
      '※ 表面利回りは概算。23区 1K/推移は housingassist 参照。</div>';
}
function openPanel(m){
  document.getElementById('pNm').textContent = m.name + '（' + (PREF_NAME[m.pref]||'') + '）';
  document.getElementById('pRk').textContent = '家賃ランク ' + m.rank + ' / ' + MUNIS.length + ' 市区町村';
  document.getElementById('pBody').innerHTML = cardHtml(m);
  document.getElementById('panel').classList.add('show');
}
/* 从右侧列表点选：地图飞到该市区町村 + 高亮该圆点 */
var hiMarker = null, focusSeq = 0;
function focusMuni(m){
  if (!map || !m || !m.lat || !m.lng) return;
  var z = Math.max(map.getZoom() || 9, 12);
  var seq = ++focusSeq;
  if (map.flyTo) map.flyTo([m.lat, m.lng], z, { duration: .7 });
  else map.setView([m.lat, m.lng], z);
  /* 兜底：标签页在后台时浏览器会暂停 rAF，flyTo 动画不会推进 →
     900ms 后若还没到位就直接 setView，保证「点了就一定会跳过去」 */
  setTimeout(function(){
    if (seq !== focusSeq || !map) return;
    var c = map.getCenter();
    if (Math.abs(c.lat - m.lat) > 0.0006 || Math.abs(c.lng - m.lng) > 0.0006) {
      /* animate:false —— 动画路径同样依赖 rAF，兜底必须是同步跳转 */
      map.setView([m.lat, m.lng], z, { animate: false });
    }
  }, 900);
  var mk = markers[m.code];
  if (mk) {
    if (hiMarker && hiMarker !== mk) hiMarker.setStyle({ weight: 1.5, color: '#ffffff' });
    mk.setStyle({ weight: 3.5, color: '#0b3d91' });
    if (mk.bringToFront) mk.bringToFront();
    mk.openTooltip();
    hiMarker = mk;
  }
}
function openFromList(code){
  var m = byCode[code];
  if (!m) return;
  focusMuni(m);
  openPanel(m);
  /* 手机上列表是全屏覆盖层，点完先收起，否则看不到地图已经跳过去 */
  if (window.innerWidth <= 640) toggleList(false);
}
function closePanel(){ document.getElementById('panel').classList.remove('show'); }

function buildLegend(){
  var tb = META.tier_bounds || [];
  var html = '';
  TIERS.forEach(function(t){
    var b = tb.filter(function(x){ return x.tier === t.id; })[0];
    var rng = b ? ('¥'+(b.lo/10000).toFixed(1)+'〜'+(b.hi/10000).toFixed(1)+'万') : '';
    html += '<div class="tier"><span class="sw" style="background:'+t.color+'"></span>'+
      '<span class="tn">'+t.label_jp+' / '+t.label_cn+'</span><span class="tr">'+rng+'</span></div>';
  });
  document.getElementById('legendTiers').innerHTML = html;
}
function renderMap(){
  if (map) { map.remove(); map = null; }
  var center = state.pref ? PREF_CENTER[state.pref] : [35.62, 139.78];
  var zoom = state.pref ? PREF_ZOOM[state.pref] : 9;
  map = L.map('map').setView(center, zoom);
  L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png',
    { attribution: '© 国土地理院', maxZoom: 18 }).addTo(map);
  markers = {};
  hiMarker = null;
  MUNIS.forEach(function(m){
    if (!visMuni(m)) return;
    if (!m.lat || !m.lng) return;
    var r = radiusFor(m.rent_median);
    var mk = L.circleMarker([m.lat, m.lng], {
      radius: r, color: '#ffffff', weight: 1.5, fillColor: colorForTier(m.tier), fillOpacity: 0.9
    }).addTo(map);
    mk.bindTooltip(m.name + ' ¥' + (m.rent_median/10000).toFixed(1) + '万 ・ ' + (tierById(m.tier)||{}).label_jp,
      { direction: 'top', opacity: 1, className: 'proj-label' });
    mk.on('click', function(){ openPanel(m); });
    markers[m.code] = mk;
  });
}
function renderList(){
  var body = document.getElementById('listBody');
  var rows = MUNIS.filter(visMuni).slice().sort(function(a,b){ return b.rent_median - a.rent_median; }).map(function(m){
    /* 注意：code 是字符串（如 '11000'），必须用单引号包 key —— 用 JSON.stringify 会生成
       双引号，把 onclick 属性提前截断，导致后面整批行的 HTML 被浏览器丢弃、点击也失效 */
    var key = String(m.code).replace(/['"<>]/g, '');
    return '<div class="lrow" data-c="' + key + '" onclick="openFromList(this.dataset.c)">' +
      '<div class="lrank">' + m.rank + '</div>' +
      '<span class="ldot" style="background:' + colorForTier(m.tier) + '"></span>' +
      '<div class="lname">' + m.name + '<br><span style="font-size:11px;color:#8a96ac;font-weight:400">' + (PREF_NAME[m.pref]||'') + '</span></div>' +
      '<div class="lval">¥' + (m.rent_median/10000).toFixed(1) + '万<small>中央値</small></div>' +
    '</div>';
  }).join('');
  body.innerHTML = rows;
  var cnt = document.getElementById('listCnt');
  if (cnt) cnt.textContent = '(' + MUNIS.filter(visMuni).length + ')';
}
/* 右侧列表开关：地图与列表并排显示，列表可随时收起 */
function toggleList(force){
  var box = document.getElementById('list');
  var open = (typeof force === 'boolean') ? force : !box.classList.contains('show');
  box.classList.toggle('show', open);
  document.body.classList.toggle('list-open', open);
  var btn = document.getElementById('btnList');
  if (btn) btn.classList.toggle('on', open);
  if (open) renderList();
  if (map) setTimeout(function(){ map.invalidateSize(); }, 260);
}
function syncTopH(){
  var t = document.querySelector('.nav');
  if (t) document.documentElement.style.setProperty('--toph', t.offsetHeight + 'px');
}
function setPref(p){
  state.pref = p;
  var btns = document.querySelectorAll('#pfilt button');
  btns.forEach(function(b){ b.classList.toggle('on', +b.getAttribute('data-p') === p); });
  renderMap();
  renderList();
}
buildLegend();
syncTopH();
renderMap();
renderList();
/* 桌面默认展开右侧列表（手机默认收起，避免盖住地图） */
toggleList(window.innerWidth > 720);
window.addEventListener('resize', function(){ syncTopH(); });
</script>
__NAV_JS__
<script>__ANALYTICS__</script>
</body>
</html>
'''.replace('__BRAND__', BRAND) \
   .replace('__DATA__', data_inline) \
   .replace('__ANALYTICS__', _an.snippet()).replace('__THEME_TOKENS__', _theme.TOKENS).replace('__RESKIN__', _theme.RESKIN_RENTMAP).replace('__NAV_JS__', _theme.NAV_JS).replace('__NAV__', _theme.nav_html('大誠 · 一都三県 賃貸相場マップ', 'メイン指標: e-Stat 住宅・土地統計調査 2023（月額賃料 中央値・全規模）', '<button id="btnList" class="pill-btn on" onclick="toggleList()">一覧<span class="cnt" id="listCnt"></span></button>', '<div class="nav-row filters"><div id="pfilt">''<button data-p="0" class="on" onclick="setPref(0)">全国 (194市区)</button>''<button data-p="13" onclick="setPref(13)">東京都</button>''<button data-p="14" onclick="setPref(14)">神奈川</button>''<button data-p="11" onclick="setPref(11)">埼玉</button>''<button data-p="12" onclick="setPref(12)">千葉</button>''</div></div>'))


def main():
    html = build_html()
    io.open(OUT, 'w', encoding='utf-8').write(html)
    n = len(json.load(io.open(latest_rent_file(), encoding='utf-8')).get('municipalities', []))
    print('[OK] 賃貸相場マップ生成: rentmap.html (%d 市区町村)' % n)


if __name__ == '__main__':
    main()
