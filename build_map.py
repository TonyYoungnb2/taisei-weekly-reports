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
OUT = os.path.join(BASE, 'map.html')


def load_projects():
    return json.load(io.open(PROJ, encoding='utf-8'))


def build_html():
    data = load_projects()
    projects = [p for p in data.get('projects', []) if p.get('latitude') and p.get('longitude')]
    # 内联数据（避免跨文件加载 / 404）
    inline = json.dumps(projects, ensure_ascii=False)
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
  .leaflet-popup-content { font-size: 13px; line-height: 1.6; }
  .leaflet-popup-content b { color: #0b3d91; }
  .pill { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 11px; margin-left: 6px; }
  .pill.official { background: #0b3d91; color: #fff; }
  .pill.media { background: #e8eefc; color: #0b3d91; }
  /* 项目标记：醒目，放大地图时点放大 */
  .proj-halo { color: #fff; opacity: .55; }
  .proj-dot { color: #0b3d91; }
  .proj-label { background: rgba(11,61,145,.85); color:#fff; border:none; border-radius:4px;
                padding:1px 5px; font-size:11px; font-weight:600; white-space:nowrap;
                box-shadow:0 1px 3px rgba(0,0,0,.3); }
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

// 半径随缩放放大：zoom 越大点越大（修复“放大后点变小”的观感）
function dotRadius(zoom, news) {
  var base = 5 + (zoom - 5) * 1.1;          // 5级≈5px，每升一级+1.1px
  if (base < 4) base = 4;
  return base + Math.min(news || 0, 12) * 0.9; // 新闻多→更大
}
function haloRadius(zoom, news) { return dotRadius(zoom, news) * 1.9; }

var markers = [];
PROJECTS.forEach(function(p) {
  var color = p.verified ? '#0b3d91' : '#e9533b';
  var z0 = map.getZoom();
  // 外层白色光晕（提升在复杂地图底图上的辨识度）
  var halo = L.circleMarker([p.latitude, p.longitude], {
    radius: haloRadius(z0, p.news_count), color: '#fff', weight: 2,
    fillColor: '#fff', fillOpacity: 0.6, className: 'proj-halo'
  }).addTo(map);
  var dot = L.circleMarker([p.latitude, p.longitude], {
    radius: dotRadius(z0, p.news_count), color: color, weight: 2,
    fillColor: color, fillOpacity: 0.9, className: 'proj-dot'
  }).addTo(map);
  var badge = p.verified
    ? '<span class="pill official">官方</span>'
    : '<span class="pill media">媒体</span>';
  var html = '<b>' + p.name + '</b>' + badge + '<br>' +
    '开发商: ' + (p.developer || '-') + '<br>' +
    '类型: ' + (p.category || '-') + ' ／ 状态: ' + (p.status || '-') + '<br>' +
    '地区: ' + [p.prefecture, p.city, p.district].filter(Boolean).join(' ') + '<br>' +
    '相关新闻: ' + (p.news_count || 0) + ' 篇<br>' +
    '首次: ' + (p.first_seen || '-') + ' ／ 更新: ' + (p.last_updated || '-');
  dot.bindPopup(html);
  halo.bindPopup(html);
  // 悬停显示项目名标签
  var label = L.tooltip({
    permanent: false, direction: 'top', className: 'proj-label', opacity: 1
  }).setContent(p.name);
  dot.bindTooltip(label);
  markers.push({ halo: halo, dot: dot, news: p.news_count });
});

// 缩放时重算所有点大小，保持“放大→点变大”
function rescale() {
  var z = map.getZoom();
  markers.forEach(function(m) {
    m.dot.setRadius(dotRadius(z, m.news));
    m.halo.setRadius(haloRadius(z, m.news));
  });
}
map.on('zoomend', rescale);
rescale();

// 缩放提示
var hint = L.control({ position: 'bottomright' });
hint.onAdd = function() { var d = L.DomUtil.create('div'); d.id = 'zoomhint';
  d.innerHTML = '🔍 滚轮放大 · 点越大'; return d; };
hint.addTo(map);
</script>
</body>
</html>
'''.replace('__DATA__', inline).replace('__CENTER__', '%s, %s' % (center[0], center[1])).replace('__ZOOM__', str(zoom)).replace('__COUNT__', str(len(projects))).replace('__BOUNDS__', bounds)


def main():
    html = build_html()
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('[OK] 地图页已生成: map.html (%d 个已定位项目)' % len(
        [p for p in load_projects().get('projects', []) if p.get('latitude')]))


if __name__ == '__main__':
    main()
