#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_rentmap.py — 生成「東京23区 賃貸相場マップ」（方案B 独立页 rentmap.html）。
纯静态：data/rent/YYYY-MM.json 内联进 HTML，本地 vendor Leaflet + GSI 国土地理院瓦片。
零后端、零 CDN 外链、国内/微信可开。品牌蓝 #0b3d91。

数据来源（诚实标注）：
- 各区 1K 中位月額：housingassist Tokyo Rent Index（SUUMO/Homes/at Home 掲載事例 19,000+ 件, 2026-06-26 公表）
- 東京23区 分譲マンション募集賃料（¥/㎡ 平均）：東京カンテイ 月次
- 表面利回り：23区平均中古㎡単価(約108万円)を目安に概算
- 前月比/前年比：23区全体の市場趨勢(東京カンテイ/SAVILLS) を目安に各区へ按分 → 推定値
- 該区収益物件件数：data/projects.json の city フィールドから動的集計

用法: python build_rentmap.py  -> 写入 rentmap.html
"""
import io, os, json, glob, sys
import _analytics as _an

BASE = os.path.dirname(os.path.abspath(__file__))
RENT_DIR = os.path.join(BASE, 'data', 'rent')
PROJ = os.path.join(BASE, 'data', 'projects.json')
OUT = os.path.join(BASE, 'rentmap.html')

BRAND = '#0b3d91'
# 表面利回り概算用：23区平均 中古㎡単価（目安・概算）
AVG_RESIDUAL_SQMPRICE = 1080000
SQMPER_TSUBO = 3.30578
TYPICAL_SIZE = 25


def latest_rent_file():
    files = sorted(glob.glob(os.path.join(RENT_DIR, '*.json')))
    # YYYY-MM.json 命名；最新を採用
    cand = [f for f in files if os.path.basename(f)[:7].replace('-', '').isdigit()]
    if not cand:
        return files[-1] if files else None
    return sorted(cand)[-1]


def ward_project_counts():
    try:
        d = json.load(io.open(PROJ, encoding='utf-8'))
    except Exception:
        return {}
    cnt = {}
    for p in d.get('projects', []):
        c = p.get('city') or ''
        if c:
            cnt[c] = cnt.get(c, 0) + 1
    return cnt


def build_html():
    rf = latest_rent_file()
    if not rf:
        raise SystemExit('[ERR] data/rent/*.json が見つかりません')
    rent = json.load(io.open(rf, encoding='utf-8'))
    meta = rent.get('meta', {})
    wards = rent.get('wards', [])
    # ランク付け（月額降順）
    ranks = sorted(wards, key=lambda w: w['rent_1k'], reverse=True)
    for i, w in enumerate(ranks):
        w['rank'] = i + 1
    wcount = ward_project_counts()
    for w in wards:
        w['proj_count'] = wcount.get(w['ward_ja'], 0)

    data_inline = json.dumps({'meta': meta, 'wards': wards,
                              'avg_sqm_price': AVG_RESIDUAL_SQMPRICE,
                              'sqm_per_tsubo': SQMPER_TSUBO,
                              'typical_size': TYPICAL_SIZE},
                             ensure_ascii=False)

    rents = [w['rent_1k'] for w in wards]
    rmin, rmax = min(rents), max(rents)

    return '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>大誠 · 東京23区 賃貸相場マップ</title>
<link rel="stylesheet" href="vendor/leaflet/leaflet.css">
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f4f6fb; color: #1a2233; }
  #top { position: sticky; top: 0; z-index: 1500; background: __BRAND__; color: #fff;
    padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  #top h1 { font-size: 16px; margin: 0; font-weight: 600; line-height: 1.3; }
  #top .sub { font-size: 11px; opacity: .82; margin-top: 2px; font-weight: 400; }
  .view-switch { display: flex; gap: 6px; flex: 0 0 auto; }
  .view-switch button { background: rgba(255,255,255,.15); color: #fff; border: 0; border-radius: 8px;
    padding: 6px 12px; font-size: 13px; cursor: pointer; }
  .view-switch button.on { background: #fff; color: __BRAND__; font-weight: 600; }
  #map { height: calc(100vh - 58px); width: 100%; }
  /* 图例 */
  #legend { position: absolute; left: 10px; bottom: 12px; z-index: 1200; background: rgba(255,255,255,.94);
    border: 1px solid #e3e8f2; border-radius: 10px; padding: 10px 12px; font-size: 11px; line-height: 1.7;
    color: #1a2233; box-shadow: 0 2px 10px rgba(0,0,0,.12); max-width: 220px; }
  #legend .bar { height: 10px; border-radius: 5px; margin: 6px 0 3px;
    background: linear-gradient(90deg, #dbe7fb, #9bc0f0, #4f86d6, __BRAND__); }
  #legend .row { display: flex; justify-content: space-between; }
  #legend .cir { display: flex; align-items: center; gap: 6px; margin-top: 6px; }
  #legend .cir i { display: inline-block; border-radius: 50%; background: rgba(11,61,145,.15); border: 1.5px solid __BRAND__; }
  /* 地图气泡 tooltip（区名 + 月額） */
  .proj-label { background: rgba(255,255,255,.95); color: __BRAND__; border: 1px solid #cdd9f3;
    border-radius: 8px; padding: 2px 8px; font-size: 12px; font-weight: 600; box-shadow: 0 1px 4px rgba(11,61,145,.18); }
  .proj-label::before { display: none; }
  /* 侧栏卡片 */
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
  .rc-chips .chip { font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
  .rc-chips .up { background: rgba(11,61,145,.10); color: __BRAND__; }
  .rc-chips .down { background: rgba(13,148,136,.12); color: #0d9488; }
  .rc-spark { background: #f4f6fb; border-radius: 10px; padding: 12px; margin: 8px 0; }
  .rc-spark .t { font-size: 11px; color: #5a6a85; margin-bottom: 6px; }
  .rc-yield { font-size: 14px; font-weight: 700; color: #1a2233; margin: 12px 0 6px; }
  .rc-yield small { font-size: 11px; color: #8a96ac; font-weight: 400; display: block; margin-top: 2px; }
  .rc-link { margin: 14px 0 8px; }
  .rc-link a { color: __BRAND__; text-decoration: none; font-weight: 600; font-size: 14px;
    display: inline-block; padding: 9px 14px; border: 1px solid #cdd9f3; border-radius: 10px; width: 100%; text-align: center; }
  .rc-link a.none { color: #9aa5b8; pointer-events: none; border-color: #e3e8f2; }
  .rc-src { font-size: 10.5px; color: #8a96ac; line-height: 1.6; border-top: 1px solid #eef1f7; padding-top: 10px; margin-top: 8px; }
  /* 一覧 */
  #list { display: none; padding: 12px; }
  .lrow { background: #fff; border: 1px solid #e3e8f2; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px;
    display: flex; align-items: center; gap: 12px; cursor: pointer; }
  .lrow:active { background: #f0f4fb; }
  .lrank { flex: 0 0 34px; height: 34px; border-radius: 50%; background: #eef1f7; color: #46546e; font-weight: 700;
    display: flex; align-items: center; justify-content: center; font-size: 13px; }
  .lname { flex: 1 1 auto; font-size: 15px; font-weight: 600; }
  .lval { font-size: 15px; font-weight: 800; color: __BRAND__; }
  .lval small { font-size: 11px; color: #8a96ac; font-weight: 500; margin-left: 4px; }
  @media (max-width: 640px) {
    #legend { max-width: 180px; font-size: 10px; padding: 8px 9px; }
    #top h1 { font-size: 14px; }
  }
</style>
</head>
<body>
<div id="top">
  <div>
    <h1>大誠 · 東京23区 賃貸相場マップ</h1>
    <div class="sub">データ: housingassist (掲載事例 19,000+ 件) ／ 東京カンテイ 分譲賃料</div>
  </div>
  <div class="view-switch">
    <button id="btnMap" class="on" onclick="setView('map')">地図</button>
    <button id="btnList" onclick="setView('list')">一覧</button>
  </div>
</div>
<div id="map"></div>
<div id="legend">
  <div>円の大きさ・色 = 1K 中位月額</div>
  <div class="bar"></div>
  <div class="row"><span>安 __RMIN_K__万</span><span>高 __RMAX_K__万</span></div>
  <div class="cir"><i style="width:10px;height:10px"></i><i style="width:16px;height:16px"></i> 家賃が高いほど大きい</div>
</div>
<div id="list"><div id="listBody"></div></div>

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
var WARDS = DATA.wards;
var META = DATA.meta;
var BRAND = '__BRAND__';
var rmin = Math.min.apply(null, WARDS.map(function(w){ return w.rent_1k; }));
var rmax = Math.max.apply(null, WARDS.map(function(w){ return w.rent_1k; }));
var map = null, markers = {};
var state = { view: 'map' };

function fmt(n){ return n.toLocaleString('ja-JP'); }
// 円→色（低:薄い青 → 高:ブランド青）
function colorFor(v){
  var t = (v - rmin) / (rmax - rmin || 1); // 0..1
  // 薄 (#dbe7fb) → 濃 (#0b3d91)
  var stops = [[219,231,251],[155,192,240],[79,134,214],[11,61,145]];
  var seg = t * (stops.length - 1);
  var i = Math.floor(seg), f = seg - i;
  if (i >= stops.length - 1) i = stops.length - 2, f = 1;
  var a = stops[i], b = stops[i+1];
  var c = a.map(function(x,k){ return Math.round(x + (b[k]-x)*f); });
  return 'rgb('+c[0]+','+c[1]+','+c[2]+')';
}
function radiusFor(v){
  var t = (v - rmin) / (rmax - rmin || 1);
  return 10 + t * 16; // 10..26 px
}
// 火花线（23区全体 平均推移）
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
function cardHtml(w){
  var perSqm = Math.round(w.rent_1k / DATA.typical_size);
  var perTsubo = Math.round(perSqm * DATA.sqm_per_tsubo);
  var annual = w.rent_1k * 12;
  var price = DATA.typical_size * DATA.avg_sqm_price;
  var yieldPct = (annual / price * 100);
  var mom = (w.mom_pct >= 0 ? '+' : '') + w.mom_pct.toFixed(1) + '%';
  var yoy = (w.yoy_pct >= 0 ? '+' : '') + w.yoy_pct.toFixed(1) + '%';
  var link;
  if (w.proj_count > 0) {
    link = '<a href="projects.html?city=' + encodeURIComponent(w.ward_ja) + '">該区の収益物件 ' + w.proj_count + '件を見る ›</a>';
  } else {
    link = '<a class="none">該区の収益物件はまだ登録なし</a>';
  }
  return '' +
    '<div class="rc-main">¥' + (w.rent_1k/10000).toFixed(1) + '万<small>1K 中位月額</small></div>' +
    '<div class="rc-units">' +
      '<div class="u"><span class="num">¥' + fmt(perSqm) + '</span><span class="lab">¥/㎡（推算: 1K÷25㎡）</span></div>' +
      '<div class="u"><span class="num">¥' + fmt(perTsubo) + '</span><span class="lab">坪単価（推算）</span></div>' +
    '</div>' +
    '<div class="rc-chips">' +
      '<span class="chip up">前月比 ' + mom + ' (推定)</span>' +
      '<span class="chip up">前年比 ' + yoy + ' (推定)</span>' +
    '</div>' +
    '<div class="rc-spark"><div class="t">東京23区 平均賃料推移（参考）</div>' + sparkline() + '</div>' +
    '<div class="rc-yield">表面利回り(概算): 約 ' + yieldPct.toFixed(1) + '%' +
      '<small>年賃料 ÷ 23区平均中古㎡単価(約108万円) を目安に概算（25㎡想定）</small></div>' +
    '<div class="rc-link">' + link + '</div>' +
    '<div class="rc-src">出所: ' + (META.source || 'housingassist') + '<br>' +
      '東京カンテイ 分譲賃料 23区平均 ' + (META.official_check || '') + '<br>' +
      '※ 前月比/前年比は市場趨勢からの推定値。表面利回りは概算。</div>';
}
function openPanel(w){
  document.getElementById('pNm').textContent = w.ward_cn + '（' + w.ward_ja + '）';
  document.getElementById('pRk').textContent = '家賃ランク ' + w.rank + ' / ' + WARDS.length + ' 区';
  document.getElementById('pBody').innerHTML = cardHtml(w);
  document.getElementById('panel').classList.add('show');
}
function closePanel(){ document.getElementById('panel').classList.remove('show'); }

function renderMap(){
  map = L.map('map').setView([35.6895, 139.7595], 11);
  L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png',
    { attribution: '© 国土地理院', maxZoom: 18 }).addTo(map);
  WARDS.forEach(function(w){
    var r = radiusFor(w.rent_1k);
    var mk = L.circleMarker([w.lat, w.lng], {
      radius: r, color: BRAND, weight: 2, fillColor: colorFor(w.rent_1k), fillOpacity: 0.55
    }).addTo(map);
    mk.bindTooltip(w.ward_cn + ' ¥' + (w.rent_1k/10000).toFixed(1) + '万',
      { direction: 'top', opacity: 1, className: 'proj-label' });
    mk.on('click', function(){ openPanel(w); });
    markers[w.ward_ja] = mk;
  });
}
function renderList(){
  var body = document.getElementById('listBody');
  var rows = WARDS.slice().sort(function(a,b){ return b.rent_1k - a.rent_1k; }).map(function(w){
    return '<div class="lrow" onclick="openPanel(WARDS.find(function(x){return x.ward_ja===' +
      JSON.stringify(w.ward_ja) + ';}))">' +
      '<div class="lrank">' + w.rank + '</div>' +
      '<div class="lname">' + w.ward_cn + '<br><span style="font-size:11px;color:#8a96ac;font-weight:400">' + w.ward_ja + '</span></div>' +
      '<div class="lval">¥' + (w.rent_1k/10000).toFixed(1) + '万<small>1K</small></div>' +
    '</div>';
  }).join('');
  body.innerHTML = rows;
}
function setView(v){
  state.view = v;
  document.getElementById('btnMap').classList.toggle('on', v==='map');
  document.getElementById('btnList').classList.toggle('on', v==='list');
  document.getElementById('map').style.display = v==='map' ? 'block' : 'none';
  document.getElementById('list').style.display = v==='list' ? 'block' : 'none';
  if (v==='map' && map) setTimeout(function(){ map.invalidateSize(); }, 50);
}
renderMap();
renderList();
</script>
<script>__ANALYTICS__</script>
</body>
</html>
'''.replace('__BRAND__', BRAND) \
   .replace('__DATA__', data_inline) \
   .replace('__RMIN_K__', '%.1f' % (rmin/10000)) \
   .replace('__RMAX_K__', '%.1f' % (rmax/10000)) \
   .replace('__ANALYTICS__', _an.snippet())


def main():
    html = build_html()
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('[OK] 賃貸相場マップ生成: rentmap.html (%d 区)' % len(json.load(io.open(latest_rent_file(), encoding='utf-8')).get('wards', [])))


if __name__ == '__main__':
    main()
