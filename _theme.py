# -*- coding: utf-8 -*-
"""平台页（项目库 / 项目地图 / 租金地图）共用的视觉主题。

与主页 index.html 同一套设计令牌（方案2「明亮清爽」+ 深色模式），
各 builder 只需：
    import _theme
    css  = _theme.TOKENS + 页面自己的 CSS + _theme.RESKIN_xxx
    body = _theme.nav_html(title, sub, actions) + ...
    js   = _theme.NAV_JS
"""

# ── 设计令牌 + 导航栏 + 通用按钮 + 深色模式 ────────────────────────────────
TOKENS = """
:root{
  --paper:#f4f8fe; --surface:#ffffff;
  --ink:#0c1d33; --ink-2:#2a4160; --ink-3:#526a86; --ink-4:#7d90a8;
  --line:#dde8f6; --line-2:#bcd2ea;
  --accent:#1668dc; --accent-2:#3b8ef0; --accent-deep:#0d4ea8;
  --up:#d13b30; --down:#0f8a5f;
  --r:18px; --r-sm:12px;
  --shadow:0 2px 6px rgba(13,78,168,.05), 0 14px 34px rgba(13,78,168,.08);
  --shadow-sm:0 1px 3px rgba(13,78,168,.05), 0 6px 16px rgba(13,78,168,.05);
  --toph:56px;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif;
}
html.theme-dark{
  --paper:#08182c; --surface:#102539;
  --ink:#e9f1fb; --ink-2:#b7c9df; --ink-3:#8ba2bd; --ink-4:#6f87a3;
  --line:#1d3a5c; --line-2:#2c4a70;
  --accent:#5aa5f2; --accent-2:#7cbbf7; --accent-deep:#9ccdf9;
  --up:#f2685e; --down:#3ecf9a;
  --shadow:0 2px 6px rgba(0,0,0,.3), 0 16px 40px rgba(0,0,0,.38);
  --shadow-sm:0 1px 3px rgba(0,0,0,.28), 0 8px 22px rgba(0,0,0,.3);
  color-scheme:dark;
}
/* ===== 顶栏（与主页同构：白底 + 细线 + 药丸按钮） ===== */
.nav{ position:sticky; top:0; z-index:1500; background:var(--surface); border-bottom:1px solid var(--line); }
.nav-row{ display:flex; align-items:center; gap:12px; padding:9px 18px; min-height:56px; }
.nav-row.filters{ padding:0 18px 11px; flex-wrap:wrap; gap:8px; min-height:0; }
.nav .brand{ display:flex; align-items:center; gap:12px; min-width:0; }
.nav .mark{ font-family:var(--sans); font-size:15px; font-weight:800; letter-spacing:5px;
  color:var(--accent-deep); flex:0 0 auto; }
.nav .titles{ min-width:0; }
.nav h1{ font-size:16px; font-weight:800; color:var(--ink); margin:0; line-height:1.25;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.nav .sub{ display:block; font-size:11px; color:var(--ink-4); margin-top:2px;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.nav .actions{ margin-left:auto; display:flex; align-items:center; gap:8px; flex:0 0 auto; }
.pill-btn{ background:#eef4fd; border:1px solid var(--line-2); color:var(--accent-deep);
  font-family:inherit; font-size:12px; font-weight:800; line-height:1.2; padding:7px 14px;
  border-radius:999px; cursor:pointer; text-decoration:none; white-space:nowrap;
  display:inline-flex; align-items:center; gap:6px;
  transition:background .15s, border-color .15s, color .15s; }
.pill-btn:hover{ background:#e2ecfa; border-color:var(--accent-2); }
.pill-btn.on{ background:var(--accent); border-color:var(--accent); color:#fff; }
.pill-btn .cnt{ opacity:.7; font-size:11px; }
html.theme-dark .pill-btn{ background:#17334f; border-color:#25507a; color:var(--accent-deep); }
html.theme-dark .pill-btn:hover{ background:#1c3d5e; }
html.theme-dark .pill-btn.on{ background:var(--accent); border-color:var(--accent); color:#04121f; }
html.theme-dark .pill-btn.on .cnt{ opacity:.65; }
html.theme-dark .leaflet-layer,
html.theme-dark .leaflet-tile-pane{ filter:brightness(.72) saturate(.85); }
@media (max-width:640px){
  .nav-row{ padding:8px 12px; min-height:50px; gap:8px; }
  .nav-row.filters{ padding:0 12px 9px; }
  .nav h1{ font-size:14px; }
  .nav .sub{ display:none; }
  .nav .mark{ font-size:13px; letter-spacing:3px; }
  .pill-btn{ padding:6px 11px; font-size:11.5px; }
}
"""

