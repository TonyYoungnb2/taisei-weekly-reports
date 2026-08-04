#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_map.py — 生成房地产情报平台地图页（Phase 0.5）。
纯静态：把 data/projects.json 内联进 HTML，本地 vendor Leaflet + GSI 国土地理院瓦片。
零后端、零 API key、国内/微信可开（不引 CDN 外链）。
用法: python build_map.py  -> 写入 map.html
"""
import io, os, json, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, 'data', 'projects.json')
NEWS_DIR = os.path.join(BASE, 'data', 'news')
OUT = os.path.join(BASE, 'map.html')


def load_news():
    news = []
    if not os.path.isdir(NEWS_DIR):
        return news
    for root, _, fnames in os.walk(NEWS_DIR):
        for fn in fnames:
            if not fn.endswith('.json'):
                continue
            try:
                d = json.load(io.open(os.path.join(root, fn), encoding='utf-8'))
            except Exception:
                continue
            if isinstance(d, list):
                news.extend(d)
            elif isinstance(d, dict) and 'news' in d:
                news.extend(d['news'])
    return news


def load_projects():
    return json.load(io.open(PROJ, encoding='utf-8'))


def build_html():
    data = load_projects()
    projects = [p for p in data.get('projects', []) if p.get('latitude') and p.get('longitude')]
    news = load_news()
    # 内联数据（避免跨文件加载 / 404）
    inline = json.dumps(projects, ensure_ascii=False)
    news_inline = json.dumps(news, ensure_ascii=False)
    lats = [p['latitude'] for p in projects]
    lngs = [p['longitude'] for p in projects]
    # 计算所有点的边界，用于载入时自适应框选（fitBounds）
    if lats:
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        center = [(min_lat + max_lat) / 2, (min_lng + max_lng) / 2]
        bounds = '[[%s, %s], [%s, %s]]' % (min_lat, min_lng, max_lat, max_lng)
    else:
        center = [36.5, 138.5]
        bounds = 'null'
    zoom = 5

    return '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>大誠 · 東京不動產情報地図</title>
<link rel="stylesheet" href="vendor/leaflet/leaflet.css">
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
  #top { position: sticky; top: 0; z-index: 1000; background: #0b3d91; color: #fff; padding: 12px 16px;
         display: flex; align-items: center; justify-content: space-between; }
  #top h1 { font-size: 17px; margin: 0; font-weight: 600; }
  #top .meta { font-size: 12px; opacity: .85; }
  #map { height: calc(100vh - 52px); width: 100%; }
  .leaflet-popup-content { font-size: 13px; line-height: 1.55; }
  .leaflet-popup-content b { font-size: 14px; color: #0b3d91; }
  .pop-news { margin-top: 6px; }
  .pop-news a { color: #e9533b; text-decoration: none; }
  .pop-news a:hover { text-decoration: underline; }
  /* 透明但醒目的环形标记：细描边 + 外发光，中心半透明可透出底图 */
  /* 简洁实心圆点：状态色填充 + 白边 + 淡投影，无彩色光晕（不刺眼） */
  .proj-pin {
    border-radius: 50%;
    border: 2px solid #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.28);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font: 700 11px/1 -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    box-sizing: border-box; transition: transform .12s ease;
  }
  .proj-pin.st-done { background:#1f9d55; }
  .proj-pin.st-dev  { background:#0b3d91; }
  .proj-pin.st-plan { background:#9aa5b8; }
  .proj-pin.has-news { background:#e9533b; }
  .proj-pin:hover { transform: scale(1.12); }
  /* 状态色：完工=绿 开发中=蓝 规划=灰（has-news 橙色优先） */


  
  .proj-halo { display: none; }
  #legend { background:rgba(255,255,255,.92); border:1px solid #e3e8f2; border-radius:8px; padding:8px 10px; font-size:11px; line-height:1.8; color:#1a2233; box-shadow:0 2px 8px rgba(0,0,0,.12); }
  #legend .row { display:flex; align-items:center; gap:6px; }
  #legend .dot { width:11px; height:11px; border-radius:50%; display:inline-block; border:2px solid; box-sizing:border-box; }
  #legend .d-done { border-color:#1f9d55; background:rgba(31,157,85,.2); }
  #legend .d-dev  { border-color:#0b3d91; background:rgba(11,61,145,.2); }
  #legend .d-plan { border-color:#8a96ac; background:rgba(138,150,172,.2); }
  #legend .d-news { border-color:#e9533b; background:rgba(233,83,59,.25); }
  .proj-label { background: rgba(11,61,145,.9); color:#fff; border:none; border-radius:4px;
    padding:1px 6px; font-size:11px; font-weight:600; white-space:nowrap; box-shadow:0 1px 3px rgba(0,0,0,.3); }
  .proj-label::before { display:none; }
  #zoomhint { position:absolute; right:10px; bottom:10px; z-index:1000; background:rgba(0,0,0,.55);
              color:#fff; font-size:11px; padding:5px 9px; border-radius:6px; }
  #empty { position: absolute; inset: 52px 0 0 0; display: flex; align-items: center; justify-content: center;
           color: #888; font-size: 14px; }
</style>
</head>
<body>
<div id="top">
  <h1>大誠 · 東京不動產情報地図</h1>
  <span class="meta">項目数: __COUNT__ ｜ 国土地理院地図</span>
</div>
<div id="map"></div>
<div id="empty" style="display:none">暂无已定位的项目</div>
<script src="vendor/leaflet/leaflet.js"></script>
<script>
var PROJECTS = __DATA__;
var NEWS = __NEWS__;
var map = L.map('map').setView([__CENTER__], __ZOOM__);
L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', {
  attribution: '© 国土地理院',
  maxZoom: 18
}).addTo(map);

// 载入时自适应框选所有项目（而不是死盯日本中心）
var BOUNDS = __BOUNDS__;
if (BOUNDS) { map.fitBounds(BOUNDS, { padding: [40, 40] }); }

if (!PROJECTS.length) {
  document.getElementById('empty').style.display = 'flex';
}

// 状态→颜色键：完工=done 开发中=dev 规划=plan
function statusKey(p){ var s=(p.status||''); if(s==='完工')return 'done'; if(s==='规划')return 'plan'; return 'dev'; }
// 半径随缩放放大：zoom 越大点越大（修复“放大后点变小”的观感）
function dotRadius(zoom, news) {
  var base = 5 + (zoom - 5) * 1.1;          // 5级≈5px，每升一级+1.1px
  if (base < 4) base = 4;
  return base + Math.min(news || 0, 12) * 0.9; // 新闻多→更大
}
function haloRadius(zoom, news) { return dotRadius(zoom, news) * 1.9; }

var markers = [];
PROJECTS.forEach(function(p) {
  var z0 = map.getZoom();
  var r = dotRadius(z0, p.news_count);
  // 渐变圆点：有新闻=暖橙，无新闻=品牌蓝；中心显示新闻数
  var dotLabel = (p.news_count && p.news_count > 0) ? String(p.news_count) : '';
  var dot = L.divIcon({ className: 'proj-pin st-' + statusKey(p) + (dotLabel ? ' has-news' : ''),
    html: '<div style="width:' + (r*2) + 'px;height:' + (r*2) + 'px;display:flex;align-items:center;justify-content:center;font:700 ' + Math.max(10, Math.round(r*0.95)) + 'px/1 sans-serif;color:#fff">' + dotLabel + '</div>',
    iconSize: [r*2, r*2], iconAnchor: [r, r] });
  var mk = L.marker([p.latitude, p.longitude], { icon: dot }).addTo(map);
  // 关联新闻：弹窗列出（至多3条）
  var news = (typeof NEWS !== 'undefined' ? NEWS : []).filter(function(n){ return n.project_id === p.id; })
    .sort(function(a,b){ return (b.publish_date||'').localeCompare(a.publish_date||''); });
  var newsHtml = news.length ? news.slice(0,3).map(function(n){
      var link = n.url ? ' <a href="' + n.url + '" target="_blank" rel="noopener">[' + (n.url_text || '链接') + ']</a>' : '';
      return '・' + n.title + link;
    }).join('<br>') : '(暂无关联新闻)';
  var html = '<b>' + p.name + '</b><br>' +
    '开发商: ' + (p.developer || '-') + '<br>' +
    '类型: ' + (p.category || '-') + ' ／ 状态: ' + (p.status || '-') + '<br>' +
    '地区: ' + [p.prefecture, p.city, p.district].filter(Boolean).join(' ') + '<br>' +
    '引用: ' + (p.source_name || '-') + (p.source_url ? ' <a href="' + p.source_url + '" target="_blank" rel="noopener">[リンク]</a>' : '') + '<br>' +
    '<div class="pop-news">相关新闻 (' + news.length + ' 篇):<br>' + newsHtml + '</div>';
  mk.bindPopup(html);
  // 悬停显示项目名标签
  var label = L.tooltip({
    permanent: false, direction: 'top', className: 'proj-label', opacity: 1
  }).setContent(p.name);
  mk.bindTooltip(label);
  markers.push({ dot: mk, news: p.news_count, r: r, p: p });
});

// 缩放时重算所有点大小，保持“放大→点变大”
function rescale() {
  var z = map.getZoom();
  markers.forEach(function(m) {
    var r = dotRadius(z, m.news);
    var lbl = (m.news && m.news > 0) ? String(m.news) : '';
    m.dot.setIcon(L.divIcon({ className: 'proj-pin st-' + statusKey(m.p) + (lbl ? ' has-news' : ''),
      html: '<div style="width:' + (r*2) + 'px;height:' + (r*2) + 'px;display:flex;align-items:center;justify-content:center;font:700 ' + Math.max(10, Math.round(r*0.95)) + 'px/1 sans-serif;color:#fff">' + lbl + '</div>',
      iconSize: [r*2, r*2], iconAnchor: [r, r] }));
  });
}
map.on('zoomend', rescale);
rescale();

// 缩放提示
var hint = L.control({ position: 'bottomright' });
hint.onAdd = function() { var d = L.DomUtil.create('div'); d.id = 'zoomhint';
  d.innerHTML = '🔍 滚轮放大 · 点越大'; return d; };
hint.addTo(map);
// 图例（状态色 + 新闻）
var legend = L.control({ position: 'bottomleft' });
legend.onAdd = function() {
  var d = L.DomUtil.create('div'); d.id = 'legend';
  d.innerHTML = '<div class="row"><span class="dot d-done"></span>完工</div>' +
    '<div class="row"><span class="dot d-dev"></span>开发中</div>' +
    '<div class="row"><span class="dot d-plan"></span>规划</div>' +
    '<div class="row"><span class="dot d-news"></span>有新闻</div>';
  return d;
};
legend.addTo(map);
</script>
</body>
</html>
'''.replace('__DATA__', inline).replace('__NEWS__', news_inline).replace('__CENTER__', '%s, %s' % (center[0], center[1])).replace('__ZOOM__', str(zoom)).replace('__COUNT__', str(len(projects))).replace('__BOUNDS__', bounds)


def main():
    html = build_html()
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('[OK] 地图页已生成: map.html (%d 个已定位项目)' % len(
        [p for p in load_projects().get('projects', []) if p.get('latitude')]))


if __name__ == '__main__':
    main()
