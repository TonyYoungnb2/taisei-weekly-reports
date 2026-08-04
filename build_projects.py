#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_projects.py — 生成房地产情报平台主界面（Phase 1）。
纯静态：data/projects.json + data/news/**/*.json 内联进 HTML，本地 vendor Leaflet + GSI 瓦片。
零后端、零 CDN 外链、国内/微信可开。
功能：Project List(Dashboard) / List-Map 视图切换 / 筛选 / 按企业·按地区分组 / 项目详情(新闻时间轴) / 新闻详情。
用法: python build_projects.py  -> 写入 projects.html
"""
import io, os, json, glob, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, 'data', 'projects.json')
NEWS_DIR = os.path.join(BASE, 'data', 'news')
OUT = os.path.join(BASE, 'projects.html')


def load_projects():
    return json.load(io.open(PROJ, encoding='utf-8')).get('projects', [])


def load_news():
    news = []
    for fp in glob.glob(os.path.join(NEWS_DIR, '**', '*.json'), recursive=True):
        if os.path.basename(fp) == 'projects.json':
            continue
        try:
            nd = json.load(io.open(fp, encoding='utf-8'))
        except Exception:
            continue
        for n in nd.get('news', []):
            news.append(n)
    return news


def build_html():
    projects = load_projects()
    news = load_news()
    # 真实新闻数（覆盖可能陈旧的 stored 值）
    counts = {}
    for n in news:
        counts[n.get('project_id')] = counts.get(n.get('project_id'), 0) + 1
    for p in projects:
        p = dict(p)
        p['news_count'] = counts.get(p['id'], p.get('news_count', 0))
    proj_inline = json.dumps(projects, ensure_ascii=False)
    news_inline = json.dumps(news, ensure_ascii=False)

    lats = [p['latitude'] for p in projects if p.get('latitude')]
    lngs = [p['longitude'] for p in projects if p.get('longitude')]
    if lats:
        center = [sum(lats) / len(lats), sum(lngs) / len(lngs)]
        zoom = 5
    else:
        center = [36.5, 138.5]
        zoom = 5

    return '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>大誠 · 東京不動産プロジェクト一覧</title>
<link rel="stylesheet" href="vendor/leaflet/leaflet.css">
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f4f6fb; color: #1a2233; }
  #top { position: sticky; top: 0; z-index: 1100; background: #0b3d91; color: #fff;
    padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; }
  #top h1 { font-size: 17px; margin: 0; font-weight: 600; }
  #top .count { font-size: 12px; opacity: .85; margin-left: 8px; }
  .view-switch { display: flex; gap: 6px; }
  .view-switch button { background: rgba(255,255,255,.15); color: #fff; border: 0; border-radius: 8px;
    padding: 6px 12px; font-size: 13px; cursor: pointer; }
  .view-switch button.on { background: #fff; color: #0b3d91; font-weight: 600; }
  #filters { background: #fff; padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
    border-bottom: 1px solid #e3e8f2; position: sticky; top: 52px; z-index: 1000; }
  #search { flex: 1 1 200px; min-width: 0; padding: 8px 10px; border: 1px solid #d3dbe8; border-radius: 8px; font-size: 13px; }
  .chip { border: 1px solid #cfd8e8; background: #fff; color: #3a4a66; border-radius: 16px; padding: 5px 12px;
    font-size: 12px; cursor: pointer; white-space: nowrap; }
  .chip.on { background: #0b3d91; color: #fff; border-color: #0b3d91; }
  .group-sel { margin-left: auto; font-size: 12px; color: #5a6a85; }
  .group-sel select { border: 1px solid #cfd8e8; border-radius: 8px; padding: 5px 8px; font-size: 12px; }
  #list { padding: 14px 16px; }
  .group-title { font-size: 14px; font-weight: 700; color: #0b3d91; margin: 16px 0 10px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(0, 1fr)); gap: 12px; }
  @media (min-width: 640px) { .grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); } }
  .card { background: #fff; border: 1px solid #e3e8f2; border-radius: 12px; padding: 14px; cursor: pointer;
    min-width: 0; overflow: hidden; transition: box-shadow .15s; }
  .card:hover { box-shadow: 0 4px 16px rgba(11,61,145,.12); }
  .card h3 { margin: 0 0 8px; font-size: 15px; line-height: 1.4; word-break: break-word; }
  .card .meta { font-size: 12px; color: #5a6a85; line-height: 1.7; word-break: break-word; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; margin-right: 6px; }
  #srcChips { display: none; }
  .pill.cat { background: #eef1f7; color: #46546e; }
  .st-done { border-color:#1f9d55 !important; background:rgba(31,157,85,.2); }
  .st-dev  { border-color:#0b3d91 !important; background:rgba(11,61,145,.2); }
  .st-plan { border-color:#8a96ac !important; background:rgba(138,150,172,.2); }
  .proj-label { background: rgba(11,61,145,.85); color:#fff; border:none; border-radius:4px;
                padding:1px 5px; font-size:11px; font-weight:600; white-space:nowrap;
                box-shadow:0 1px 3px rgba(0,0,0,.3); }
  .proj-label::before { display:none; }
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

  

  #map { display: none; height: calc(100vh - 104px); width: 100%; }
  #maplegend { position:absolute; left:10px; bottom:10px; z-index:1100; background:rgba(255,255,255,.92);
    border:1px solid #e3e8f2; border-radius:8px; padding:8px 10px; font-size:11px; line-height:1.8; color:#1a2233;
    box-shadow:0 2px 8px rgba(0,0,0,.12); }
  #maplegend .row { display:flex; align-items:center; gap:6px; }
  #maplegend .dot { width:11px; height:11px; border-radius:50%; display:inline-block; border:2px solid; box-sizing:border-box; }
  #maplegend .d-done { border-color:#1f9d55; background:rgba(31,157,85,.2); }
  #maplegend .d-dev  { border-color:#0b3d91; background:rgba(11,61,145,.2); }
  #maplegend .d-plan { border-color:#8a96ac; background:rgba(138,150,172,.2); }
  #maplegend .d-news { border-color:#e9533b; background:rgba(233,83,59,.25); }
  #empty { text-align: center; color: #9aa5b8; padding: 40px 0; font-size: 14px; }
  /* 详情抽屉 */
  #detail { position: fixed; inset: 0; background: rgba(20,30,50,.45); z-index: 2000; display: none;
    align-items: flex-end; justify-content: center; }
  #detail.show { display: flex; }
  .sheet { background: #fff; width: 100%; max-width: 680px; max-height: 88vh; overflow-y: auto;
    border-radius: 16px 16px 0 0; padding: 18px 18px 28px; }
  .sheet .close { float: right; cursor: pointer; font-size: 22px; color: #99a; border: 0; background: none; }
  .sheet h2 { margin: 0 0 10px; font-size: 18px; line-height: 1.4; padding-right: 30px; word-break: break-word; }
  .sheet .info { font-size: 13px; color: #46546e; line-height: 1.9; border-bottom: 1px solid #eef1f7; padding-bottom: 12px; }
  .sheet h4 { font-size: 14px; color: #0b3d91; margin: 16px 0 8px; }
  .tl { border-left: 2px solid #d3dcef; margin-left: 6px; padding-left: 14px; }
  .tl-item { margin-bottom: 14px; }
  .tl-date { font-size: 11px; color: #8a96ac; }
  .tl-title { font-size: 14px; font-weight: 600; cursor: pointer; word-break: break-word; }
  .tl-src { font-size: 11px; color: #8a96ac; }
  .tl-sum { font-size: 13px; color: #46546e; margin-top: 4px; display: none; word-break: break-word; }
  .tl-sum.open { display: block; }
  .tl-link { font-size: 12px; color: #0b3d91; text-decoration: none; }
  @media (max-width: 640px) {
    .grid { grid-template-columns: minmax(0, 1fr); gap: 10px; }
    .card { padding: 12px; }
    .sheet { border-radius: 14px 14px 0 0; }
    #search { flex: 1 1 100%; }
  }
</style>
</head>
<body>
<div id="top">
  <div><h1>大誠 · 不動産プロジェクト</h1><span class="count" id="count"></span></div>
  <div class="view-switch">
    <button id="btnList" class="on" onclick="setView('list')">列表</button>
    <button id="btnMap" onclick="setView('map')">地図</button>
  </div>
</div>
<div id="filters">
  <input id="search" placeholder="検索：プロジェクト名・企業・地区…">
  <span id="catChips" class="chip-row"></span>
  <span id="prefChips" class="chip-row"></span>
  <span id="srcChips" class="chip-row"></span>
  <span class="group-sel">表示：
    <select id="groupSel" onchange="render()">
      <option value="none">一覧</option>
      <option value="dev">企業別</option>
      <option value="pref">地区別</option>
    </select>
  </span>
</div>
<div id="list"><div id="listBody"></div></div>
<div id="map"></div>

<div id="detail" onclick="if(event.target===this)closeDetail()">
  <div class="sheet" id="sheet"></div>
</div>

<script src="vendor/leaflet/leaflet.js"></script>
<script>
var PROJECTS = __DATA__;
var NEWS = __NEWS__;
var CENTER = __CENTER__;
var ZOOM = __ZOOM__;
var map = null, markers = {};

var state = { view: 'list', cat: 'all', pref: 'all', q: '', group: 'none' };

// 类别 / 地区 / 来源 选项
function uniq(arr){ return arr.filter(function(v,i){ return arr.indexOf(v)===i; }); }
var CATS = uniq(PROJECTS.map(function(p){ return p.category || '其他'; }));
var PREFS = uniq(PROJECTS.map(function(p){ return p.prefecture || '不明'; }));
function statusKey(p){ var s=(p.status||''); if(s==='完工')return 'done'; if(s==='规划')return 'plan'; return 'dev'; }

function buildChips(){
  var catHtml = '<span class="chip on" data-k="cat" data-v="all">全部类别</span>' +
    CATS.map(function(c){ return '<span class="chip" data-k="cat" data-v="'+c+'">'+c+'</span>'; }).join('');
  var prefHtml = '<span class="chip on" data-k="pref" data-v="all">全部地区</span>' +
    PREFS.map(function(c){ return '<span class="chip" data-k="pref" data-v="'+c+'">'+c+'</span>'; }).join('');
  var srcHtml = '<span class="chip on" data-k="src" data-v="all">全部来源</span>' +
    '<span class="chip" data-k="src" data-v="official">官方</span>' +
    '<span class="chip" data-k="src" data-v="media">媒体</span>';
  document.getElementById('catChips').innerHTML = catHtml;
  document.getElementById('prefChips').innerHTML = prefHtml;
  document.getElementById('srcChips').style.display = 'none';
  document.querySelectorAll('.chip').forEach(function(el){
    el.onclick = function(){
      var k = el.getAttribute('data-k');
      state[k] = el.getAttribute('data-v');
      document.querySelectorAll('.chip[data-k="'+k+'"]').forEach(function(x){ x.classList.remove('on'); });
      el.classList.add('on');
      render();
    };
  });
}

function filtered(){
  var q = state.q.trim().toLowerCase();
  return PROJECTS.filter(function(p){
    if (state.cat !== 'all' && (p.category||'其他') !== state.cat) return false;
    if (state.pref !== 'all' && (p.prefecture||'不明') !== state.pref) return false;
    if (q) {
      var hay = (p.name + ' ' + (p.developer||'') + ' ' + (p.prefecture||'') + ' ' + (p.city||'') + ' ' + (p.aliases||[]).join(' ')).toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    return true;
  });
}

function badge(p){ return ''; }
function card(p){
  var region = [p.prefecture, p.city, p.district].filter(Boolean).join(' ');
  var src = p.source_url ? ' <a href="'+p.source_url+'" target="_blank" rel="noopener" style="color:#0b3d91;text-decoration:none">［引用］</a>' : '';
  return '<div class="card" onclick="openDetail('+String.fromCharCode(39)+p.id+String.fromCharCode(39)+')">' +
    '<h3><span style="display:inline-block;width:9px;height:9px;border-radius:50%;border:2px solid;box-sizing:border-box;margin-right:6px;vertical-align:middle" class="st-'+statusKey(p)+'"></span>'+p.name+'</h3>' +
    '<div><span class="pill cat">'+(p.category||'其他')+'</span></div>' +
    '<div class="meta">開発：'+(p.developer||'-')+'<br>地区：'+region+'<br>状態：'+(p.status||'-')+' ｜ 関連ニュース：'+(p.news_count||0)+'件<br>引用：'+(p.source_name||'-')+src+'</div>' +
    '</div>';
}
function render(){
  var list = filtered();
  document.getElementById('count').textContent = '（'+list.length+' / '+PROJECTS.length+' 件）';
  // 列表
  var body = document.getElementById('listBody');
  if (!list.length) { body.innerHTML = '<div id="empty">該当するプロジェクトがありません</div>'; }
  else if (state.group === 'none') {
    body.innerHTML = '<div class="grid">'+list.map(card).join('')+'</div>';
  } else {
    var key = state.group === 'dev' ? 'developer' : 'prefecture';
    var groups = {};
    list.forEach(function(p){ var k = p[key]||'不明'; (groups[k]=groups[k]||[]).push(p); });
    body.innerHTML = Object.keys(groups).sort().map(function(g){
      return '<div class="group-title">'+g+'（'+groups[g].length+'）</div><div class="grid">'+groups[g].map(card).join('')+'</div>';
    }).join('');
  }
  // 地图
  if (map) { renderMap(list); }
}
function renderMap(list){
  Object.keys(markers).forEach(function(id){ map.removeLayer(markers[id].mk); delete markers[id]; });
  function dotR(z, news){ var b = 5 + (z-5)*1.1; if(b<4)b=4; return b + Math.min(news||0,12)*0.9; }
  function mkIcon(p, z){
    var r = dotR(z, p.news_count||0);
    var lbl = (p.news_count && p.news_count>0) ? String(p.news_count) : '';
    return L.divIcon({ className: 'proj-pin st-' + statusKey(p) + (lbl ? ' has-news' : ''),
      html: '<div style="width:'+(r*2)+'px;height:'+(r*2)+'px;display:flex;align-items:center;justify-content:center;font:800 '+Math.max(10,Math.round(r*0.95))+'px/1 sans-serif;color:#fff">'+lbl+'</div>',
      iconSize:[r*2,r*2], iconAnchor:[r,r] });
  }
  list.forEach(function(p){
    if (!p.latitude || !p.longitude) return;
    var z0 = map ? map.getZoom() : ZOOM;
    var mk = L.marker([p.latitude, p.longitude], { icon: mkIcon(p, z0) }).addTo(map);
    markers[p.id] = { mk: mk, news: p.news_count, p: p };
    var news = (NEWS||[]).filter(function(n){ return n.project_id === p.id; })
      .sort(function(a,b){ return (b.publish_date||'').localeCompare(a.publish_date||''); });
    var newsHtml = news.length ? news.slice(0,3).map(function(n){
      var link = n.url ? ' <a href="'+n.url+'" target="_blank" rel="noopener">['+(n.url_text||'リンク')+']</a>' : '';
      return '・'+n.title+link;
    }).join('<br>') : '関連ニュースなし';
    var srcLink = p.source_url ? ' <a href="'+p.source_url+'" target="_blank" rel="noopener">[リンク]</a>' : '';
    var pop = '<b>'+p.name+'</b><br>開発：'+(p.developer||'-')+'<br>状態：'+(p.status||'-')+
      '<br>引用：'+(p.source_name||'-')+srcLink+
      '<br>関連ニュース('+news.length+'件)：<br>'+newsHtml;
    mk.bindPopup(pop);
    mk.bindTooltip(L.tooltip({permanent:false, direction:'top', opacity:1, className:'proj-label'}).setContent(p.name));
    markers[p.id] = { mk: mk, news: p.news_count };
  });
  if (map) {
    map.off('zoomend', map._rescaleMap);
    map._rescaleMap = function(){
      var z = map.getZoom();
      Object.keys(markers).forEach(function(id){
        var r = markers[id];
        r.mk.setIcon(mkIcon({ news_count: r.news, status: r.p ? r.p.status : '' }, z));
      });
    };
    map.on('zoomend', map._rescaleMap);
  }
}
function setView(v){
  state.view = v;
  document.getElementById('btnList').classList.toggle('on', v==='list');
  document.getElementById('btnMap').classList.toggle('on', v==='map');
  document.getElementById('list').style.display = v==='list' ? 'block' : 'none';
  document.getElementById('map').style.display = v==='map' ? 'block' : 'none';
  if (v==='map') {
    if (!map) {
      map = L.map('map').setView(CENTER, ZOOM);
      L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', { attribution:'© 国土地理院', maxZoom:18 }).addTo(map);
      setTimeout(function(){ map.invalidateSize(); renderMap(filtered());
        if (!document.getElementById('maplegend')) {
          var lg = document.createElement('div'); lg.id = 'maplegend';
          lg.innerHTML = '<div class="row"><span class="dot d-done"></span>完工</div>' +
            '<div class="row"><span class="dot d-dev"></span>开发中</div>' +
            '<div class="row"><span class="dot d-plan"></span>规划</div>' +
            '<div class="row"><span class="dot d-news"></span>有新闻</div>';
          document.getElementById('map').parentNode.appendChild(lg);
        }
      }, 80);
    } else { setTimeout(function(){ map.invalidateSize(); }, 50); }
  }
}
function openDetail(id){
  var p = PROJECTS.find(function(x){ return x.id===id; });
  if (!p) return;
  var region = [p.prefecture, p.city, p.district].filter(Boolean).join(' ');
  var news = NEWS.filter(function(n){ return n.project_id===id; })
    .sort(function(a,b){ return (b.publish_date||'').localeCompare(a.publish_date||''); });
  var tl = news.map(function(n,i){
    var link = n.url ? ' <a class="tl-link" href="'+n.url+'" target="_blank" rel="noopener">['+(n.url_text||'リンク')+']</a>' : '';
    return '<div class="tl-item"><div class="tl-date">'+(n.publish_date||'')+'</div>'+
      '<div class="tl-title" onclick="toggleSum('+i+')">'+n.title+'</div>'+
      '<div class="tl-src">'+(n.source||'')+link+'</div>'+
      '<div class="tl-sum" id="sum'+i+'">'+(n.summary||'')+'</div></div>';
  }).join('') || '<div class="tl-src">関連ニュースなし</div>';
  document.getElementById('sheet').innerHTML =
    '<button class="close" onclick="closeDetail()">×</button>'+
    '<h2>'+p.name+'</h2>'+
    '<div class="info">企業：'+(p.developer||'-')+'<br>類別：'+(p.category||'-')+' ／ 状態：'+(p.status||'-')+
      '<br>地区：'+region+'<br>初見：'+(p.first_seen||'-')+' ／ 更新：'+(p.last_updated||'-')+
      '<br>引用：'+(p.source_name||'-')+(p.source_url ? ' <a class="tl-link" href="'+p.source_url+'" target="_blank" rel="noopener">[リンク]</a>' : '')+
      '</div>' +
    '<h4>関連ニュース（'+(news.length)+'件）</h4><div class="tl">'+tl+'</div>';
  document.getElementById('detail').classList.add('show');
}
function toggleSum(i){ document.getElementById('sum'+i).classList.toggle('open'); }
function closeDetail(){ document.getElementById('detail').classList.remove('show'); }

document.getElementById('search').addEventListener('input', function(e){ state.q = e.target.value; render(); });
buildChips();
render();
</script>
</body>
</html>
'''.replace('__DATA__', proj_inline).replace('__NEWS__', news_inline).replace('__CENTER__', str(center)).replace('__ZOOM__', str(zoom))


def main():
    html = build_html()
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('[OK] 平台主界面已生成: projects.html (%d 项目 / %d 新闻)' % (
        len(load_projects()), len(load_news())))


if __name__ == '__main__':
    main()