# ── 通用脚本：深浅色 + 顶栏高度测量 ────────────────────────────────────────
NAV_JS = """
<script>
/* ===== 深浅色（与主页共用 localStorage 键 taisei_theme） ===== */
function applyTheme(mode){
  var dark = (mode === 'dark');
  document.documentElement.classList.toggle('theme-dark', dark);
  var b = document.getElementById('themeBtn');
  if (b) b.textContent = dark ? '亮色' : '暗色';
  try { localStorage.setItem('taisei_theme', dark ? 'dark' : 'light'); } catch(e){}
}
function toggleTheme(){
  applyTheme(document.documentElement.classList.contains('theme-dark') ? 'light' : 'dark');
}
function syncNavH(){
  var n = document.querySelector('.nav');
  if (n) document.documentElement.style.setProperty('--toph', n.offsetHeight + 'px');
}
(function(){
  var t = null;
  try { t = localStorage.getItem('taisei_theme'); } catch(e){}
  if (!t) t = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  applyTheme(t);
  syncNavH();
  window.addEventListener('resize', syncNavH);
  window.addEventListener('load', syncNavH);
})();
</script>
"""


def nav_html(title, sub='', actions='', extra=''):
    """统一顶栏。actions 为页面自有按钮（如 一覧 / 列表·地図），返回主页与主题按钮自动带上。"""
    sub_html = ('<span class="sub">%s</span>' % sub) if sub else ''
    return (
        '<header class="nav">'
        '<div class="nav-row">'
        '<div class="brand">'
        '<span class="mark">TAISEI</span>'
        '<span class="titles"><h1>%s</h1>%s</span>'
        '</div>'
        '<div class="actions">%s'
        '<a class="pill-btn" href="index.html">返回主页</a>'
        '<button type="button" class="pill-btn" id="themeBtn" onclick="toggleTheme()">暗色</button>'
        '</div>'
        '</div>'
        '%s'
        '</header>'
    ) % (title, sub_html, actions, extra)


# ── 项目地图页（map.html）的覆盖层 ─────────────────────────────────────────
RESKIN_MAP = """
body{ background:var(--paper); color:var(--ink); font-family:var(--sans); }
#map{ height:calc(100vh - var(--toph, 56px)); }
#empty{ color:var(--ink-4); }
#legend{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
  padding:11px 13px; box-shadow:var(--shadow); color:var(--ink); }
#legend .lt{ color:var(--ink-3); font-weight:800; cursor:pointer; display:flex;
  align-items:center; justify-content:space-between; gap:8px; }
#legend .lt .caret{ font-size:9px; opacity:.6; transition:transform .15s; }
#legend.collapsed .lt .caret{ transform:rotate(-90deg); }
#legend.collapsed #legendTiers, #legend.collapsed .note{ display:none; }
#legend .note{ color:var(--ink-4); }
#zoomhint{ background:rgba(12,29,51,.72); border-radius:999px; padding:6px 12px; font-weight:600; }
.leaflet-popup-content-wrapper{ border-radius:14px; box-shadow:var(--shadow); }
.leaflet-popup-content b{ color:var(--accent-deep); }
.leaflet-popup-content a{ color:var(--accent); }
.proj-label{ background:var(--surface); color:var(--accent-deep); border:1px solid var(--line-2);
  border-radius:8px; padding:3px 9px; font-size:11px; font-weight:700; box-shadow:var(--shadow-sm); }
html.theme-dark .leaflet-popup-content-wrapper,
html.theme-dark .leaflet-popup-tip{ background:#132b45; color:var(--ink); }
html.theme-dark .leaflet-container{ background:#0b1a2e; }
"""

# ── 项目库（projects.html）的覆盖层 ────────────────────────────────────────
RESKIN_PROJECTS = """
body{ background:var(--paper); color:var(--ink); font-family:var(--sans); }
#filters{ background:var(--surface); border-bottom:1px solid var(--line); padding:10px 18px;
  gap:8px; top:var(--toph, 56px); }
#search{ background:var(--paper); border:1px solid var(--line-2); border-radius:999px;
  padding:9px 14px; font-size:13px; color:var(--ink); }
#search:focus{ outline:none; border-color:var(--accent-2); background:var(--surface); }
.chip{ border:1px solid var(--line-2); background:var(--surface); color:var(--ink-3);
  border-radius:999px; padding:6px 13px; font-size:12px; font-weight:700; }
.chip:hover{ border-color:var(--accent-2); color:var(--accent-deep); }
.chip.on{ background:var(--accent); color:#fff; border-color:var(--accent); }
#customRange{ color:var(--ink-3); }
#customRange input{ background:var(--paper); border:1px solid var(--line-2); border-radius:8px;
  color:var(--ink); padding:5px 7px; }
.right-sel{ margin-left:auto; display:inline-flex; align-items:center; gap:10px; flex-wrap:wrap; }
.group-sel{ color:var(--ink-3); display:inline-flex; align-items:center; gap:6px; white-space:nowrap; }
.group-sel select{ background:var(--surface); border:1px solid var(--line-2); border-radius:999px;
  color:var(--ink); padding:6px 10px; cursor:pointer; }
#list{ padding:16px 18px 40px; }
.group-title{ color:var(--accent-deep); font-size:14px; font-weight:800; letter-spacing:.5px; }
.card{ background:var(--surface); border:1px solid var(--line); border-radius:var(--r);
  box-shadow:var(--shadow-sm); padding:16px; }
.card:hover{ box-shadow:var(--shadow); transform:translateY(-2px); border-color:var(--line-2); }
.card h3{ color:var(--ink); font-weight:800; }
.card .meta{ color:var(--ink-3); }
.pill{ border-radius:999px; padding:2px 9px; font-weight:700; }
.pill.cat{ background:#eaf2fe; color:var(--accent-deep); }
#empty{ color:var(--ink-4); }
.pill-btn.only-mobile{ display:none; }
.nav .sub #count{ color:var(--ink-3); font-weight:800; }
#map{ height:calc(100vh - var(--toph, 56px) - var(--filtersh, 58px)); }
#maplegend{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
  box-shadow:var(--shadow); color:var(--ink); }
#detail{ background:rgba(8,24,44,.5); backdrop-filter:blur(3px); }
.sheet{ background:var(--surface); border-radius:22px 22px 0 0; box-shadow:0 -20px 50px rgba(8,24,44,.28);
  padding:20px 20px 30px; }
.sheet .close{ background:#eef4fd; color:var(--ink-3); border-radius:999px; width:32px; height:32px;
  font-size:17px; line-height:1; padding:0; }
.sheet h2{ color:var(--ink); font-weight:800; }
.sheet .info{ color:var(--ink-2); border-bottom:1px solid var(--line); }
.sheet h4{ color:var(--accent-deep); font-weight:800; }
.tl{ border-left:2px solid var(--line-2); }
.tl-date,.tl-src{ color:var(--ink-4); }
.tl-title{ color:var(--ink); }
.tl-sum{ color:var(--ink-2); }
.pf-search .pagefind-ui{ --pagefind-ui-primary:#0d4ea8; --pagefind-ui-text:#0c1d33;
  --pagefind-ui-background:#ffffff; --pagefind-ui-border:#dde8f6; --pagefind-ui-tag:#eef4fd; }
html.theme-dark .pf-search .pagefind-ui{ --pagefind-ui-primary:#9ccdf9; --pagefind-ui-text:#e9f1fb;
  --pagefind-ui-background:#102539; --pagefind-ui-border:#1d3a5c; --pagefind-ui-tag:#17334f; }
html.theme-dark .leaflet-popup-content-wrapper,
html.theme-dark .leaflet-popup-tip{ background:#132b45; color:var(--ink); }
html.theme-dark .leaflet-container{ background:#0b1a2e; }
html.theme-dark .proj-label{ background:#17334f; color:var(--accent-deep); border-color:#25507a; }
/* 手机：顶栏拆两行（标题一行 / 按钮一行，按钮可横向滚动），筛选条可收起 */
@media (max-width:640px){
  .nav-row{ flex-wrap:wrap; row-gap:8px; padding:8px 12px 9px; min-height:0; }
  .nav .brand{ flex:1 1 100%; }
  .nav h1{ font-size:14px; white-space:normal; overflow:visible; text-overflow:clip; }
  .nav .actions{ flex:1 1 100%; margin-left:0; gap:6px; overflow-x:auto;
    padding-bottom:2px; scrollbar-width:none; }
  .nav .actions::-webkit-scrollbar{ display:none; }
  #filters{ padding:9px 12px; gap:7px; }
  #filters.collapsed #catChips, #filters.collapsed #prefChips, #filters.collapsed #timeChips,
  #filters.collapsed #customRange, #filters.collapsed .group-sel,
  #filters.collapsed .right-sel{ display:none; }
  .right-sel{ flex:1 1 100%; margin-left:0; justify-content:flex-end; gap:8px; }
  .group-sel select{ padding:5px 9px; font-size:12px; }
  .chip-row{ display:flex; flex-wrap:nowrap; overflow-x:auto; width:100%; gap:6px;
    scrollbar-width:none; }
  .chip-row::-webkit-scrollbar{ display:none; }
  .chip{ flex:0 0 auto; }
  #customRange{ flex:1 1 100%; }
  .pill-btn.only-mobile{ display:inline-flex; }
}
html.theme-dark .pill.cat{ background:#17334f; color:var(--accent-deep); }
html.theme-dark .sheet .close{ background:#17334f; color:var(--accent-deep); }
"""

# ── 租金地图（rentmap.html）的覆盖层 ──────────────────────────────────────
RESKIN_RENTMAP = """
body{ background:var(--paper); color:var(--ink); font-family:var(--sans); }
#pfilt{ display:flex; gap:8px; flex-wrap:wrap; flex:1 1 auto; margin:0; }
#pfilt button{ background:#eef4fd; color:var(--ink-3); border:1px solid var(--line-2);
  border-radius:999px; padding:5px 13px; font-size:12px; font-weight:700; }
#pfilt button:hover{ border-color:var(--accent-2); color:var(--accent-deep); }
#pfilt button.on{ background:var(--accent); color:#fff; border-color:var(--accent); }
#map{ height:calc(100vh - var(--toph, 100px)); }
#legend{ background:var(--surface); border:1px solid var(--line); border-radius:16px;
  box-shadow:var(--shadow); color:var(--ink); }
#legend .lt{ color:var(--ink-3); font-weight:800; }
#legend .lt{ cursor:pointer; display:flex; align-items:center; justify-content:space-between; gap:8px; }
#legend .lt .caret{ font-size:9px; opacity:.6; transition:transform .15s; }
#legend.collapsed .lt .caret{ transform:rotate(-90deg); }
#legend.collapsed #legendTiers, #legend.collapsed .note{ display:none; }
#legend .tr{ color:var(--ink-4); }
#legend .note{ color:var(--ink-4); }
#list{ background:var(--paper); box-shadow:-6px 0 24px rgba(13,78,168,.10); padding:0 12px 24px; }
#list .list-head{ background:var(--paper); border-bottom:1px solid var(--line); }
#list .lh-t{ color:var(--ink); }
#list .list-head .handle{ display:none; }
#list .lh-close{ background:var(--surface); border:1px solid var(--line-2); color:var(--ink-3);
  border-radius:999px; width:30px; height:30px; font-size:15px; }
#list .lh-close:hover{ border-color:var(--accent-2); color:var(--accent-deep); }
#list .lrow{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
  box-shadow:var(--shadow-sm); transition:box-shadow .15s, transform .15s, border-color .15s; }
#list .lrow:hover{ box-shadow:var(--shadow); border-color:var(--accent-2); transform:translateY(-1px); }
#list .lrow:active{ background:#eaf2fe; }
#list .lrank{ background:#eaf2fe; color:var(--accent-deep); font-weight:800; }
#list .lname{ color:var(--ink); }
#list .lname small{ color:var(--ink-4) !important; }
#list .lval{ color:var(--accent-deep); }
#list .lval small{ color:var(--ink-4); }
.proj-label{ background:var(--surface); color:var(--accent-deep); border:1px solid var(--line-2);
  border-radius:8px; padding:3px 9px; font-size:11px; font-weight:700; box-shadow:var(--shadow-sm); }
/* ===== 详情卡片（重做） ===== */
#panel{ top:var(--toph, 100px); bottom:0; height:auto; background:var(--surface); border-radius:22px 0 0 22px; box-shadow:-18px 0 50px rgba(8,24,44,.18);
  padding:0 0 26px; width:400px; max-width:94vw; }
#panel .ph{ background:linear-gradient(120deg,var(--accent-deep),var(--accent) 60%,var(--accent-2));
  color:#fff; padding:18px 20px 16px; border-radius:22px 0 0 0; }
#panel .ph .close{ width:30px; height:30px; border-radius:999px; background:rgba(255,255,255,.18);
  color:#fff; font-size:17px; line-height:1; display:flex; align-items:center; justify-content:center; }
#panel .ph .close:hover{ background:rgba(255,255,255,.32); }
#panel .ph .nm{ font-size:21px; font-weight:800; letter-spacing:.3px; padding-right:38px; }
#panel .ph .rk{ font-size:12px; opacity:.9; margin-top:4px; }
#panel .body{ padding:16px 20px 4px; }
.rc-main{ font-size:34px; font-weight:800; color:var(--ink); letter-spacing:-.5px; line-height:1.15; }
.rc-main small{ display:block; font-size:12px; font-weight:600; color:var(--ink-4); margin:6px 0 0; letter-spacing:0; }
.rc-units{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:14px 0 12px; }
.rc-units .u{ background:var(--paper); border:1px solid var(--line); border-radius:14px; padding:12px 13px; }
.rc-units .u .num{ font-size:17px; font-weight:800; color:var(--ink); }
.rc-units .u .lab{ display:block; font-size:10.5px; color:var(--ink-4); margin-top:4px; line-height:1.45; }
.rc-chips{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 12px; }
.rc-chips .chip{ font-size:12px; padding:5px 12px; border-radius:999px; font-weight:800; border:0; }
.rc-chips .up{ background:#eaf2fe; color:var(--accent-deep); }
.rc-chips .down{ background:#e6f6ef; color:var(--down); }
.rc-sub{ background:#eaf2fe; border:0; border-left:3px solid var(--accent); border-radius:12px;
  padding:11px 13px; margin:10px 0; font-size:12px; color:var(--ink-2); line-height:1.7; }
.rc-sub b{ color:var(--accent-deep); }
.rc-sub .mom{ margin-left:8px; font-weight:800; font-size:12px; }
.rc-sub .mom.up{ color:#c62f28; }
.rc-sub .mom.down{ color:#0f8a5f; }
html.theme-dark .rc-sub .mom.up{ color:#f2685e; }
html.theme-dark .rc-sub .mom.down{ color:#3ecf9a; }
.rc-spark{ background:var(--paper); border:1px solid var(--line); border-radius:14px; padding:12px 13px; margin:10px 0; }
.rc-spark .t{ font-size:11px; font-weight:700; color:var(--ink-3); margin-bottom:8px; }
.rc-yield{ background:var(--paper); border:1px solid var(--line); border-radius:14px;
  padding:13px 15px; margin:12px 0; font-size:15px; font-weight:800; color:var(--ink); }
.rc-yield small{ display:block; font-size:10.5px; font-weight:600; color:var(--ink-4);
  margin-top:5px; line-height:1.55; }
.rc-link{ margin:14px 0 10px; }
.rc-link a{ display:block; text-align:center; padding:12px 14px; border-radius:999px;
  background:linear-gradient(100deg,var(--accent),var(--accent-2)); color:#fff;
  text-decoration:none; font-size:13px; font-weight:800; letter-spacing:.5px;
  box-shadow:0 10px 24px rgba(22,104,220,.22); }
.rc-link a.none{ background:var(--paper); color:var(--ink-4); box-shadow:none; border:1px dashed var(--line-2); }
.rc-src{ font-size:10.5px; color:var(--ink-4); line-height:1.7; border-top:1px solid var(--line);
  padding-top:12px; margin-top:12px; }
html.theme-dark .rc-chips .down{ background:#123f33; color:var(--down); }
html.theme-dark #list .lrank{ background:#17334f; color:var(--accent-deep); }
html.theme-dark #list .lrow:active{ background:#17334f; }
html.theme-dark .rc-chips .up{ background:#17334f; color:var(--accent-deep); }
html.theme-dark .rc-sub{ background:#17334f; border-left-color:var(--accent); }
html.theme-dark .rc-sub b{ color:var(--accent-deep); }
html.theme-dark .rc-link a{ box-shadow:none; }
html.theme-dark .leaflet-container{ background:#0b1a2e; }
/* 手机：列表=底部抽屉（默认露出 44vh，可上拉到 86vh），详情=底部卡片（最高 62vh，上方仍看得到地图） */
@media (max-width:640px){
  #map{ height:calc(100vh - var(--toph, 100px)); }
  body.list-open #map{ height:calc(100vh - var(--toph, 100px) - 44vh); width:100%; }
  #list{ top:auto; left:0; right:0; bottom:0; width:100%; max-width:100%;
    height:44vh; border-radius:20px 20px 0 0; padding:0 12px 14px;
    box-shadow:0 -14px 40px rgba(8,24,44,.22); transition:height .22s ease; }
  #list.expanded{ height:86vh; }
  #list .list-head{ padding:7px 14px 10px; margin:0 -12px; border-radius:20px 20px 0 0;
    cursor:grab; touch-action:none; }
  #list .list-head .handle{ display:block; width:38px; height:4px; border-radius:999px;
    background:var(--line-2); margin:0 auto 9px; }
  #list .lh-t{ font-size:13px; }
  #panel{ top:auto; bottom:0; left:0; right:0; width:100%; max-width:100%;
    height:62vh; max-height:62vh; overflow-y:auto; border-radius:20px 20px 0 0;
    transform:translateY(105%); box-shadow:0 -18px 50px rgba(8,24,44,.3); }
  #panel.show{ transform:translateY(0); }
  /* mini：只显示「名称 + 价格」，其余内容收起；点蓝色标题栏或上拉展开 */
  #panel.mini{ height:auto; overflow:hidden; }
  #panel.mini .rc-units,
  #panel.mini .rc-chips,
  #panel.mini .rc-sub,
  #panel.mini .rc-spark,
  #panel.mini .rc-yield,
  #panel.mini .rc-link,
  #panel.mini .rc-src{ display:none; }
  #panel .ph{ cursor:grab; touch-action:none; }
  #panel.mini .ph::after{ content:'\25B4'; position:absolute; right:44px; bottom:13px;
    font-size:12px; opacity:.75; }
  #panel .ph{ border-radius:20px 20px 0 0; padding:22px 18px 14px; position:relative; }
  #panel .ph::before{ content:''; position:absolute; top:8px; left:50%; transform:translateX(-50%);
    width:38px; height:4px; border-radius:999px; background:rgba(255,255,255,.55); }
  #panel .ph .nm{ font-size:19px; padding-right:34px; }
  #panel .body{ padding:14px 18px 4px; }
  .rc-main{ font-size:29px; }
  .rc-units{ gap:8px; }
  .rc-units .u{ padding:10px 11px; }
  #legend{ top:calc(var(--toph, 100px) + 10px); bottom:auto; left:10px; right:auto;
    max-width:172px; font-size:10px; padding:8px 10px; border-radius:12px; }
}
"""
